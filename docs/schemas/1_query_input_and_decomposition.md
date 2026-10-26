# Query Input and Decomposition Contract

## 1. Query Input

Input to `POST /query`.

| Field | Type | Required | Ownership and meaning |
|---|---|---|---|
| `conversation_id` | string or null | No | Application-generated conversation identifier. The client supplies it on subsequent requests. |
| `query` | nonblank string | Yes | Client-provided question, trimmed and passed to the decomposition LLM. |

An omitted or null `conversation_id` indicates a new conversation.
Application generation and persistence of this ID are not yet implemented.
Blank or whitespace-only queries and unexpected input fields are rejected at
the API boundary.

### Example

```json
{
  "conversation_id": null,
  "query": "Find the status and owner of Project X."
}
```

## 2. Query Decomposition

The LLM identifies distinct information requirements.
The application validates its output and adds sub-query IDs.

| Field | Type | Ownership | Meaning and consumer |
|---|---|---|---|
| `sub_queries` | array of objects | LLM-generated | Information requirements passed to planning. |
| `sub_query` | string | LLM-generated | One focused question used by the planning LLM. |
| `sub_query_id` | string | Application-generated | Identifier used by planning and downstream application stages to associate steps, results, and evidence with a sub-query. |

All fields are required in the application decomposition.
The LLM output excludes `sub_query_id`; the application adds it.
IDs must be treated as opaque strings.

### LLM Output Example

```json
{
  "sub_queries": [
    {
      "sub_query": "Find the current status of Project X."
    },
    {
      "sub_query": "Find the owner of Project X."
    }
  ]
}
```

### Application Output Example

```json
{
  "sub_queries": [
    {
      "sub_query_id": "sq-1",
      "sub_query": "Find the current status of Project X."
    },
    {
      "sub_query_id": "sq-2",
      "sub_query": "Find the owner of Project X."
    }
  ]
}
```
