# Agentic RAG

A Python project building toward an enterprise intelligence system across
GitHub, Slack, and Notion.

## Current Milestone

A working GitHub-backed pipeline retrieves live records, assesses
answerability, and generates claims with evidence references and resolved
source links.

This is a development milestone, not a production-ready enterprise system.

## Implemented Capabilities

| Tool | Purpose |
|---|---|
| `github.search` | Search issues and pull requests |
| `github.get_issue` | Retrieve a known issue or a PR's common fields |
| `github.list_issue_comments` | Retrieve general issue or PR discussion comments |

PR common fields do not establish merge status or review decisions.
General discussion comments do not include inline code-review comments.

## Processing Flow

```text
User question
    → LLM decomposition
    → Planning
        ├─ direct answer
        └─ tool execution → normalization → assessment → synthesis
                           → citation validation → source-link resolution
    → API response
```

Synthesis runs only after a sufficient or partial assessment.
Partial answers preserve assessment gaps and an explicit limitation.

Insufficient evidence skips synthesis. Assessment and synthesis failures
are reported separately while preserving completed retrieval results.

Tool execution has bounded retries and timeouts. When retrieval succeeds but
evidence is insufficient, including successful empty-result retrievals, the
LangGraph workflow allows one bounded correction attempt. Correction stops if
all executions fail, the budget is exhausted, or the replanner returns an
identical plan.

The current API is scoped to GitHub-backed enterprise-data questions. Planning
returns `executable`, `clarification_required`, `unsupported`, or
`no_tool_required`. Only executable plans reach tool execution; clarification
and unsupported outcomes stop the graph, while no-tool requests use the
direct-answer path.

## Development Setup

Requires Python 3.12.

Install the application and test dependencies:

```bash
python -m pip install -e ".[test]"
python -m pip check
```

Install the lint/format tool separately if needed:

```bash
python -m pip install "ruff>=0.16,<0.17"
```

### Routine Tests

These tests use deterministic implementations, fakes, or mocks and do not
require GitHub or LM Studio:

```bash
python -m pytest -m "not live" -q
```

### Live Tests

These require external services such as LM Studio or GitHub:

```bash
python -m pytest -m live -q
```

Plain `python -m pytest` selects both groups.

### Lint and Formatting

Check without modifying files:

```bash
ruff check .
ruff format --check .
```

Apply available automatic fixes and formatting:

```bash
ruff check . --fix
ruff format .
```

Ruff cannot automatically fix every reported issue. Review the changes
and rerun the checks afterward.

## Run the API

Start LM Studio's OpenAI-compatible server at
`http://localhost:1234/v1` with the configured model loaded.

The current default model identifier is `qwen/qwen3-8b`.
Configuration is in `src/agentic_rag/llm/lm_studio.py`.

Then start FastAPI:

```bash
python -m uvicorn agentic_rag.api.app:app --reload
```

Open Swagger at `http://127.0.0.1:8000/docs`.

## Demo Query

Submit to `POST /query`:

```json
{
  "query": "What currently blocks production rollout according to issue #1 and its comments in rajashree23/agentic-rag-demo-data?"
}
```

The demo data contains an original rollout requirement and later discussion
updates. The pipeline should distinguish the current documented blocker
from an earlier, superseded blocker.

The API returns:

- Execution results and tool metadata.
- Normalized evidence and normalization warnings.
- Evidence assessment or assessment error.
- Synthesized claims and limitations, or synthesis error.
- Resolved citations containing original source metadata and URLs.

Evidence IDs are generated per normalization and may differ between requests.

## Validation Boundaries

Implemented checks include structured model validation, assessment evidence
references, claim-level citation requirements, citation scope, duplicate
evidence-ID rejection during source resolution, and response-state consistency.

A valid citation reference does not prove that the evidence supports the
claim. Source resolution does not verify URL accessibility.

## Retrieval Strategy

The current milestone implements live retrieval through GitHub API tools.
It does not yet implement indexed document retrieval.

Planned indexed retrieval includes:

1. Ingesting documents and historical source records.
2. Splitting content into meaningful chunks.
3. Preserving source metadata and access-control information per chunk.
4. Generating embeddings and storing chunks in a searchable index.
5. Retrieving relevant chunks using semantic, keyword, or hybrid search.
6. Normalizing retrieved chunks into the common evidence contract.
7. Assessing evidence and synthesizing answers with source citations.

Index refresh, changed/deleted content, retrieval quality, and authorization
will need explicit handling.

Live retrieval and indexed retrieval are separate paths that will feed
the same evidence, assessment, and synthesis stages.

## Remaining Work

- Detailed PR information, reviews, and other targeted GitHub capabilities.
- Slack and Notion retrieval.
- Stateful graph orchestration beyond the current bounded correction loop.
- Step and sub-query UUID migration.
- Authentication and authorization.
- Stronger prompt-injection controls.
- Automated semantic-grounding evaluation.
- Indexed retrieval: ingestion, chunking, embeddings, indexing, and retrieval.
- Index refresh and source-change handling.
- Persistent memory, separate from the retrieval index.
- Observability.
- A demo UI.

## Documentation

- `docs/system-contract.md`: intended scope and requirements.
- `docs/architecture.md`: architectural direction.
- `docs/schemas/`: stage contracts.

Some architecture documents describe target behavior beyond the current
implementation. The current milestone is live GitHub retrieval through
evidence-backed synthesis and source resolution.
