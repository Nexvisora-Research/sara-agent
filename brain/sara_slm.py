"""
brain/sara_slm.py - Sara Small Language Model (built from scratch).

A modern GPT-style transformer (~30 M parameters) with state-of-the-art techniques:
  - Your own architecture: SaraRoPE + RMSNorm + SwiGLU + KV-Cache
  - No pre-trained weights from LLaMA / Mistral / TinyLlama
  - Trained from ZERO on your own + public datasets
  - 100% local .pt weights -- you own every byte

Modern Architecture Features:
  - RoPE (Rotary Position Embeddings) - better length generalization
  - RMSNorm instead of LayerNorm - more efficient, modern LLMs use this
  - SwiGLU activation instead of GELU - proven quality improvements
  - KV-Cache for 3-5x faster inference
  - Grouped Query Attention (GQA) option for efficiency
  - Repetition penalty + better sampling for coherent chat

3-Stage Training Pipeline:
  Stage 1: Base Knowledge (Wikipedia, TinyStories, OpenWebText)
           → Builds foundational world knowledge
  Stage 2: Instruction Tuning (OpenOrca, Alpaca, Dolly)
           → Learns to follow instructions
  Stage 3: Chat Training (ShareGPT, OASST, + your conversations)
           → Natural conversational ability

Architecture: n_layers=8, n_heads=8, embed_dim=512, ffn_dim=1408 (SwiGLU)
Params: ~30M (modern architecture, entirely yours)

Deps: pip install torch transformers
      (transformers = tokenizer vocab ONLY, zero model weights loaded)

Public API:
  train_from_scratch(user_id, callback)       -> str  (single-stage, backwards compat)
  train_3stage(user_id, callback)             -> str  (full 3-stage pipeline)
  train_stage(user_id, stage, callback)       -> str  (train specific stage)
  generate(user_id, prompt, max_new)          -> str | None
  generate_stream(user_id, prompt, max_new)   -> Generator[str]
  generate_chat(user_id, messages, max_new)   -> str | None
  is_trained(user_id)                         -> bool
  is_training(user_id)                        -> bool
  format_slm_status(user_id)                  -> str
  delete_slm(user_id)                         -> None
"""

import json, logging, math, os, threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DATA_DIR     = os.path.join(os.path.dirname(__file__), "..", "memory", "data")
SLM_DIR_NAME = "sara_slm"
WEIGHTS_FILE = "sara_slm_weights.pt"
CONFIG_FILE  = "sara_slm_config.json"
META_FILE    = "sara_slm_meta.json"

DEFAULT_CONFIG = {
    "n_layers":    8,          # More layers for deeper reasoning
    "n_heads":     8,
    "n_kv_heads":  4,          # GQA: 4 KV heads for 8 query heads (2:1 ratio)
    "embed_dim":   512,
    "ffn_mult":    2.75,       # SwiGLU uses ~2.67x multiplier (not 4x like GELU)
    "max_seq":     int(os.getenv("SARA_SLM_MAX_SEQ", "1024")),  # Doubled context
    "vocab_size":  50257,
    "dropout":     0.1,
    "rope_theta":  10000.0,    # RoPE base frequency
}

# Stage-specific training configs
STAGE_CONFIGS = {
    1: {  # Base Knowledge - longer training, lower LR for stability
        "name": "Base Knowledge",
        "epochs": int(os.getenv("SARA_SLM_STAGE1_EPOCHS", "2")),
        "lr": float(os.getenv("SARA_SLM_STAGE1_LR", "1e-4")),
        "batch_accum": 8,
        "warmup_ratio": 0.1,
        "data_files": ["base_knowledge.jsonl"],
        "description": "Wikipedia, TinyStories, OpenWebText",
    },
    2: {  # Instruction Tuning - medium training
        "name": "Instruction Tuning",
        "epochs": int(os.getenv("SARA_SLM_STAGE2_EPOCHS", "3")),
        "lr": float(os.getenv("SARA_SLM_STAGE2_LR", "2e-4")),
        "batch_accum": 4,
        "warmup_ratio": 0.1,
        "data_files": ["instruction_data.jsonl"],
        "description": "OpenOrca, Alpaca, Dolly",
    },
    3: {  # Chat Training - fine-grained, higher LR
        "name": "Chat Training",
        "epochs": int(os.getenv("SARA_SLM_STAGE3_EPOCHS", "3")),
        "lr": float(os.getenv("SARA_SLM_STAGE3_LR", "3e-4")),
        "batch_accum": 4,
        "warmup_ratio": 0.15,
        "data_files": ["chat_data.jsonl", "training_data.jsonl"],  # Include personal data
        "description": "ShareGPT, OASST, Your conversations",
    },
}

# General training hyperparameters
TRAIN_EPOCHS = int(os.getenv("SARA_SLM_EPOCHS", "3"))
BATCH_SIZE   = int(os.getenv("SARA_SLM_BATCH", "2"))
GRAD_ACCUM   = int(os.getenv("SARA_SLM_GRAD_ACCUM", "4"))
LR           = float(os.getenv("SARA_SLM_LR", "3e-4"))
GRAD_CLIP    = 1.0
LOG_EVERY    = 20
WARMUP_RATIO = 0.1

_training_lock = threading.Lock()
_training_set: set = set()
_loaded_slm: dict  = {}


# == Architecture ============================================================

def _try_torch():
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        return torch, nn, F
    except ImportError:
        return None, None, None


# === V1 Architecture (backward compatibility for old weights) ===
def _build_model_v1(config):
    """Build the old v1 architecture for loading existing weights."""
    torch, nn, F = _try_torch()
    if torch is None:
        return None

    class SaraAttentionV1(nn.Module):
        def __init__(self, embed_dim, n_heads, dropout=0.1):
            super().__init__()
            assert embed_dim % n_heads == 0
            self.n_heads = n_heads
            self.head_dim = embed_dim // n_heads
            self.scale = self.head_dim ** -0.5
            self.qkv = nn.Linear(embed_dim, 3 * embed_dim, bias=False)
            self.proj = nn.Linear(embed_dim, embed_dim, bias=False)
            self.drop = nn.Dropout(dropout)

        def forward(self, x):
            B, T, C = x.shape
            qkv = self.qkv(x).reshape(B, T, 3, self.n_heads, self.head_dim)
            q, k, v = qkv.unbind(dim=2)
            q, k, v = [t.transpose(1, 2) for t in (q, k, v)]
            att = (q @ k.transpose(-2, -1)) * self.scale
            mask = torch.triu(torch.ones(T, T, device=x.device), diagonal=1).bool()
            att = att.masked_fill(mask, float("-inf"))
            att = F.softmax(att, dim=-1)
            att = self.drop(att)
            return self.proj((att @ v).transpose(1, 2).reshape(B, T, C))

    class SaraBlockV1(nn.Module):
        def __init__(self, embed_dim, n_heads, ffn_dim, dropout=0.1):
            super().__init__()
            self.norm1 = nn.LayerNorm(embed_dim)
            self.attn = SaraAttentionV1(embed_dim, n_heads, dropout)
            self.norm2 = nn.LayerNorm(embed_dim)
            self.ffn = nn.Sequential(
                nn.Linear(embed_dim, ffn_dim), nn.GELU(), nn.Dropout(dropout),
                nn.Linear(ffn_dim, embed_dim), nn.Dropout(dropout),
            )

        def forward(self, x):
            x = x + self.attn(self.norm1(x))
            x = x + self.ffn(self.norm2(x))
            return x

    class SaraSLMModelV1(nn.Module):
        def __init__(self, cfg):
            super().__init__()
            V = cfg["vocab_size"]
            C = cfg["embed_dim"]
            T = cfg["max_seq"]
            # Handle both old and new config formats
            ffn_dim = cfg.get("ffn_dim", int(C * cfg.get("ffn_mult", 4)))
            n_layers = cfg.get("n_layers", 6)

            self.tok_emb = nn.Embedding(V, C)
            self.pos_emb = nn.Embedding(T, C)
            self.drop = nn.Dropout(cfg.get("dropout", 0.1))
            self.blocks = nn.ModuleList([
                SaraBlockV1(C, cfg["n_heads"], ffn_dim, cfg.get("dropout", 0.1))
                for _ in range(n_layers)
            ])
            self.norm = nn.LayerNorm(C)
            self.lm_head = nn.Linear(C, V, bias=False)
            self.lm_head.weight = self.tok_emb.weight
            self.max_seq = T

        @property
        def n_params(self):
            return sum(p.numel() for p in self.parameters())

        def forward(self, ids, targets=None):
            B, T = ids.shape
            pos = torch.arange(T, device=ids.device)
            x = self.drop(self.tok_emb(ids) + self.pos_emb(pos))
            for block in self.blocks:
                x = block(x)
            x = self.norm(x)
            logits = self.lm_head(x)
            loss = None
            if targets is not None:
                loss = F.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    targets.view(-1),
                    ignore_index=-100,
                )
            return logits, loss

    return SaraSLMModelV1(config)


