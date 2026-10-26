import pytest

from agentic_rag.models.synthesis import (
    Citation,
    SupportedClaim,
    Synthesis,
)
from agentic_rag.synthesis.validation import (
    validate_synthesis_references,
)


def make_claim(text, evidence_ids):
    return SupportedClaim(
        text=text,
        citations=[Citation(evidence_id=evidence_id) for evidence_id in evidence_ids],
    )


def test_accepts_known_citations():
    synthesis = Synthesis(
        claims=[
            make_claim("Migration approval is pending.", ["ev-1"]),
            make_claim("Staging verification passed.", ["ev-2"]),
        ],
        limitations=[],
    )

    validate_synthesis_references(synthesis, {"ev-1", "ev-2"})


@pytest.mark.parametrize(
    "references",
    [
        ["invented-id"],
        ["ev-1", "invented-id"],
    ],
)
def test_rejects_unknown_citation(references):
    synthesis = Synthesis(
        claims=[
            make_claim("Migration approval is pending.", references),
        ],
        limitations=[],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_synthesis_references(synthesis, {"ev-1"})


def test_checks_later_claims():
    synthesis = Synthesis(
        claims=[
            make_claim("Migration approval is pending.", ["ev-1"]),
            make_claim("Staging verification passed.", ["invented-id"]),
        ],
        limitations=[],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_synthesis_references(synthesis, {"ev-1"})


def test_rejects_citations_when_no_evidence_is_allowed():
    synthesis = Synthesis(
        claims=[
            make_claim("Migration approval is pending.", ["ev-1"]),
        ],
        limitations=[],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_synthesis_references(synthesis, set())
