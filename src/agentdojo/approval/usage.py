"""Provider-neutral extraction of token and cost data from API responses."""

from typing import Any


def requests_usage_cost(client: Any) -> bool:
    """Return whether the endpoint supports OpenRouter's cost opt-in body."""

    return "openrouter.ai" in str(getattr(client, "base_url", "")).lower()


def extract_usage(completion: Any) -> dict[str, int | float]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0}
    extras = getattr(usage, "model_extra", None) or {}
    cost = extras.get("cost", 0.0)
    return {
        "input_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "cost_usd": float(cost or 0.0),
    }


def add_usage(total: dict[str, int | float], addition: dict[str, int | float]) -> dict[str, int | float]:
    return {key: total.get(key, 0) + addition.get(key, 0) for key in total | addition}
