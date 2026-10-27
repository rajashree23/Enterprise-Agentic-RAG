import pytest

from agentic_rag.orchestration.fast_path import is_clear_general_query

ROUTING_CASES = [
    # Clearly general questions: expected to use the fast path.
    ("general_what_is", "What is retrieval augmented generation?", True),
    ("general_explain", "Explain how vector search works.", True),
    ("general_define", "Define cosine similarity.", True),
    ("general_how", "How does a Python decorator work?", True),
    ("general_why", "Why is chunking useful in RAG?", True),
    ("general_write", "Write a short project summary.", True),
    ("general_draft", "Draft an interview introduction.", True),
    ("general_summarize", "Summarize this paragraph about embeddings.", True),
    ("general_trip", "Plan a trip to Milan.", True),
    ("general_report", "Write a report about prompt design.", True),
    # External-system requests: expected to use normal planning.
    ("tool_github", "What is the latest GitHub issue?", False),
    ("tool_repository", "Explain this repository's open work.", False),
    ("tool_repo", "Find bugs in the repo.", False),
    ("tool_slack", "Summarize the Slack discussion.", False),
    ("tool_notion", "Find the Notion page about onboarding.", False),
    # Ambiguous requests: expected to fall back to normal planning.
    ("ambiguous_status", "What is the status?", False),
    ("ambiguous_find", "Find the latest information.", False),
    ("ambiguous_search", "Search for authentication details.", False),
    ("ambiguous_current", "What is currently happening?", False),
    ("ambiguous_details", "Give me the details.", False),
]


@pytest.mark.parametrize(
    ("name", "query", "expected_fast_path"),
    ROUTING_CASES,
    ids=[case[0] for case in ROUTING_CASES],
)
def test_fast_path_routing_evaluation(name, query, expected_fast_path):
    assert is_clear_general_query(query) is expected_fast_path, (
        f"Unexpected routing for evaluation case {name!r}: {query!r}"
    )


def test_clear_general_query_uses_fast_path():
    assert is_clear_general_query("What is RAG?") is True
    assert is_clear_general_query("Plan a trip to Milan") is True


def test_external_system_hint_stays_on_normal_path():
    assert is_clear_general_query("What is the latest GitHub issue?") is False
    assert is_clear_general_query("Explain this repository") is False


def test_tool_hints_are_matched_as_words():
    assert is_clear_general_query("Write a report about RAG") is True


def test_writing_request_can_include_project_context():
    assert is_clear_general_query("Write a short project summary.") is True