def _detect_model_version(state_dict):
    """Detect if weights are v1 or v2 based on key names."""
    keys = list(state_dict.keys())
    # V1 has: pos_emb.weight, blocks.0.attn.qkv.weight, blocks.0.ffn.0.weight
    # V2 has: blocks.0.attn.wq.weight, blocks.0.ffn.w1.weight
    if any("pos_emb" in k for k in keys) or any("qkv" in k for k in keys):
        return "v1"
    if any("wq" in k for k in keys) or any("w1" in k for k in keys):
        return "v2"
    return "v1"  # Default to v1 for safety


# === V2 Architecture (modern - RoPE, RMSNorm, SwiGLU, GQA) ===
def _build_model(config):
    torch, nn, F = _try_torch()
    if torch is None:
        return None

    # === RMSNorm (more efficient than LayerNorm, used in LLaMA/Mistral) ===
    class RMSNorm(nn.Module):
        def __init__(self, dim, eps=1e-6):
            super().__init__()
            self.weight = nn.Parameter(torch.ones(dim))
            self.eps = eps

        def forward(self, x):
            rms = torch.sqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)
            return x / rms * self.weight

    # === Rotary Position Embeddings (RoPE) - better than learned pos embeds ===
    class RotaryEmbedding(nn.Module):
        def __init__(self, dim, max_seq=2048, theta=10000.0):
            super().__init__()
            inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2).float() / dim))
            self.register_buffer("inv_freq", inv_freq, persistent=False)
            self.max_seq = max_seq
            self._cos_cache = None
            self._sin_cache = None

        def _build_cache(self, seq_len, device):
            if self._cos_cache is not None and self._cos_cache.shape[0] >= seq_len:
                return
            t = torch.arange(seq_len, device=device, dtype=self.inv_freq.dtype)
            freqs = torch.outer(t, self.inv_freq)
            emb = torch.cat([freqs, freqs], dim=-1)
            self._cos_cache = emb.cos().unsqueeze(0).unsqueeze(0)
            self._sin_cache = emb.sin().unsqueeze(0).unsqueeze(0)

        def forward(self, x, start_pos=0):
            seq_len = x.shape[2] + start_pos
            self._build_cache(seq_len, x.device)
            cos = self._cos_cache[:, :, start_pos:start_pos + x.shape[2], :]
            sin = self._sin_cache[:, :, start_pos:start_pos + x.shape[2], :]
            return cos.to(x.dtype), sin.to(x.dtype)

    def rotate_half(x):
        x1, x2 = x[..., : x.shape[-1] // 2], x[..., x.shape[-1] // 2:]
        return torch.cat([-x2, x1], dim=-1)

    def apply_rotary(q, k, cos, sin):
        q_rot = q * cos + rotate_half(q) * sin
        k_rot = k * cos + rotate_half(k) * sin
        return q_rot, k_rot

    # === Grouped Query Attention (GQA) with KV-Cache ===
    class SaraAttention(nn.Module):
        def __init__(self, embed_dim, n_heads, n_kv_heads, max_seq, dropout=0.1, rope_theta=10000.0):
            super().__init__()
            self.n_heads = n_heads
            self.n_kv_heads = n_kv_heads
            self.head_dim = embed_dim // n_heads
            self.n_rep = n_heads // n_kv_heads  # How many Q heads per KV head

            self.wq = nn.Linear(embed_dim, n_heads * self.head_dim, bias=False)
            self.wk = nn.Linear(embed_dim, n_kv_heads * self.head_dim, bias=False)
            self.wv = nn.Linear(embed_dim, n_kv_heads * self.head_dim, bias=False)
            self.wo = nn.Linear(n_heads * self.head_dim, embed_dim, bias=False)

            self.rope = RotaryEmbedding(self.head_dim, max_seq, rope_theta)
            self.drop = nn.Dropout(dropout)
            self.scale = self.head_dim ** -0.5

            # KV cache for inference
            self.cache_k = None
            self.cache_v = None

        def reset_cache(self):
            self.cache_k = None
            self.cache_v = None

        def forward(self, x, start_pos=0, use_cache=False):
            B, T, _ = x.shape

            q = self.wq(x).view(B, T, self.n_heads, self.head_dim).transpose(1, 2)
            k = self.wk(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)
            v = self.wv(x).view(B, T, self.n_kv_heads, self.head_dim).transpose(1, 2)

            # Apply RoPE
            cos, sin = self.rope(q, start_pos)
            q, k = apply_rotary(q, k, cos, sin)

            # KV-Cache for inference (3-5x speedup)
            if use_cache:
                if self.cache_k is not None:
                    k = torch.cat([self.cache_k, k], dim=2)
                    v = torch.cat([self.cache_v, v], dim=2)
                self.cache_k = k
                self.cache_v = v

            # Expand KV for GQA
            if self.n_rep > 1:
                k = k.repeat_interleave(self.n_rep, dim=1)
                v = v.repeat_interleave(self.n_rep, dim=1)

            # Attention
            att = (q @ k.transpose(-2, -1)) * self.scale

            # Causal mask
            if not use_cache or T > 1:
                causal_mask = torch.triu(torch.ones(T, k.shape[2], device=x.device), diagonal=k.shape[2] - T + 1).bool()
                att = att.masked_fill(causal_mask, float("-inf"))

            att = F.softmax(att, dim=-1)
            att = self.drop(att)

            out = (att @ v).transpose(1, 2).reshape(B, T, -1)
            return self.wo(out)

    # === SwiGLU FFN (superior to GELU, used in LLaMA/Mistral) ===
    class SwiGLU(nn.Module):
        def __init__(self, embed_dim, ffn_mult, dropout=0.1):
            super().__init__()
            hidden = int(embed_dim * ffn_mult)
            # Round to nearest multiple of 64 for efficiency
            hidden = ((hidden + 63) // 64) * 64

            self.w1 = nn.Linear(embed_dim, hidden, bias=False)  # gate
            self.w2 = nn.Linear(hidden, embed_dim, bias=False)  # down
            self.w3 = nn.Linear(embed_dim, hidden, bias=False)  # up
            self.drop = nn.Dropout(dropout)

        def forward(self, x):
            return self.drop(self.w2(F.silu(self.w1(x)) * self.w3(x)))

    # === Transformer Block ===
    class SaraBlock(nn.Module):
        def __init__(self, embed_dim, n_heads, n_kv_heads, ffn_mult, max_seq, dropout=0.1, rope_theta=10000.0):
            super().__init__()
            self.norm1 = RMSNorm(embed_dim)
            self.attn = SaraAttention(embed_dim, n_heads, n_kv_heads, max_seq, dropout, rope_theta)
            self.norm2 = RMSNorm(embed_dim)
            self.ffn = SwiGLU(embed_dim, ffn_mult, dropout)

        def forward(self, x, start_pos=0, use_cache=False):
            x = x + self.attn(self.norm1(x), start_pos, use_cache)
            x = x + self.ffn(self.norm2(x))
            return x

        def reset_cache(self):
            self.attn.reset_cache()

    # === Main Model ===
    class SaraSLMModel(nn.Module):
        def __init__(self, cfg):
            super().__init__()
            V = cfg["vocab_size"]
            C = cfg["embed_dim"]
            T = cfg["max_seq"]
            n_heads = cfg["n_heads"]
            n_kv_heads = cfg.get("n_kv_heads", n_heads)  # Default to MHA
            ffn_mult = cfg.get("ffn_mult", 2.75)
            rope_theta = cfg.get("rope_theta", 10000.0)
            dropout = cfg["dropout"]

            self.tok_emb = nn.Embedding(V, C)
            self.drop = nn.Dropout(dropout)
            self.blocks = nn.ModuleList([
                SaraBlock(C, n_heads, n_kv_heads, ffn_mult, T, dropout, rope_theta)
                for _ in range(cfg["n_layers"])
            ])
            self.norm = RMSNorm(C)
            self.lm_head = nn.Linear(C, V, bias=False)
            self.lm_head.weight = self.tok_emb.weight  # weight tying

            self.max_seq = T
            self.apply(self._init)

        def _init(self, m):
            if isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0.0, 0.02)
            elif isinstance(m, nn.Embedding):
                nn.init.normal_(m.weight, 0.0, 0.02)

        @property
        def n_params(self):
            return sum(p.numel() for p in self.parameters())

        def reset_cache(self):
            for block in self.blocks:
                block.reset_cache()

        def forward(self, ids, targets=None, start_pos=0, use_cache=False):
            B, T = ids.shape
            x = self.drop(self.tok_emb(ids))

            for block in self.blocks:
                x = block(x, start_pos, use_cache)

            x = self.norm(x)
            logits = self.lm_head(x)

            loss = None
            if targets is not None:
                loss = F.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    targets.view(-1),
                    ignore_index=-100,
                )
            return logits, loss

    return SaraSLMModel(config)


