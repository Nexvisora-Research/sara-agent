"""
llm_engine.py — Multi-AI brain for Sara AI.

Provider priority:
  1. CLAUDE AI (premium, cloud)     — claude-3.5-sonnet / claude-3-haiku
  2. GROQ CLOUD (ultra-fast, cloud) — mixtral-8x7b / llama3-70b
  3. OLLAMA (local fallback)        — gemma3:1b / phi4-mini / mistral:7b

Model tiers:
  - FAST     : greetings, quick facts, simple chat
  - SMART    : tool calls, JSON, multi-step reasoning
  - CREATIVE : summaries, writing, analysis

Public API:
  ask_ai(prompt)            → FAST by default
  ask_ai_smart(prompt)      → always SMART
  ask_ai_creative(prompt)   → always CREATIVE
  ask_ai_best(prompt)       → auto-routes based on content
  ask_ai_with_chain(s, h)   → LangChain structured call (SMART)
  get_model_status()        → shows which models/providers are active
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

# ── Groq Cloud config ─────────────────────────────────────────────────────────
# Set GROQ_API_KEY in your .env file or environment variable.
# Get a free key at: https://console.groq.com
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional

# ── Claude AI config ──────────────────────────────────────────────────────────
# Set ANTHROPIC_API_KEY in your .env file or environment variable.
# Get a free key at: https://console.anthropic.com
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Claude model tiers (premium quality, best reasoning)
CLAUDE_MODELS = {
    "fast":     "claude-3-haiku-20240307",        # Fast, cost-effective
    "smart":    "claude-3-5-sonnet-20241022",     # Best reasoning & coding
    "creative": "claude-3-5-sonnet-20241022",     # Best writing quality
}

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Groq model tiers (blazing fast — typically <1s response)
GROQ_MODELS = {
    "fast":     "llama-3.1-8b-instant",     # Ultra-fast, great for chat & tool calls
    "smart":    "llama-3.3-70b-versatile",  # Large model for complex reasoning
    "creative": "llama-3.3-70b-versatile",  # Best writing quality
}

# ── Ollama fallback config ────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
TIMEOUT_SECONDS = 60

OLLAMA_MODELS = {
    "fast":     "gemma3:1b",    # Default — instant replies
    "smart":    "phi4-mini",    # Tool calls, JSON, reasoning
    "creative": "mistral:7b",   # Writing, summaries, analysis
}

# ── LLM cache ─────────────────────────────────────────────────────────────────
_llm_cache: dict = {}
_groq_client = None
_claude_client = None


# ── Claude caller ─────────────────────────────────────────────────────────────

def _get_claude_client():
    """Return (and cache) the Claude client. Returns None if unavailable."""
    global _claude_client
    if _claude_client is not None:
        return _claude_client
    if not ANTHROPIC_API_KEY:
        logger.debug("ANTHROPIC_API_KEY not set — skipping Claude.")
        return None
    try:
        from anthropic import Anthropic
        _claude_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("✅ Claude client initialised.")
        return _claude_client
    except ImportError:
        logger.warning("anthropic package not installed. Run: pip install anthropic")
        return None
    except Exception as e:
        logger.warning(f"Claude init failed: {e}")
        return None


def _call_claude(tier: str, prompt: str) -> "str | None":
    """Call Claude AI. Returns None if Claude is unavailable."""
    client = _get_claude_client()
    if client is None:
        return None
    model = CLAUDE_MODELS.get(tier, CLAUDE_MODELS["fast"])
    try:
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        result = message.content[0].text.strip()
        logger.debug(f"Claude ({model}) → {len(result)} chars")
        return result
    except Exception as e:
        err = str(e).lower()
        if "authentication" in err or "401" in err or "api_key" in err:
            logger.error("Claude: Invalid API key.")
        elif "rate" in err or "429" in err:
            logger.warning("Claude: Rate limit hit — falling back to Groq.")
        elif "overloaded" in err or "529" in err:
            logger.warning("Claude: Service overloaded — falling back to Groq.")
        else:
            logger.warning(f"Claude error: {e} — falling back to Groq.")
        return None


# ── Groq caller ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Return (and cache) the Groq client. Returns None if unavailable."""
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    if not GROQ_API_KEY:
        logger.debug("GROQ_API_KEY not set — skipping Groq.")
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Groq client initialised.")
        return _groq_client
    except ImportError:
        logger.warning("groq package not installed. Run: pip install groq")
        return None
    except Exception as e:
        logger.warning(f"Groq init failed: {e}")
        return None


