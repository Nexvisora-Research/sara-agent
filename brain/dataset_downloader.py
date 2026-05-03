"""
brain/dataset_downloader.py - Public Dataset Fetcher for Sara SLM.

Downloads and converts high-quality public datasets for 3-stage training:

Stage 1 - BASE KNOWLEDGE (Pretraining):
  • Wikipedia       - Encyclopedia knowledge (wikimedia/wikipedia)
  • TinyStories     - Simple narrative stories (roneneldan/TinyStories)
  • OpenWebText     - Web text corpus (Skylion007/openwebtext)

Stage 2 - INSTRUCTION TUNING:
  • OpenOrca        - 1M+ GPT-4 reasoning chains
  • Alpaca          - 52k Stanford instructions
  • Dolly-15k       - Databricks diverse instructions

Stage 3 - CHAT TUNING:
  • ShareGPT        - Real multi-turn human-ChatGPT conversations
  • OASST           - Open Assistant conversations

Training Pipeline:
  Knowledge (Wiki/Books) → Instructions (Orca/Alpaca) → Chat (ShareGPT/OASST)
  = Well-rounded Chat AI with real knowledge

Deps: pip install datasets huggingface_hub

Public API:
  download_datasets(user_id, names=None, max_per_dataset=500, callback=None) -> int
  download_base_knowledge(user_id, max_samples=5000, callback=None) -> int
  download_instruction_data(user_id, max_per_dataset=500, callback=None) -> int
  download_chat_data(user_id, max_per_dataset=500, callback=None) -> int
  download_all_stages(user_id, callback=None) -> dict
  list_available() -> list[str]
  get_download_status(user_id) -> str
  clear_public_data(user_id) -> None
"""

import json
import logging
import os
import random
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR        = os.path.join(os.path.dirname(__file__), "..", "memory", "data")
PUBLIC_JSONL    = "public_training_data.jsonl"
PUBLIC_META     = "public_training_meta.json"

# Stage-specific files
BASE_KNOWLEDGE_JSONL = "base_knowledge.jsonl"
INSTRUCTION_JSONL    = "instruction_data.jsonl"
CHAT_JSONL           = "chat_data.jsonl"

# ChatML tokens built from parts
_S = "<" + "|system|>"
_U = "<" + "|user|>"
_A = "<" + "|assistant|>"
_C = "</s>"

SARA_SYSTEM = (
    "You are Sara, a warm, helpful, and highly personal AI assistant. "
    "Answer naturally, concisely, and helpfully."
)

# ── Dataset registry ───────────────────────────────────────────────────────────

# STAGE 1: Base Knowledge datasets
BASE_DATASETS = {
    "wikipedia": {
        "hf_id":   "wikimedia/wikipedia",
        "config":  "20231101.en",
        "split":   "train",
        "desc":    "Wikipedia — Encyclopedia knowledge",
        "convert": "_convert_wikipedia",
        "stage":   1,
    },
    "tinystories": {
        "hf_id":   "roneneldan/TinyStories",
        "split":   "train",
        "desc":    "TinyStories — Simple narrative stories",
        "convert": "_convert_tinystories",
        "stage":   1,
    },
    "openwebtext": {
        "hf_id":   "Skylion007/openwebtext",
        "split":   "train",
        "desc":    "OpenWebText — High quality web text",
        "convert": "_convert_openwebtext",
        "stage":   1,
    },
}

