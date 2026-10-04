# Agentic RAG

Enterprise-grade, stateful Agentic RAG system for retrieving and reasoning over live enterprise application data and persistent knowledge.

## Current Status

🚧 Early development — project foundation and initial domain models are being implemented.

## Architecture

The system is being designed around:

* Stateful agent orchestration
* Multi-source enterprise retrieval
* MCP-based tool integration
* Semantic/vector retrieval
* Persistent memory
* Evidence-grounded synthesis
* Observability and evaluation

## Development Setup

Requires Python 3.12.

```bash
python -m pip install -e .
pytest
```

## Development Commands

### Install / update project

```bash
python -m pip install -e .
```

### Run tests

```bash
pytest
```

### Lint and auto-fix

```bash
ruff check . --fix
```

### Format code

```bash
ruff format .
```

### Check formatting

```bash
ruff format --check .
```

### Recommended pre-commit check

```bash
ruff check . --fix
ruff format .
pytest
```

## Project Structure

```text
docs/       Architecture and system contracts
src/        Application source code
tests/      Automated tests
```

## Goal

Build an enterprise-grade Agentic RAG system as a portfolio project demonstrating production-oriented AI system design, orchestration, retrieval, state management, and observability.
