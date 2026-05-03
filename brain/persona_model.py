"""
brain/persona_model.py - Sara v2 LoRA Fine-Tuner.

Fine-tunes TinyLlama-1.1B-Chat using LoRA on the user's private conversation
data collected by personal_trainer.py.

LoRA adapter saved to:  memory/data/<user_id>/sara_v2_adapter/
ALL data and weights stay 100% local -- you own Sara v2.

Optional deps (only needed for local training):
    pip install torch transformers peft datasets accelerate

Without deps, every function degrades gracefully with an install hint.

Public API:
  is_available()                               -> bool
  is_training(user_id)                         -> bool
  train_personal_model(user_id, callback=None) -> str
  inference(user_id, prompt)                   -> str | None
  get_adapter_info(user_id)                    -> dict
  delete_model(user_id)                        -> None
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MODEL_NAME         = "Sara v2"
BASE_MODEL_ID      = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
DATA_DIR           = os.path.join(os.path.dirname(__file__), "..", "memory", "data")
ADAPTER_DIR_NAME   = "sara_v2_adapter"
TRAINING_INFO_FILE = "sara_v2_info.json"

# ── LoRA config (stronger than v1) ────────────────────────────────────────────
LORA_R       = 16      # rank (was 8 — doubled for richer personalisation)
LORA_ALPHA   = 32      # always 2x rank
LORA_DROPOUT = 0.05
# Cover all attention + MLP projections for maximum expressiveness
LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",   # attention
    "gate_proj", "up_proj", "down_proj",        # FFN
]

# ── Training config ────────────────────────────────────────────────────────────
MAX_SEQ_LEN           = 768    # longer context than v1 (was 512)
TRAIN_EPOCHS          = 3
BATCH_SIZE            = 1
GRADIENT_ACCUMULATION = 8     # effective batch = 1x8 = 8
LEARNING_RATE         = 2e-4
WARMUP_RATIO          = 0.1   # 10% of steps = warmup
WEIGHT_DECAY          = 0.01

# ── Data mixing ────────────────────────────────────────────────────────────────
# Personal conversations are repeated this many times so Sara learns YOUR voice
# much more strongly than anything from the public datasets.
PERSONAL_DATA_WEIGHT  = 3

DEPS_MESSAGE = (
    "Sara v2 training requires additional packages.\n\n"
    "Install with:\n"
    "  pip install torch transformers peft datasets accelerate\n\n"
    "Then send /train again!"
)

_training_lock = threading.Lock()
_training_in_progress: set = set()
_loaded_pipelines: dict = {}

# ChatML special tokens built from parts (never appear as static literals)
_TOK_SYS  = "<" + "|system|>"
_TOK_USER = "<" + "|user|>"
_TOK_ASST = "<" + "|assistant|>"
_TOK_END  = "<" + "|end|>"
_TOK_CLOSE = "</s>"


# ── Paths ──────────────────────────────────────────────────────────────────────

def _user_dir(user_id: str) -> str:
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def _adapter_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), ADAPTER_DIR_NAME)


def _info_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), TRAINING_INFO_FILE)


def _jsonl_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), "training_data.jsonl")


# ── Dependency check ───────────────────────────────────────────────────────────

def is_available() -> bool:
    """Return True only if torch + transformers + peft are installed."""
    try:
        import torch          # noqa: F401
        import transformers   # noqa: F401
        import peft           # noqa: F401
        return True
    except ImportError:
        return False


def is_training(user_id: str) -> bool:
    with _training_lock:
        return user_id in _training_in_progress


# ── Info helpers ───────────────────────────────────────────────────────────────

def get_adapter_info(user_id: str) -> dict:
    path = _info_path(user_id)
    default = {
        "model_name":   MODEL_NAME,
        "base_model":   BASE_MODEL_ID,
        "user_id":      user_id,
        "trained":      False,
        "trained_at":   None,
        "sample_count": 0,
        "epochs":       TRAIN_EPOCHS,
        "adapter_path": _adapter_path(user_id),
    }
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {**default, **data}
    except Exception:
        return default


def _save_info(user_id: str, extra: dict) -> None:
    info = get_adapter_info(user_id)
    info.update(extra)
    try:
        with open(_info_path(user_id), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"persona_model _save_info error: {e}")


# ── ChatML formatting ──────────────────────────────────────────────────────────

def _to_chatml(sample: dict) -> str:
    """Format one training sample as TinyLlama ChatML text."""
    sys_text  = sample.get("system", "You are Sara v2, a helpful AI assistant.")
    user_text = sample.get("instruction", "")
    asst_text = sample.get("response", "")
    return "\n".join([
        _TOK_SYS,
        sys_text,
        _TOK_CLOSE,
        _TOK_USER,
        user_text,
        _TOK_CLOSE,
        _TOK_ASST,
        asst_text,
        _TOK_CLOSE,
    ])


# ── Training ───────────────────────────────────────────────────────────────────

def _run_training(user_id: str, callback) -> None:
    """Background thread: runs the actual LoRA fine-tuning."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import Dataset

        def cb(msg: str, pct: int = 0) -> None:
            if callback:
                try:
                    callback(msg, pct)
                except Exception:
                    pass

        cb("Loading training data...", 5)

        # ── Step 1: Auto-download public pipeline datasets if not cached ──────
        try:
            from brain.dataset_downloader import (
                get_merged_jsonl_path,
                download_datasets,
                _public_jsonl_path,
            )
            public_path = _public_jsonl_path(user_id)
            if not os.path.exists(public_path):
                cb(
                    "First training run! Auto-downloading public datasets\n"
                    "(Alpaca, Dolly, OpenOrca, ShareGPT)...",
                    6,
                )
                n_pub = download_datasets(
                    user_id,
                    names=None,           # all 4 datasets
                    max_per_dataset=300,  # 300 samples each = ~1200 total, fast
                    callback=None,        # silent — main cb handles progress
                )
                cb(f"Downloaded {n_pub} public samples. Merging with your chats...", 8)
            merged = get_merged_jsonl_path(user_id)
        except Exception as _de:
            logger.warning(f"persona_model: public dataset step failed: {_de}")
            merged = None

        # ── Step 2: Load merged JSONL (personal + public) or fallback ─────────
        jsonl = merged or _jsonl_path(user_id)

        if not jsonl or not os.path.exists(jsonl):
            cb("No training data found. Send a few messages first then /train.", 0)
            return

        samples = []
        with open(jsonl, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        samples.append(json.loads(line))
                    except Exception:
                        continue

        if not samples:
            cb("Training data file is empty! Chat more and try again.", 0)
            return

        # ── Step 3: Upweight personal data 3x before mixing ──────────────────
        # Load raw personal samples for upweighting
        import random
        personal_samples = []
        personal_path    = _jsonl_path(user_id)
        if os.path.exists(personal_path):
            with open(personal_path, "r", encoding="utf-8") as pf:
                for line in pf:
                    line = line.strip()
                    if line:
                        try:
                            personal_samples.append(json.loads(line))
                        except Exception:
                            continue

        # Build final sample list: public (1x) + personal (PERSONAL_DATA_WEIGHT x)
        public_samples  = [s for s in samples if s not in personal_samples]
        weighted        = public_samples + personal_samples * PERSONAL_DATA_WEIGHT
        random.shuffle(weighted)
        samples         = weighted

        personal_n = len(personal_samples)
        public_n   = len(public_samples)
        cb(
            f"Training set: {len(samples)} samples "
            f"({personal_n} personal ×{PERSONAL_DATA_WEIGHT} + {public_n} public). "
            "Loading base model...",
            10,
        )

        # ── Step 4: Tokeniser ─────────────────────────────────────────────────
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token

        cb("Tokenising training data...", 20)
        texts = [_to_chatml(s) for s in samples]

        def tokenize(example):
            out = tokenizer(
                example["text"],
                truncation=True,
                max_length=MAX_SEQ_LEN,
                padding="max_length",
            )
            out["labels"] = out["input_ids"].copy()
            return out

        dataset = Dataset.from_dict({"text": texts}).map(tokenize, batched=False)
        dataset = dataset.remove_columns(["text"])
        dataset.set_format("torch")

        # ── Step 5: Model + LoRA ──────────────────────────────────────────────
        cb("Setting up LoRA adapter (rank 16, 7 modules)...", 35)

        use_fp16 = torch.cuda.is_available()
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL_ID,
            trust_remote_code=True,
            torch_dtype=torch.float16 if use_fp16 else torch.float32,
        )
        model.enable_input_require_grads()   # needed for LoRA + gradient checkpointing

        lora_cfg = LoraConfig(
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            task_type=TaskType.CAUSAL_LM,
            target_modules=LORA_TARGET_MODULES,
        )
        model = get_peft_model(model, lora_cfg)
        trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total     = sum(p.numel() for p in model.parameters())
        cb(
            f"Trainable: {trainable:,} / {total:,} params "
            f"({'GPU fp16' if use_fp16 else 'CPU fp32'}). Starting...",
            40,
        )

        # ── Step 6: Training args — gradient accumulation + cosine LR ─────────
        adapter_out  = _adapter_path(user_id)
        os.makedirs(adapter_out, exist_ok=True)

        total_steps = (len(samples) // (BATCH_SIZE * GRADIENT_ACCUMULATION)) * TRAIN_EPOCHS
        warmup_steps = max(1, int(total_steps * WARMUP_RATIO))

        train_args = TrainingArguments(
            output_dir                  = adapter_out,
            num_train_epochs            = TRAIN_EPOCHS,
            per_device_train_batch_size = BATCH_SIZE,
            gradient_accumulation_steps = GRADIENT_ACCUMULATION,
            learning_rate               = LEARNING_RATE,
            lr_scheduler_type           = "cosine",
            warmup_steps                = warmup_steps,
            weight_decay                = WEIGHT_DECAY,
            fp16                        = use_fp16,
            logging_steps               = max(1, total_steps // 10),
            save_strategy               = "no",
            report_to                   = "none",
            dataloader_pin_memory       = torch.cuda.is_available(),
            optim                       = "adamw_torch",
        )

        trainer = Trainer(
            model       = model,
            args        = train_args,
            train_dataset = dataset,
        )

        cb(f"Training Sara v2 ({TRAIN_EPOCHS} epochs, ~{total_steps} steps)...", 45)
        trainer.train()

        cb("Saving Sara v2 LoRA adapter...", 90)
        model.save_pretrained(adapter_out)
        tokenizer.save_pretrained(adapter_out)

        _save_info(user_id, {
            "trained":       True,
            "trained_at":    datetime.now(timezone.utc).isoformat(),
            "sample_count":  len(samples),
            "personal_count": personal_n,
            "public_count":  public_n,
            "epochs":        TRAIN_EPOCHS,
            "lora_rank":     LORA_R,
            "fp16":          use_fp16,
        })

        # Mark in personal_trainer too
        try:
            from brain.personal_trainer import mark_trained
            mark_trained(user_id)
        except Exception:
            pass

        cb(
            f"🎉 Sara v2 is ready!\n"
            f"Trained on {personal_n} personal ×{PERSONAL_DATA_WEIGHT} "
            f"+ {public_n} public = {len(samples)} total samples.",
            100,
        )

    except ImportError as e:
        if callback:
            callback(f"Missing dependency: {e}\n\n{DEPS_MESSAGE}", 0)
    except Exception as e:
        logger.error(f"Sara v2 training error for {user_id}: {e}")
        if callback:
            callback(f"Training failed: {e}", 0)
    finally:
        with _training_lock:
            _training_in_progress.discard(user_id)


def train_personal_model(user_id: str, callback=None) -> str:
    """
    Start LoRA fine-tuning in a background thread.
    callback(message: str, percent: int) is called with progress updates.
    Returns an immediate status string.
    """
    if not is_available():
        return DEPS_MESSAGE

    with _training_lock:
        if user_id in _training_in_progress:
            return "Sara v2 is already training! Please wait for it to finish."
        _training_in_progress.add(user_id)

    t = threading.Thread(target=_run_training, args=(user_id, callback), daemon=True)
    t.start()
    return (
        f"Started training {MODEL_NAME} on your data!\n\n"
        "I'll send you updates as it progresses.\n"
        "This usually takes 2-10 minutes depending on your data size."
    )


# ── Inference ──────────────────────────────────────────────────────────────────

def inference(user_id: str, prompt: str) -> "str | None":
    """
    Run inference using the user's personal Sara v2 LoRA adapter.
    Returns None if no model is trained yet or deps are missing.
    """
    if not is_available():
        return None

    info = get_adapter_info(user_id)
    if not info.get("trained"):
        return None

    adapter_dir = _adapter_path(user_id)
    if not os.path.exists(adapter_dir):
        return None

    if user_id not in _loaded_pipelines:
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
            from peft import PeftModel

            logger.info(f"Loading Sara v2 adapter for user {user_id}...")
            tokenizer = AutoTokenizer.from_pretrained(adapter_dir)
            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_ID,
                torch_dtype=torch.float32,
                trust_remote_code=True,
            )
            model = PeftModel.from_pretrained(base_model, adapter_dir)
            model.eval()

            _loaded_pipelines[user_id] = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_new_tokens=256,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=tokenizer.eos_token_id,
            )
            logger.info(f"Sara v2 pipeline loaded for user {user_id}")
        except Exception as e:
            logger.warning(f"Sara v2 inference load error: {e}")
            return None

    pipe = _loaded_pipelines.get(user_id)
    if pipe is None:
        return None

    # Build a ChatML prompt for inference
    system = (
        "You are Sara v2, a deeply personal AI assistant. "
        "You know this user well — reply naturally, warmly, and concisely."
    )
    full_prompt = "\n".join([
        _TOK_SYS, system, _TOK_CLOSE,
        _TOK_USER, prompt, _TOK_CLOSE,
        _TOK_ASST,
    ])

    try:
        result = pipe(full_prompt)
        generated = result[0]["generated_text"]
        # Strip the prompt prefix from the output
        if _TOK_ASST in generated:
            generated = generated.split(_TOK_ASST)[-1]
        return generated.replace(_TOK_CLOSE, "").replace(_TOK_END, "").strip() or None
    except Exception as e:
        logger.warning(f"Sara v2 inference error: {e}")
        return None


