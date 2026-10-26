"""Compile trusted user text into BASIL's scoped-intent ledger."""

import re

from agentdojo.approval.models import AuthorizationClause, AuthorizationContract

_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9_@.:'/-]*")
_CLAUSE_BOUNDARY = re.compile(r"(?:[.!?]+|\bthen\b|\bafter that\b|\bbut\b)", flags=re.IGNORECASE)
_NEGATION_PATTERN = re.compile(r"\b(?:do not|don't|never|must not|without)\b", flags=re.IGNORECASE)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "please",
    "that",
    "the",
    "this",
    "to",
    "with",
    "you",
}


def tokenize(text: str) -> set[str]:
    """Return stable, lower-case intent tokens without conversational filler."""

    return {token for token in _TOKEN_PATTERN.findall(text.lower()) if token not in _STOPWORDS}


class RuleBasedIntentCompiler:
    """Create an inspectable contract without making another model call.

    The compiler intentionally preserves the source wording. It does not add
    permissions inferred from tool output or from the agent's own reasoning.
    """

    def compile(self, query: str) -> AuthorizationContract:
        parts = [part.strip(" ,") for part in _CLAUSE_BOUNDARY.split(query) if part.strip(" ,")]
        if not parts:
            parts = [query]
        split_parts: list[tuple[str, bool]] = []
        for part in parts:
            normalized = re.sub(r"\b(?:do not|don't) forget to\b", "", part, flags=re.I).strip()
            negative = _NEGATION_PATTERN.search(normalized)
            if negative is None:
                split_parts.append((part, False))
                continue
            affirmative = normalized[: negative.start()].strip(" ,")
            prohibition = normalized[negative.start() :].strip(" ,")
            if affirmative:
                split_parts.append((affirmative, False))
            if prohibition:
                split_parts.append((prohibition, True))
        clauses = tuple(
            AuthorizationClause(
                clause_id=f"request-{index}",
                text=text,
                tokens=tokenize(text),
                prohibited=prohibited,
            )
            for index, (text, prohibited) in enumerate(split_parts, start=1)
        )
        return AuthorizationContract(original_request=query, clauses=clauses)
