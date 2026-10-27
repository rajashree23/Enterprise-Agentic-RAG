# Query Response Contract

## 1. Purpose

Application-assembled response from `POST /query`.

It combines execution outcomes, evidence, assessment, synthesis, errors,
and resolved citations for API consumers.

## 2. QueryResponse Schema

| Field | Type | Required / default | Ownership and meaning |
|---|---|---|---|
| `execution_results` | array of ExecutionResult | Required | Application-generated execution outcomes. See the execution-result contract. |
| `evidence` | array of Evidence | Required | Application-normalized source records. See the evidence contract. |
| `normalization_warnings` | array of NormalizationWarning | Required | Application-generated explanations of results that could not be normalized. |
| `assessment` | EvidenceAssessment or null | Defaults to null | Validated assessment output, or an application-generated decision for empty evidence. |
| `assessment_error` | AssessmentError or null | Defaults to null | Application-generated assessment failure information. |
| `synthesis` | Synthesis or null | Defaults to null | Validated claims and limitations, accepted after citation resolution succeeds. |
| `synthesis_error` | SynthesisError or null | Defaults to null | Application-generated synthesis or citation-resolution failure information. |
| `resolved_citations` | array of ResolvedCitation | Defaults to an empty array | Application-resolved source metadata for cited evidence. |
| `planning_outcome` | PlanningOutcome or null | Defaults to null | Planning result: executable, clarification_required, unsupported, or no_tool_required. |
| `planning_reason` | string or null | Defaults to null | Application or planner explanation of the planning result. |
| `clarification_question` | string or null | Defaults to null | Question returned when required planning information is missing. |
| `direct_answer` | DirectAnswer or null | Defaults to null | Answer for a no-tool request. |
| `direct_answer_error` | DirectAnswerError or null | Defaults to null | Direct-answer generation failure information. |

The response model does not currently contain `conversation_id` or
`query_id`.

## 3. NormalizationWarning Schema

All fields are required. `capability` may be null.

| Field | Type | Ownership and meaning |
|---|---|---|
| `step_id` | string | Copied from the execution result that could not be normalized. |
| `capability` | string or null | Capability copied from tool identity; null when identity is missing. |
| `message` | string | Application-generated explanation of the normalization problem. |

A warning is produced when a successful result has no registered
normalizer or normalization raises a validation error.

Failed and skipped executions remain in `execution_results`; they do not
produce normalization warnings.

### Example

```json
{
  "step_id": "step-1",
  "capability": "github.get_issue",
  "message": "Tool output did not satisfy the evidence contract."
}
```

## 4. AssessmentError and SynthesisError Schemas

Both models have the same fields. All fields are required.

| Field | Type | Ownership and meaning |
|---|---|---|
| `code` | `invalid_output` or `unavailable` | Application-assigned failure category. |
| `message` | string | Application-generated explanation containing at least one character. |

- `invalid_output`: Assessment output, answer output, or citation
  resolution failed validation.
- `unavailable`: An LLM client failure or timeout prevented completion.

Unexpected fields in these error objects are rejected.

### Example

```json
{
  "code": "invalid_output",
  "message": "Answer generation or citation resolution was invalid."
}
```

## 5. Outcome Rules

- `assessment` and `assessment_error` cannot both be present.
- `synthesis` and `synthesis_error` cannot both be present.
- A synthesis result or error requires a sufficient or partial assessment.
- Nonempty `resolved_citations` requires a successful synthesis.
- Assessment failure or insufficient evidence skips synthesis.
- Synthesis or citation-resolution failure preserves execution results,
  evidence, and assessment, but returns `synthesis: null` and an empty
  resolved-citation list.
- Null assessment and assessment error together mean assessment did not
  run. Null synthesis and synthesis error together mean synthesis did
  not run.
- The service allows these stages to be omitted; the API route supplies
  both components and applies the execution rules above.
- An empty warning list does not establish evidence sufficiency.
- Returning this response does not mean every tool succeeded or that a
  factual answer was produced.

