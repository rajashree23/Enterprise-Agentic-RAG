"""Conservative routing for queries that clearly do not need tools."""

import re

TOOL_HINTS = (
    "github",
    "repository",
    "repo",
    "issue",
    "pull request",
    "pull-request",
    "slack",
    "notion",
)

WORKSPACE_HINTS = ("project",)

AMBIGUOUS_HINTS = (
    "currently",
    "latest",
    "status",
    "happening",
    "details",
    "information",
)

GENERAL_QUERY_PREFIXES = (
    "what is ",
    "what are ",
    "what does ",
    "explain ",
    "define ",
    "how does ",
    "how do ",
    "why does ",
    "why is ",
    "write ",
    "draft ",
    "summarize ",
    "plan a ",
)

WRITING_PREFIXES = ("write ", "draft ", "summarize ")


def is_clear_general_query(query: str) -> bool:
    """Return true only for queries safe to route around planning.

    The gate is intentionally conservative: external-system hints always keep
    the request on the normal decomposition and planning path.
    """

    normalized = " ".join(query.casefold().split())
    if any(re.search(rf"\b{re.escape(hint)}\b", normalized) for hint in TOOL_HINTS):
        return False

    if any(
        re.search(rf"\b{re.escape(hint)}\b", normalized) for hint in AMBIGUOUS_HINTS
    ):
        return False

    # Writing requests can mention a project as user-provided context without
    # requiring retrieval from an enterprise system.
    if normalized.startswith(WRITING_PREFIXES):
        return True

    if any(
        re.search(rf"\b{re.escape(hint)}\b", normalized) for hint in WORKSPACE_HINTS
    ):
        return False

    return normalized.startswith(GENERAL_QUERY_PREFIXES)
