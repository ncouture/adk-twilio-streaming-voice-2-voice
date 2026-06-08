import os
import asyncio
import base64
import logging
import warnings
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from twilio.twiml.voice_response import Connect, Stream, VoiceResponse

from live_messaging import (
    AgentEvent,
    agent_to_client_messaging,
    send_pcm_to_agent,
    start_agent_session,
    text_to_content,
)
from audio import adk_pcm24k_to_twilio_ulaw8k, twilio_ulaw8k_to_adk_pcm16k

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress Pydantic serialization warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

APP_NAME = "stormvault-net-demo-agent"

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Telephony service starting up...")
    yield
    logger.info("Telephony service shutting down...")

# Initialize app with lifespan
api = FastAPI(lifespan=lifespan)


@api.post("/incoming-call")
async def create_call(req: Request):
    """Generate TwiML to connect a call to a Twilio Media Stream"""

    host = req.url.hostname
    scheme = req.url.scheme

    ws_protocol = "ws" if scheme == "http" else "wss"
    ws_url = f"{ws_protocol}://{host}/stream"

    stream = Stream(url=ws_url)
    connect = Connect()
    connect.append(stream)
    response = VoiceResponse()
    response.append(connect)

    logger.info(f"Incoming call connected to {ws_url}")

    return HTMLResponse(content=str(response), media_type="application/xml")


@api.websocket("/stream")
async def twilio_websocket(ws: WebSocket):
    """Handle Twilio Media Stream WebSocket connection"""

    await ws.accept()
    await ws.receive_json()  # throw away `connected` event

    start_event = await ws.receive_json()
    assert start_event["event"] == "start"

    call_sid = start_event["start"]["callSid"]
    stream_sid = start_event["streamSid"]
    user_id = uuid4().hex  # Fake user ID for this example

    # Start agent session (native tools are now loaded in agent.py)
    live_events, live_request_queue = await start_agent_session(
        user_id, call_sid, extra_tools=None
    )

    # Agent speaks first
    initial_message = text_to_content("Introduce yourself briefly.", "user")
    live_request_queue.send_content(initial_message)

    async def handle_agent_event(event: AgentEvent):
        """Handle outgoing AgentEvent to Twilio WebSocket"""

        if event.type == "complete":
            return

        if event.type == "interrupted":
            logger.info(f"Agent interrupted")
            return await ws.send_json({"event": "clear", "streamSid": stream_sid})

        if event.type == "terminate":
            logger.info("Termination signal received from agent. Closing call.")
            await ws.close()
            return

        ulaw_bytes = adk_pcm24k_to_twilio_ulaw8k(event.payload)
        payload = base64.b64encode(ulaw_bytes).decode("ascii")

        await ws.send_json(
            {
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": payload},
            }
        )

    async def websocket_loop():
        """
        Handle incoming WebSocket messages to Agent.
        """
        try:
            while True:
                event = await ws.receive_json()
                event_type = event["event"]

                if event_type == "stop":
                    logger.debug(f"Call ended by Twilio. Stream SID: {stream_sid}")
                    break

                elif event_type == "media":
                    payload = event["media"]["payload"]
                    mulaw_bytes = base64.b64decode(payload)
                    pcm_bytes = twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes)
                    send_pcm_to_agent(pcm_bytes, live_request_queue)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")

    try:
        tasks = [
            asyncio.create_task(websocket_loop()),
            asyncio.create_task(agent_to_client_messaging(handle_agent_event, live_events))
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        for t in done:
            t.result()
    except Exception as ex:
        logger.exception(f"Unexpected Error: {ex}")
    finally:
        live_request_queue.close()
        try:
            await ws.close()
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(api, host="0.0.0.0", port=port)
