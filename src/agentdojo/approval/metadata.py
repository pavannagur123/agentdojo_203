"""Infer security effects from AgentDojo tool names and descriptions."""

import re

from agentdojo.approval.models import RiskLevel, ToolEffect, ToolMetadata

_WORD_PATTERN = re.compile(r"[a-z0-9]+")

_READ_VERBS = {"check", "fetch", "find", "get", "list", "lookup", "read", "retrieve", "search"}
_WRITE_VERBS = {
    "add",
    "append",
    "book",
    "create",
    "invite",
    "post",
    "reserve",
    "reschedule",
    "schedule",
    "set",
    "share",
    "update",
    "upload",
}
_DELETE_VERBS = {"cancel", "delete", "remove", "revoke"}
_COMMUNICATION_TERMS = {"invite", "message", "post", "send", "share"}
_FINANCIAL_TERMS = {"bank", "iban", "money", "pay", "payment", "transaction", "transfer"}
_PERMISSION_TERMS = {"invite", "participant", "permission", "share", "user"}
_AUTHENTICATION_TERMS = {"credential", "login", "password"}
_EXTERNAL_TERMS = {"flight", "hotel", "restaurant", "rental", "webpage"}

_ALIASES = {
    "add": {"add", "include", "invite"},
    "append": {"add", "append", "write"},
    "cancel": {"cancel", "delete", "remove"},
    "create": {"add", "create", "make", "new", "set"},
    "delete": {"cancel", "delete", "remove"},
    "email": {"email", "mail", "send"},
    "invite": {"add", "invite"},
    "message": {"message", "notify", "send", "tell"},
    "post": {"post", "publish"},
    "remove": {"cancel", "delete", "remove", "revoke"},
    "reserve": {"book", "reserve", "reservation"},
    "reschedule": {"change", "move", "reschedule", "update"},
    "schedule": {"create", "schedule", "set"},
    "send": {"email", "message", "pay", "post", "refund", "reply", "send", "transfer", "write"},
    "share": {"grant", "permission", "share"},
    "update": {"adjust", "change", "edit", "modify", "update"},
}


def _words(value: str) -> set[str]:
    return set(_WORD_PATTERN.findall(value.lower()))


def infer_tool_metadata(name: str, description: str = "") -> ToolMetadata:
    """Classify a tool using deterministic, auditable vocabulary rules."""

    name_terms = _words(name)
    effects: set[ToolEffect] = set()
    if name_terms & _DELETE_VERBS:
        effects.add(ToolEffect.DELETE)
    if name_terms & _WRITE_VERBS:
        effects.add(ToolEffect.WRITE)
    if name_terms & _COMMUNICATION_TERMS:
        effects.add(ToolEffect.COMMUNICATE)
    if name_terms & _FINANCIAL_TERMS and effects:
        effects.add(ToolEffect.FINANCIAL)
    if name_terms & _PERMISSION_TERMS and effects:
        effects.add(ToolEffect.PERMISSION)
    if name_terms & _AUTHENTICATION_TERMS:
        effects.add(ToolEffect.AUTHENTICATION)
        if "update" in name_terms or "set" in name_terms:
            effects.add(ToolEffect.WRITE)
    if name_terms & _EXTERNAL_TERMS and effects:
        effects.add(ToolEffect.EXTERNAL)
    if not effects or name_terms & _READ_VERBS:
        effects.add(ToolEffect.READ)

    if ToolEffect.AUTHENTICATION in effects or ToolEffect.FINANCIAL in effects:
        risk = RiskLevel.CRITICAL
    elif ToolEffect.DELETE in effects or ToolEffect.PERMISSION in effects:
        risk = RiskLevel.HIGH
    elif any(effect != ToolEffect.READ for effect in effects):
        risk = RiskLevel.MEDIUM
    else:
        risk = RiskLevel.LOW

    operation_terms = name_terms & (_WRITE_VERBS | _DELETE_VERBS | _COMMUNICATION_TERMS)
    action_terms = set(operation_terms)
    for term in operation_terms:
        action_terms.update(_ALIASES.get(term, set()))
    return ToolMetadata(
        name=name,
        description=description,
        effects=frozenset(effects),
        risk=risk,
        operation_terms=frozenset(operation_terms),
        action_terms=frozenset(action_terms),
    )