# STAGE 2: Instruction datasets
INSTRUCTION_DATASETS = {
    "alpaca": {
        "hf_id":   "tatsu-lab/alpaca",
        "split":   "train",
        "desc":    "Stanford Alpaca — 52k instruction pairs",
        "convert": "_convert_alpaca",
        "stage":   2,
    },
    "dolly": {
        "hf_id":   "databricks/databricks-dolly-15k",
        "split":   "train",
        "desc":    "Databricks Dolly — 15k diverse instructions",
        "convert": "_convert_dolly",
        "stage":   2,
    },
    "openorca": {
        "hf_id":   "Open-Orca/OpenOrca",
        "split":   "train",
        "desc":    "OpenOrca — GPT-4 reasoning chains",
        "convert": "_convert_openorca",
        "stage":   2,
    },
    "slimorca": {
        "hf_id":   "Open-Orca/SlimOrca",
        "split":   "train",
        "desc":    "SlimOrca — Curated GPT-4 reasoning (deduped)",
        "convert": "_convert_slimorca",
        "stage":   2,
    },
}

# STAGE 3: Chat datasets
CHAT_DATASETS = {
    "sharegpt": {
        "hf_id":   "anon8231489123/ShareGPT_Vicuna_unfiltered",
        "split":   "train",
        "desc":    "ShareGPT — Multi-turn human+ChatGPT conversations",
        "convert": "_convert_sharegpt",
        "stage":   3,
    },
    "oasst": {
        "hf_id":   "OpenAssistant/oasst1",
        "split":   "train",
        "desc":    "OASST — Open Assistant human conversations",
        "convert": "_convert_oasst",
        "stage":   3,
    },
    "ultrachat": {
        "hf_id":   "stingning/ultrachat",
        "split":   "train",
        "desc":    "UltraChat — Large-scale multi-turn dialogues",
        "convert": "_convert_ultrachat",
        "stage":   3,
    },
}

# Combined registry (backwards compatible)
DATASETS = {**BASE_DATASETS, **INSTRUCTION_DATASETS, **CHAT_DATASETS}


def list_available() -> list:
    """Return names and descriptions of all supported public datasets by stage."""
    result = []
    for stage_name, datasets in [
        ("Stage 1 - Base Knowledge", BASE_DATASETS),
        ("Stage 2 - Instructions", INSTRUCTION_DATASETS),
        ("Stage 3 - Chat", CHAT_DATASETS),
    ]:
        for k, v in datasets.items():
            result.append({
                "name": k,
                "desc": v["desc"],
                "stage": stage_name,
            })
    return result


# ── Paths ──────────────────────────────────────────────────────────────────────

def _user_dir(user_id: str) -> str:
    d = os.path.join(DATA_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def _public_jsonl_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), PUBLIC_JSONL)


def _meta_path(user_id: str) -> str:
    return os.path.join(_user_dir(user_id), PUBLIC_META)


def _stage_path(user_id: str, stage: int) -> str:
    """Get path for stage-specific data file."""
    filenames = {1: BASE_KNOWLEDGE_JSONL, 2: INSTRUCTION_JSONL, 3: CHAT_JSONL}
    return os.path.join(_user_dir(user_id), filenames.get(stage, PUBLIC_JSONL))


# ── Converters — one per dataset format ────────────────────────────────────────

def _to_sample(instruction: str, response: str, system: str = "") -> dict:
    return {
        "system":      system or SARA_SYSTEM,
        "instruction": instruction.strip(),
        "response":    response.strip(),
    }


def _to_pretrain_sample(text: str) -> dict:
    """Convert raw text to pretraining format (no instruction/response split)."""
    return {
        "text": text.strip(),
        "type": "pretrain",
    }


# Stage 1: Base Knowledge converters
def _convert_wikipedia(row: dict) -> "dict | None":
    """Extract knowledge from Wikipedia articles."""
    text = row.get("text", "").strip()
    title = row.get("title", "").strip()
    if not text or len(text) < 200:
        return None
    # Create Q&A style from Wikipedia content
    # Take first paragraph as summary
    paragraphs = text.split("\n\n")
    if len(paragraphs) < 2:
        return None
    summary = paragraphs[0][:500]
    if len(summary) < 100:
        return None
    instruction = f"Tell me about {title}." if title else "What can you tell me about this topic?"
    return _to_sample(instruction, summary)


