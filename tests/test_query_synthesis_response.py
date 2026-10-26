import pytest
from pydantic import ValidationError

from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.query import QueryResponse, SynthesisError
from agentic_rag.models.synthesis import Synthesis


def make_synthesis():
    return Synthesis.model_validate(
        {
            "claims": [
                {
                    "text": "Migration approval remains pending.",
                    "citations": [{"evidence_id": "ev-1"}],
                }
            ],
            "limitations": [],
        }
    )


def make_assessment(status):
    return EvidenceAssessment(
        status=status,
        reason="Assessment explanation.",
        relevant_evidence_ids=["ev-1"] if status != "insufficient" else [],
        gaps=[],
    )


@pytest.mark.parametrize("status", ["sufficient", "partial"])
def test_accepts_synthesis_after_answerable_assessment(status):
    synthesis = make_synthesis()

    response = QueryResponse(
        execution_results=[],
        evidence=[],
        normalization_warnings=[],
        assessment=make_assessment(status),
        synthesis=synthesis,
    )

    assert response.synthesis == synthesis
    assert response.synthesis_error is None


def test_accepts_synthesis_failure():
    error = SynthesisError(
        code="invalid_output",
        message="The generated answer contained invalid citations.",
    )

    response = QueryResponse(
        execution_results=[],
        evidence=[],
        normalization_warnings=[],
        assessment=make_assessment("sufficient"),
        synthesis_error=error,
    )

    assert response.synthesis is None
    assert response.synthesis_error == error


def test_rejects_synthesis_result_and_error_together():
    with pytest.raises(ValidationError, match="cannot both be present"):
        QueryResponse(
            execution_results=[],
            evidence=[],
            normalization_warnings=[],
            assessment=make_assessment("sufficient"),
            synthesis=make_synthesis(),
            synthesis_error=SynthesisError(
                code="unavailable",
                message="Synthesis could not complete.",
            ),
        )


@pytest.mark.parametrize("outcome", ["synthesis", "synthesis_error"])
@pytest.mark.parametrize("status", [None, "insufficient"])
def test_rejects_synthesis_without_answerable_assessment(outcome, status):
    value = (
        make_synthesis()
        if outcome == "synthesis"
        else SynthesisError(
            code="unavailable",
            message="Synthesis could not complete.",
        )
    )

    with pytest.raises(ValidationError, match="requires"):
        QueryResponse(
            execution_results=[],
            evidence=[],
            normalization_warnings=[],
            assessment=make_assessment(status) if status is not None else None,
            **{outcome: value},
        )


@pytest.mark.parametrize("status", [None, "sufficient"])
def test_rejects_resolved_citations_without_synthesis(status):
    with pytest.raises(
        ValidationError,
        match="Resolved citations require a successful synthesis",
    ):
        QueryResponse(
            execution_results=[],
            evidence=[],
            normalization_warnings=[],
            assessment=(make_assessment(status) if status is not None else None),
            resolved_citations=[
                {
                    "evidence_id": "ev-1",
                    "source": {
                        "system": "github",
                        "record_type": "issue",
                        "record_id": "123",
                        "url": "https://github.com/acme/payments/issues/1",
                    },
                }
            ],
        )
