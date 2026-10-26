from agentic_rag.models.evidence import (
    Evidence,
    EvidenceSource,
)
from agentic_rag.models.execution_result import ToolCalled


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
        source=EvidenceSource(
            system="github",
            record_type="issue",
            record_id="9001",
            url="https://github.com/acme/payments/issues/123",
            title="Release payment retry feature",
        ),
    )

    assert evidence.evidence_id == "ev-1"
    assert evidence.step_id == "step-1"
    assert evidence.source.system == "github"
    assert evidence.source.record_id == "9001"
    assert evidence.source.url == ("https://github.com/acme/payments/issues/123")
    assert evidence.content == "The agentic-rag project is currently active."
