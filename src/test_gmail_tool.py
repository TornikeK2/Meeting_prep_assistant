"""
Test GmailTool with real calendar meetings
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.auth import GoogleAuthManager
from src.tools.calendar_tool import CalendarTool
from src.tools.gmail_tool import GmailTool


def test_gmail_tool():
    """Test GmailTool with real meeting data"""
    print("=== Testing GmailTool ===\n")

    # Authenticate
    print("Authenticating...")
    auth = GoogleAuthManager()
    calendar_service = auth.get_calendar_service()
    gmail_service = auth.get_gmail_service()

    # Get calendar tool
    calendar_tool = CalendarTool(
        calendar_service,
        internal_domains=['gmail.com']  # Your emails are gmail.com
    )

    # Create Gmail tool
    gmail_tool = GmailTool(gmail_service)

    # Get upcoming meetings
    print("Fetching meetings...\n")
    meetings = calendar_tool.get_upcoming_meetings(
        hours_ahead_min=0,
        hours_ahead_max=168  # 7 days
    )

    if not meetings:
        print("❌ No meetings found to test with.")
        print("Create some test meetings in your Google Calendar first!")
        return

    print(f"✓ Found {len(meetings)} meetings to test\n")
    print("=" * 80)

    # Test email search for each meeting
    for i, meeting in enumerate(meetings[:3], 1):  # Test first 3 meetings
        print(f"\n[{i}] Testing meeting: {meeting['title']}")
        print(f"    Time: {meeting['start_time'].strftime('%Y-%m-%d %I:%M %p')}")
        print(f"    Attendees: {len(meeting['attendees'])} people")

        # Show attendees
        for attendee in meeting['attendees'][:5]:
            print(f"      - {attendee}")
        print()

        # Search for relevant emails with different timeframes
        for days in [7, 14]:  # Test 7 and 14 days
            print(f"    Searching last {days} days...")
            relevant_emails = gmail_tool.search_relevant_emails(meeting, days=days, max_results=5)

            if not relevant_emails:
                print(f"    ⚠️  No relevant emails found (last {days} days)")
                continue

            print(f"    ✓ Found {len(relevant_emails)} relevant emails:\n")

            # Display results
            for j, email in enumerate(relevant_emails, 1):
                print(f"    Email {j}: (Score: {email['relevance_score']})")
                print(f"      Subject: {email['subject']}")
                print(f"      From: {email['from']}")
                print(f"      Date: {email['date']}")
                print(f"      Preview: {email['snippet'][:80]}...")
                print(f"      Link: {email['gmail_link']}")
                print()

            break  # Only test 7 days for first pass

        print("-" * 80)

    print("\n✓ GmailTool test complete!")
    print("\nNext steps:")
    print("1. Verify the correct emails were found for each meeting")
    print("2. Check relevance scores make sense")
    print("3. Adjust scoring algorithm if needed")


if __name__ == "__main__":
    test_gmail_tool()