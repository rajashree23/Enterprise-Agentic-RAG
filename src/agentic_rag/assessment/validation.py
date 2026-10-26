from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)


def validate_assessment_references(
    assessment: EvidenceAssessment,
    available_evidence_ids: set[str],
) -> None:
    referenced_ids = set(assessment.relevant_evidence_ids)
    unknown_ids = referenced_ids - available_evidence_ids

    if unknown_ids:
        raise ValueError("Assessment references unknown evidence IDs")

    answerable_statuses = {
        AssessmentStatus.SUFFICIENT,
        AssessmentStatus.PARTIAL,
    }

    if assessment.status in answerable_statuses and not referenced_ids:
        raise ValueError("Sufficient or partial assessments must reference evidence")
