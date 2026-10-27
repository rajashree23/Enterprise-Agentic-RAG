# ADR-002: Use bounded evidence-driven correction

## Status

Accepted

## Decision

Allow the LangGraph workflow one correction attempt when retrieval executes
successfully but the resulting evidence is insufficient, including empty
search results.

Keep tool retries inside the execution engine. Do not re-plan when all tool
calls fail, when the correction budget is exhausted, or when the replanner
returns an identical plan.

## Consequences

- The workflow can recover from incomplete or empty retrieval results.
- Duplicate plans cannot cause repeated execution.
- Execution remains bounded and predictable.
- More correction attempts can be introduced later with explicit budgets and
  evaluation.
