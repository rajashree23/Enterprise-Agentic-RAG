from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.query import QueryInput, QueryResponse
from agentic_rag.orchestration.graph import run_query_graph
from agentic_rag.orchestration.nodes import QueryGraphDependencies
from agentic_rag.planner.interface import QueryPlanner
from agentic_rag.synthesis.interface import AnswerSynthesizer


async def process_query(
    query_input: QueryInput,
    decomposer: QueryDecomposer,
    planner: QueryPlanner,
    executor: ExecutionEngine,
    normalizers: dict[str, EvidenceNormalizer],
    assessor: EvidenceAssessor | None = None,
    synthesizer: AnswerSynthesizer | None = None,
) -> QueryResponse:
    """Run the query workflow through the LangGraph orchestrator."""

    dependencies = QueryGraphDependencies(
        decomposer=decomposer,
        planner=planner,
        executor=executor,
        normalizers=normalizers,
        replanner=(planner if hasattr(planner, "create_correction_plan") else None),
        assessor=assessor,
        synthesizer=synthesizer,
    )

    return await run_query_graph(
        query_input=query_input,
        dependencies=dependencies,
    )
