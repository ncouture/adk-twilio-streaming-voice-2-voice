import asyncio
from agents.google_calendar_booking.agent import get_booking_agent


async def main():
    # Initialize the native ADK Agent
    agent = get_booking_agent()

    print("Google Calendar Booking Agent initialized (Native).")

    # Execute a Natural Language query
    user_prompt = "What is on my calendar for today?"
    print(f"User: {user_prompt}\n")

    print("Agent is thinking...\n")
    response = await agent.invoke_async(user_prompt)

    print(f"Agent: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
