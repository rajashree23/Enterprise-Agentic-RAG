import pytest

from agentic_rag.assessment.validation import (
    validate_assessment_references,
)
from agentic_rag.models.evidence_assessment import EvidenceAssessment


@pytest.mark.parametrize(
    ("status", "references", "available_ids", "expected_error"),
    [
        ("sufficient", ["ev-1"], {"ev-1"}, None),
        ("partial", ["ev-1"], {"ev-1"}, None),
        ("insufficient", [], set(), None),
        ("sufficient", ["invented-id"], {"ev-1"}, "unknown evidence"),
        ("sufficient", [], {"ev-1"}, "must reference evidence"),
        ("partial", [], {"ev-1"}, "must reference evidence"),
    ],
)
def test_validate_assessment_references(
    status,
    references,
    available_ids,
    expected_error,
):
    assessment = EvidenceAssessment(
        status=status,
        reason="Assessment explanation.",
        relevant_evidence_ids=references,
        gaps=[],
    )

    if expected_error is not None:
        with pytest.raises(ValueError, match=expected_error):
            validate_assessment_references(assessment, available_ids)
    else:
        validate_assessment_references(assessment, available_ids)
