import pytest
from pydantic import ValidationError

from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)


def test_evidence_assessment():
    assessment = EvidenceAssessment(
        status="sufficient",
        reason="The discussion explicitly identifies the remaining blocker.",
        relevant_evidence_ids=["ev-1"],
        gaps=[],
    )

    assert assessment.status == AssessmentStatus.SUFFICIENT
    assert assessment.relevant_evidence_ids == ["ev-1"]
    assert assessment.gaps == []


def test_evidence_assessment_rejects_unknown_status():
    with pytest.raises(ValidationError):
        EvidenceAssessment(
            status="maybe",
            reason="Uncertain.",
            relevant_evidence_ids=[],
            gaps=[],
        )
