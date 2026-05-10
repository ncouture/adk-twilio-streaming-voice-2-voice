import os

# import datetime
import asyncio
import base64
import logging
import warnings

from contextlib import asynccontextmanager
from uuid import uuid4

import mcp

# from google.adk.tools.mcp_tool import mcp_session_manager
# from google.adk.tools.mcp_tool import mcp_toolset
from google.adk.tools.mcp_tool.mcp_toolset import StdioServerParameters, MCPToolset

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

# We're storing the tools globally so the Agent can use them
mcp_tools = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Define how to launch the server
    server_params = StdioServerParameters(
        command="python3",
        args=[os.path.abspath("mcp_service/google_calendar_api.py")],
        env=os.environ.copy(),
    )

    # 2. Initialize the toolset and get tools
    calendar_toolset = MCPToolset(connection_params=server_params)
    try:
        global mcp_tools
        mcp_tools = await calendar_toolset.get_tools()
        logger.info(f"Connected to MCP: Loaded {len(mcp_tools)} tools.")

        yield  # The FastAPI app runs while we are inside this context
    finally:
        await calendar_toolset.close()


# Initialize app with lifespan
api = FastAPI(lifespan=lifespan)


@api.post("/incoming-call")
def create_call(req: Request):
    """Generate TwiML to connect a call to a Twilio Media Stream"""

    host = req.url.hostname
    scheme = req.url.scheme
    form_data = req.form()

    ws_protocol = "ws" if scheme == "http" else "wss"
    logger.info(f"twilio call request object: {dir(form_data)}")
    logger.info("MCP: Loaded {len(mcp_tools)} tools.")
    ws_url = f"{ws_protocol}://{host}/stream"

    stream = Stream(url=ws_url)
    connect = Connect()
    connect.append(stream)
    response = VoiceResponse()
    response.append(connect)

    logger.info(response)

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

    # Pass the globally loaded MCP tools from lifespan into the session
    live_events, live_request_queue = await start_agent_session(
        user_id, call_sid, extra_tools=mcp_tools
    )

    # Sending an initial message makes the agent speak first when the call starts.
    initial_message = text_to_content("Introduce yourself.", "user")
    live_request_queue.send_content(initial_message)

    async def handle_agent_event(event: AgentEvent):
        """Handle outgoing AgentEvent to Twilio WebSocket"""

        if event.type == "complete":
            logger.info(f"Agent turn complete at {event.timestamp}")
            return

        if event.type == "interrupted":
            logger.info(f"Agent interrupted at {event.timestamp}")
            # https://www.twilio.com/docs/voice/media-streams/websocket-messages#send-a-clear-message
            return await ws.send_json({"event": "clear", "streamSid": stream_sid})

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
        while True:
            event = await ws.receive_json()
            event_type = event["event"]

            if event_type == "stop":
                logger.debug(f"Call ended by Twilio. Stream SID: {stream_sid}")
                break

            if event_type == "start" or event_type == "connected":
                logger.warning(f"Unexpected Twilio Initialization event: {event}")
                continue

            elif event_type == "dtmf":
                digit = event["dtmf"]["digit"]
                logger.info(f"DTMF: {digit}")
                continue

            elif event_type == "mark":
                logger.info(f"Twilio sent a Mark Event: {event}")
                continue

            elif event_type == "media":
                payload = event["media"]["payload"]
                mulaw_bytes = base64.b64decode(payload)
                pcm_bytes = twilio_ulaw8k_to_adk_pcm16k(mulaw_bytes)
                send_pcm_to_agent(pcm_bytes, live_request_queue)

    try:
        websocket_coro = websocket_loop()
        websocket_task = asyncio.create_task(websocket_coro)
        messaging_coro = agent_to_client_messaging(handle_agent_event, live_events)
        messaging_task = asyncio.create_task(messaging_coro)
        tasks = [websocket_task, messaging_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for p in pending:
            p.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for d in done:
            if d.cancelled():
                continue
            exception = d.exception()
            if exception:
                raise exception
    except (KeyboardInterrupt, asyncio.CancelledError, WebSocketDisconnect):
        logger.warning("Process interrupted, exiting...")
    except Exception as ex:
        logger.exception(f"Unexpected Error: {ex}")
    finally:
        live_request_queue.close()
        try:
            await ws.close()
        except Exception as ex:
            logger.warning(f"Error while closing WebSocket: {ex}")