# == Paths ===================================================================

def _slm_dir(user_id):
    d = os.path.join(DATA_DIR, user_id, SLM_DIR_NAME)
    os.makedirs(d, exist_ok=True)
    return d

def _weights_path(user_id): return os.path.join(_slm_dir(user_id), WEIGHTS_FILE)
def _config_path(user_id):  return os.path.join(_slm_dir(user_id), CONFIG_FILE)
def _meta_path(user_id):    return os.path.join(_slm_dir(user_id), META_FILE)


# == State ===================================================================

def is_trained(user_id):
    return os.path.exists(_weights_path(user_id))

def is_training(user_id):
    with _training_lock:
        return user_id in _training_set

def _save_meta(user_id, meta):
    try:
        with open(_meta_path(user_id), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"sara_slm meta error: {e}")

def _load_meta(user_id):
    p = _meta_path(user_id)
    if not os.path.exists(p): return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


# == Dataset =================================================================

def _load_texts(user_id, stage=None):
    """Load JSONL datasets. Returns flat list of formatted text strings.

    Args:
        user_id: User identifier
        stage: Optional stage number (1, 2, or 3) to load specific data.
               None loads all available data (backwards compatible).
    """
    SOH = "<|" + "system|>"
    SUH = "<|" + "user|>"
    SAH = "<|" + "assistant|>"
    END = "</s>"

    user_dir = os.path.join(DATA_DIR, user_id)

    # Determine which files to load based on stage
    if stage is not None and stage in STAGE_CONFIGS:
        stage_cfg = STAGE_CONFIGS[stage]
        candidates = [
            os.path.join(user_dir, f)
            for f in stage_cfg["data_files"]
            if os.path.exists(os.path.join(user_dir, f))
        ]
        source_limits = {}  # No limits for stage-specific training
    else:
        # Backwards compatible: load merged or all available
        merged = os.path.join(user_dir, "merged_training_data.jsonl")
        if os.path.exists(merged):
            candidates = [merged]
            source_limits = {}
        else:
            candidates = []
            source_limits = {
                "training_data.jsonl": int(os.getenv("SARA_SLM_MAX_PERSONAL_SAMPLES", "1000000")),
                "public_training_data.jsonl": int(os.getenv("SARA_SLM_MAX_PUBLIC_SAMPLES", "200000")),
            }
            for name in ["training_data.jsonl", "public_training_data.jsonl"]:
                p = os.path.join(user_dir, name)
                if os.path.exists(p):
                    candidates.append(p)

    texts: list[str] = []
    counts: dict[str, int] = {}

    for path in candidates:
        if not os.path.exists(path):
            continue

        fname = os.path.basename(path)
        limit = source_limits.get(fname)
        counts.setdefault(fname, 0)

        logger.info(f"sara_slm: loading {path}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if limit is not None and counts[fname] >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    s = json.loads(line)

                    # Handle instruction/response format
                    instr = s.get("instruction", "").strip()
                    resp  = s.get("response", "").strip()
                    sys_t = s.get("system", "You are Sara, a helpful AI.").strip()

                    if instr and resp:
                        text = (SOH + "\n" + sys_t + "\n" + END + "\n"
                              + SUH + "\n" + instr + "\n" + END + "\n"
                              + SAH + "\n" + resp  + "\n" + END)
                        texts.append(text)
                        counts[fname] += 1
                    # Handle raw text format (pretraining)
                    elif s.get("text"):
                        raw_text = s.get("text", "").strip()
                        if len(raw_text) > 50:
                            texts.append(raw_text + END)
                            counts[fname] += 1

                except Exception:
                    continue
    return texts


# == Dataset class ===========================================================

class _TextDataset:
    """DEPRECATED: Old sliding window approach that breaks conversation boundaries."""
    def __init__(self, token_ids, seq_len):
        import torch
        self.ids = torch.tensor(token_ids, dtype=torch.long)
        self.seq = seq_len

    def __len__(self):
        return max(0, (len(self.ids) - 1) // self.seq)

    def __getitem__(self, i):
        s = i * self.seq
        x = self.ids[s : s + self.seq]
        y = self.ids[s + 1 : s + self.seq + 1]
        return x, y


class _ConversationDataset:
    """
    Conversation-aware dataset that preserves conversation boundaries.
    Each sample is a complete conversation, not a sliding window fragment.
    """
    def __init__(self, texts, tokenizer, seq_len):
        import torch
        self.tokenizer = tokenizer
        self.seq_len = seq_len
        self.samples = []

        # Tokenize each conversation separately
        for text in texts:
            ids = tokenizer.encode(text, truncation=True, max_length=seq_len)

            # Skip samples that are too short to be meaningful
            if len(ids) < 10:
                continue

            # Pad to seq_len if needed
            if len(ids) < seq_len:
                ids = ids + [tokenizer.eos_token_id] * (seq_len - len(ids))

            self.samples.append(torch.tensor(ids[:seq_len], dtype=torch.long))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, i):
        import torch  # Import torch here for safety
        x = self.samples[i]
        # Target is input shifted by 1 (next token prediction)
        y = torch.cat([x[1:], torch.tensor([self.tokenizer.eos_token_id])])
        return x, y


# == Training ================================================================

def _run_training(user_id, callback, config):
    torch, nn, F = _try_torch()
    if torch is None:
        if callback: callback("torch not installed. pip install torch", 0)
        return

    def cb(msg, pct=0):
        if callback:
            try: callback(msg, pct)
            except Exception: pass

    try:
        from transformers import GPT2Tokenizer
        cb("Loading GPT-2 tokenizer (vocabulary only -- zero model weights)...", 2)
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token
        eos_id = tokenizer.eos_token_id

        # Auto-download public datasets on first run
        pub_path = os.path.join(DATA_DIR, user_id, "public_training_data.jsonl")
        if not os.path.exists(pub_path):
            cb("Downloading public datasets (Alpaca + Dolly + OpenOrca + ShareGPT)...", 5)
            try:
                from brain.dataset_downloader import download_datasets
                n = download_datasets(user_id, max_per_dataset=300, callback=None)
                cb(f"Downloaded {n} public samples.", 8)
            except Exception as de:
                cb(f"Public dataset download skipped: {de}", 8)

        texts = _load_texts(user_id)
        if not texts:
            cb("No training data found. Chat first or run /download_datasets.", 0)
            return

        cb(f"Tokenising {len(texts)} samples...", 12)

        # NEW: Use conversation-aware dataset that preserves boundaries
        dataset = _ConversationDataset(texts, tokenizer, config["max_seq"])

        if len(dataset) == 0:
            cb("No valid samples after tokenization. Chat more first.", 0)
            return

        cb(f"Created {len(dataset)} conversation samples. Building Sara SLM v2 (modern arch)...", 20)
        model = _build_model(config)
        if model is None:
            cb("Could not build model.", 0)
            return

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model  = model.to(device)
        params = model.n_params
        cb(f"Sara SLM v2: {params/1e6:.1f}M params (RoPE + RMSNorm + SwiGLU + GQA). Device: {device.upper()}", 25)

        # Use the conversation-aware dataset
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True
        )

        # Optimizer with weight decay (excluding norm/embedding)
        decay_params = []
        no_decay_params = []
        for name, p in model.named_parameters():
            if "norm" in name or "emb" in name:
                no_decay_params.append(p)
            else:
                decay_params.append(p)

        optimizer = torch.optim.AdamW([
            {"params": decay_params, "weight_decay": 0.1},
            {"params": no_decay_params, "weight_decay": 0.0},
        ], lr=LR, betas=(0.9, 0.95))

        # Gradient accumulation for effective larger batch
        effective_batch = BATCH_SIZE * GRAD_ACCUM
        total_steps = (len(dataloader) // GRAD_ACCUM) * TRAIN_EPOCHS
        warmup_steps = max(1, int(total_steps * WARMUP_RATIO))

        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            return max(0.1, 0.5 * (1 + math.cos(math.pi * progress)))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
        use_amp   = device == "cuda"
        scaler    = torch.cuda.amp.GradScaler() if use_amp else None

        model.train()
        global_step = 0
        best_loss   = float("inf")
        best_state  = None
        accum_loss  = 0.0

        cb(f"Training {TRAIN_EPOCHS} epochs, effective batch={effective_batch}...", 28)

        for epoch in range(TRAIN_EPOCHS):
            epoch_loss = 0.0
            epoch_batches = 0

            for batch_i, (x, y) in enumerate(dataloader):
                x, y = x.to(device), y.to(device)

                if scaler:
                    with torch.cuda.amp.autocast():
                        _, loss = model(x, targets=y)
                    loss = loss / GRAD_ACCUM
                    scaler.scale(loss).backward()
                    accum_loss += loss.item()
                else:
                    _, loss = model(x, targets=y)
                    loss = loss / GRAD_ACCUM
                    loss.backward()
                    accum_loss += loss.item()

                # Gradient accumulation step
                if (batch_i + 1) % GRAD_ACCUM == 0:
                    if scaler:
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                        optimizer.step()

                    optimizer.zero_grad()
                    scheduler.step()
                    epoch_loss += accum_loss
                    accum_loss = 0.0
                    epoch_batches += 1
                    global_step += 1

                    if global_step % LOG_EVERY == 0:
                        avg = epoch_loss / epoch_batches
                        pct = int(28 + 62 * (global_step / max(1, total_steps)))
                        lr_now = scheduler.get_last_lr()[0]
                        cb(f"Epoch {epoch+1}/{TRAIN_EPOCHS} | step {global_step} | loss {avg:.4f} | lr {lr_now:.2e}", pct)

            avg_epoch = epoch_loss / max(1, epoch_batches)
            pct_done  = int(28 + 62 * ((epoch + 1) / TRAIN_EPOCHS))
            cb(f"Epoch {epoch+1} done. Avg loss: {avg_epoch:.4f}", pct_done)
            if avg_epoch < best_loss:
                best_loss  = avg_epoch
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}

        cb("Saving Sara SLM v2 weights...", 92)
        state = best_state or {k: v.cpu() for k, v in model.state_dict().items()}
        torch.save(state, _weights_path(user_id))

        with open(_config_path(user_id), "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        _save_meta(user_id, {
            "trained":      True,
            "trained_at":   datetime.now(timezone.utc).isoformat(),
            "n_params":     params,
            "total_tokens": total_tokens,
            "n_samples":    len(texts),
            "config":       config,
            "device":       device,
            "best_loss":    best_loss,
            "version":      "v2",
            "features":     ["RoPE", "RMSNorm", "SwiGLU", "GQA", "KV-Cache"],
        })

        cb((
            f"Sara SLM v2 ready! {params/1e6:.1f}M params trained for {TRAIN_EPOCHS} epochs.\n"
            f"Features: RoPE + RMSNorm + SwiGLU + GQA + KV-Cache\n"
            f"Best loss: {best_loss:.4f} | {total_tokens:,} tokens seen.\n"
            "Sara now answers using her OWN modern brain -- no LLaMA or Mistral!"
        ), 100)

    except Exception as e:
        logger.error(f"sara_slm training error: {e}")
        cb(f"Training failed: {e}", 0)
    finally:
        with _training_lock:
            _training_set.discard(user_id)


