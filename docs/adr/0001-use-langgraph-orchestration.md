# ADR-001: Use LangGraph for workflow orchestration

## Status

Accepted

## Decision

Use LangGraph to orchestrate the query workflow because the system needs
typed state transitions, conditional routing, bounded re-planning, and future
support for checkpointing and human-in-the-loop execution.

Keep application services injected as dependencies and keep per-run data in
the graph state.

## Consequences

- Workflow control becomes explicit and testable.
- Correction loops can be bounded and observed.
- Persistence and human-in-the-loop execution can be added later.
- The project gains an additional framework dependency and graph-specific
  state-management complexity.
