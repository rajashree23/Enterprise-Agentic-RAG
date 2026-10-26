import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from agentic_rag.assessment.llm_assessor import LLMEvidenceAssessor
from agentic_rag.llm.interface import LLM
from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.evidence_assessment import AssessmentStatus
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
    ToolCalled,
)
from agentic_rag.models.query import (
    NormalizationWarning,
    QueryInput,
)


@pytest.fixture
def evidence():
    return Evidence(
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
    )


@pytest.fixture
def llm():
    return AsyncMock(spec=LLM)


@pytest.mark.asyncio
async def test_assesses_supplied_evidence(llm, evidence):
    llm.generate.return_value = json.dumps(
        {
            "status": "sufficient",
            "reason": "The comment identifies the blocker.",
            "relevant_evidence_ids": [evidence.evidence_id],
            "gaps": [],
        }
    )

    assessment = await LLMEvidenceAssessor(llm).assess(
        query_input=QueryInput(query="What blocks rollout?"),
        evidence=[evidence],
        execution_results=[],
        normalization_warnings=[],
    )

    assert assessment.status == AssessmentStatus.SUFFICIENT
    assert assessment.relevant_evidence_ids == [evidence.evidence_id]
    llm.generate.assert_awaited_once()

    prompt = llm.generate.call_args.args[0]
    assert evidence.evidence_id in prompt
    assert evidence.content in prompt
    assert "What blocks rollout?" in prompt


@pytest.mark.asyncio
async def test_empty_evidence_skips_llm(llm):
    assessment = await LLMEvidenceAssessor(llm).assess(
        query_input=QueryInput(query="What blocks rollout?"),
        evidence=[],
        execution_results=[],
        normalization_warnings=[],
    )

    assert assessment.status == AssessmentStatus.INSUFFICIENT
    assert assessment.relevant_evidence_ids == []
    assert assessment.gaps
    llm.generate.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        "not valid JSON",
        json.dumps({"status": "sufficient"}),
    ],
)
async def test_rejects_malformed_output(llm, evidence, response):
    llm.generate.return_value = response

    with pytest.raises(ValidationError):
        await LLMEvidenceAssessor(llm).assess(
            query_input=QueryInput(query="What blocks rollout?"),
            evidence=[evidence],
            execution_results=[],
            normalization_warnings=[],
        )


@pytest.mark.asyncio
async def test_rejects_invented_evidence_id(llm, evidence):
    llm.generate.return_value = json.dumps(
        {
            "status": "sufficient",
            "reason": "The comment identifies the blocker.",
            "relevant_evidence_ids": ["invented-id"],
            "gaps": [],
        }
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        await LLMEvidenceAssessor(llm).assess(
            query_input=QueryInput(query="What blocks rollout?"),
            evidence=[evidence],
            execution_results=[],
            normalization_warnings=[],
        )


@pytest.mark.asyncio
async def test_passes_retrieval_limitations_to_prompt(llm, evidence):
    llm.generate.return_value = json.dumps(
        {
            "status": "partial",
            "reason": "Some discussion records remain unavailable.",
            "relevant_evidence_ids": [evidence.evidence_id],
            "gaps": ["Unread comments may contain further updates."],
        }
    )

    execution_result = ExecutionResult(
        step_id=evidence.step_id,
        sub_query_id=evidence.sub_query_id,
        status=ExecutionStatus.SUCCESS,
        tool_called=evidence.tool_called,
        tool_response=[{"raw_marker": "RAW_RECORD_NOT_NEEDED"}],
        tool_metadata={"has_more": True},
    )

    warning = NormalizationWarning(
        step_id=str(uuid4()),
        capability="github.get_issue",
        message="Tool output did not satisfy the evidence contract.",
    )

    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id=evidence.sub_query_id,
                sub_query="Identify the current rollout blocker.",
            )
        ]
    )
    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id=evidence.step_id,
                sub_query_id=evidence.sub_query_id,
                action="Retrieve rollout discussion comments",
                capability="github.list_issue_comments",
                arguments={
                    "owner": "acme",
                    "repo": "payments",
                    "issue_number": 1,
                },
                depends_on=[],
            )
        ]
    )

    assessment = await LLMEvidenceAssessor(llm).assess(
        query_input=QueryInput(query="What currently blocks rollout?"),
        evidence=[evidence],
        execution_results=[execution_result],
        normalization_warnings=[warning],
        decomposition=decomposition,
        plan=plan,
    )

    llm.generate.assert_awaited_once()
    prompt = llm.generate.call_args.args[0]

    context = json.loads(prompt.split("Untrusted context as JSON:\n", maxsplit=1)[1])

    assert context["execution_results"][0]["tool_metadata"] == {
        "has_more": True,
    }
    assert context["normalization_warnings"] == [
        warning.model_dump(mode="json"),
    ]
    assert context["decomposition"] == decomposition.model_dump(mode="json")
    assert context["execution_plan"] == plan.model_dump(mode="json")
    assert "tool_response" not in context["execution_results"][0]
    assert "tool_response" not in context["evidence"][0]
    assert "RAW_RECORD_NOT_NEEDED" not in prompt
    assert assessment.status == AssessmentStatus.PARTIAL