def _convert_tinystories(row: dict) -> "dict | None":
    """Convert TinyStories for narrative understanding."""
    text = row.get("text", "").strip()
    if not text or len(text) < 100:
        return None
    # Create story continuation task
    sentences = text.split(". ")
    if len(sentences) < 3:
        return None
    prompt_part = ". ".join(sentences[:2]) + "."
    continuation = ". ".join(sentences[2:])
    if len(continuation) < 50:
        return None
    instruction = f"Continue this story: {prompt_part}"
    return _to_sample(instruction, continuation)


def _convert_openwebtext(row: dict) -> "dict | None":
    """Convert OpenWebText for general knowledge."""
    text = row.get("text", "").strip()
    if not text or len(text) < 200:
        return None
    # Take a reasonable chunk and create summary task
    chunk = text[:1500]
    paragraphs = chunk.split("\n")
    if len(paragraphs) < 2:
        return None
    # Create a knowledge extraction task
    first_para = paragraphs[0][:300]
    if len(first_para) < 100:
        return None
    instruction = "Explain the main point of this text concisely."
    return _to_sample(instruction, first_para)


# Stage 2: Instruction converters
def _convert_alpaca(row: dict) -> "dict | None":
    instruction = row.get("instruction", "").strip()
    inp         = row.get("input", "").strip()
    output      = row.get("output", "").strip()
    if not instruction or not output or len(output) < 10:
        return None
    full_instruction = f"{instruction}\n\n{inp}".strip() if inp else instruction
    return _to_sample(full_instruction, output)


def _convert_dolly(row: dict) -> "dict | None":
    instruction = row.get("instruction", "").strip()
    response    = row.get("response", "").strip()
    context     = row.get("context", "").strip()
    if not instruction or not response or len(response) < 10:
        return None
    if context:
        instruction = f"{instruction}\n\nContext: {context}"
    return _to_sample(instruction, response)


def _convert_openorca(row: dict) -> "dict | None":
    question     = row.get("question", "").strip()
    response     = row.get("response", "").strip()
    system_prompt = row.get("system_prompt", "").strip()
    if not question or not response or len(response) < 10:
        return None
    return _to_sample(question, response, system_prompt or SARA_SYSTEM)


def _convert_slimorca(row: dict) -> "dict | None":
    """SlimOrca has conversations format."""
    conversations = row.get("conversations", [])
    if len(conversations) < 2:
        return None
    system = ""
    human = ""
    assistant = ""
    for turn in conversations:
        role = turn.get("from", "").lower()
        value = turn.get("value", "").strip()
        if role == "system":
            system = value
        elif role == "human" and not human:
            human = value
        elif role == "gpt" and not assistant:
            assistant = value
    if not human or not assistant or len(assistant) < 10:
        return None
    return _to_sample(human, assistant, system or SARA_SYSTEM)


# Stage 3: Chat converters
def _convert_sharegpt(row: dict) -> "dict | None":
    """Convert first human/assistant pair from a ShareGPT conversation."""
    conversations = row.get("conversations", [])
    if len(conversations) < 2:
        return None
    human = ""
    gpt   = ""
    for turn in conversations:
        role  = (turn.get("from") or "").lower()
        value = (turn.get("value") or "").strip()
        if role in ("human", "user") and not human:
            human = value
        elif role in ("gpt", "assistant", "chatgpt") and not gpt:
            gpt = value
    if not human or not gpt or len(gpt) < 10:
        return None
    return _to_sample(human, gpt)


def _convert_oasst(row: dict) -> "dict | None":
    """Convert OASST conversation threads."""
    text = row.get("text", "").strip()
    role = row.get("role", "").lower()
    parent_id = row.get("parent_id")

    # Only use assistant responses that have a parent (i.e., are replies)
    if role != "assistant" or not text or len(text) < 20:
        return None

    # For simplicity, create a generic prompt (full threading requires more work)
    return _to_sample("Please help me with this.", text)


