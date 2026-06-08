✦ I have refactored both @agents/google_calendar_booking and @agents/agentic_telephony to be production-ready and
  compatible with Cloud Run, following the design pattern of @agents/content_builder.
 
  Key Changes:
   1. Removed MCP Design Pattern: Both agents now use native ADK tools (@agent_tool) instead of external MCP servers.
      The Google Calendar integration has been moved directly into the agent logic.
   2. Cloud Run Compatibility: 
       * Created Dockerfile and pyproject.toml for agentic_telephony matching the content_builder example.
       * Updated google_calendar_booking configuration for consistency.
       * Updated dependencies to include google-adk, a2a-sdk, twilio, soxr, and numpy.
   3. Shared Utilities: Due to environment restrictions on creating symbolic links, I have updated adk_app.py and
      a2a_utils.py in both agent directories with the latest content from @shared to ensure compatibility.
   4. Telephony Improvements:
       * Fixed the "Zombie" hangup issue by removing long sleeps and implementing a termination signal ({"signal":
         "terminate"}).
 
       * Updated live_messaging.py and main.py to handle the termination signal gracefully.
   5. Local Execution: Updated @run_local.sh to include both agents on new ports (8005 and 8006), ensuring they can be
      tested locally alongside the other microservices.
 
  Deployment Instructions:
  Both agents are now configured to be deployed to Cloud Run using uv and adk_app.py.
   - Google Calendar Booking: Port 8006 (local) or standard 8080 (Cloud Run).
   - Agentic Telephony: Port 8005 (local). Note that for full telephony functionality, the main.py entry point handles
     the Twilio-specific Media Stream WebSocket and TwiML webhooks.
 
  To run telephony locally:
 
   cd agents/agentic_telephony
   PORT=8005 uv run main.py
 
  To run standard ADK interfaces:
 
   uv run adk_app.py --host 0.0.0.0 --port 8000 --a2a .
 

