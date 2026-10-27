# Architecture Goals

The architecture is designed to:

1. **Support multi-step, stateful reasoning** through controlled, graph-based orchestration and bounded self-correction.

2. **Separate core responsibilities** across query understanding, planning, execution, retrieval, evidence validation, memory, and synthesis.

3. **Support live and indexed retrieval** from enterprise applications, semantic knowledge stores, and persistent memory.

4. **Provide standardized, extensible integration** through MCP boundaries, allowing new enterprise sources without changing core orchestration.

5. **Enforce strong contracts and structured data flow** using typed schemas, validation, interfaces, and dependency injection.

6. **Enforce security boundaries** including authentication, authorization, PII handling, prompt-injection protection, and treating retrieved content as untrusted data.

7. **Produce grounded, traceable responses** with validated evidence, provenance, and source-linked citations.

8. **Provide production reliability** through timeouts, bounded retries, failure handling, fallback strategies, and prompt/model versioning.

9. **Provide cost-aware, observable execution** with token/cost tracking, end-to-end tracing, state transitions, tool calls, latency, and failures.

10. **Support scalable retrieval and quality evaluation** through source-aware chunking, metadata enrichment, embeddings, semantic/hybrid search, persistent memory, and independent evaluation of planning, retrieval, grounding, and response quality.


# High-Level Architecture

The system is organized into distinct layers for client access, API handling, agent orchestration, retrieval, evidence processing, and response synthesis.

```text

                              ┌──────────────────────┐
                              │      Client / UI     │
                              │                      │
                              │ Query / Answer /     │
                              │ Citations / Trace    │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │   API / Service      │
                              │        Layer         │
                              │                      │
                              │ Request Validation   │
                              └──────────┬───────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────┐
                    │       Agent Orchestration Layer     │
                    │                                     │
                    │  Query Understanding                │
                    │          ↓                          │
                    │  Planning / Decomposition           │
                    │          ↓                          │
                    │  Execution / Routing                │
                    │          ↓                          │
                    │  State Management                   │
                    │          ↓                          │
                    │  Retry / Re-planning                │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌───────────────────────────────────────┐
                    │           Retrieval Layer             │
                    │                                       │
                    │  ┌──────────┐ ┌──────────┐ ┌──────┐   │
                    │  │   Live   │ │ Indexed  │ │Memory│   │
                    │  │ Retrieval│ │ Retrieval│ │Retrieval │
                    │  └────┬─────┘ └────┬─────┘ └───┬──┘   │
                    └───────┼────────────┼───────────┼──────┘
                            │            │           │
                            ▼            ▼           ▼
                         GitHub       Indexed      Memory
                         Slack        Knowledge     Store
                         Notion
                            │            │           │
                            └────────────┼───────────┘
                                         ▼
                    ┌─────────────────────────────────────┐
                    │            Evidence Layer           │
                    │                                     │
                    │   Normalize → Validate → Provenance │
                    │                                     │
                    │         ┌───────────────┐           │
                    │         │ Evidence      │           │
                    │         │ Sufficient?   │           │
                    │         └───────┬───────┘           │
                    │                 │                   │
                    │                Yes                  │
                    └─────────────────┼───────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────┐
                    │           Synthesis Layer           │
                    │                                     │
                    │       Grounded Response Generation  │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                              ┌──────────────────┐
                              │ Answer +         │
                              │ Citations        │
                              └──────────────────┘


                    ┌──────────────────────────────────────┐
                    │        Insufficient Evidence         │
                    │                  │                   │
                    │                  ▼                   │
                    │        Agent Orchestration           │
                    │                  │                   │
                    │                  ▼                   │
                    │              Re-plan                 │
                    │                  │                   │
                    │                  ▼                   │
                    │              Retrieval               │
                    └──────────────────────────────────────┘


        ┌──────────────────────────────────────────────────────────────────────────────────┐
        │                Cross-Cutting Concerns                                            │
        │                                                                                  │
        │       Security  │  Authorization  │ Prompt Injection Protection | Observability  │ 
        |       Guardrails | Evaluation                                                    │
        └──────────────────────────────────────────────────────────────────────────────────┘


```

# Current Implemented Graph

```text
decompose → plan
              ├─ executable → execute → normalize → assess → synthesize/END
              │                                  └─ bounded replan → execute
              ├─ no_tool_required → direct_answer → END
              └─ clarification_required or unsupported → END
```

Planning validates capabilities and required arguments before execution.

# Component Responsibilities

| Component                     | Responsibility                                                                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Client / UI**               | Submit queries and present answers, citations, and execution status.                                                                      |
| **API / Service Layer**       | Provide the application boundary, validate requests, and manage API-level concerns.                                                       |
| **Agent Orchestration Layer** | Understand queries, create execution plans, route execution, maintain workflow state, and perform bounded retries or re-planning.         |
| **Retrieval Layer**           | Retrieve information from live enterprise sources, indexed knowledge, and persistent memory.                                              |
| **Evidence Layer**            | Normalize retrieved results, validate evidence, maintain provenance, and determine whether collected evidence is sufficient for the task. |
| **Synthesis Layer**           | Generate grounded responses using validated evidence and produce traceable citations.                                                     |
| **Enterprise Sources**        | Provide source data through the supported retrieval interfaces.                                                                           |
| **Security & Authorization**  | Enforce identity, access control, and data/tool permissions independently of agent reasoning.                                             |
| **Observability**             | Capture execution traces, state transitions, retrieval activity, tool calls, latency, failures, and relevant execution metadata.          |