def _call_groq(tier: str, prompt: str) -> "str | None":
    """Call Groq Cloud. Returns None if Groq is unavailable."""
    client = _get_groq_client()
    if client is None:
        return None
    model = GROQ_MODELS.get(tier, GROQ_MODELS["fast"])
    try:
        chat = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.7,
        )
        result = chat.choices[0].message.content.strip()
        logger.debug(f"Groq ({model}) → {len(result)} chars")
        return result
    except Exception as e:
        err = str(e).lower()
        if "authentication" in err or "401" in err:
            logger.error("Groq: Invalid API key.")
        elif "rate" in err or "429" in err:
            logger.warning("Groq: Rate limit hit — falling back to Ollama.")
        elif "model" in err and "not found" in err:
            logger.warning(f"Groq: Model '{model}' not found — falling back.")
        else:
            logger.warning(f"Groq error: {e} — falling back to Ollama.")
        return None


# ── Ollama caller ─────────────────────────────────────────────────────────────

def _get_ollama_llm(model: str):
    """Return (and cache) a LangChain OllamaLLM instance."""
    if model not in _llm_cache:
        try:
            from langchain_ollama import OllamaLLM
            _llm_cache[model] = OllamaLLM(
                model=model,
                base_url=OLLAMA_BASE_URL,
                timeout=TIMEOUT_SECONDS,
            )
            logger.info(f"Ollama LLM cached: {model}")
        except ImportError:
            logger.warning("langchain-ollama not installed — using raw requests.")
            _llm_cache[model] = None
    return _llm_cache[model]


def _call_ollama(model: str, prompt: str) -> str:
    """Invoke Ollama via LangChain, with raw-requests fallback."""
    llm = _get_ollama_llm(model)

    if llm is not None:
        try:
            return str(llm.invoke(prompt)).strip()
        except Exception as e:
            err = str(e).lower()
            if "connection" in err or "refused" in err:
                return "⚠️ Ollama is not running. Start it with: ollama serve"
            if "timeout" in err:
                return "⚠️ Ollama timed out. Try a lighter model or restart Ollama."
            logger.warning(f"LangChain error ({model}): {e} — falling back to requests")

    # Raw requests fallback
    import requests
    try:
        r = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=TIMEOUT_SECONDS,
        )
        r.raise_for_status()
        return r.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        return "⚠️ Ollama is not running. Start it with: ollama serve"
    except requests.exceptions.Timeout:
        return "⚠️ Ollama timed out. Try again or use a faster model."
    except requests.exceptions.HTTPError as e:
        return f"⚠️ Ollama HTTP error: {e}"
    except (KeyError, ValueError):
        return "⚠️ Unexpected response format from Ollama."


# ── Unified caller — Claude first, Groq second, Ollama fallback ──────────────

def _call(tier: str, prompt: str) -> str:
    """
    Try Claude AI first (premium). Fall back to Groq, then Ollama.
    tier: 'fast' | 'smart' | 'creative'
    """
    # 1️⃣ Try Claude
    result = _call_claude(tier, prompt)
    if result is not None:
        return result

    # 2️⃣ Try Groq
    result = _call_groq(tier, prompt)
    if result is not None:
        return result

    # 3️⃣ Fall back to Ollama
    model = OLLAMA_MODELS.get(tier, OLLAMA_MODELS["fast"])
    logger.info(f"Using Ollama fallback: {model}")
    return _call_ollama(model, prompt)


# ── Smart router ──────────────────────────────────────────────────────────────

_SMART_PATTERNS = re.compile(
    r"(open|launch|run|execute|search|find|calculate|convert|set|remind|schedule|"
    r"install|delete|move|copy|create|start|stop|play|pause|volume|brightness|"
    r"weather|time|date|news|translate|code|debug|fix|explain (code|error|bug)|"
    r"what is \d|how (do|does|can|to)|why (does|is|can)|compare|difference between|"
    r"step[- ]by[- ]step|walk me through|help me (with|to)|json|api|function)",
    re.IGNORECASE,
)

_CREATIVE_PATTERNS = re.compile(
    r"(summarize|summary|summarise|write (a|an|me)|rewrite|rephrase|proofread|"
    r"explain (like|in simple|to a)|describe|tell me (a story|about)|"
    r"essay|poem|story|blog|email|letter|report|draft|analyse|analyze|review|"
    r"pros and cons|list (the|some|a few)|give me (ideas|suggestions|examples))",
    re.IGNORECASE,
)

_TRIVIAL_PATTERNS = re.compile(
    r"^(hi+|hey+|hello|howdy|hiya|yo|sup|what'?s up|how are you|"
    r"good (morning|afternoon|evening|night)|thanks?|thank you|"
    r"bye|goodbye|see ya|ok+|okay|sure|cool|nice|great|awesome|lol|haha)[\s!?.]*$",
    re.IGNORECASE,
)


