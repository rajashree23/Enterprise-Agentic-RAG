from dataclasses import replace
from unittest.mock import AsyncMock, Mock

import pytest

from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.direct_answer import DirectAnswer
from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionResults,
    ExecutionStatus,
    ToolCalled,
)
from agentic_rag.models.planning import PlanningDecision, PlanningOutcome
from agentic_rag.models.query import QueryInput
from agentic_rag.models.synthesis import Citation, SupportedClaim, Synthesis
from agentic_rag.orchestration.graph import run_query_graph
from agentic_rag.orchestration.nodes import QueryGraphDependencies
from agentic_rag.planner.interface import QueryPlanner
from agentic_rag.synthesis.interface import AnswerSynthesizer


def create_dependencies(
    assessment_status: str = "sufficient",
) -> tuple[QueryInput, QueryGraphDependencies]:
    query_input = QueryInput(query="What blocks rollout?")
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find the rollout blocker.",
            )
        ]
    )
    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Retrieve the issue",
                capability="github.get_issue",
                arguments={
                    "owner": "acme",
                    "repo": "payments",
                    "issue_number": 1,
                },
                depends_on=[],
            )
        ]
    )
    tool = ToolCalled(
        tool_id="github.get_issue",
        tool_name="github.get_issue",
    )
    result = ExecutionResult(
        step_id="step-1",
        sub_query_id="sq-1",
        status=ExecutionStatus.SUCCESS,
        tool_called=tool,
    )
    evidence = Evidence(
        evidence_id="evidence-1",
        step_id="step-1",
        sub_query_id="sq-1",
        tool_called=tool,
        source=EvidenceSource(
            system="github",
            record_type="issue",
            record_id="1",
            url="https://github.com/acme/payments/issues/1",
        ),
        content="Migration approval remains pending.",
    )

    decomposer = AsyncMock(spec=QueryDecomposer)
    decomposer.decompose.return_value = decomposition

    planner = AsyncMock(spec=QueryPlanner)
    planner.create_plan.return_value = plan

    executor = AsyncMock(spec=ExecutionEngine)
    executor.execute.return_value = ExecutionResults(execution_results=[result])

    normalizer = Mock(spec=EvidenceNormalizer)
    normalizer.normalize.return_value = [evidence]

    assessor = AsyncMock(spec=EvidenceAssessor)
    assessor.assess.return_value = EvidenceAssessment(
        status=assessment_status,
        reason="The available evidence was assessed.",
        relevant_evidence_ids=(
            [evidence.evidence_id]
            if assessment_status in {"sufficient", "partial"}
            else []
        ),
        gaps=(
            []
            if assessment_status == "sufficient"
            else ["Some supporting information is unavailable."]
        ),
    )

    synthesizer = AsyncMock(spec=AnswerSynthesizer)
    synthesizer.synthesize.return_value = Synthesis(
        claims=[
            SupportedClaim(
                text="Migration approval remains pending.",
                citations=[Citation(evidence_id=evidence.evidence_id)],
            )
        ],
        limitations=[],
    )

    graph_dependencies = QueryGraphDependencies(
        decomposer=decomposer,
        planner=planner,
        executor=executor,
        normalizers={"github.get_issue": normalizer},
        assessor=assessor,
        synthesizer=synthesizer,
    )

    return query_input, graph_dependencies


async def test_graph_stops_before_execution_for_clarification():
    query_input, dependencies = create_dependencies()
    planner = AsyncMock(spec=QueryPlanner)
    planner.create_planning_decision = AsyncMock(
        return_value=PlanningDecision(
            outcome=PlanningOutcome.CLARIFICATION_REQUIRED,
            reason="A repository is required before searching.",
            clarification_question="Which repository should I search?",
        )
    )
    dependencies = replace(dependencies, planner=planner)

    response = await run_query_graph(query_input, dependencies)

    assert response.planning_outcome == PlanningOutcome.CLARIFICATION_REQUIRED
    assert response.clarification_question == "Which repository should I search?"
    assert response.execution_results == []
    dependencies.executor.execute.assert_not_awaited()


async def test_graph_generates_direct_answer_without_tool_execution():
    query_input, dependencies = create_dependencies()
    planner = AsyncMock(spec=QueryPlanner)
    planner.create_planning_decision = AsyncMock(
        return_value=PlanningDecision(
            outcome=PlanningOutcome.NO_TOOL_REQUIRED,
            reason="The question can be answered from general knowledge.",
        )
    )
    direct_answer_generator = AsyncMock()
    direct_answer_generator.generate.return_value = DirectAnswer(
        answer="Git is a version-control system."
    )
    dependencies = replace(
        dependencies,
        planner=planner,
        direct_answer_generator=direct_answer_generator,
    )

    response = await run_query_graph(query_input, dependencies)

    assert response.planning_outcome == PlanningOutcome.NO_TOOL_REQUIRED
    assert response.direct_answer is not None
    assert response.direct_answer.answer == "Git is a version-control system."
    assert response.execution_results == []
    dependencies.executor.execute.assert_not_awaited()
    direct_answer_generator.generate.assert_awaited_once()