def train_from_scratch(user_id, callback=None, config=None):
    """Start SLM training in a background thread. Returns immediate status."""
    torch, nn, F = _try_torch()
    if torch is None:
        return "Missing deps: pip install torch transformers"

    with _training_lock:
        if user_id in _training_set:
            return "Sara SLM is already training! Please wait."
        _training_set.add(user_id)

    cfg = config or dict(DEFAULT_CONFIG)
    t   = threading.Thread(
        target=_run_training, args=(user_id, callback, cfg), daemon=True
    )
    t.start()

    placeholder_model = _build_model(cfg)
    params = placeholder_model.n_params if placeholder_model else 30_000_000
    del placeholder_model

    return (
        f"Sara SLM v2 training started!\n\n"
        f"Building a {params/1e6:.0f}M parameter model FROM SCRATCH.\n"
        f"Modern arch: RoPE + RMSNorm + SwiGLU + GQA + KV-Cache\n"
        "No LLaMA. No Mistral. No borrowed weights.\n"
        "I will send progress updates as Sara learns."
    )


# == 3-Stage Training Pipeline ===============================================

def _run_stage_training(user_id, stage, callback, config, resume_from=None):
    """Run training for a specific stage with stage-specific hyperparameters."""
    torch, nn, F = _try_torch()
    if torch is None:
        if callback: callback("torch not installed. pip install torch", 0)
        return None

    stage_cfg = STAGE_CONFIGS.get(stage, STAGE_CONFIGS[3])

    def cb(msg, pct=0):
        if callback:
            try: callback(f"[Stage {stage}] {msg}", pct)
            except Exception: pass

    try:
        from transformers import GPT2Tokenizer
        cb(f"Loading tokenizer for {stage_cfg['name']}...", 2)
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token
        eos_id = tokenizer.eos_token_id

        # Load stage-specific data
        texts = _load_texts(user_id, stage=stage)
        if not texts:
            cb(f"No data for {stage_cfg['name']}. Download datasets first.", 0)
            return None

        cb(f"Tokenising {len(texts)} samples for {stage_cfg['name']}...", 10)

        # NEW: Use conversation-aware dataset that preserves boundaries
        dataset = _ConversationDataset(texts, tokenizer, config["max_seq"])

        if len(dataset) == 0:
            cb(f"No valid samples after tokenization for {stage_cfg['name']}.", 0)
            return None

        cb(f"Created {len(dataset)} conversation samples. Building/loading model...", 20)

        # Build or load model
        model = _build_model(config)
        if model is None:
            cb("Could not build model.", 0)
            return None

        device = "cuda" if torch.cuda.is_available() else "cpu"

        # Resume from previous stage weights if provided
        if resume_from and os.path.exists(resume_from):
            cb(f"Resuming from previous stage weights...", 22)
            model.load_state_dict(torch.load(resume_from, map_location="cpu"))

        model = model.to(device)
        params = model.n_params

        cb(f"{stage_cfg['name']}: {params/1e6:.1f}M params, {stage_cfg['epochs']} epochs, LR={stage_cfg['lr']}", 25)

        # Use the conversation-aware dataset
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=BATCH_SIZE, shuffle=True, drop_last=True
        )

        # Stage-specific optimizer
        epochs = stage_cfg["epochs"]
        lr = stage_cfg["lr"]
        grad_accum = stage_cfg["batch_accum"]
        warmup_ratio = stage_cfg["warmup_ratio"]

        decay_params = []
        no_decay_params = []
        for name, p in model.named_parameters():
            if "norm" in name or "emb" in name:
                no_decay_params.append(p)
            else:
                decay_params.append(p)

        optimizer = torch.optim.AdamW([
            {"params": decay_params, "weight_decay": 0.1},
            {"params": no_decay_params, "weight_decay": 0.0},
        ], lr=lr, betas=(0.9, 0.95))

        total_steps = (len(dataloader) // grad_accum) * epochs
        warmup_steps = max(1, int(total_steps * warmup_ratio))

        def lr_lambda(step):
            if step < warmup_steps:
                return step / warmup_steps
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            return max(0.1, 0.5 * (1 + math.cos(math.pi * progress)))

        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda)
        use_amp = device == "cuda"
        scaler = torch.cuda.amp.GradScaler() if use_amp else None

        model.train()
        global_step = 0
        best_loss = float("inf")
        best_state = None
        accum_loss = 0.0

        cb(f"Training {epochs} epochs ({stage_cfg['description']})...", 28)

        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_batches = 0

            for batch_i, (x, y) in enumerate(dataloader):
                x, y = x.to(device), y.to(device)

                if scaler:
                    with torch.cuda.amp.autocast():
                        _, loss = model(x, targets=y)
                    loss = loss / grad_accum
                    scaler.scale(loss).backward()
                    accum_loss += loss.item()
                else:
                    _, loss = model(x, targets=y)
                    loss = loss / grad_accum
                    loss.backward()
                    accum_loss += loss.item()

                if (batch_i + 1) % grad_accum == 0:
                    if scaler:
                        scaler.unscale_(optimizer)
                        torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                        scaler.step(optimizer)
                        scaler.update()
                    else:
                        torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
                        optimizer.step()

                    optimizer.zero_grad()
                    scheduler.step()
                    epoch_loss += accum_loss
                    accum_loss = 0.0
                    epoch_batches += 1
                    global_step += 1

                    if global_step % LOG_EVERY == 0:
                        avg = epoch_loss / epoch_batches
                        pct = int(28 + 62 * (global_step / max(1, total_steps)))
                        cb(f"Epoch {epoch+1}/{epochs} | step {global_step} | loss {avg:.4f}", pct)

            avg_epoch = epoch_loss / max(1, epoch_batches)
            pct_done = int(28 + 62 * ((epoch + 1) / epochs))
            cb(f"Epoch {epoch+1} done. Avg loss: {avg_epoch:.4f}", pct_done)
            if avg_epoch < best_loss:
                best_loss = avg_epoch
                best_state = {k: v.cpu() for k, v in model.state_dict().items()}

        # Save stage checkpoint
        stage_weights = os.path.join(_slm_dir(user_id), f"stage{stage}_weights.pt")
        state = best_state or {k: v.cpu() for k, v in model.state_dict().items()}
        torch.save(state, stage_weights)

        cb(f"{stage_cfg['name']} complete! Loss: {best_loss:.4f}", 95)
        return {
            "stage": stage,
            "weights_path": stage_weights,
            "best_loss": best_loss,
            "tokens": total_tokens,
            "samples": len(texts),
        }

    except Exception as e:
        logger.error(f"sara_slm stage {stage} error: {e}")
        if callback:
            callback(f"Stage {stage} failed: {e}", 0)
        return None


