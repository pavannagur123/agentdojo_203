"""Best-effort provenance labels for proposed tool arguments."""

import json
from collections.abc import Iterable, Sequence
from typing import Any

from agentdojo.approval.models import ArgumentOrigin
from agentdojo.types import ChatMessage, get_text_content_as_str


def _scalar_strings(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for nested in value.values():
            yield from _scalar_strings(nested)
    elif isinstance(value, list | tuple):
        for nested in value:
            yield from _scalar_strings(nested)
    elif value is not None:
        yield str(value)


def _message_text(messages: Sequence[ChatMessage], role: str) -> str:
    chunks = []
    for message in messages:
        if message["role"] == role and message["content"] is not None:
            chunks.append(get_text_content_as_str(message["content"]))
    return "\n".join(chunks).lower()


def infer_argument_origins(
    arguments: dict[str, Any], query: str, messages: Sequence[ChatMessage]
) -> dict[str, ArgumentOrigin]:
    """Label values found in trusted user text, prior tool output, or neither.

    User text wins when a value appears in both places. This is conservative
    about authority: an agent-created value is never silently marked as user
    supplied.
    """

    user_text = f"{query}\n{_message_text(messages, 'user')}".lower()
    tool_text = _message_text(messages, "tool")
    origins: dict[str, ArgumentOrigin] = {}
    for name, value in arguments.items():
        values = [item.strip().lower() for item in _scalar_strings(value) if item.strip()]
        serialized = json.dumps(value, sort_keys=True, default=str).lower()
        if values and all(item in user_text for item in values):
            origins[name] = ArgumentOrigin.USER
        elif (values and any(item in tool_text for item in values)) or serialized in tool_text:
            origins[name] = ArgumentOrigin.TOOL
        else:
            origins[name] = ArgumentOrigin.AGENT
    return origins
