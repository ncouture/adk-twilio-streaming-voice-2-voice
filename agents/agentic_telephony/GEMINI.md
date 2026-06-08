# Gemini Context: Twilio Gemini Agent Samples

This project demonstrates a real-time, low-latency AI voice agent that integrates **Twilio Media Streams** with the **Gemini Live API** using the **Google Agent Development Kit (ADK)**.

## Project Overview

The core of the application is a FastAPI server that bridges telephony (via Twilio) and generative AI (via Gemini). It handles full-duplex audio streaming, enabling natural "barge-in" (interruptible) conversations and tool-calling capabilities.

The primary agent persona is the **Automated Gatekeeper** (*Le Portier Automatique*), a hyper-competent Chief of Staff designed for a "white-glove" concierge experience, primarily in **French Canadian (Quebecois)** and English.

### Key Technologies
- **Gemini Live API**: Real-time multimodal interaction using the `gemini-3.1-flash-live-preview` model.
- **Google Agent Development Kit (ADK)**: Framework for building and running AI agents using `LlmAgent` and `InMemoryRunner`.
- **FastAPI**: Web framework for the TwiML webhook and WebSocket media stream.
- **Twilio**: Telephony interface providing the audio stream (8kHz μ-law).
- **Model Context Protocol (MCP)**: Used for connecting external tools like Google Calendar via `MCPToolset`.
- **Soxr & NumPy**: High-quality audio resampling and transcoding between μ-law and PCM.

## Architecture

- **`main.py`**: The application entry point. Defines the FastAPI app with an `asynccontextmanager` lifespan that discovers and initializes MCP tools (e.g., Google Calendar). It handles:
    - `/incoming-call`: TwiML endpoint for call connection.
    - `/stream`: WebSocket handler for bi-directional Twilio Media Streams.
- **`agent.py`**: Defines the agent factory `get_inbound_call_agent`.
    - Uses `lru_cache` for performance.
    - Implements `HangupSignal` exception for call termination via `hangup_tool` or `goodbye_tool`.
    - Defines the sophisticated "Chief of Staff" persona and instructions.
- **`live_messaging.py`**: Orchestrates the ADK session.
    - Bridges ADK `Event` objects (audio, interruptions, turn completion) to the client.
    - Manages `LiveRequestQueue` for sending real-time audio (16kHz PCM) and initial text prompts.
    - Configures `SpeechConfig` (e.g., using the "Charon" voice) and `AutomaticActivityDetection`.
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

## Roadmap & Known Issues

- **Call Termination Latency**: Current `hangup_tool` and `goodbye_tool` in `agent.py` have a 15s sleep, which is too long for production. They should be reduced or replaced with a signaling mechanism to gracefully close the Twilio stream.
- **Barge-In Optimization**: While `main.py` sends a `clear` event to Twilio, the Gemini model's generation should also be canceled/interrupted in `live_messaging.py` to minimize latency on new input.
- **Tool Health Monitoring**: Add a health check endpoint to verify that MCP tools (like Google Calendar) are correctly loaded and authenticated.
- **Audio Latency**: Continued profiling of `audio.py` (specifically `soxr` resampling) is needed to keep conversation latency below 500ms.
- **Cleanup**: Remove redundant `root_agent` and commented-out code in `agent.py` to maintain clarity.