Decomposition, planning, and unexpected application exceptions are not
represented by these stage-error fields.

## 6. Empty Search Result Example

The tool succeeded, but no evidence was retrieved. The application
therefore generated an insufficient assessment and skipped synthesis.

```json
{
  "execution_results": [
    {
      "step_id": "step-1",
      "sub_query_id": "sq-1",
      "status": "SUCCESS",
      "tool_called": {
        "tool_id": "github.search",
        "tool_name": "github.search"
      },
      "tool_response": [],
      "tool_error": null,
      "tool_metadata": {
        "total_count": 0,
        "incomplete_results": false
      }
    }
  ],
  "evidence": [],
  "normalization_warnings": [],
  "assessment": {
    "status": "insufficient",
    "reason": "No normalized evidence is available to assess.",
    "relevant_evidence_ids": [],
    "gaps": [
      "Supporting evidence for the question is unavailable."
    ]
  },
  "assessment_error": null,
  "synthesis": null,
  "synthesis_error": null,
  "resolved_citations": []
}
```

## 7. Successful Answer Example

The tool retrieved an issue, the application normalized it into evidence,
and assessment found sufficient support for an answer.

```json
{
  "execution_results": [
    {
      "step_id": "step-1",
      "sub_query_id": "sq-1",
      "status": "SUCCESS",
      "tool_called": {
        "tool_id": "github.get_issue",
        "tool_name": "github.get_issue"
      },
      "tool_response": [
        {
          "id": 9001,
          "repository": "acme/payments",
          "number": 123,
          "record_type": "issue",
          "title": "Production rollout blocked",
          "body": "Database migration approval is the only remaining rollout blocker.",
          "state": "open",
          "url": "https://github.com/acme/payments/issues/123",
          "author": "developer-a",
          "created_at": "2026-10-20T10:00:00Z",
          "updated_at": "2026-10-24T10:00:00Z"
        }
      ],
      "tool_error": null,
      "tool_metadata": {}
    }
  ],
  "evidence": [
    {
      "evidence_id": "80d38cf2-b5a3-4cb5-af8e-99442d6c4bc6",
      "step_id": "step-1",
      "sub_query_id": "sq-1",
      "tool_called": {
        "tool_id": "github.get_issue",
        "tool_name": "github.get_issue"
      },
      "source": {
        "system": "github",
        "record_type": "issue",
        "record_id": "9001",
        "url": "https://github.com/acme/payments/issues/123",
        "title": "Production rollout blocked",
        "author": "developer-a",
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-24T10:00:00Z"
      },
      "tool_response": [
        {
          "id": 9001,
          "repository": "acme/payments",
          "number": 123,
          "record_type": "issue",
          "title": "Production rollout blocked",
          "body": "Database migration approval is the only remaining rollout blocker.",
          "state": "open",
          "url": "https://github.com/acme/payments/issues/123",
          "author": "developer-a",
          "created_at": "2026-10-20T10:00:00Z",
          "updated_at": "2026-10-24T10:00:00Z"
        }
      ],
      "content": "Repository: acme/payments\nNumber: 123\nType: issue\nTitle: Production rollout blocked\nState: open\nDescription: Database migration approval is the only remaining rollout blocker."
    }
  ],
  "normalization_warnings": [],
  "assessment": {
    "status": "sufficient",
    "reason": "The issue explicitly identifies the remaining rollout blocker.",
    "relevant_evidence_ids": [
      "80d38cf2-b5a3-4cb5-af8e-99442d6c4bc6"
    ],
    "gaps": []
  },
  "assessment_error": null,
  "synthesis": {
    "claims": [
      {
        "text": "Database migration approval is the only documented remaining rollout blocker.",
        "citations": [
          {
            "evidence_id": "80d38cf2-b5a3-4cb5-af8e-99442d6c4bc6"
          }
        ]
      }
    ],
    "limitations": []
  },
  "synthesis_error": null,
  "resolved_citations": [
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
}
```
