from agentic_rag.prompts.decomposition import (
    PROMPT_ID as DECOMPOSITION_ID,
)
from agentic_rag.prompts.decomposition import (
    PROMPT_VERSION as DECOMPOSITION_VERSION,
)
from agentic_rag.prompts.decomposition import (
    build_decomposition_prompt,
)
from agentic_rag.prompts.planning import (
    PROMPT_ID as PLANNING_ID,
)
from agentic_rag.prompts.planning import (
    PROMPT_VERSION as PLANNING_VERSION,
)
from agentic_rag.prompts.planning import (
    build_planning_prompt,
)


def test_decomposition_prompt_contains_query():
    prompt = build_decomposition_prompt("Find Project X status")

    assert "Find Project X status" in prompt
    assert "sub_queries" in prompt
    assert DECOMPOSITION_ID == "query_decomposition"
    assert DECOMPOSITION_VERSION == "v1"


def test_planning_prompt_contains_subqueries():
    prompt = build_planning_prompt("- sq-1: Find Project X status")

    assert "sq-1: Find Project X status" in prompt
    assert "github.search" in prompt
    assert PLANNING_ID == "query_planning"
    assert PLANNING_VERSION == "v1"
