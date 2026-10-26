import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentic_rag.llm.interface import LLM
from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)
from agentic_rag.models.execution_result import ToolCalled
from agentic_rag.models.query import QueryInput
from agentic_rag.synthesis.llm_synthesizer import LLMAnswerSynthesizer


def make_response(evidence_id):
    return json.dumps(
        {
            "claims": [
                {
                    "text": "Migration approval remains pending.",
                    "citations": [{"evidence_id": evidence_id}],
                }
            ],
            "limitations": [],
        }
    )


@pytest.fixture
def inputs():
    evidence = Evidence(
        evidence_id=str(uuid4()),
        step_id=str(uuid4()),
        sub_query_id=str(uuid4()),
        tool_called=ToolCalled(
            tool_id="github.list_issue_comments",
            tool_name="github.list_issue_comments",
        ),
        source=EvidenceSource(
            system="github",
            record_type="issue_comment",
            record_id="123",
            url="https://github.com/acme/payments/issues/1#issuecomment-123",
        ),
        content="Migration approval remains pending.",
        tool_response=[{"raw_marker": "RAW_RECORD_NOT_NEEDED"}],
    )

    unrelated = evidence.model_copy(
        update={
            "evidence_id": str(uuid4()),
            "content": "UNRELATED_CONTENT_NOT_NEEDED",
        }
    )

    return {
        "query_input": QueryInput(query="What blocks rollout?"),
        "assessment": EvidenceAssessment(
            status="sufficient",
            reason="The comment identifies the blocker.",
            relevant_evidence_ids=[evidence.evidence_id],
            gaps=[],
        ),
        "evidence": [evidence, unrelated],
    }


@pytest.fixture
def llm(inputs):
    mock = AsyncMock(spec=LLM)
    mock.generate.return_value = make_response(inputs["evidence"][0].evidence_id)
    return mock


@pytest.mark.asyncio
async def test_synthesizes_from_selected_evidence(llm, inputs):
    result = await LLMAnswerSynthesizer(llm).synthesize(**inputs)

    evidence = inputs["evidence"][0]
    assert result.claims[0].citations[0].evidence_id == evidence.evidence_id
    assert result.limitations == []

    llm.generate.assert_awaited_once()
    prompt = llm.generate.call_args.args[0]
    context = json.loads(prompt.split("Untrusted context as JSON:\n", maxsplit=1)[1])

    assert context["query"] == "What blocks rollout?"
    assert len(context["evidence"]) == 1
    assert context["evidence"][0]["evidence_id"] == evidence.evidence_id
    assert "tool_response" not in context["evidence"][0]
    assert "RAW_RECORD_NOT_NEEDED" not in prompt
    assert "UNRELATED_CONTENT_NOT_NEEDED" not in prompt


@pytest.mark.asyncio
async def test_preserves_partial_answer_limitations(llm, inputs):
    inputs["assessment"] = EvidenceAssessment(
        status="partial",
        reason="Some discussion remains unread.",
        relevant_evidence_ids=[
            inputs["evidence"][0].evidence_id,
        ],
        gaps=["Additional comments remain unread."],
    )

    result = await LLMAnswerSynthesizer(llm).synthesize(**inputs)

    assert "Additional comments remain unread." in result.limitations
    assert (
        "The available evidence supports only a partial answer." in result.limitations
    )


@pytest.mark.asyncio
async def test_insufficient_assessment_skips_llm(llm, inputs):
    inputs["assessment"] = EvidenceAssessment(
        status=AssessmentStatus.INSUFFICIENT,
        reason="The question is not supported.",
        relevant_evidence_ids=[],
        gaps=["Relevant evidence is missing."],
    )

    with pytest.raises(ValueError, match="insufficient evidence"):
        await LLMAnswerSynthesizer(llm).synthesize(**inputs)

    llm.generate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("references", [[], ["invented-id"]])
async def test_invalid_assessment_references_skip_llm(
    llm,
    inputs,
    references,
):
    inputs["assessment"] = EvidenceAssessment(
        status="sufficient",
        reason="Assessment explanation.",
        relevant_evidence_ids=references,
        gaps=[],
    )

    with pytest.raises(ValueError):
        await LLMAnswerSynthesizer(llm).synthesize(**inputs)

    llm.generate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        "not valid JSON",
        json.dumps({"claims": [], "limitations": []}),
    ],
)
async def test_rejects_malformed_output(llm, inputs, response):
    llm.generate.return_value = response

    with pytest.raises(ValidationError):
        await LLMAnswerSynthesizer(llm).synthesize(**inputs)


@pytest.mark.asyncio
@pytest.mark.parametrize("citation_type", ["unknown", "unselected"])
async def test_rejects_out_of_scope_citations(
    llm,
    inputs,
    citation_type,
):
    evidence_id = (
        "invented-id"
        if citation_type == "unknown"
        else inputs["evidence"][1].evidence_id
    )
    llm.generate.return_value = make_response(evidence_id)

    with pytest.raises(ValueError, match="unknown evidence"):
        await LLMAnswerSynthesizer(llm).synthesize(**inputs)


@pytest.mark.asyncio
async def test_propagates_llm_failure(llm, inputs):
    llm.generate.side_effect = TimeoutError("Model request timed out")

    with pytest.raises(TimeoutError):
        await LLMAnswerSynthesizer(llm).synthesize(**inputs)

    llm.generate.assert_awaited_once()
