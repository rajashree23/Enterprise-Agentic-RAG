import pytest

from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.execution_result import ToolCalled
from agentic_rag.models.synthesis import Synthesis
from agentic_rag.synthesis.citation_resolution import resolve_citations


@pytest.fixture
def evidence():
    return [
        Evidence(
            evidence_id=f"ev-{number}",
            step_id="step-1",
            sub_query_id="sq-1",
            tool_called=ToolCalled(
                tool_id="github.list_issue_comments",
                tool_name="github.list_issue_comments",
            ),
            source=EvidenceSource(
                system="github",
                record_type="issue_comment",
                record_id=str(number),
                url=(
                    f"https://github.com/acme/payments/issues/1#issuecomment-{number}"
                ),
                title=None,
                author="developer-a",
            ),
            content=f"Discussion record {number}.",
        )
        for number in (1, 2)
    ]


def make_synthesis(claim_references):
    return Synthesis.model_validate(
        {
            "claims": [
                {
                    "text": "A supported statement.",
                    "citations": [
                        {"evidence_id": evidence_id} for evidence_id in references
                    ],
                }
                for references in claim_references
            ],
            "limitations": [],
        }
    )


def test_resolves_sources_in_first_citation_order(evidence):
    synthesis = make_synthesis(
        [
            ["ev-2", "ev-2"],
            ["ev-1", "ev-2"],
        ]
    )

    original_synthesis = synthesis.model_dump()
    original_evidence = [item.model_dump() for item in evidence]

    resolved = resolve_citations(synthesis, evidence)

    assert [item.evidence_id for item in resolved] == ["ev-2", "ev-1"]
    assert resolved[0].source == evidence[1].source
    assert resolved[1].source == evidence[0].source
    assert resolved[0].source.title is None

    assert synthesis.model_dump() == original_synthesis
    assert [item.model_dump() for item in evidence] == original_evidence


def test_excludes_uncited_evidence(evidence):
    synthesis = make_synthesis([["ev-1"]])

    resolved = resolve_citations(synthesis, evidence)

    assert len(resolved) == 1
    assert resolved[0].evidence_id == "ev-1"
    assert resolved[0].source.url == evidence[0].source.url


@pytest.mark.parametrize(
    "references",
    [
        ["invented-id"],
        ["ev-1", "invented-id"],
    ],
)
def test_rejects_unknown_citations(evidence, references):
    synthesis = make_synthesis([references])

    with pytest.raises(ValueError, match="unknown evidence"):
        resolve_citations(synthesis, evidence)


def test_rejects_duplicate_evidence_ids(evidence):
    synthesis = make_synthesis([["ev-1"]])
    duplicate = evidence[1].model_copy(
        update={"evidence_id": evidence[0].evidence_id},
    )

    with pytest.raises(ValueError, match="Duplicate evidence IDs"):
        resolve_citations(synthesis, [evidence[0], duplicate])


def test_keeps_distinct_evidence_ids_with_same_url(evidence):
    evidence[1].source.url = evidence[0].source.url
    synthesis = make_synthesis([["ev-1", "ev-2"]])

    resolved = resolve_citations(synthesis, evidence)

    assert [item.evidence_id for item in resolved] == ["ev-1", "ev-2"]
    assert resolved[0].source.url == resolved[1].source.url