@pytest.mark.parametrize(
    ("assessment_status", "expected_synthesis_calls"),
    [
        ("sufficient", 1),
        ("partial", 1),
        ("insufficient", 0),
    ],
)
async def test_graph_routes_assessment_paths(
    assessment_status,
    expected_synthesis_calls,
):
    query_input, graph_dependencies = create_dependencies(assessment_status)

    graph_response = await run_query_graph(query_input, graph_dependencies)

    assert graph_response.assessment is not None
    assert graph_response.assessment.status == assessment_status
    assert len(graph_response.execution_results) == 1
    assert len(graph_response.evidence) == 1
    assert (
        graph_dependencies.synthesizer.synthesize.await_count
        == expected_synthesis_calls
    )

    if expected_synthesis_calls:
        assert graph_response.synthesis is not None
        assert len(graph_response.resolved_citations) == 1
    else:
        assert graph_response.synthesis is None
        assert graph_response.resolved_citations == []


@pytest.mark.parametrize(
    ("stage", "exception_type", "expected_code"),
    [
        ("assessment", ValueError, "invalid_output"),
        ("assessment", TimeoutError, "unavailable"),
        ("synthesis", ValueError, "invalid_output"),
        ("synthesis", TimeoutError, "unavailable"),
    ],
)
async def test_graph_preserves_completed_stages_for_handled_failures(
    stage,
    exception_type,
    expected_code,
):
    query_input, graph_dependencies = create_dependencies()

    if stage == "assessment":
        graph_dependencies.assessor.assess.side_effect = exception_type("failed")
    else:
        graph_dependencies.synthesizer.synthesize.side_effect = exception_type("failed")

    graph_response = await run_query_graph(query_input, graph_dependencies)

    assert len(graph_response.execution_results) == 1
    assert len(graph_response.evidence) == 1

    if stage == "assessment":
        assert graph_response.assessment_error is not None
        assert graph_response.assessment_error.code == expected_code
        assert graph_response.synthesis is None
    else:
        assert graph_response.synthesis_error is not None
        assert graph_response.synthesis_error.code == expected_code


async def test_graph_performs_one_bounded_correction_attempt():
    query_input, dependencies = create_dependencies("insufficient")
    initial_assessment = dependencies.assessor.assess.return_value
    final_assessment = initial_assessment.model_copy(
        update={
            "status": "sufficient",
            "reason": "The corrected retrieval is sufficient.",
            "gaps": [],
        }
    )
    dependencies.assessor.assess.side_effect = [
        initial_assessment,
        final_assessment,
    ]

    replanner = AsyncMock()
    corrected_plan = dependencies.planner.create_plan.return_value.model_copy(
        deep=True,
        update={
            "execution_steps": [
                dependencies.planner.create_plan.return_value.execution_steps[
                    0
                ].model_copy(update={"action": "Retrieve issue discussion comments"})
            ]
        },
    )
    replanner.create_correction_plan.return_value = corrected_plan
    dependencies = replace(dependencies, replanner=replanner)

    response = await run_query_graph(query_input, dependencies)

    decomposition = dependencies.planner.create_plan.await_args.args[0]
    assert response.assessment == final_assessment
    assert response.synthesis is not None
    assert dependencies.executor.execute.await_count == 2
    assert dependencies.assessor.assess.await_count == 2
    replanner.create_correction_plan.assert_awaited_once_with(
        decomposition,
        initial_assessment,
        dependencies.planner.create_plan.return_value,
    )
    assert dependencies.synthesizer.synthesize.await_count == 1


async def test_graph_stops_after_correction_budget():
    query_input, dependencies = create_dependencies("insufficient")
    replanner = AsyncMock()
    replanner.create_correction_plan.return_value = (
        dependencies.planner.create_plan.return_value
    )
    dependencies.assessor.assess.side_effect = [
        dependencies.assessor.assess.return_value,
        dependencies.assessor.assess.return_value,
    ]
    dependencies = replace(
        dependencies,
        replanner=replanner,
        max_correction_attempts=1,
    )

    response = await run_query_graph(query_input, dependencies)

    assert response.assessment is not None
    assert response.assessment.status == "insufficient"
    assert response.synthesis is None
    assert dependencies.executor.execute.await_count == 1
    assert dependencies.assessor.assess.await_count == 1
    replanner.create_correction_plan.assert_awaited_once()


def test_graph_dependencies_require_positive_stage_timeout():
    _, dependencies = create_dependencies()

    with pytest.raises(ValueError, match="stage_timeout_seconds must be positive"):
        QueryGraphDependencies(
            decomposer=dependencies.decomposer,
            planner=dependencies.planner,
            executor=dependencies.executor,
            normalizers=dependencies.normalizers,
            stage_timeout_seconds=0,
        )
