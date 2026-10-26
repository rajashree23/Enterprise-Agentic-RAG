import pytest
from pydantic import ValidationError

from agentic_rag.models.synthesis import (
    Citation,
    SupportedClaim,
    Synthesis,
)


def test_synthesis():
    synthesis = Synthesis(
        claims=[
            SupportedClaim(
                text="Migration approval remains pending.",
                citations=[Citation(evidence_id="ev-1")],
            ),
        ],
        limitations=[],
    )

    assert len(synthesis.claims) == 1
    assert synthesis.claims[0].text == "Migration approval remains pending."
    assert synthesis.claims[0].citations[0].evidence_id == "ev-1"
    assert synthesis.limitations == []


@pytest.mark.parametrize(
    "claim",
    [
        {"text": "", "citations": [{"evidence_id": "ev-1"}]},
        {"text": "   ", "citations": [{"evidence_id": "ev-1"}]},
        {"text": "Migration approval is pending.", "citations": []},
        {
            "text": "Migration approval is pending.",
            "citations": [{"evidence_id": "   "}],
        },
    ],
)
def test_rejects_invalid_claim(claim):
    with pytest.raises(ValidationError):
        SupportedClaim.model_validate(claim)


def test_rejects_empty_claims():
    with pytest.raises(ValidationError):
        Synthesis(claims=[], limitations=[])
