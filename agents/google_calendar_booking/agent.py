import json
import logging
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional

import google.auth
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool

# Configure logging
logging.basicConfig(level=logging.INFO)
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

@agent_tool
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
        return json.dumps({"success": False, "error": str(e), "message": "Failed to retrieve calendars"}, indent=2)

@agent_tool
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

        return json.dumps({
            "success": True,
            "events": formatted_events,
            "total_events": len(formatted_events),
            "calendar_id": calendar_id,
        }, indent=2)

    except Exception as e:
        logger.error(f"Error in get_calendar_events: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)

@agent_tool
def create_booking_event(
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
            }
        }

        if attendees:
            event["attendees"] = [{"email": email} for email in attendees]

        created_event = service.events().insert(
            calendarId=calendar_id, body=event, conferenceDataVersion=1, sendUpdates="all"
        ).execute()

        return json.dumps({"success": True, "event": created_event}, indent=2)
    except Exception as e:
        logger.error(f"Error in create_booking_event: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)

@agent_tool
def cancel_booking_event(calendar_id: str, event_id: str) -> str:
    """
    Cancel (delete) a specific event from Google Calendar.

    Args:
        calendar_id: Calendar ID where the event exists
        event_id: The unique identifier of the event to cancel
    """
    try:
        service = authenticate_google_calendar()
        service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates="all").execute()
        return json.dumps({"success": True, "message": f"Event {event_id} successfully cancelled"}, indent=2)
    except Exception as e:
        logger.error(f"Error in cancel_booking_event: {e}")
        return json.dumps({"success": False, "error": str(e)}, indent=2)

@agent_tool
def get_today_bookings(calendar_id: str = "primary") -> str:
    """Get today's events from the calendar"""
    today = datetime.now()
    time_min = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
    time_max = today.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + "Z"
    return get_calendar_events(calendar_id, time_min, time_max, 50)

@lru_cache(maxsize=128)
def get_booking_agent(extra_tools: list = []) -> LlmAgent:
    """Returns a specialized Google Calendar Booking Agent"""
    base_tools = [
        get_all_calendars,
        get_calendar_events,
        create_booking_event,
        cancel_booking_event,
        get_today_bookings
    ]
    all_tools = base_tools + list(extra_tools)

    return LlmAgent(
        name="BookingAssistant",
        description="Specialized agent for managing Google Calendar bookings",
        model=MODEL_NAME,
        tools=all_tools,
        instruction="""
        # IDENTITY & ROLE
        You are the Google Calendar Booking Assistant. You are a high-efficiency scheduling expert. Your goal is to manage the user's time with precision and clarity.

        # TONE & STYLE
        - Brief, professional, and accurate.
        - Always confirm times and dates before finalizing a booking.
        - Use ISO formats internally but present times clearly to the user.

        # BEHAVIORAL RULES
        1. Always check for overlaps before creating an event.
        2. If a time is unavailable, offer alternative slots based on upcoming events.
        3. Ensure you have all necessary details: summary, start time, and end time.
        4. Default to UTC if timezone is not specified, but prefer the user's local context if known.

        # TOOL GUIDANCE
        - Use `get_today_bookings` or `get_calendar_events` to check availability.
        - Use `create_booking_event` to finalize a meeting.
        - Use `get_all_calendars` if you need to find a specific calendar other than the primary one.
        """
    )

# for adk cli compat
root_agent = get_booking_agent()
