import pytest

from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.models.query import QueryInput

EVALUATION_CASES = [
    {
        "name": "single_requirement",
        "query": "Find the owner of Project X",
        "expected_min_subqueries": 1,
        "expected_max_subqueries": 1,
        "required_terms": ["owner", "Project X"],
    },
    {
        "name": "multiple_requirements",
        "query": "Find the status and owner of Project X",
        "expected_min_subqueries": 2,
        "expected_max_subqueries": 2,
        "required_terms": ["status", "owner", "Project X"],
    },
    {
        "name": "cross_application_query",
        "query": (
            "Find the latest GitHub pull requests for Project X "
            "and the related Slack discussion"
        ),
        "expected_min_subqueries": 2,
        "expected_max_subqueries": 3,
        "required_terms": ["GitHub", "Slack", "Project X"],
    },
]


@pytest.mark.parametrize(
    "case",
    EVALUATION_CASES,
    ids=[case["name"] for case in EVALUATION_CASES],
)
async def test_decomposition_quality(case):
    llm = LMStudioLLM(temperature=0.0)
    decomposer = LLMQueryDecomposer(llm)

    result = await decomposer.decompose(QueryInput(query=case["query"]))

    subqueries = [item.sub_query for item in result.sub_queries]
    combined_output = " ".join(subqueries).lower()

    print(f"\nCase: {case['name']}")
    print(f"Query: {case['query']}")
    print(f"Subqueries: {subqueries}")

    assert (
        case["expected_min_subqueries"]
        <= len(subqueries)
        <= case["expected_max_subqueries"]
    ), f"Unexpected number of subqueries: {subqueries}"

    for term in case["required_terms"]:
        assert term.lower() in combined_output, (
            f"Missing required term {term!r}: {subqueries}"
        )

    assert all(item.strip() for item in subqueries)
    assert len({item.sub_query_id for item in result.sub_queries}) == len(
        result.sub_queries
    )
