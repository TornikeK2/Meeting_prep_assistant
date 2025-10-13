"""
Test script for Google Calendar API integration
Lists your upcoming calendar events
"""
from datetime import datetime, timedelta
from src.utils.auth import GoogleAuthManager


def test_calendar_access():
    """Test basic calendar access and list upcoming events"""
    print("--- Testing Google Calendar API ---\n")

    # Authenticate
    auth = GoogleAuthManager()
    calendar_service = auth.get_calendar_service()

    # Get events for next 7 days
    now = datetime.utcnow()
    time_min = now.isoformat() + 'Z'
    time_max = (now + timedelta(days=7)).isoformat() + 'Z'

    print(f"Fetching events from {now.strftime('%Y-%m-%d')} to " +
          f"{(now + timedelta(days=7)).strftime('%Y-%m-%d')}\n")

    try:
        events_result = calendar_service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print("No upcoming events found.")
            return

        print(f"Found {len(events)} upcoming events:\n")
        print("-" * 80)

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', '(No title)')
            attendees = event.get('attendees', [])

            print(f"\n {title}")
            print(f"   Time: {start}")
            print(f"   Attendees: {len(attendees)} people")

            if event.get('description'):
                desc = event['description'][:100]
                print(f"   Description: {desc}...")

        print("\n" + "-" * 80)
        print(f"\n✓ Successfully retrieved {len(events)} events from Calendar API!")

    except Exception as e:
        print(f" Error accessing Calendar API: {e}")
        raise


if __name__ == "__main__":
    test_calendar_access()