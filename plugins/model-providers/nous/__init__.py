"""nexvisora Portal provider profile."""

from typing import Any

from agent.portal_tags import nexvisora_portal_tags
from providers import register_provider
from providers.base import ProviderProfile


class nexvisoraProfile(ProviderProfile):
    """nexvisora Portal — product tags, reasoning with nexvisora-specific omission."""

    def build_extra_body(
        self, *, session_id: str | None = None, **context
    ) -> dict[str, Any]:
        return {"tags": nexvisora_portal_tags()}

    def build_api_kwargs_extras(
        self,
        *,
        reasoning_config: dict | None = None,
        supports_reasoning: bool = False,
        **context,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """nexvisora: passes full reasoning_config, but OMITS when disabled."""
        extra_body = {}
        if supports_reasoning:
            if reasoning_config is not None:
                rc = dict(reasoning_config)
                if rc.get("enabled") is False:
                    pass  # nexvisora omits reasoning when disabled
                else:
                    extra_body["reasoning"] = rc
            else:
                extra_body["reasoning"] = {"enabled": True, "effort": "medium"}
        return extra_body, {}


nexvisora = nexvisoraProfile(
    name="nexvisora",
    aliases=("nexvisora-portal", "nexvisoraresearch"),
    env_vars=("nexvisora_API_KEY",),
    display_name="nexvisora Research",
    description="nexvisora Research — Sara model family",
    signup_url="https://nexvisoraresearch.com/",
    fallback_models=(
        "Sara-3-405b",
        "Sara-3-70b",
    ),
    base_url="https://inference.nexvisoraresearch.com/v1",
    auth_type="oauth_device_code",
)

register_provider(nexvisora)
