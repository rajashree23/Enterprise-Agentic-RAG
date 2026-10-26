from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from agentic_rag.application.query_service import process_query
from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionResults,
    ExecutionStatus,
    ToolCalled,
)
from agentic_rag.models.query import QueryInput
from agentic_rag.models.synthesis import Synthesis
from agentic_rag.planner.interface import QueryPlanner
from agentic_rag.synthesis.interface import AnswerSynthesizer


@pytest.fixture
def dependencies():
    tool = ToolCalled(
        tool_id="github.get_issue",
        tool_name="github.get_issue",
    )

    evidence = Evidence(
        evidence_id=str(uuid4()),
        step_id=str(uuid4()),
        sub_query_id=str(uuid4()),
        tool_called=tool,
        source=EvidenceSource(
            system="github",
            record_type="issue",
            record_id="123",
            url="https://github.com/acme/payments/issues/1",
        ),
        content="Migration approval remains pending.",
    )

    execution = ExecutionResult(
        step_id=evidence.step_id,
        sub_query_id=evidence.sub_query_id,
        status=ExecutionStatus.SUCCESS,
        tool_called=tool,
    )

    executor = AsyncMock(spec=ExecutionEngine)
    executor.execute.return_value = ExecutionResults(
        execution_results=[execution],
    )

    normalizer = Mock(spec=EvidenceNormalizer)
    normalizer.normalize.return_value = [evidence]

    assessor = AsyncMock(spec=EvidenceAssessor)
    assessor.assess.return_value = EvidenceAssessment(
        status="sufficient",
        reason="The issue identifies the blocker.",
        relevant_evidence_ids=[evidence.evidence_id],
        gaps=[],
    )

    synthesizer = AsyncMock(spec=AnswerSynthesizer)
    synthesizer.synthesize.return_value = Synthesis.model_validate(
        {
            "claims": [
                {
                    "text": "Migration approval remains pending.",
                    "citations": [
                        {"evidence_id": evidence.evidence_id},
                    ],
                }
            ],
            "limitations": [],
        }
    )

    return {
        "query_input": QueryInput(query="What blocks rollout?"),
        "decomposer": AsyncMock(spec=QueryDecomposer),
        "planner": AsyncMock(spec=QueryPlanner),
        "executor": executor,
        "normalizers": {"github.get_issue": normalizer},
        "assessor": assessor,
        "synthesizer": synthesizer,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["sufficient", "partial"])
async def test_runs_synthesis_after_answerable_assessment(
    dependencies,
    status,
):
    assessor = dependencies["assessor"]
    synthesizer = dependencies["synthesizer"]

    assessor.assess.return_value = assessor.assess.return_value.model_copy(
        update={"status": status},
    )

    response = await process_query(**dependencies)

    synthesizer.synthesize.assert_awaited_once_with(
        query_input=dependencies["query_input"],
        assessment=response.assessment,
        evidence=response.evidence,
    )

    assert response.synthesis == synthesizer.synthesize.return_value
    assert response.synthesis_error is None
    assert response.assessment_error is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "condition",
    ["no-assessor", "insufficient", "assessment-failure"],
)
async def test_skips_synthesis_without_answerable_assessment(
    dependencies,
    condition,
):
    assessor = dependencies["assessor"]
    synthesizer = dependencies["synthesizer"]

    if condition == "no-assessor":
        dependencies["assessor"] = None
    elif condition == "insufficient":
        assessor.assess.return_value = EvidenceAssessment(
            status="insufficient",
            reason="The evidence cannot answer the question.",
            relevant_evidence_ids=[],
            gaps=["Required information is missing."],
        )
    else:
        assessor.assess.side_effect = ValueError("Invalid assessment")

    response = await process_query(**dependencies)

    synthesizer.synthesize.assert_not_awaited()
    assert response.synthesis is None
    assert response.synthesis_error is None
    assert response.resolved_citations == []

    if condition == "assessment-failure":
        assert response.assessment_error is not None
        assert response.assessment_error.code == "invalid_output"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_type", "expected_code"),
    [
        (ValueError, "invalid_output"),
        (TimeoutError, "unavailable"),
    ],
)
async def test_preserves_completed_stages_when_synthesis_fails(
    dependencies,
    exception_type,
    expected_code,
):
    dependencies["synthesizer"].synthesize.side_effect = exception_type(
        "Synthesis failed",
    )

    response = await process_query(**dependencies)

    assert len(response.execution_results) == 1
    assert response.execution_results[0].status == ExecutionStatus.SUCCESS
    assert len(response.evidence) == 1
    assert response.assessment == (dependencies["assessor"].assess.return_value)
    assert response.assessment_error is None
    assert response.synthesis is None
    assert response.synthesis_error is not None
    assert response.synthesis_error.code == expected_code
    assert response.resolved_citations == []


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ["unknown-id", "duplicate-id"])
async def test_preserves_evidence_when_citation_resolution_fails(
    dependencies,
    failure_kind,
):
    normalizer = dependencies["normalizers"]["github.get_issue"]

    if failure_kind == "unknown-id":
        dependencies["synthesizer"].synthesize.return_value = Synthesis.model_validate(
            {
                "claims": [
                    {
                        "text": "Migration approval remains pending.",
                        "citations": [
                            {"evidence_id": "invented-id"},
                        ],
                    }
                ],
                "limitations": [],
            }
        )
    else:
        item = normalizer.normalize.return_value[0]
        normalizer.normalize.return_value = [
            item,
            item.model_copy(deep=True),
        ]

    response = await process_query(**dependencies)

    assert response.evidence == normalizer.normalize.return_value
    assert len(response.execution_results) == 1
    assert response.assessment == (dependencies["assessor"].assess.return_value)
    assert response.assessment_error is None

    assert response.synthesis is None
    assert response.resolved_citations == []
    assert response.synthesis_error is not None
    assert response.synthesis_error.code == "invalid_output"

    dependencies["synthesizer"].synthesize.assert_awaited_once()