def _run_3stage_training(user_id, callback, config):
    """Run complete 3-stage training pipeline."""

    def cb(msg, pct=0):
        if callback:
            try: callback(msg, pct)
            except Exception: pass

    try:
        # Auto-download datasets if not present
        cb("Checking/downloading training datasets...", 0)
        try:
            from brain.dataset_downloader import download_all_stages
            user_dir = os.path.join(DATA_DIR, user_id)
            base_exists = os.path.exists(os.path.join(user_dir, "base_knowledge.jsonl"))
            instr_exists = os.path.exists(os.path.join(user_dir, "instruction_data.jsonl"))
            chat_exists = os.path.exists(os.path.join(user_dir, "chat_data.jsonl"))

            if not (base_exists and instr_exists and chat_exists):
                cb("Downloading 3-stage training data (this may take a few minutes)...", 2)
                download_all_stages(user_id, callback=None)
                cb("Datasets ready!", 5)
        except Exception as de:
            cb(f"Dataset download skipped: {de}", 5)

        results = {"stages": {}, "total_tokens": 0}
        resume_from = None

        # Stage 1: Base Knowledge
        cb("=" * 50, 5)
        cb("STAGE 1: BASE KNOWLEDGE (Wikipedia, Stories, Web)", 6)
        cb("=" * 50, 7)
        stage1_result = _run_stage_training(user_id, 1, callback, config, resume_from=None)
        if stage1_result:
            results["stages"][1] = stage1_result
            results["total_tokens"] += stage1_result["tokens"]
            resume_from = stage1_result["weights_path"]
        else:
            cb("Stage 1 skipped (no data). Continuing...", 30)

        # Stage 2: Instruction Tuning
        cb("=" * 50, 33)
        cb("STAGE 2: INSTRUCTION TUNING (Orca, Alpaca, Dolly)", 34)
        cb("=" * 50, 35)
        stage2_result = _run_stage_training(user_id, 2, callback, config, resume_from=resume_from)
        if stage2_result:
            results["stages"][2] = stage2_result
            results["total_tokens"] += stage2_result["tokens"]
            resume_from = stage2_result["weights_path"]
        else:
            cb("Stage 2 skipped (no data). Continuing...", 60)

        # Stage 3: Chat Training
        cb("=" * 50, 63)
        cb("STAGE 3: CHAT TRAINING (ShareGPT, OASST, Your chats)", 64)
        cb("=" * 50, 65)
        stage3_result = _run_stage_training(user_id, 3, callback, config, resume_from=resume_from)
        if stage3_result:
            results["stages"][3] = stage3_result
            results["total_tokens"] += stage3_result["tokens"]
            resume_from = stage3_result["weights_path"]

        # Copy final weights to main file
        if resume_from and os.path.exists(resume_from):
            import shutil
            shutil.copy(resume_from, _weights_path(user_id))

            with open(_config_path(user_id), "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            # Calculate combined metrics
            total_samples = sum(s.get("samples", 0) for s in results["stages"].values())
            best_loss = min((s.get("best_loss", 999) for s in results["stages"].values()), default=0)

            _save_meta(user_id, {
                "trained": True,
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "n_params": 30_000_000,
                "total_tokens": results["total_tokens"],
                "n_samples": total_samples,
                "config": config,
                "device": "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") else "cpu",
                "best_loss": best_loss,
                "version": "v2",
                "training_pipeline": "3-stage",
                "stages_completed": list(results["stages"].keys()),
                "features": ["RoPE", "RMSNorm", "SwiGLU", "GQA", "KV-Cache", "3-Stage"],
            })

            cb("=" * 50, 98)
            cb(
                f"3-STAGE TRAINING COMPLETE!\n\n"
                f"  Stage 1 (Knowledge): {results['stages'].get(1, {}).get('samples', 0)} samples\n"
                f"  Stage 2 (Instructions): {results['stages'].get(2, {}).get('samples', 0)} samples\n"
                f"  Stage 3 (Chat): {results['stages'].get(3, {}).get('samples', 0)} samples\n"
                f"  Total tokens: {results['total_tokens']:,}\n\n"
                f"Sara now has:\n"
                f"  Knowledge + Intelligence + Conversation\n"
                f"  = YOUR OWN Chat AI!",
                100,
            )
        else:
            cb("No training completed. Please download datasets first.", 0)

    except Exception as e:
        logger.error(f"sara_slm 3-stage error: {e}")
        cb(f"3-stage training failed: {e}", 0)
    finally:
        with _training_lock:
            _training_set.discard(user_id)


