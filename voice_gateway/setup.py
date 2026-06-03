"""
Sara Voice Gateway setup script.
Registers the voice gateway as a sara platform component.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from gateway.platform_registry import platform_registry, PlatformEntry

    def _check_fn() -> bool:
        try:
            import fastapi
            import uvicorn
            import httpx
            return True
        except ImportError:
            return False

    def _validate_config(config) -> bool:
        return True

    entry = PlatformEntry(
        name="voice_assistant",
        label="Voice Assistant",
        adapter_factory=lambda cfg: None,  # Handled by built-in path
        check_fn=_check_fn,
        validate_config=_validate_config,
        required_env=["VOICE_ASSISTANT_ENABLED"],
        install_hint="pip install fastapi uvicorn httpx",
        emoji="🎤",
        platform_hint=(
            "You are a voice assistant on the user's device. "
            "Keep responses concise and conversational since they will be "
            "read aloud via text-to-speech."
        ),
        max_message_length=4096,
        pii_safe=True,
        allow_update_command=False,
    )

    platform_registry.register(entry)
    logger.info("Voice Assistant platform registered")

except ImportError:
    logger.debug("Voice Assistant setup: gateway modules not available")
except Exception as e:
    logger.debug("Voice Assistant setup skipped: %s", e)
