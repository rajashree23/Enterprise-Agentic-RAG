from agentic_rag.models.evidence import Evidence, EvidenceCollection, ToolCalled


def test_evidence():
    evidence = Evidence(
        evidence_id="ev-1",
        step_id="step-1",
        sub_query_id="sq-1",
        tool_called=ToolCalled(
            tool_id="github-search",
            tool_name="GitHub Search",
        ),
        tool_response=[
            {"repository": "agentic-rag", "status": "active"},
        ],
        content="The agentic-rag project is currently active.",
    )

    assert evidence.evidence_id == "ev-1"
    assert evidence.step_id == "step-1"
    assert evidence.content == "The agentic-rag project is currently active."


def test_evidence_collection():
    collection = EvidenceCollection(
        evidence=[
            Evidence(
                evidence_id="ev-1",
                step_id="step-1",
                sub_query_id="sq-1",
                tool_called=ToolCalled(
                    tool_id="github-search",
                    tool_name="GitHub Search",
                ),
                content="The project is active.",
            )
        ],
        is_sufficient=True,
    )

    assert len(collection.evidence) == 1
    assert collection.is_sufficient is True
