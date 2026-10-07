# Agentic RAG

Enterprise-grade, stateful Agentic RAG system for retrieving and reasoning over live enterprise application data and persistent knowledge.

## Current Status

🚧 **Early development**

The core application pipeline is functional, including:

* LLM-based query decomposition and planning
* Dependency-aware asynchronous execution
* FastAPI API boundary
* Real LLM integration through LM Studio
* Automated unit and integration testing
* Interactive API testing through Swagger UI

MCP-based enterprise tools, live and semantic retrieval, evidence-grounded synthesis, persistent memory, and observability are being developed incrementally.

Production engineering concerns such as AuthN/AuthZ, PII protection, prompt-injection defense, secure tool execution, cost tracking, reliability, tracing, and evaluation will be incorporated throughout development.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the detailed architecture.

## Development Setup

Requires Python 3.12.

### Install

```bash
python -m pip install -e .
```

### Run Tests

```bash
python -m pytest
```

### Lint / Format

```bash
ruff check . --fix
ruff format .
ruff format --check .
```

## Run the API

The current LLM integration uses Qwen3 through LM Studio.

Start the LM Studio local server, then run:

```bash
python -m uvicorn agentic_rag.api.app:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Interactive Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

## Project Structure

```text
docs/       Architecture and system contracts
src/        Application source code
tests/      Automated tests
```

## Goal

Build a production-oriented Agentic RAG system demonstrating senior-level software engineering across:

* AI agent orchestration
* Enterprise retrieval and tool integration
* State and memory management
* Security and access control
* Reliability and observability
* Evaluation and production hardening