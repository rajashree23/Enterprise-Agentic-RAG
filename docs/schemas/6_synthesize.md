# Synthesis and Citation Contract

## 1. Purpose

Generate factual claims from assessed evidence, with citations connecting
each claim to its supporting records.

The LLM generates claims and evidence references.
Application code validates references and resolves source links.

## 2. Inputs

| Input | Provided by | Meaning and use |
|---|---|---|
| `query_input` | Application | The user's question. Only `query_input.query` enters the LLM prompt; `conversation_id` is excluded. |
| `assessment` | Assessment stage | Answerability decision, relevant evidence references, and gaps used to guide synthesis. |
| `evidence` | Application normalizers | Available source records. The application selects the assessment's relevant records before prompting the LLM. |

Selected evidence enters the prompt without `tool_response`.
The assessment's explanation is not an independent source of project facts.

## 3. Synthesis Schema

All fields are required.

| Field | Type | Ownership | Meaning and consumer |
|---|---|---|---|
| `claims` | array of SupportedClaim | LLM-generated | Nonempty list of factual statements returned to API consumers. |
| `limitations` | array of strings | LLM-generated; supplemented by application | Missing information and uncertainty. The application preserves assessment gaps and adds a partial-answer notice when applicable. |

### SupportedClaim

| Field | Type | Ownership | Meaning and consumer |
|---|---|---|---|
| `text` | string | LLM-generated | Nonblank factual statement presented to the user. |
| `citations` | array of Citation | LLM-generated | Nonempty list of supporting evidence references, validated by the application. |

### Citation

| Field | Type | Ownership | Meaning and consumer |
|---|---|---|---|
| `evidence_id` | string | Application-generated ID selected by LLM | References evidence supplied to synthesis. Used for validation and source resolution. |

Claims do not have separate claim IDs.

## 4. Validation and Behavior

- Synthesis runs only after a sufficient or partial assessment.
- Insufficient evidence is rejected before an LLM synthesis call.
- Assessment references must identify available evidence.
- Every claim must contain nonblank text and at least one citation.
- Citation IDs must be nonblank and reference selected evidence.
- Unexpected fields in synthesis, claims, and citations are rejected.
- Assessment gaps are appended to limitations without duplicate strings.
- Partial assessments add:
  "The available evidence supports only a partial answer."
- Limitations must describe uncertainty or missing information, not
  introduce uncited project facts. This is a generation rule, not
  a semantic check enforced by the model.
- Reference validation does not prove that evidence supports a claim.
- Invalid output and processing failures are reported separately as
  `synthesis_error` in the query response.

## 5. Synthesis Example

The cited evidence must support the statement and must have been supplied
to the synthesis LLM.

```json
{
  "claims": [
    {
      "text": "Database migration approval remains pending.",
      "citations": [
        {
          "evidence_id": "80d38cf2-b5a3-4cb5-af8e-99442d6c4bc6"
        }
      ]
    }
  ],
  "limitations": []
}
```

## 6. ResolvedCitation Schema

Application-generated source information returned separately in
`QueryResponse.resolved_citations`. It is not part of the LLM output.

Both fields are required.

| Field | Type | Ownership | Meaning and consumer |
|---|---|---|---|
| `evidence_id` | string | Copied by application | Connects the resolved source to a claim's citation. |
| `source` | EvidenceSource | Copied from matching evidence | Original source metadata used by API consumers to display source links. See the evidence contract. |

### Resolution Rules

- Unknown citation IDs and duplicate evidence IDs are rejected.
- Each cited evidence ID is resolved once, in first-citation order.
- Different evidence IDs are not merged merely because they share a URL.
- Resolution does not modify claims or evidence.
- URLs come from evidence, not from the synthesis LLM.
- Source resolution does not verify URL accessibility or factual support.
- If resolution fails, the service returns no accepted synthesis or
  resolved citations and reports a synthesis error.

## 7. Resolved Citations Example

This list belongs to the query response, alongside `synthesis`.

```json
[
  {
    "evidence_id": "80d38cf2-b5a3-4cb5-af8e-99442d6c4bc6",
    "source": {
      "system": "github",
      "record_type": "issue",
      "record_id": "9001",
      "url": "https://github.com/acme/payments/issues/123",
      "title": "Production rollout blocked",
      "author": "developer-a",
      "created_at": "2026-10-20T10:00:00Z",
      "updated_at": "2026-10-24T10:00:00Z"
    }
  }
]
```