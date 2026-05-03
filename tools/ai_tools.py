"""
tools/ai_tools.py — AI Content Tools powered by LangChain + Ollama.

Tools:
  generate_text(prompt)      — Write articles, emails, scripts, code
  summarize_text(text)       — Summarize long text
  analyze_document(path)     — Read a file and produce an AI summary
"""

import os
import logging

logger = logging.getLogger(__name__)

MAX_INPUT_CHARS = 8000  # Limit text fed into the LLM to avoid OOM


def generate_text(prompt: str) -> str:
    """Generate text content (articles, emails, code, etc.) from a prompt."""
    prompt = prompt.strip()
    if not prompt:
        return "❓ Please provide a prompt, e.g. 'write a Python script that...' "

    from brain.llm_engine import ask_ai_with_chain
    result = ask_ai_with_chain(
        system=(
            "You are a professional AI writer and developer. "
            "Generate high-quality, well-structured content based on the user's request. "
            "Be concise and clear. Use markdown formatting where appropriate."
        ),
        human=prompt,
    )
    return f"✍️ **Generated:**\n\n{result}"


def summarize_text(text: str) -> str:
    """Summarize a block of text."""
    text = text.strip()
    if not text:
        return "❓ Please provide text to summarize."

    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + "\n...[truncated]"

    from brain.llm_engine import ask_ai_with_chain
    result = ask_ai_with_chain(
        system=(
            "You are an expert summarizer. "
            "Produce a clear, concise summary that captures the key points. "
            "Use bullet points if there are multiple main ideas."
        ),
        human=f"Summarize this:\n\n{text}",
    )
    return f"📝 **Summary:**\n\n{result}"


def analyze_document(file_path: str) -> str:
    """Read a text/PDF-like file and produce an AI analysis."""
    path = file_path.strip().strip('"').strip("'")

    if not os.path.isfile(path):
        return f"❌ File not found: `{path}`"

    ext = os.path.splitext(path)[1].lower()

    # Read content depending on type
    try:
        if ext == ".pdf":
            try:
                import pdfplumber
                with pdfplumber.open(path) as pdf:
                    content = "\n".join(
                        page.extract_text() or "" for page in pdf.pages
                    )
            except ImportError:
                return (
                    "❌ Reading PDFs requires `pdfplumber`.\n"
                    "Run: `pip install pdfplumber`"
                )
        else:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
    except PermissionError:
        return f"⛔ Permission denied: `{path}`"
    except Exception as e:
        return f"❌ Could not read file: {e}"

    if not content.strip():
        return f"⚠️ File appears to be empty or unreadable: `{path}`"

    if len(content) > MAX_INPUT_CHARS:
        content = content[:MAX_INPUT_CHARS] + "\n...[truncated]"

    from brain.llm_engine import ask_ai_with_chain
    result = ask_ai_with_chain(
        system=(
            "You are a document analyst. Analyze the given document and provide: "
            "1. A brief summary (2-3 sentences). "
            "2. Key topics or themes. "
            "3. Any important findings, conclusions, or action items. "
            "Be concise and professional."
        ),
        human=f"Document: {os.path.basename(path)}\n\n{content}",
    )
    return f"📊 **Analysis of `{os.path.basename(path)}`:**\n\n{result}"