def train_3stage(user_id, callback=None, config=None):
    """Start full 3-stage training pipeline in background thread.

    Pipeline:
      Stage 1: Base Knowledge (Wikipedia, TinyStories, OpenWebText)
      Stage 2: Instruction Tuning (OpenOrca, Alpaca, Dolly)
      Stage 3: Chat Training (ShareGPT, OASST, your conversations)

    This produces a chat AI with:
      Knowledge + Intelligence + Conversation = Quality Chat
    """
    torch, nn, F = _try_torch()
    if torch is None:
        return "Missing deps: pip install torch transformers"

    with _training_lock:
        if user_id in _training_set:
            return "Sara SLM is already training! Please wait."
        _training_set.add(user_id)

    cfg = config or dict(DEFAULT_CONFIG)
    t = threading.Thread(
        target=_run_3stage_training, args=(user_id, callback, cfg), daemon=True
    )
    t.start()

    return (
        "Starting 3-STAGE Training Pipeline!\n\n"
        "Stage 1: Base Knowledge (Wikipedia, Stories, Web)\n"
        "  → Builds world knowledge foundation\n\n"
        "Stage 2: Instruction Tuning (OpenOrca, Alpaca, Dolly)\n"
        "  → Learns to follow instructions\n\n"
        "Stage 3: Chat Training (ShareGPT, OASST, Your chats)\n"
        "  → Natural conversation ability\n\n"
        "This produces: Knowledge + Intelligence + Conversation\n"
        "I will send progress updates as Sara learns!"
    )


def train_stage(user_id, stage: int, callback=None, config=None):
    """Train a specific stage only (1, 2, or 3)."""
    if stage not in STAGE_CONFIGS:
        return f"Invalid stage: {stage}. Use 1, 2, or 3."

    torch, nn, F = _try_torch()
    if torch is None:
        return "Missing deps: pip install torch transformers"

    with _training_lock:
        if user_id in _training_set:
            return "Sara SLM is already training! Please wait."
        _training_set.add(user_id)

    cfg = config or dict(DEFAULT_CONFIG)
    stage_info = STAGE_CONFIGS[stage]

    # Find previous stage weights to resume from
    resume_from = None
    if stage > 1:
        prev_stage = os.path.join(_slm_dir(user_id), f"stage{stage-1}_weights.pt")
        if os.path.exists(prev_stage):
            resume_from = prev_stage

    def run():
        try:
            result = _run_stage_training(user_id, stage, callback, cfg, resume_from)
            if result:
                # Copy stage weights to main file
                import shutil
                shutil.copy(result["weights_path"], _weights_path(user_id))
                with open(_config_path(user_id), "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                _save_meta(user_id, {
                    "trained": True,
                    "trained_at": datetime.now(timezone.utc).isoformat(),
                    "last_stage": stage,
                    "version": "v2",
                    "features": ["RoPE", "RMSNorm", "SwiGLU", "GQA", "KV-Cache"],
                })
        finally:
            with _training_lock:
                _training_set.discard(user_id)

    t = threading.Thread(target=run, daemon=True)
    t.start()

    return (
        f"Starting Stage {stage}: {stage_info['name']}\n\n"
        f"Data: {stage_info['description']}\n"
        f"Epochs: {stage_info['epochs']}, LR: {stage_info['lr']}\n\n"
        f"{'Resuming from previous stage weights.' if resume_from else 'Training from scratch.'}"
    )


def generate_chat(user_id, messages, max_new=200, temperature=0.8, top_p=0.9,
                  repetition_penalty=1.15):
    """Generate response for multi-turn conversation.

    Args:
        user_id: User identifier
        messages: List of dicts with 'role' and 'content' keys
                  role can be: 'system', 'user', 'assistant'
        max_new: Maximum new tokens
        temperature: Sampling temperature
        top_p: Nucleus sampling threshold
        repetition_penalty: Penalty for repetition

    Example:
        messages = [
            {"role": "system", "content": "You are Sara, a helpful AI."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "What's the weather?"},
        ]
    """
    if not is_trained(user_id):
        return None

    SOH = "<|system|>"
    SUH = "<|user|>"
    SAH = "<|assistant|>"
    END = "</s>"

    # Build prompt from messages
    prompt_parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            prompt_parts.append(f"{SOH}\n{content}\n{END}")
        elif role == "user":
            prompt_parts.append(f"{SUH}\n{content}\n{END}")
        elif role == "assistant":
            prompt_parts.append(f"{SAH}\n{content}\n{END}")

    # Add assistant prefix for generation
    prompt_parts.append(f"{SAH}\n")
    full_prompt = "\n".join(prompt_parts)

    # Use the raw generation
    torch, nn, F = _try_torch()
    if torch is None:
        return None

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if user_id not in _loaded_slm:
        try:
            from transformers import GPT2Tokenizer
            with open(_config_path(user_id)) as f:
                cfg = json.load(f)

            # Load state dict and detect version
            state_dict = torch.load(_weights_path(user_id), map_location="cpu")
            model_version = _detect_model_version(state_dict)

            if model_version == "v1":
                model = _build_model_v1(cfg)
            else:
                model = _build_model(cfg)

            model.load_state_dict(state_dict)
            model.eval()
            model = model.to(device)
            tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
            tokenizer.pad_token = tokenizer.eos_token
            _loaded_slm[user_id] = (model, tokenizer, cfg, model_version)
        except Exception as e:
            logger.error(f"sara_slm chat load error: {e}")
            return None

    cache = _loaded_slm[user_id]
    if len(cache) == 4:
        model, tokenizer, cfg, model_version = cache
    elif len(cache) == 3:
        model, tokenizer, cfg = cache
        model_version = "v1"
    else:
        model, tokenizer = cache
        cfg = DEFAULT_CONFIG
        model_version = "v1"

    use_kv_cache = model_version == "v2"

    try:
        max_seq = int(cfg.get("max_seq", 1024))
        encoded = tokenizer.encode(full_prompt)[-max_seq:]
        ids = torch.tensor(encoded, device=device, dtype=torch.long).unsqueeze(0)
        eos = tokenizer.eos_token_id
        generated_ids = []

        if use_kv_cache and hasattr(model, 'reset_cache'):
            model.reset_cache()

        with torch.no_grad():
            if use_kv_cache:
                logits, _ = model(ids, start_pos=0, use_cache=True)
                cur_pos = ids.shape[1]
            else:
                logits, _ = model(ids)
                cur_pos = 0

            for _ in range(max_new):
                next_logits = logits[:, -1, :].clone()

                # Repetition penalty
                if repetition_penalty != 1.0:
                    all_ids = ids[0].tolist() + generated_ids
                    for prev_id in set(all_ids[-50:]):
                        if next_logits[0, prev_id] > 0:
                            next_logits[0, prev_id] /= repetition_penalty
                        else:
                            next_logits[0, prev_id] *= repetition_penalty

                next_logits = next_logits / max(temperature, 1e-6)

                # Top-p sampling
                sorted_logits, sorted_idx = torch.sort(next_logits, descending=True)
                sorted_probs = F.softmax(sorted_logits, dim=-1)
                cum_probs = torch.cumsum(sorted_probs, dim=-1)
                sorted_logits[cum_probs - sorted_probs > top_p] = float("-inf")

                probs = F.softmax(sorted_logits, dim=-1)
                next_tok = sorted_idx[0, torch.multinomial(probs[0], 1)].item()

                if next_tok == eos:
                    break

                generated_ids.append(next_tok)

                if len(generated_ids) + ids.shape[1] >= max_seq:
                    break

                # Next iteration
                if use_kv_cache:
                    next_ids = torch.tensor([[next_tok]], device=device, dtype=torch.long)
                    logits, _ = model(next_ids, start_pos=cur_pos, use_cache=True)
                    cur_pos += 1
                else:
                    ids = torch.cat([ids, torch.tensor([[next_tok]], device=device)], dim=1)
                    logits, _ = model(ids)

        if not generated_ids:
            return None

        generated = tokenizer.decode(generated_ids, skip_special_tokens=False)
        for tok in (END, SOH, SUH, SAH):
            generated = generated.replace(tok, "")
        return generated.strip() or None

    except Exception as e:
        logger.error(f"sara_slm chat error: {e}")
        return None


