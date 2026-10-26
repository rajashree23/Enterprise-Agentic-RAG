from agentic_rag.models.synthesis import Synthesis


def validate_synthesis_references(
    synthesis: Synthesis,
    allowed_evidence_ids: set[str],
) -> None:
    for claim in synthesis.claims:
        referenced_ids = {citation.evidence_id for citation in claim.citations}

        unknown_ids = referenced_ids - allowed_evidence_ids

        if unknown_ids:
            raise ValueError("Synthesis references unknown evidence IDs")
