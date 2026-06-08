# AI Agent Samples (ADK & A2A)

This repository features a collection of AI agent systems built with Google's **Agent Development Kit (ADK)** and the **Agent-to-Agent (A2A)** protocol. It demonstrates various patterns, from distributed microservice orchestration to real-time voice telephony.

## Main Projects

### 1. Course Creation Agent (Distributed)
A multi-agent system that researches, judges, and builds educational content. It features a team of microservice agents orchestrated to deliver high-quality results.

*   **Architecture:** Distributed microservices where each agent runs in its own container and communicates via A2A.
*   **Orchestrator:** Manages the workflow using `LoopAgent` and `SequentialAgent`.
*   **Researcher:** Gathers information using Google Search.
*   **Judge:** Evaluates research quality.
*   **Content Builder:** Compiles the final course.

### 2. Agentic Telephony
A production-ready, real-time, low-latency AI voice agent that integrates **Twilio Media Streams** with the **Gemini Live API**.

*   **Capabilities:** Full-duplex audio, natural barge-in, and native tool-calling (e.g., Google Calendar).
*   **Persona:** "The Automated Gatekeeper", a bilingual (French/English) Chief of Staff.
*   **Deployment:** Fully containerized for Google Cloud Run.

### 3. Google Calendar Booking
A specialized agent for managing Google Calendar events using native **ADK tools**.

*   **Capabilities:** List calendars, view/create/cancel events with Meet integration.
*   **Deployment:** Fully containerized for Google Cloud Run.

---

## Project Structure

```
production-ready-ai/
├── agents/
│   ├── orchestrator/        # Course Creator Orchestrator
│   ├── researcher/          # Course Creator Researcher
│   ├── judge/               # Course Creator Judgec
│   ├── ontent_builder/      # Course Creator Content Builder
│   ├── agentic_telephony/      # Real-time Voice Agent (Twilio + Gemini Live)
│   ├── google_calendar_booking/ # Native ADK Calendar Agent


├── app/                     # Web App for Course Creator
├── shared/                  # Common logic (A2A utils, Auth, etc.)
└── utils/                   # Helper scripts
```

### Shared files
Files in `shared` are linked into respective agent subdirectories as **symlinks** to avoid duplication.

## Requirements

*   **uv**: Python package manager.
*   **Google Cloud SDK**: For GCP services and authentication.
*   **Twilio Account**: Required for the Telephony agent.

## Quick Start (Course Creator)

1.  **Install Dependencies:**
    ```bash
    uv sync
    ```

2.  **Set up credentials:**
    ```bash
    gcloud auth application-default login
    ```

3.  **Run Locally:**
    ```bash
    ./run_local.sh
    ```
    Access the App at **http://localhost:8000**.

## Deployment

To deploy the Course Creation system to Google Cloud Run, each service must be deployed individually. See `GEMINI.md` or `deploy.sh` for details.