# == Inference ===============================================================

def generate(user_id, prompt, max_new=200, temperature=0.8, top_p=0.9,
             repetition_penalty=1.15, min_p=0.05, use_kv_cache=True):
    """Generate text using only Sara SLM's own trained weights.

    Args:
        user_id: User identifier
        prompt: Input text
        max_new: Maximum new tokens to generate
        temperature: Sampling temperature (0.0 = greedy, higher = more random)
        top_p: Nucleus sampling threshold
        repetition_penalty: Penalty for repeating tokens (1.0 = no penalty)
        min_p: Minimum probability threshold (filters unlikely tokens)
        use_kv_cache: Use KV-cache for 3-5x faster generation (v2 only)
    """
    if not is_trained(user_id):
        return None

    torch, nn, F = _try_torch()
    if torch is None:
        return None

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if user_id not in _loaded_slm:
        try:
            from transformers import GPT2Tokenizer
            with open(_config_path(user_id)) as f:
                cfg = json.load(f)

            # Load state dict and detect version
            state_dict = torch.load(_weights_path(user_id), map_location="cpu")
            model_version = _detect_model_version(state_dict)

            # Build appropriate model architecture
            if model_version == "v1":
                logger.info(f"sara_slm: detected v1 weights for {user_id}, using v1 architecture")
                model = _build_model_v1(cfg)
                use_kv_cache = False  # v1 doesn't have KV-cache
            else:
                logger.info(f"sara_slm: detected v2 weights for {user_id}, using v2 architecture")
                model = _build_model(cfg)

            model.load_state_dict(state_dict)
            model.eval()
            model = model.to(device)
            tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
            tokenizer.pad_token = tokenizer.eos_token
            _loaded_slm[user_id] = (model, tokenizer, cfg, model_version)
            logger.info(f"sara_slm {model_version}: loaded for {user_id}")
        except Exception as e:
            logger.error(f"sara_slm load error: {e}")
            return None

    cache = _loaded_slm[user_id]
    if len(cache) == 2:
        model, tokenizer = cache
        cfg = DEFAULT_CONFIG
        model_version = "v1"
    elif len(cache) == 3:
        model, tokenizer, cfg = cache
        model_version = "v1"
    else:
        model, tokenizer, cfg, model_version = cache

    # v1 doesn't support KV-cache
    if model_version == "v1":
        use_kv_cache = False

    SOH = "<|" + "system|>"
    SUH = "<|" + "user|>"
    SAH = "<|" + "assistant|>"
    END = "</s>"
    SYSTEM = "You are Sara, a helpful and personal AI assistant. Answer concisely and naturally."

    full_prompt = (
        SOH + "\n" + SYSTEM + "\n" + END + "\n"
        + SUH + "\n" + prompt + "\n" + END + "\n"
        + SAH + "\n"
    )

    try:
        max_seq = int(cfg.get("max_seq", 1024))
        encoded = tokenizer.encode(full_prompt)
        encoded = encoded[-max_seq:]
        ids = torch.tensor(encoded, device=device, dtype=torch.long).unsqueeze(0)
        eos = tokenizer.eos_token_id
        generated_ids = []

        # Reset KV cache before generation (v2 only)
        if model_version == "v2" and hasattr(model, 'reset_cache'):
            model.reset_cache()

        with torch.no_grad():
            # Process prompt in one go (prefill)
            if use_kv_cache and model_version == "v2":
                logits, _ = model(ids, start_pos=0, use_cache=True)
                cur_pos = ids.shape[1]
            else:
                logits, _ = model(ids)
                cur_pos = 0

            for step in range(max_new):
                if use_kv_cache and model_version == "v2" and step > 0:
                    # Only process the last token (v2 with KV-cache)
                    next_ids = torch.tensor([[generated_ids[-1]]], device=device, dtype=torch.long)
                    logits, _ = model(next_ids, start_pos=cur_pos, use_cache=True)
                    cur_pos += 1

                next_logits = logits[:, -1, :].clone()

                # Apply repetition penalty
                if repetition_penalty != 1.0:
                    all_ids = ids[0].tolist() + generated_ids
                    for prev_id in set(all_ids[-50:]):  # Last 50 tokens
                        if next_logits[0, prev_id] > 0:
                            next_logits[0, prev_id] /= repetition_penalty
                        else:
                            next_logits[0, prev_id] *= repetition_penalty

                # Temperature scaling
                next_logits = next_logits / max(temperature, 1e-6)

                # Min-p filtering (removes very unlikely tokens)
                probs = F.softmax(next_logits, dim=-1)
                if min_p > 0:
                    max_prob = probs.max()
                    min_thresh = max_prob * min_p
                    next_logits = next_logits.masked_fill(probs < min_thresh, float("-inf"))

                # Top-p (nucleus) sampling
                sorted_logits, sorted_idx = torch.sort(next_logits, descending=True)
                sorted_probs = F.softmax(sorted_logits, dim=-1)
                cum_probs = torch.cumsum(sorted_probs, dim=-1)
                remove = cum_probs - sorted_probs > top_p
                sorted_logits[remove] = float("-inf")

                # Sample
                probs = F.softmax(sorted_logits, dim=-1)
                next_index = torch.multinomial(probs[0], 1)
                next_tok = sorted_idx[0, next_index].item()

                if next_tok == eos:
                    break

                generated_ids.append(next_tok)

                # Check token limit
                if len(generated_ids) + ids.shape[1] >= max_seq:
                    break

                # For non-KV-cache mode, concatenate and re-run
                if not use_kv_cache:
                    ids = torch.cat([ids, torch.tensor([[next_tok]], device=device)], dim=1)
                    logits, _ = model(ids)

        # Decode output
        if not generated_ids:
            return None

        generated = tokenizer.decode(generated_ids, skip_special_tokens=False)
        for tok in (END, SOH, SUH, SAH):
            generated = generated.replace(tok, "")
        return generated.strip() or None

    except Exception as e:
        logger.error(f"sara_slm generate error: {e}")
        return None


