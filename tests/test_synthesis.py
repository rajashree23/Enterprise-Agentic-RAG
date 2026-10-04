from agentic_rag.models.synthesis import Citation, Synthesis


def test_synthesis():
    synthesis = Synthesis(
        response="The project is currently active.",
        citations=[
            Citation(evidence_id="ev-1"),
        ],
    )

    assert synthesis.response == "The project is currently active."
    assert len(synthesis.citations) == 1
    assert synthesis.citations[0].evidence_id == "ev-1"