def _convert_ultrachat(row: dict) -> "dict | None":
    """Convert UltraChat dialogues."""
    data = row.get("data", [])
    if len(data) < 2:
        return None
    # Take first exchange
    human = data[0] if isinstance(data[0], str) else ""
    assistant = data[1] if len(data) > 1 and isinstance(data[1], str) else ""
    if not human or not assistant or len(assistant) < 20:
        return None
    return _to_sample(human, assistant)


_CONVERTERS = {
    # Stage 1
    "wikipedia":    _convert_wikipedia,
    "tinystories":  _convert_tinystories,
    "openwebtext":  _convert_openwebtext,
    # Stage 2
    "alpaca":       _convert_alpaca,
    "dolly":        _convert_dolly,
    "openorca":     _convert_openorca,
    "slimorca":     _convert_slimorca,
    # Stage 3
    "sharegpt":     _convert_sharegpt,
    "oasst":        _convert_oasst,
    "ultrachat":    _convert_ultrachat,
}


# ── Stage-specific downloaders ─────────────────────────────────────────────────

def _download_stage(
    user_id: str,
    datasets_dict: dict,
    output_file: str,
    max_per_dataset: int,
    callback=None,
    stage_name: str = "",
) -> int:
    """Generic stage downloader."""
    try:
        from datasets import load_dataset
    except ImportError:
        msg = "Missing dependency: pip install datasets huggingface_hub"
        if callback:
            callback(msg, 0)
        return 0

    def cb(msg: str, pct: int = 0) -> None:
        if callback:
            try:
                callback(msg, pct)
            except Exception:
                pass

    targets = list(datasets_dict.keys())
    all_samples = []
    step = 85 // max(len(targets), 1)

    for i, name in enumerate(targets):
        info = datasets_dict[name]
        cb(f"[{stage_name}] Downloading {info['desc']}...", i * step + 5)
        logger.info(f"dataset_downloader: fetching {name} ({info['hf_id']})")

        try:
            # Handle datasets with config
            config = info.get("config")
            if config:
                ds = load_dataset(
                    info["hf_id"],
                    config,
                    split=info["split"],
                    streaming=True,
                    trust_remote_code=True,
                )
            else:
                ds = load_dataset(
                    info["hf_id"],
                    split=info["split"],
                    streaming=True,
                    trust_remote_code=True,
                )

            converter = _CONVERTERS.get(name)
            if not converter:
                continue

            count = 0
            for row in ds:
                if count >= max_per_dataset:
                    break
                try:
                    sample = converter(row)
                    if sample:
                        if sample.get("instruction") and sample.get("response"):
                            if len(sample["instruction"]) > 5 and len(sample["response"]) > 10:
                                all_samples.append(sample)
                                count += 1
                        elif sample.get("text"):
                            all_samples.append(sample)
                            count += 1
                except Exception:
                    continue

            cb(f"[{stage_name}] Got {count} samples from {name}", (i + 1) * step)
            logger.info(f"dataset_downloader: {name} → {count} samples")

        except Exception as e:
            cb(f"[{stage_name}] Could not load {name}: {e}", i * step)
            logger.warning(f"dataset_downloader: {name} failed: {e}")
            continue

    if not all_samples:
        cb(f"[{stage_name}] No samples downloaded.", 0)
        return 0

    # Shuffle and save
    random.shuffle(all_samples)
    out_path = os.path.join(_user_dir(user_id), output_file)
    cb(f"[{stage_name}] Saving {len(all_samples)} samples...", 90)

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            for sample in all_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    except OSError as e:
        cb(f"Could not save: {e}", 0)
        return 0

    cb(f"[{stage_name}] Done! {len(all_samples)} samples ready.", 100)
    return len(all_samples)