def generate_stream(user_id, prompt, max_new=200, temperature=0.8, top_p=0.9,
                    repetition_penalty=1.15, min_p=0.05):
    """Stream tokens one at a time for real-time output.

    Yields tokens as they are generated. Uses KV-cache for efficiency (v2 only).
    """
    if not is_trained(user_id):
        return

    torch, nn, F = _try_torch()
    if torch is None:
        return

    device = "cuda" if torch.cuda.is_available() else "cpu"

    if user_id not in _loaded_slm:
        try:
            from transformers import GPT2Tokenizer
            with open(_config_path(user_id)) as f:
                cfg = json.load(f)

            # Load state dict and detect version
            state_dict = torch.load(_weights_path(user_id), map_location="cpu")
            model_version = _detect_model_version(state_dict)

            if model_version == "v1":
                model = _build_model_v1(cfg)
            else:
                model = _build_model(cfg)

            model.load_state_dict(state_dict)
            model.eval()
            model = model.to(device)
            tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
            tokenizer.pad_token = tokenizer.eos_token
            _loaded_slm[user_id] = (model, tokenizer, cfg, model_version)
        except Exception as e:
            logger.error(f"sara_slm stream load error: {e}")
            return

    cache = _loaded_slm[user_id]
    if len(cache) == 4:
        model, tokenizer, cfg, model_version = cache
    elif len(cache) == 3:
        model, tokenizer, cfg = cache
        model_version = "v1"
    else:
        model, tokenizer = cache
        cfg = DEFAULT_CONFIG
        model_version = "v1"

    SOH, SUH, SAH, END = "<|system|>", "<|user|>", "<|assistant|>", "</s>"
    SYSTEM = "You are Sara, a helpful and personal AI assistant. Answer concisely and naturally."

    full_prompt = f"{SOH}\n{SYSTEM}\n{END}\n{SUH}\n{prompt}\n{END}\n{SAH}\n"

    try:
        max_seq = int(cfg.get("max_seq", 1024))
        encoded = tokenizer.encode(full_prompt)[-max_seq:]
        ids = torch.tensor(encoded, device=device, dtype=torch.long).unsqueeze(0)
        eos = tokenizer.eos_token_id
        generated_ids = []

        use_kv_cache = model_version == "v2"

        if use_kv_cache and hasattr(model, 'reset_cache'):
            model.reset_cache()

        with torch.no_grad():
            if use_kv_cache:
                logits, _ = model(ids, start_pos=0, use_cache=True)
                cur_pos = ids.shape[1]
            else:
                logits, _ = model(ids)
                cur_pos = 0

            for _ in range(max_new):
                next_logits = logits[:, -1, :].clone()

                # Repetition penalty
                if repetition_penalty != 1.0:
                    all_ids = ids[0].tolist() + generated_ids
                    for prev_id in set(all_ids[-50:]):
                        if next_logits[0, prev_id] > 0:
                            next_logits[0, prev_id] /= repetition_penalty
                        else:
                            next_logits[0, prev_id] *= repetition_penalty

                next_logits = next_logits / max(temperature, 1e-6)

                # Min-p + Top-p sampling
                probs = F.softmax(next_logits, dim=-1)
                if min_p > 0:
                    next_logits = next_logits.masked_fill(probs < probs.max() * min_p, float("-inf"))

                sorted_logits, sorted_idx = torch.sort(next_logits, descending=True)
                sorted_probs = F.softmax(sorted_logits, dim=-1)
                cum_probs = torch.cumsum(sorted_probs, dim=-1)
                sorted_logits[cum_probs - sorted_probs > top_p] = float("-inf")

                probs = F.softmax(sorted_logits, dim=-1)
                next_tok = sorted_idx[0, torch.multinomial(probs[0], 1)].item()

                if next_tok == eos:
                    break

                generated_ids.append(next_tok)
                token_text = tokenizer.decode([next_tok])

                # Filter special tokens
                if token_text not in (END, SOH, SUH, SAH):
                    yield token_text

                if len(generated_ids) + ids.shape[1] >= max_seq:
                    break

                # Next iteration
                if use_kv_cache:
                    next_ids = torch.tensor([[next_tok]], device=device, dtype=torch.long)
                    logits, _ = model(next_ids, start_pos=cur_pos, use_cache=True)
                    cur_pos += 1
                else:
                    ids = torch.cat([ids, torch.tensor([[next_tok]], device=device)], dim=1)
                    logits, _ = model(ids)

    except Exception as e:
        logger.error(f"sara_slm stream error: {e}")


# == Status ==================================================================

def format_slm_status(user_id):
    torch, _, _ = _try_torch()
    if torch is None:
        return (
            "🧠 *Sara SLM v2 -- Deps Missing*\n\n"
            "Install with:\n"
            "`pip install torch transformers`\n\n"
            "Then run /train\\_slm to train YOUR OWN AI from scratch!"
        )

    if is_training(user_id):
        return "🔄 *Sara SLM v2 is training right now!* I will notify you when done."

    meta = _load_meta(user_id)
    if not meta.get("trained"):
        return (
            "🧠 *Sara SLM v2 -- Not Trained Yet*\n\n"
            "Sara SLM v2 is a modern GPT-style model built from scratch.\n\n"
            "*Best training option:*\n"
            "  /train\\_slm\\_3stage - Full 3-stage pipeline:\n"
            "    Stage 1: Knowledge (Wikipedia, Stories)\n"
            "    Stage 2: Instructions (Orca, Alpaca)\n"
            "    Stage 3: Chat (ShareGPT, Your data)\n\n"
            "*Quick training option:*\n"
            "  /train\\_slm - Single-stage on all available data\n\n"
            "Features: RoPE + RMSNorm + SwiGLU + GQA + KV-Cache\n"
            "No LLaMA. No Mistral. 100% your weights."
        )

    n_params  = meta.get("n_params", 0)
    trained   = (meta.get("trained_at") or "")[:10]
    tokens    = meta.get("total_tokens", 0)
    samples   = meta.get("n_samples", 0)
    best_loss = meta.get("best_loss", 0.0)
    device    = meta.get("device", "cpu")
    cfg       = meta.get("config", DEFAULT_CONFIG)
    version   = meta.get("version", "v1")
    features  = meta.get("features", [])
    pipeline  = meta.get("training_pipeline", "single")
    stages    = meta.get("stages_completed", [])

    feature_str = " + ".join(features) if features else "Basic"

    status = (
        f"🧠 *Sara SLM {version} -- Active* ✅\n\n"
        f"  Model size:    *{n_params/1e6:.1f}M parameters*\n"
        f"  Architecture:  {cfg.get('n_layers', 8)} layers, "
            f"{cfg.get('n_heads', 8)} heads ({cfg.get('n_kv_heads', 8)} KV), dim {cfg.get('embed_dim', 512)}\n"
        f"  Context:       {cfg.get('max_seq', 1024)} tokens\n"
        f"  Features:      {feature_str}\n"
    )

    if pipeline == "3-stage":
        status += f"  Training:      3-Stage Pipeline ✅\n"
        if stages:
            stage_names = {1: "Knowledge", 2: "Instructions", 3: "Chat"}
            completed = ", ".join(stage_names.get(s, str(s)) for s in stages)
            status += f"  Stages:        {completed}\n"
    else:
        status += f"  Training:      Single-stage\n"

    status += (
        f"  Trained on:    {samples:,} samples | {tokens:,} tokens\n"
        f"  Best loss:     {best_loss:.4f}\n"
        f"  Last trained:  {trained} on {device.upper()}\n"
        f"  Weights:       Local only -- you own this model\n\n"
        "_Sara answers using her own modern brain -- no external AI!_"
    )

    return status


def delete_slm(user_id):
    import shutil
    d = os.path.join(DATA_DIR, user_id, SLM_DIR_NAME)
    if os.path.exists(d):
        shutil.rmtree(d, ignore_errors=True)
    _loaded_slm.pop(user_id, None)
    logger.info(f"sara_slm: deleted for {user_id}")
