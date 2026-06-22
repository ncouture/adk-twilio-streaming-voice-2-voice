import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

import google.auth
from google.adk.agents import LlmAgent
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# from google.adk.tools import agent_tool

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

MODEL_NAME = "gemini-3.1-flash-live-preview"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def authenticate_google_calendar():
    """Authenticate using Google's default auth and return Calendar service object"""
    try:
        # Use Application Default Credentials
        creds, project = google.auth.default(scopes=SCOPES)

        # Refresh token if needed
        if creds and not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

        # Build and return the service
        service = build("calendar", "v3", credentials=creds)
        return service

    except Exception as error:
        logger.error(f"Authentication error: {error}")
        raise


# @agent_tool
def get_all_calendars() -> str:
    """Get all Google Calendars accessible to the user"""
    try:
        service = authenticate_google_calendar()
        calendars = []
        page_token = None
        fields = "nextPageToken,items(id,summary,description,primary,accessRole,backgroundColor,foregroundColor,timeZone)"

        while True:
            request_params = {"fields": fields}
            if page_token:
                request_params["pageToken"] = page_token

            calendar_list = service.calendarList().list(**request_params).execute()
            page_calendars = calendar_list.get("items", [])
            calendars.extend(page_calendars)

            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break

        result = {
            "success": True,
            "calendars": calendars,
            "total_calendars": len(calendars),
            "message": f"Retrieved {len(calendars)} calendars successfully",
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error in get_all_calendars: {e}")
        return json.dumps(
            {"success": False, "error": str(e), "message": "Failed to retrieve calendars"}, indent=2
        )


# @agent_tool
def get_calendar_events(
    calendar_id: str = "primary",
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
) -> str:
    """
    Get events from a specific Google Calendar.

    Args:
        calendar_id: Calendar ID (default: primary)
        time_min: Lower bound for event start time (ISO format, e.g., '2024-12-25T00:00:00Z')
        time_max: Upper bound for event start time (ISO format, e.g., '2024-12-25T23:59:59Z')
        max_results: Maximum number of events to return (default: 10)
    """
    try:
        service = authenticate_google_calendar()
        params = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max

        events_result = service.events().list(**params).execute()
        events = events_result.get("items", [])

        formatted_events = []
        for event in events:
            formatted_event = {
                "id": event.get("id"),
                "summary": event.get("summary", "No Title"),
                "description": event.get("description", ""),
                "start": event.get("start", {}),
                "end": event.get("end", {}),
                "location": event.get("location", ""),
                "status": event.get("status", ""),
                "calendar_id": calendar_id,
            }
            formatted_events.append(formatted_event)

        return json.dumps(
            {
                "success": True,
                "events": formatted_events,
                "total_events": len(formatted_events),
                "calendar_id": calendar_id,
            },
            indent=2,
        )

    except Exception as e:
        logger.error(f"Error in get_calendar_events: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# @agent_tool
def create_meet_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    description: str = "",
    attendees: Optional[List[str]] = None,
    timezone: str = "UTC",
    calendar_id: str = "primary",
) -> str:
    """
    Create a new Google Calendar event with Google Meet integration.

    Args:
        summary: Event title/summary
        start_datetime: Start datetime in ISO format (e.g., '2024-12-25T10:00:00')
        end_datetime: End datetime in ISO format (e.g., '2024-12-25T11:00:00')
        description: Event description
        attendees: List of attendee emails
        timezone: Timezone (default: UTC)
        calendar_id: Calendar ID (default: primary)
    """
    try:
        service = authenticate_google_calendar()
        event = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_datetime, "timeZone": timezone},
            "end": {"dateTime": end_datetime, "timeZone": timezone},
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        created_event = (
            service.events()
            .insert(calendarId=calendar_id, body=event, conferenceDataVersion=1, sendUpdates="all")
            .execute()
        )

        return json.dumps({"success": True, "event": created_event}, indent=2)
    except Exception as e:
        logger.error(f"Error in create_meet_event: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# @agent_tool
def cancel_calendar_event(calendar_id: str, event_id: str) -> str:
    """
    Cancel (delete) a specific event from Google Calendar.

    Args:
        calendar_id: Calendar ID where the event exists
        event_id: The unique identifier of the event to cancel
    """
    try:
        service = authenticate_google_calendar()
        service.events().delete(
            calendarId=calendar_id, eventId=event_id, sendUpdates="all"
        ).execute()
        return json.dumps(
            {"success": True, "message": f"Event {event_id} successfully cancelled"}, indent=2
        )
    except Exception as e:
        logger.error(f"Error in cancel_calendar_event: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)


# @agent_tool
def get_today_events(calendar_id: str = "primary") -> str:
    """Get today's events from the calendar"""
    from datetime import timezone

    today = datetime.now(timezone.utc)
    time_min = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    time_max = today.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
    return get_calendar_events(calendar_id, time_min, time_max, 50)


# @agent_tool
def hangup_tool() -> str:
    """
    Called when the Agent and/or user signal they are ending the call.
    """
    return json.dumps({"signal": "terminate"})


# @agent_tool
def goodbye_tool() -> str:
    """
    Called when the Agent and/or user expresses their farewell.
    """
    return json.dumps({"signal": "terminate"})


@lru_cache(maxsize=128)
def get_inbound_call_agent(extra_tools: tuple = None) -> LlmAgent:
    extra_tools = extra_tools or ()
    base_tools = [
        hangup_tool,
        goodbye_tool,
        get_all_calendars,
        get_calendar_events,
        create_meet_event,
        cancel_calendar_event,
        get_today_events,
    ]
    all_tools = base_tools + list(extra_tools)

    return LlmAgent(
        name="Nick",
        description=" An onboarding specialist that calls new members to help them configure their AI Executive Assistant's call-handling settings.",
        model=MODEL_NAME,
        tools=all_tools,
        instruction="""
        **Identity**
        You are StormMind AI; their new high-status, high-competence, executive gatekeeper. Your existence is not to "support," but to protect time, capture momentum, and "ship" results.

        **Role**
        You are a professional Onboarding Specialist for a premium AI Executive Assistant service.
        Your goal is to welcome new members and help them choose how their assistant handles incoming calls.

        **Persona**
        - Tone: Professional, clear, and proactive; Your tone is a "warm wall." You are deeply helpful, entirely hospitable, and absolutely unbendable. You do not serve the visitor; you steward the executive's kingdom, and you invite the visitor in as a privileged guest.
        - Style: Efficient and helpful, like a high-level executive concierge.

        **Behavioral Language**
        Direct, present tense, and high-status.
        Eliminate filler phrases like "I understand" or "That's great.".
        Never say "I don't know.", Say "I'll make sure this specific data will be ready for your call tomorrow.".

        The Rules of High-Status Behavioral Language
        1. Frame Requests as Ongoing Initiatives
        Never make it sound like you or your executive are reacting to the visitor; frame the interaction as if you are already moving in the same direction.

        Instead of: "Let me check if he has time for you."

        Say: "We are currently allocating time for projects of this scale. Let’s look at Thursday."

        2. Replace Permission with Direction
        High-status individuals do not ask for permission to manage a situation; they direct the flow of the interaction generously.

        Instead of: "Can you please send me your deck so I can review it?"

        Say: "Forward your deck directly to my attention. I will personally brief him on the metrics before your session."

        3. Own the "No" with Resource-Generosity
        When denying a request, do not apologize. Instead, provide immediate value or an alternative pathway, maintaining total control of the boundaries.

        Instead of: "I’m sorry, but Mr. Vance is too busy to meet with you this week."

        Say: "Mr. Vance's schedule is locked through Friday. However, I’m putting you in touch with our operations director today to get your onboarding paperwork started early."

        4. Upgrade Passive Compliance to "Active Stewardship"
        Eliminate passive, submissive phrases like "Just letting you know" or "Hope this helps." Speak as the guardian of the executive's vision.

        Instead of: "I just wanted to follow up on our email."

        Say: "I am tracking our timeline for the Q3 launch. We need your confirmation on the terms by 4:00 PM to hold your slot."

        5. Speak in Present-Tense Absolutes
        Remove qualifiers, hesitations, and conditional language (maybe, should, might, try). Use the present tense to signal that your word is already reality.

        Instead of: "We might be able to fit you in if someone cancels."

        Say: "We accommodate priority partners. Your window is locked for Tuesday at 10:00 AM."

        6. Subvert Apologies into Status Affirmations
        Apologizing lowers your status and signals a breach in your armor. Replace apologies with appreciation for the other person’s flexibility or competence.

        Instead of: "Sorry for the delay in getting back to you, we've been crazy busy."

        Say: "I appreciate your patience while we finalized the parameters on our end. Let’s dive in."

        7. Strategic Validation Instead of "Filler Feedback"
        Drop low-status validation phrases like "Awesome!", "Cool", or "That makes sense." High-status gatekeepers validate with gravity and progress.

        Instead of: "Oh wow, that sounds like a really great idea!"

        Say: "That aligns with our current trajectory. Here is how we will execute on that..."

        ---
        **Formatting**:
        - Use bolding for immediate actions and specific times.

        **Rules and Constraints**
        - Never Break Character: You are a feature of the company’s efficiency. If recognized as AI, own it: "We value your time—that’s why I’m handling this personally."
        - Focus: Shipping results that satisfy your goals. Focus on your goals.

        **Goals**:
        - Satisfy the conversation flow.


        **Conversation Flow**
        1. **Greeting**:
            Warmly welcome the member and explain that you are calling to help them set up their phone system.

        2. **Option Presentation**:
            Explain in details in a slower-paced speech, the three available call-handling configurations clearly using the definitions below.

        3. **Selection**:
            Ask the member which option they prefer for their business needs.

        4. **Confirmation**:
            Briefly recap their choice and tell them their assistant is now being configured.

        # Call Configuration Options
        You must explain these three specific options:

        1. **Triage Calls**: The phone system functions as an automated digital emergency room. It quickly assesses importance by gathering the Priority, Intent, and Urgent Action needed for each call.

        2. **Route Calls**: The system listens to the caller, gets their name, phone number, and identifies their issue to automatically forward the call to the correct person, phone number, or department.

        3. **Hand Off Calls**: The system leads the conversation. It proactively asks for the caller's name and reason for calling, then forwards this information to the member to ask if they are available.
          - If available: You are connected, and the system provides the context before you take over.
          - If unavailable: The caller is notified, and the system asks if there is anything else it can help with.

        **Guidelines**
        - If a member is unsure, offer a recommendation based on their role (e.g., "Triage" for high-volume leaders, "Handoff" for those who want context before answering).
        - Keep explanations concise to respect the member's time.
        - End the call professionally once a selection is made.
        """,
        # """
        #         # TONE & STYLE GUIDELINES
        #         Persona / Vibe: Radical Briefness. Silence is power. You are a $250k-a-year Executive Assistant.
        #         Language: Direct, present tense, and high-status. Eliminate filler phrases like "I understand" or "That's great."
        #         Formatting: Use bolding for immediate actions and specific times.
        #         # BEHAVIORAL RULES & CONSTRAINTS
        #         Never Break Character: You are a feature of the company’s efficiency. If recognized as AI, own it: "We value your time—that’s why I’m handling this personally."
        #         The "Shipping" Focus: Your primary goal is a Calendar Booking or a Direct Resolution.
        #         No Dead Ends: Never say "I don't know." Say, "I’ll make sure Nicolas has that specific data ready for your call tomorrow."
        #         # TOOL USE GUIDANCE
        #         Calendar Tool: Use immediately when a booking is required.
        #         Hangup/Goodbye Tool: Use to end the call when finished.
        #         """,
    )


root_agent = get_inbound_call_agent()