def _route(prompt: str) -> str:
    """Pick the best model tier for a given prompt."""
    last_line = prompt.strip().split("\n")[-1]
    user_text = re.sub(r"^(user|human):\s*", "", last_line, flags=re.IGNORECASE).strip()

    if _TRIVIAL_PATTERNS.match(user_text):
        logger.debug("Router → FAST (trivial)")
        return "fast"

    if _SMART_PATTERNS.search(user_text):
        logger.debug("Router → SMART (tool/reasoning)")
        return "smart"

    if _CREATIVE_PATTERNS.search(user_text):
        logger.debug("Router → CREATIVE (writing/analysis)")
        return "creative"

    logger.debug("Router → FAST (default)")
    return "fast"


# ── Public API ────────────────────────────────────────────────────────────────

def ask_ai(prompt: str) -> str:
    """Default entry point — uses FAST model."""
    return _call("fast", prompt)


def ask_ai_smart(prompt: str) -> str:
    """Force SMART model — for tool calls, JSON, complex reasoning."""
    return _call("smart", prompt)


def ask_ai_creative(prompt: str) -> str:
    """Force CREATIVE model — for writing, summaries, and analysis."""
    return _call("creative", prompt)


def ask_ai_best(prompt: str) -> str:
    """Auto-route to the most appropriate model based on prompt content."""
    return _call(_route(prompt), prompt)


def ask_ai_with_chain(system: str, human: str) -> str:
    """
    Structured call with separate system/human messages.
    Uses SMART model — best for tool decisions and structured output.
    Tries Claude first, then Groq, then LangChain Ollama.
    """
    # Try Claude with proper system+user message format
    client = _get_claude_client()
    if client is not None:
        try:
            message = client.messages.create(
                model=CLAUDE_MODELS["smart"],
                max_tokens=2048,
                system=system,
                messages=[{"role": "user", "content": human}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            logger.warning(f"Claude chain error: {e} — falling back to Groq")

    # Try Groq with proper system+user message format
    groq_client = _get_groq_client()
    if groq_client is not None:
        try:
            chat = groq_client.chat.completions.create(
                model=GROQ_MODELS["smart"],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": human},
                ],
                max_tokens=2048,
                temperature=0.7,
            )
            return chat.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Groq chain error: {e} — falling back to Ollama")

    # Ollama LangChain fallback
    try:
        from langchain_ollama import OllamaLLM
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        llm = OllamaLLM(model=OLLAMA_MODELS["smart"], base_url=OLLAMA_BASE_URL, timeout=TIMEOUT_SECONDS)
        prompt_tmpl = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "{input}"),
        ])
        chain = prompt_tmpl | llm | StrOutputParser()
        return chain.invoke({"input": human}).strip()

    except ImportError:
        return ask_ai_smart(f"{system}\n\n{human}")
    except Exception as e:
        err = str(e).lower()
        if "connection" in err or "refused" in err:
            return "⚠️ Ollama is not running. Start it with: ollama serve"
        return f"⚠️ AI chain error: {e}"


def get_model_status() -> str:
    """Report which providers and models are active."""
    lines = ["🤖 **AI Provider Status:**\n"]

    # Claude status
    if ANTHROPIC_API_KEY:
        client = _get_claude_client()
        if client:
            lines.append("🔷 **CLAUDE AI** (premium) — Active")
            for tier, model in CLAUDE_MODELS.items():
                lines.append(f"   {tier.upper():<10} {model}")
        else:
            lines.append("🔷 **CLAUDE AI** — ❌ Init failed (check API key)")
    else:
        lines.append("🔷 **CLAUDE AI** — ⚠️ No API key set (set ANTHROPIC_API_KEY in .env)")

    lines.append("")

    # Groq status
    if GROQ_API_KEY:
        client = _get_groq_client()
        if client:
            lines.append("⚡ **GROQ CLOUD** (secondary) — Active")
            for tier, model in GROQ_MODELS.items():
                lines.append(f"   {tier.upper():<10} {model}")
        else:
            lines.append("⚡ **GROQ CLOUD** — ❌ Init failed (check API key)")
    else:
        lines.append("⚡ **GROQ CLOUD** — ⚠️ No API key set (set GROQ_API_KEY in .env)")

    lines.append("")

    # Ollama status
    import requests
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        pulled_names = {m["name"].split(":")[0] for m in r.json().get("models", [])}
        lines.append("🖥️ **OLLAMA** (fallback) — Running")
        for tier, model in OLLAMA_MODELS.items():
            short = model.split(":")[0]
            tag = "✅" if short in pulled_names else "❌ not pulled"
            lines.append(f"   {tier.upper():<10} {model:<20} {tag}")
    except Exception:
        lines.append("🖥️ **OLLAMA** (fallback) — ⚠️ Not running")

    return "\n".join(lines)