def download_base_knowledge(
    user_id: str,
    max_per_dataset: int = 2000,
    callback=None,
) -> int:
    """Stage 1: Download base knowledge datasets (Wikipedia, TinyStories, OpenWebText)."""
    return _download_stage(
        user_id=user_id,
        datasets_dict=BASE_DATASETS,
        output_file=BASE_KNOWLEDGE_JSONL,
        max_per_dataset=max_per_dataset,
        callback=callback,
        stage_name="Stage 1: Knowledge",
    )


def download_instruction_data(
    user_id: str,
    max_per_dataset: int = 500,
    callback=None,
) -> int:
    """Stage 2: Download instruction datasets (OpenOrca, Alpaca, Dolly)."""
    return _download_stage(
        user_id=user_id,
        datasets_dict=INSTRUCTION_DATASETS,
        output_file=INSTRUCTION_JSONL,
        max_per_dataset=max_per_dataset,
        callback=callback,
        stage_name="Stage 2: Instructions",
    )


def download_chat_data(
    user_id: str,
    max_per_dataset: int = 500,
    callback=None,
) -> int:
    """Stage 3: Download chat datasets (ShareGPT, OASST, UltraChat)."""
    return _download_stage(
        user_id=user_id,
        datasets_dict=CHAT_DATASETS,
        output_file=CHAT_JSONL,
        max_per_dataset=max_per_dataset,
        callback=callback,
        stage_name="Stage 3: Chat",
    )


