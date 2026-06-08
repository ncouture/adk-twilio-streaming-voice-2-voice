import os
import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.mcp import MCPToolset
from mcp import StdioServerParameters

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # 1. Configure the MCP Server connection to our local service
    # This uses our internal implementation which leverages Application Default Credentials
    server_params = StdioServerParameters(
        command="python3",
        args=[os.path.abspath("mcp_service/google_calendar_api.py")],
        env={
            **os.environ,
            # Uses the same environment-based authentication as the Gemini client
        },
    )

    print("Connecting to local Google Calendar MCP Server...")

    # 2. Connect ADK to the MCP server to discover calendar tools
    # Using 'async with' handles the graceful shutdown of the subprocess
    async with MCPToolset.from_stdio(server_params) as calendar_toolset:
        # ADK dynamically queries the server for its tools (list_events, create_event, etc.)
        # and adapts their schemas into native ADK BaseTools.
        tools = await calendar_toolset.get_tools_async()
        print(f"Successfully loaded {len(tools)} tools from MCP.\n")

        # 3. Initialize the ADK Agent
        agent = LlmAgent(
            model="gemini-3.1-pro",
            tools=tools,
            system_instruction=(
                "You are an intelligent scheduling assistant. Use the provided MCP tools "
                "to read, interpret, and manage the user's Google Calendar. Always confirm "
                "times in the user's local timezone."
            ),
        )

        # 4. Execute a Natural Language query
        user_prompt = "Check my calendar for tomorrow. Do I have any overlapping events, and what time is my earliest meeting?"
        print(f"User: {user_prompt}\n")

        print("Agent is thinking (and checking your calendar)...\n")
        response = await agent.invoke_async(user_prompt)

        print(f"Agent: {response.text}")
