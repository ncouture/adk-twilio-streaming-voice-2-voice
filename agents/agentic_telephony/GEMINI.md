# Gemini Context: Twilio Gemini Agent Samples

This project demonstrates a real-time, low-latency AI voice agent that integrates **Twilio Media Streams** with the **Gemini Live API** using the **Google Agent Development Kit (ADK)**.

## Project Overview

The core of the application is a FastAPI server that bridges telephony (via Twilio) and generative AI (via Gemini). It handles full-duplex audio streaming, enabling natural "barge-in" (interruptible) conversations and tool-calling capabilities.

The primary agent persona is **Nick**, an Onboarding Specialist for the premium **StormMind AI** Executive Assistant service. Nick is a high-status, high-competence concierge who welcomes new members and guides them through configuring their call-handling preferences (Triage, Route, or Hand Off calls).

### Key Technologies
- **Gemini Live API**: Real-time multimodal interaction using the `gemini-3.1-flash-live-preview` model.
- **Google Agent Development Kit (ADK)**: Framework for building and running AI agents using `LlmAgent` and `InMemoryRunner` (using ADK 2.x).
- **OpenTelemetry / Cloud Logging**: Integrated via Google Cloud Platform logging and trace exporters for real-time diagnostics and agent observability.
- **FastAPI**: Web framework for the TwiML webhook and WebSocket media stream.
- **Twilio**: Telephony interface providing the audio stream (8kHz μ-law).
- **Model Context Protocol (MCP)**: Used for connecting external tools like Google Calendar via `MCPToolset`.
- **Soxr & NumPy**: High-quality audio resampling and transcoding between μ-law and PCM.

## Architecture

- **`main.py`**: The application entry point. Defines the FastAPI app with an `asynccontextmanager` lifespan that discovers and initializes MCP tools (e.g., Google Calendar). It also:
    - Sets up OpenTelemetry providers with GCP trace/logging exporters.
    - Handles `/incoming-call` (TwiML endpoint for call connection).
    - Handles `/stream` (WebSocket handler for bi-directional Twilio Media Streams, including handling agent termination signals).
- **`agent.py`**: Defines the agent factory `get_inbound_call_agent`.
    - Uses `lru_cache` for performance.
    - Defines the sophisticated high-status "Nick" (StormMind AI) onboarding persona and instructions.
    - Implements `hangup_tool` and `goodbye_tool` that return `{"signal": "terminate"}` to end calls cleanly.
- **`live_messaging.py`**: Orchestrates the ADK session.
    - Bridges ADK `Event` objects (audio, interruptions, turn completion) to the client.
    - Manages `LiveRequestQueue` for sending real-time audio (16kHz PCM) and initial text prompts.
    - Configures `SpeechConfig` (using the "Charon" voice) and `AutomaticActivityDetection`.
    - Checks for tool-driven `"signal": "terminate"` strings to trigger clean WebSocket termination.
- **`audio.py`**: Utilities for transcoding:
    - `adk_pcm24k_to_twilio_ulaw8k`: For agent output.
    - `twilio_ulaw8k_to_adk_pcm16k`: For user input.
- **`mcp_service/`**: Contains internal MCP server implementations.
    - `google_calendar_api.py`: A local MCP server for direct Google Calendar integration using Application Default Credentials (ADC).
- **`agent-dj-example.py`**: A reference implementation for a different persona ("DJ Jaz") using `gemini-2.5-flash-native-audio-latest`.

## Getting Started

### Prerequisites
- Python 3.10+
- A Google Cloud Project with the Gemini API enabled (Vertex AI or AI Studio).
- A Twilio account and phone number.
- Environment variables:
    - `GOOGLE_APPLICATION_CREDENTIALS`: For ADC.
    - `GEMINI_API_KEY`: If not using Vertex AI.

### Installation
```bash
# Recommended: use uv for fast dependency management
uv sync
```

### Running the Server
The server must be accessible to Twilio (e.g., via `ngrok`).
```bash
uvicorn main:api --host 0.0.0.0 --port 8000
```

### Twilio Configuration
1. Configure your Twilio Phone Number's "A Call Comes In" webhook to:
   `POST https://your-domain.com/incoming-call`

## Development Conventions

- **Agent Configuration**: Modify `agent.py` to change persona or base tools. Note that `extra_tools` must be passed as a tuple to satisfy `lru_cache`.
- **Tool Integration**: Use **MCP** for adding new capabilities. Register new servers in the `lifespan` hook in `main.py`.
- **Audio Logic**: All transcoding logic is centralized in `audio.py`.
- **Voice Selection**: Voice configuration (e.g., "Charon", "Zephyr") is managed in `live_messaging.py`.
- **Testing**: Use `mcp_service/google_calendar_api.py` as a reference for building new toolsets.

## Key Improvements (Recently Resolved)

- **Call Termination Latency**: Solved by replacing the legacy 15s sleep exception with a signaling mechanism. The goodbye/hangup tools return a `{"signal": "terminate"}` payload. `live_messaging.py` checks for this substring in the agent's text response and raises an `AgentTerminateEvent`, which prompts `main.py` to close the Twilio WebSocket immediately and cleanly.

## Roadmap & Known Issues

- **Barge-In Optimization**: While `main.py` sends a `clear` event to Twilio, the Gemini model's generation should also be canceled/interrupted in `live_messaging.py` to minimize latency on new input.
- **Tool Health Monitoring**: Add a health check endpoint to verify that MCP tools (like Google Calendar) are correctly loaded and authenticated.
- **Audio Latency**: Continued profiling of `audio.py` (specifically `soxr` resampling) is needed to keep conversation latency below 500ms.
- **Cleanup**: Remove redundant `root_agent` and commented-out code in `agent.py` to maintain clarity.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:7510c1e2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