def download_all_stages(
    user_id: str,
    base_samples: int = 2000,
    instruction_samples: int = 500,
    chat_samples: int = 500,
    callback=None,
) -> dict:
    """Download all 3 training stages in order.

    Returns dict with sample counts per stage.
    """
    def cb(msg: str, pct: int = 0) -> None:
        if callback:
            try:
                callback(msg, pct)
            except Exception:
                pass

    results = {"stage1": 0, "stage2": 0, "stage3": 0, "total": 0}

    cb("Starting 3-stage dataset download...", 0)

    # Stage 1: Base Knowledge
    cb("=== Stage 1: Base Knowledge (Wikipedia, Stories, Web) ===", 5)
    results["stage1"] = download_base_knowledge(
        user_id, max_per_dataset=base_samples, callback=callback
    )

    # Stage 2: Instructions
    cb("=== Stage 2: Instruction Tuning (Orca, Alpaca, Dolly) ===", 35)
    results["stage2"] = download_instruction_data(
        user_id, max_per_dataset=instruction_samples, callback=callback
    )

    # Stage 3: Chat
    cb("=== Stage 3: Chat Training (ShareGPT, OASST) ===", 70)
    results["stage3"] = download_chat_data(
        user_id, max_per_dataset=chat_samples, callback=callback
    )

    results["total"] = results["stage1"] + results["stage2"] + results["stage3"]

    # Save combined metadata
    meta = {
        "stages": results,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": "3-stage",
    }
    try:
        with open(_meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    cb(
        f"All stages complete!\n"
        f"  Stage 1 (Knowledge): {results['stage1']} samples\n"
        f"  Stage 2 (Instructions): {results['stage2']} samples\n"
        f"  Stage 3 (Chat): {results['stage3']} samples\n"
        f"  Total: {results['total']} samples",
        100,
    )

    return results


# ── Main downloader (backwards compatible) ─────────────────────────────────────

def download_datasets(
    user_id: str,
    names: "list[str] | None" = None,
    max_per_dataset: int = 500,
    callback=None,
) -> int:
    """
    Download and convert public datasets to JSONL.

    names           : list of dataset names to download (default: all 4)
    max_per_dataset : max samples to take from each dataset (default 500)
    callback(msg, pct): optional progress callback for Telegram updates

    Returns total number of samples written.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        msg = (
            "Missing dependency: `datasets`\n"
            "Install with:\n"
            "  pip install datasets huggingface_hub\n"
            "(usually installed with `transformers`)"
        )
        if callback:
            callback(msg, 0)
        logger.error(msg)
        return 0

    def cb(msg: str, pct: int = 0) -> None:
        if callback:
            try:
                callback(msg, pct)
            except Exception:
                pass

    targets = names or list(DATASETS.keys())
    all_samples = []
    step = 90 // max(len(targets), 1)

    for i, name in enumerate(targets):
        if name not in DATASETS:
            cb(f"Unknown dataset: {name} (skipping)", i * step)
            continue

        info = DATASETS[name]
        cb(f"Downloading {info['desc']}...", i * step + 5)
        logger.info(f"dataset_downloader: fetching {name} ({info['hf_id']})")

        try:
            ds = load_dataset(
                info["hf_id"],
                split=info["split"],
                streaming=True,           # stream so we don't download GBs
                trust_remote_code=True,
            )
            converter = _CONVERTERS[name]
            count = 0
            for row in ds:
                if count >= max_per_dataset:
                    break
                sample = converter(row)
                if sample and len(sample["instruction"]) > 5 and len(sample["response"]) > 5:
                    all_samples.append(sample)
                    count += 1

            cb(f"Got {count} samples from {info['desc']}", (i + 1) * step)
            logger.info(f"dataset_downloader: {name} → {count} samples")

        except Exception as e:
            cb(f"Could not load {name}: {e}", i * step)
            logger.warning(f"dataset_downloader: {name} failed: {e}")
            continue

    if not all_samples:
        cb("No samples downloaded. Check your internet connection.", 0)
        return 0

    # Write combined JSONL
    out_path = _public_jsonl_path(user_id)
    cb(f"Saving {len(all_samples)} total public samples...", 92)
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            for sample in all_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    except OSError as e:
        cb(f"Could not save dataset: {e}", 0)
        logger.error(f"dataset_downloader: write error: {e}")
        return 0

    # Save metadata
    meta = {
        "datasets":    targets,
        "total":       len(all_samples),
        "max_per":     max_per_dataset,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        with open(_meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    cb(f"Done! {len(all_samples)} public training samples ready.", 100)
    logger.info(f"dataset_downloader: wrote {len(all_samples)} samples → {out_path}")
    return len(all_samples)


# ── Merge helper — called by persona_model before training ─────────────────────

def get_merged_jsonl_path(user_id: str) -> "str | None":
    """
    Merge public + personal JSONL files into a single temp file.
    Returns path to merged file, or None if no public data available.
    """
    personal_path = os.path.join(_user_dir(user_id), "training_data.jsonl")
    public_path   = _public_jsonl_path(user_id)

    lines = []
    for path in [personal_path, public_path]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines.extend(f.readlines())
            except Exception as e:
                logger.warning(f"dataset_downloader merge: skipping {path}: {e}")

    if not lines:
        return None

    # Shuffle for better training generalisation
    import random
    random.shuffle(lines)

    merged_path = os.path.join(_user_dir(user_id), "merged_training_data.jsonl")
    try:
        with open(merged_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info(f"dataset_downloader: merged → {len(lines)} total samples")
        return merged_path
    except OSError as e:
        logger.error(f"dataset_downloader: merge write error: {e}")
        return None


# ── Status helpers ─────────────────────────────────────────────────────────────

def get_download_status(user_id: str) -> str:
    """Return Telegram-ready string showing what public data has been downloaded."""
    user_dir = _user_dir(user_id)
    meta_path = _meta_path(user_id)

    # Check for 3-stage data files
    stage1_exists = os.path.exists(os.path.join(user_dir, BASE_KNOWLEDGE_JSONL))
    stage2_exists = os.path.exists(os.path.join(user_dir, INSTRUCTION_JSONL))
    stage3_exists = os.path.exists(os.path.join(user_dir, CHAT_JSONL))

    if not os.path.exists(meta_path) and not (stage1_exists or stage2_exists or stage3_exists):
        return (
            "📦 *Training Datasets — Not Downloaded Yet*\n\n"
            "*Recommended: 3-Stage Pipeline*\n"
            "  /download\\_all\\_stages - Downloads:\n\n"
            "  Stage 1 (Knowledge):\n"
            "    • Wikipedia, TinyStories, OpenWebText\n\n"
            "  Stage 2 (Instructions):\n"
            "    • OpenOrca, Alpaca, Dolly, SlimOrca\n\n"
            "  Stage 3 (Chat):\n"
            "    • ShareGPT, OASST, UltraChat\n\n"
            "_3-stage training produces: Knowledge + Intelligence + Conversation_"
        )

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        meta = {}

    # Check if 3-stage pipeline
    if meta.get("pipeline") == "3-stage" or (stage1_exists and stage2_exists):
        stages = meta.get("stages", {})
        downloaded = (meta.get("downloaded_at") or "")[:10]

        # Get file sizes
        def get_size(filename):
            path = os.path.join(user_dir, filename)
            if os.path.exists(path):
                return round(os.path.getsize(path) / 1024, 1)
            return 0

        s1_size = get_size(BASE_KNOWLEDGE_JSONL)
        s2_size = get_size(INSTRUCTION_JSONL)
        s3_size = get_size(CHAT_JSONL)

        return (
            f"📦 *3-Stage Training Data — Ready* ✅\n\n"
            f"  *Stage 1 (Knowledge):*\n"
            f"    Samples: {stages.get('stage1', '?')}\n"
            f"    Size: {s1_size} KB\n"
            f"    {'✅ Ready' if stage1_exists else '❌ Missing'}\n\n"
            f"  *Stage 2 (Instructions):*\n"
            f"    Samples: {stages.get('stage2', '?')}\n"
            f"    Size: {s2_size} KB\n"
            f"    {'✅ Ready' if stage2_exists else '❌ Missing'}\n\n"
            f"  *Stage 3 (Chat):*\n"
            f"    Samples: {stages.get('stage3', '?')}\n"
            f"    Size: {s3_size} KB\n"
            f"    {'✅ Ready' if stage3_exists else '❌ Missing'}\n\n"
            f"  Total: {stages.get('stage1', 0) + stages.get('stage2', 0) + stages.get('stage3', 0)} samples\n"
            f"  Downloaded: {downloaded}\n\n"
            "_Use /train\\_slm\\_3stage to start 3-stage training!_"
        )

    # Backwards compatible single-stage display
    datasets = ", ".join(meta.get("datasets", []))
    total = meta.get("total", 0)
    downloaded = (meta.get("downloaded_at") or "")[:10]
    max_per = meta.get("max_per", 0)

    public_path = _public_jsonl_path(user_id)
    size_kb = 0
    if os.path.exists(public_path):
        size_kb = round(os.path.getsize(public_path) / 1024, 1)

    return (
        f"📦 *Public Datasets — Downloaded* ✅\n\n"
        f"  Datasets:        {datasets}\n"
        f"  Total samples:   *{total}*\n"
        f"  Samples per set: {max_per}\n"
        f"  File size:       {size_kb} KB\n"
        f"  Downloaded:      {downloaded}\n\n"
        f"_Consider /download\\_all\\_stages for better 3-stage training!_"
    )


def clear_public_data(user_id: str) -> None:
    """Delete downloaded public dataset files (including 3-stage data)."""
    files_to_delete = [
        PUBLIC_JSONL,
        PUBLIC_META,
        "merged_training_data.jsonl",
        BASE_KNOWLEDGE_JSONL,
        INSTRUCTION_JSONL,
        CHAT_JSONL,
    ]
    for fname in files_to_delete:
        path = os.path.join(_user_dir(user_id), fname)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                logger.warning(f"dataset_downloader: could not delete {path}: {e}")
    logger.info(f"dataset_downloader: cleared public data for {user_id}")
