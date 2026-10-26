# Execution Result Contract

## 1. Purpose

Application-generated output describing the outcome of execution steps.
The executor does not use an LLM to generate these results.

## 2. Schema

### ExecutionResults

| Field | Type | Required | Meaning |
|---|---|---|---|
| `execution_results` | array of ExecutionResult | Yes | Step outcomes collected by the execution engine. Used by the application for normalization, assessment, and API output. |

### ExecutionResult

| Field | Type | Required / default | Ownership and meaning |
|---|---|---|---|
| `step_id` | string | Required | Copied by the application from the executed step. Identifies the step that produced this result. |
| `sub_query_id` | string | Required | Copied by the application from the executed step. Links the result to its sub-query. |
| `status` | ExecutionStatus | Required | Application-assigned execution outcome. |
| `tool_called` | ToolCalled or null | Defaults to null | Application-populated identity of the selected tool. Used for traceability and normalizer selection. |
| `tool_response` | array of dictionaries or null | Defaults to null | Tool-output records mapped by the application adapter. Used for evidence normalization; not necessarily the complete external API response. |
| `tool_error` | ToolError or null | Defaults to null | Application-populated execution failure information. Used for diagnostics and assessment. |
| `tool_metadata` | object | Defaults to an empty object | Tool-provided metadata preserved by the adapter, such as pagination or search coverage. Used by assessment and API consumers. |

### ExecutionStatus

| Value | Meaning |
|---|---|
| `SUCCESS` | The execution completed successfully. This does not establish evidence sufficiency. |
| `FAILED` | The execution failed. |
| `SKIPPED` | The step was not executed because a dependency failed or was skipped. |

### ToolCalled

Both fields are required when `tool_called` is present.

| Field | Type | Ownership and meaning |
|---|---|---|
| `tool_id` | string | Application-populated capability identifier, such as `github.get_issue`. |
| `tool_name` | string | Application-populated tool name. Currently the same capability identifier. |

### ToolError

All fields are required when `tool_error` is present.

| Field | Type | Ownership and meaning |
|---|---|---|
| `error_id` | string | Application-defined error category, not a unique occurrence ID. |
| `error_title` | string | Application-defined short error description. |
| `error_msg` | string | Application-populated details describing the failure. May include a tool-reported error. |

## 3. Rules

- Result IDs reference the executed plan; they are not newly generated.
- The execution engine checks returned step and sub-query IDs against
  the executed step, and checks the capability when tool identity is present.
- Tool-response record structure depends on the selected capability.
- An empty successful response is valid and does not mean execution failed.
- The adapter separates `data.items` records from sibling metadata when
  `items` is a list of dictionaries. Otherwise, it wraps the complete
  `data` object in `tool_response`.
- After retries are exhausted, the engine returns the last result;
  this schema does not contain attempt history.
- Failed and skipped results do not produce normalized evidence.
- Status-specific field relationships are application behavior, not
  enforced by the ExecutionResult model itself.

## 4. Successful Execution Example

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
  ]
}
```

The search completed successfully but returned no matching records.

## 5. Failed Execution Example

```json
{
  "execution_results": [
    {
      "step_id": "step-1",
      "sub_query_id": "sq-1",
      "status": "FAILED",
      "tool_called": {
        "tool_id": "github.get_issue",
        "tool_name": "github.get_issue"
      },
      "tool_response": null,
      "tool_error": {
        "error_id": "tool_execution_failed",
        "error_title": "Tool execution failed",
        "error_msg": "GitHub API returned HTTP 404"
      },
      "tool_metadata": {}
    }
  ]
}
```