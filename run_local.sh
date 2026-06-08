#!/bin/bash

# Kill any existing processes on these ports
echo "Stopping any existing processes on ports 8000-8006..."
lsof -ti:8000,8001,8002,8003,8004,8005,8006 | xargs kill -9 2>/dev/null

# Set common environment variables for local development
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="True" # Use Gemini API locally
export GOOGLE_API_KEY="<your-key-here>" # Use if not using Vertex AI

echo "Starting Researcher Agent on port 8001..."
pushd agents/researcher
uv run adk_app.py --host 0.0.0.0 --port 8001 --a2a . &
RESEARCHER_PID=$!
popd

echo "Starting Judge Agent on port 8002..."
pushd agents/judge
uv run adk_app.py --host 0.0.0.0 --port 8002 --a2a . &
JUDGE_PID=$!
popd

echo "Starting Content Builder Agent on port 8003..."
pushd agents/content_builder
uv run adk_app.py --host 0.0.0.0 --port 8003 --a2a . &
CONTENT_BUILDER_PID=$!
popd

echo "Starting Agentic Telephony on port 8005..."
pushd agents/agentic_telephony
PORT=8005 uv run main.py &
TELEPHONY_PID=$!
popd

echo "Starting Google Calendar Booking on port 8006..."
pushd agents/google_calendar_booking
uv run adk_app.py --host 0.0.0.0 --port 8006 --a2a . &
BOOKING_PID=$!
popd

export RESEARCHER_AGENT_CARD_URL=http://localhost:8001/a2a/agent/.well-known/agent-card.json
export JUDGE_AGENT_CARD_URL=http://localhost:8002/a2a/agent/.well-known/agent-card.json
export CONTENT_BUILDER_AGENT_CARD_URL=http://localhost:8003/a2a/agent/.well-known/agent-card.json

echo "Starting Orchestrator Agent on port 8004..."
pushd agents/orchestrator
uv run adk_app.py --host 0.0.0.0 --port 8004 . &
ORCHESTRATOR_PID=$!
popd

# Wait a bit for them to start up
sleep 5

echo "Starting App Server on port 8000..."
pushd app
export AGENT_SERVER_URL=http://localhost:8004

uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
popd

echo "All agents started!"
echo "Researcher: http://localhost:8001"
echo "Judge: http://localhost:8002"
echo "Content Builder: http://localhost:8003"
echo "Orchestrator: http://localhost:8004"
echo "Agentic Telephony: http://localhost:8005"
echo "Google Calendar Booking: http://localhost:8006"
echo "App Server (Frontend): http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop all agents."

# Wait for all processes
trap "kill $RESEARCHER_PID $JUDGE_PID $CONTENT_BUILDER_PID $ORCHESTRATOR_PID $TELEPHONY_PID $BOOKING_PID $BACKEND_PID; exit" INT
wait
