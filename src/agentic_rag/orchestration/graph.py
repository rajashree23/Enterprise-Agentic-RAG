from langgraph.graph import END, START, StateGraph

from agentic_rag.models.query import QueryInput, QueryResponse
from agentic_rag.orchestration.nodes import (
    QueryGraphDependencies,
    QueryGraphNodes,
)
from agentic_rag.orchestration.state import AgentState


def build_query_graph(dependencies: QueryGraphDependencies):
    nodes = QueryGraphNodes(dependencies)
    graph = StateGraph(AgentState)

    graph.add_node("fast_path", nodes.fast_path)
    graph.add_node("decompose", nodes.decompose)
    graph.add_node("plan", nodes.plan)
    graph.add_node("direct_answer", nodes.direct_answer)
    graph.add_node("execute", nodes.execute)
    graph.add_node("replan", nodes.replan)
    graph.add_node("normalize", nodes.normalize)
    graph.add_node("assess", nodes.assess)
    graph.add_node("synthesize", nodes.synthesize)

    graph.add_edge(START, "fast_path")
    graph.add_conditional_edges(
        "fast_path",
        nodes.route_after_fast_path,
        {
            "direct_answer": "direct_answer",
            "decompose": "decompose",
        },
    )
    graph.add_edge("decompose", "plan")
    graph.add_conditional_edges(
        "plan",
        nodes.route_after_plan,
        {
            "execute": "execute",
            "direct_answer": "direct_answer",
            "end": END,
        },
    )
    graph.add_edge("execute", "normalize")
    graph.add_edge("normalize", "assess")
    graph.add_conditional_edges(
        "assess",
        nodes.route_after_assessment,
        {
            "synthesize": "synthesize",
            "replan": "replan",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "replan",
        nodes.route_after_replan,
        {
            "execute": "execute",
            "end": END,
        },
    )
    graph.add_edge("synthesize", END)
    graph.add_edge("direct_answer", END)

    return graph.compile()


async def run_query_graph(
    query_input: QueryInput,
    dependencies: QueryGraphDependencies,
) -> QueryResponse:
    graph = build_query_graph(dependencies)
    final_state = await graph.ainvoke(
        {
            "query_input": query_input,
            "correction_attempts": 0,
            "max_correction_attempts": dependencies.max_correction_attempts,
        }
    )

    results = final_state.get("execution_results")
    planning_decision = final_state.get("planning_decision")
    if results is None and planning_decision is None:
        raise ValueError("Query graph completed without a planning decision")

    return QueryResponse(
        execution_results=(results.execution_results if results is not None else []),
        evidence=final_state.get("evidence", []),
        normalization_warnings=final_state.get("normalization_warnings", []),
        assessment=final_state.get("assessment"),
        assessment_error=final_state.get("assessment_error"),
        synthesis=final_state.get("synthesis"),
        synthesis_error=final_state.get("synthesis_error"),
        resolved_citations=final_state.get("resolved_citations", []),
        planning_outcome=(
            planning_decision.outcome if planning_decision is not None else None
        ),
        planning_reason=(
            planning_decision.reason if planning_decision is not None else None
        ),
        clarification_question=(
            planning_decision.clarification_question
            if planning_decision is not None
            else None
        ),
        direct_answer=final_state.get("direct_answer"),
        direct_answer_error=final_state.get("direct_answer_error"),
    )