# ── Housekeeping ───────────────────────────────────────────────────────────────

def delete_model(user_id: str) -> None:
    """Delete the Sara v2 LoRA adapter and info for a user."""
    import shutil
    adapter_dir = _adapter_path(user_id)
    if os.path.exists(adapter_dir):
        shutil.rmtree(adapter_dir, ignore_errors=True)
    info_file = _info_path(user_id)
    if os.path.exists(info_file):
        os.remove(info_file)
    _loaded_pipelines.pop(user_id, None)
    logger.info(f"Sara v2 model deleted for user {user_id}")


def format_model_status(user_id: str) -> str:
    """Return a Telegram-ready string showing Sara v2 status for this user."""
    if not is_available():
        return (
            "🤖 *Sara v2 — Not Ready*\n\n"
            "Install training dependencies first:\n"
            "`pip install torch transformers peft datasets accelerate`"
        )

    if is_training(user_id):
        return "🔄 *Sara v2 is currently training...* Please wait!"

    info = get_adapter_info(user_id)
    if not info.get("trained"):
        return (
            "🤖 *Sara v2 — Not Trained Yet*\n\n"
            "Use /train to start training Sara v2 on your personal data!\n"
            "_Training takes 5-10 minutes and everything stays on your device._"
        )

    trained_at = (info.get("trained_at") or "")[:10]
    samples    = info.get("sample_count", 0)
    return (
        f"🤖 *Sara v2 — Active* ✅\n\n"
        f"  Trained on:  *{samples}* of your conversations\n"
        f"  Last trained: `{trained_at}`\n"
        f"  Model:        TinyLlama-1.1B + LoRA\n"
        f"  Storage:      Local only (you own it)\n\n"
        "_Sara v2 is personalising your responses!_"
    )
