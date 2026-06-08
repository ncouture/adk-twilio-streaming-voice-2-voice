# Project: production-ready-ai

A collection of distributed AI agent systems demonstrating multi-agent orchestration, real-time voice telephony, and calendar integration using Google's Agent Development Kit (ADK) and the Agent-to-Agent (A2A) protocol.

## Tech Stack

- **Language(s):** Python 3.10+, JavaScript, HTML/CSS
- **Framework(s):** Google ADK, A2A SDK, FastAPI, Uvicorn
- **Package Manager:** `uv`
- **Test Framework:** `pytest` (with `pytest-asyncio`)

## Commands

- **Build:** `uv sync` (to synchronize dependencies)
- **Test:** `uv run pytest`
- **Lint:** `uv run ruff check` and `uv run mypy .`
- **Format:** `uv run ruff format`
- **Run:** `./run_local.sh` (to run services locally)

## Directory Structure

- `agents/` — Containerized microservice agents (orchestrator, researcher, judge, content_builder, agentic_telephony, google_calendar_booking)
- `app/` — Web application frontend (Vanilla HTML/CSS/JS) and FastAPI backend for the Course Creation system
- `shared/` — Common logic symlinked into agent directories (modify here, not in symlinks)
- `tests/` — Contains `unit` and `integration` test suites
- `utils/` — Miscellaneous helper and utility scripts

## Conventions

- **Naming Convention:** `snake_case` for functions/variables/files, `PascalCase` for classes.
- **Error Handling:** Standard Python exceptions, Pydantic/JSON validation, and strict type checking with mypy.
- **Import Pattern:** Absolute imports from the project root and shared libraries.
- **Test Organization:** Co-located in `tests/` directory split into `unit` and `integration` subdirectories.
