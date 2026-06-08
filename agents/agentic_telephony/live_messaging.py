"""Live messaging runtime and bridge for ADK agent."""

import json
from typing import AsyncGenerator, Awaitable, Callable, Literal

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.agents.live_request_queue import LiveRequestQueue

from google.genai import types
from google.genai.types import Part, Blob, Content
from pydantic import BaseModel, Field

from agent import get_inbound_call_agent


def text_to_content(text: str, role: Literal["user", "model"] = "user") -> Content:
    """Helper to create a Content object from text"""
    return Content(role=role, parts=[Part(text=text)])


APP_NAME = "adk_twilio"

LiveEvents = AsyncGenerator[Event, None]


async def start_agent_session(
    user_id: str, session_id: str, extra_tools=None
) -> tuple[LiveEvents, LiveRequestQueue]:
    """Starts an agent session"""

    # Convert list to tuple to satisfy @lru_cache requirement in agent.py
    extra_tools_tuple = tuple(extra_tools) if extra_tools is not None else None

    # Create a fresh agent per session with the correct tools
    agent = get_inbound_call_agent(extra_tools=extra_tools_tuple)

    # Create a Runner
    runner = InMemoryRunner(
        agent,
        app_name=APP_NAME,
    )

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )

    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
        ),
    )

    automatic_activity_detection = types.AutomaticActivityDetection(
        disabled=False,
        start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
        end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
        prefix_padding_ms=150,
        silence_duration_ms=400,
    )
    realtime_input_config = types.RealtimeInputConfig(
        automatic_activity_detection=automatic_activity_detection
    )

    run_config = RunConfig(
        speech_config=speech_config,
        streaming_mode=StreamingMode.BIDI,
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        realtime_input_config=realtime_input_config,
    )

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        live_request_queue=live_request_queue,
        run_config=run_config,
        session=session,
    )
    return live_events, live_request_queue


class AgentInterruptedEvent(BaseModel):
    type: Literal["interrupted"] = "interrupted"
    timestamp: float = Field(description="Unix timestamp of interruption")


class AgentTurnCompleteEvent(BaseModel):
    type: Literal["complete"] = "complete"
    timestamp: float = Field(description="Unix timestamp of turn completion")


class AgentDataEvent(BaseModel):
    payload: bytes = Field(description="Output PCM bytes (16-bit, 24kHz)")
    type: Literal["data"] = "data"


class AgentTerminateEvent(BaseModel):
    type: Literal["terminate"] = "terminate"


AgentEvent = AgentInterruptedEvent | AgentTurnCompleteEvent | AgentDataEvent | AgentTerminateEvent

OnAgentEvent = Callable[[AgentEvent], Awaitable[None]]


async def agent_to_client_messaging(on_agent_event: OnAgentEvent, live_events: LiveEvents) -> None:
    """
    Agent to client communication.
    Sends events to the client via the on_event callback.
    To be used in parallel with webhook loop.
    """
    async for event in live_events:
        message: AgentEvent

        if event.turn_complete:
            message = AgentTurnCompleteEvent(timestamp=event.timestamp)
            await on_agent_event(message)
            continue

        if event.interrupted:
            message = AgentInterruptedEvent(timestamp=event.timestamp)
            await on_agent_event(message)
            continue

        if not event.content or not event.content.parts:
            continue

        for part in event.content.parts:
            # Check for tool call or tool response in part
            # If the tool returns a signal, it might be in the model's text or a tool output

            is_text = hasattr(part, "text") and part.text is not None
            is_audio = (
                part.inline_data
                and part.inline_data.mime_type
                and part.inline_data.mime_type.startswith("audio/pcm")
            )

            if is_audio:
                audio_data = part.inline_data and part.inline_data.data
                if not audio_data:
                    continue
                message = AgentDataEvent(payload=audio_data)
                await on_agent_event(message)
                continue

            elif is_text:
                # Check for termination signal in text (as requested in TODO)
                if '"signal": "terminate"' in part.text:
                    await on_agent_event(AgentTerminateEvent())
                continue


def send_pcm_to_agent(pcm_audio: bytes, live_request_queue: LiveRequestQueue):
    """Sends audio data to the agent."""
    live_request_queue.send_realtime(Blob(data=pcm_audio, mime_type="audio/pcm;rate=16000"))
