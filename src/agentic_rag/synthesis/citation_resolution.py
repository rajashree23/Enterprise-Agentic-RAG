from agentic_rag.models.citation import ResolvedCitation
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.synthesis import Synthesis
from agentic_rag.synthesis.validation import validate_synthesis_references


def resolve_citations(
    synthesis: Synthesis,
    evidence: list[Evidence],
) -> list[ResolvedCitation]:
    evidence_by_id: dict[str, Evidence] = {}

    for item in evidence:
        if item.evidence_id in evidence_by_id:
            raise ValueError("Duplicate evidence IDs prevent citation resolution")

        evidence_by_id[item.evidence_id] = item

    validate_synthesis_references(
        synthesis,
        set(evidence_by_id),
    )

    resolved: list[ResolvedCitation] = []
    seen_ids: set[str] = set()

    for claim in synthesis.claims:
        for citation in claim.citations:
            evidence_id = citation.evidence_id

            if evidence_id in seen_ids:
                continue

            item = evidence_by_id[evidence_id]

            resolved.append(
                ResolvedCitation(
                    evidence_id=evidence_id,
                    source=item.source,
                )
            )
            seen_ids.add(evidence_id)

    return resolved
