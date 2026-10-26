# Evidence Contract

## 1. Purpose

Evidence represents a retrieved source record in a common structure for
assessment, synthesis, and citations.

The application normalizes tool-output records into evidence.
No LLM generates evidence during normalization.

## 2. Evidence Schema

| Field | Type | Required / default | Ownership and meaning |
|---|---|---|---|
| `evidence_id` | string | Required | Application-generated UUID4 identifying this evidence item. Used by assessment and claim citations. |
| `step_id` | string | Required | Copied from the execution result. Identifies the originating step. |
| `sub_query_id` | string | Required | Copied from the execution result. Links evidence to its sub-query. |
| `tool_called` | ToolCalled | Required | Copied from the execution result. Identifies the originating capability. |
| `source` | EvidenceSource | Required | Application-mapped source identity and metadata. Used for provenance and citation resolution. |
| `tool_response` | array of dictionaries or null | Defaults to null | Associated tool-output records retained by the normalizer. Not necessarily the complete external API response. |
| `content` | string | Required | Readable source information assembled by application code. Used by assessment and synthesis LLMs. |

### ToolCalled

Both fields are required.

| Field | Type | Ownership and meaning |
|---|---|---|
| `tool_id` | string | Application-managed capability identifier. |
| `tool_name` | string | Application-managed tool name; currently the capability identifier. |

## 3. EvidenceSource Schema

| Field | Type | Required / default | Ownership and meaning |
|---|---|---|---|
| `system` | string | Required | Assigned by the normalizer, such as `github`. |
| `record_type` | string | Required | Mapped from the source record, such as `issue`, `pull_request`, or `issue_comment`. |
| `record_id` | string | Required | Source-assigned record ID converted to a string by the application. Not the evidence ID or repository-local issue number. |
| `url` | string | Required | Original source-record URL, mapped by the application. Used to resolve citations. |
| `title` | string or null | Defaults to null | Source-provided title, when available. |
| `author` | string or null | Defaults to null | Source-provided author, when available. |
| `created_at` | datetime or null | Defaults to null | Source-record creation time, serialized as an ISO 8601 string. |
| `updated_at` | datetime or null | Defaults to null | Source-record modification time, serialized as an ISO 8601 string. |

Source timestamps are not retrieval timestamps.
Source identity combines `system`, `record_type`, and `record_id`.

## 4. Rules

- Evidence is returned as `list[Evidence]`.
- Each independently citable source record produces one evidence item.
  One tool execution may therefore produce multiple evidence items.
- Current GitHub normalizers validate the complete record list before
  creating evidence.
- Failed or skipped executions produce no evidence.
- A successful execution with an empty record list produces no evidence.
- Missing tool identity, an unsupported capability, a null response,
  or malformed records cause normalization to fail.
- Current GitHub normalizers retain one serialized record in each
  evidence item's `tool_response`.
- `content` is assembled deterministically. Missing facts are not invented.
- Assessment and synthesis prompts exclude `tool_response` to avoid
  duplicating records already represented by content and provenance.
- Normalization does not establish relevance, sufficiency, or truth.
- Evidence IDs are generated as UUID4 strings, but the Evidence model
  itself does not enforce UUID syntax.
- Source URLs are stored as strings; this model does not verify their
  syntax or accessibility.

## 5. Example

Fictional issue evidence:

```json
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
      "body": "Waiting for migration approval.",
      "state": "open",
      "url": "https://github.com/acme/payments/issues/123",
      "author": "developer-a",
      "created_at": "2026-10-20T10:00:00Z",
      "updated_at": "2026-10-24T10:00:00Z"
    }
  ],
  "content": "Repository: acme/payments\nNumber: 123\nType: issue\nTitle: Production rollout blocked\nState: open\nDescription: Waiting for migration approval."
}
```