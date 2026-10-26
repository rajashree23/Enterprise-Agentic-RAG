import pytest
from pydantic import ValidationError

from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.query import AssessmentError, QueryResponse


def make_assessment():
    return EvidenceAssessment(
        status="insufficient",
        reason="No evidence is available.",
        relevant_evidence_ids=[],
        gaps=["Supporting evidence is missing."],
    )


def test_response_accepts_completed_assessment():
    assessment = make_assessment()

    response = QueryResponse(
        execution_results=[],
        evidence=[],
        normalization_warnings=[],
        assessment=assessment,
    )

    assert response.assessment == assessment
    assert response.assessment_error is None


def test_response_accepts_assessment_failure():
    error = AssessmentError(
        code="invalid_output",
        message="The assessor returned an invalid response.",
    )

    response = QueryResponse(
        execution_results=[],
        evidence=[],
        normalization_warnings=[],
        assessment_error=error,
    )

    assert response.assessment is None
    assert response.assessment_error == error


def test_response_accepts_assessment_not_run():
    response = QueryResponse(
        execution_results=[],
        evidence=[],
        normalization_warnings=[],
    )

    assert response.assessment is None
    assert response.assessment_error is None


def test_response_rejects_result_and_error_together():
    with pytest.raises(ValidationError, match="cannot both be present"):
        QueryResponse(
            execution_results=[],
            evidence=[],
            normalization_warnings=[],
            assessment=make_assessment(),
            assessment_error=AssessmentError(
                code="unavailable",
                message="The assessment service is unavailable.",
            ),
        )
