"""Main script for meeting prep assistant"""
import os
import sys
from datetime import datetime
from pathlib import Path
import logging
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import local modules - use absolute imports from project root
from src.utils.auth import GoogleAuthManager
from src.tools.calendar_tool import CalendarTool
from src.tools.gmail_tool import GmailTool

# Load environment variables
load_dotenv()

# Setup logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_meeting_prep_summary(meeting, relevant_emails):
    """Generate prep summary for meeting"""
    summary = []
    summary.append("=" * 60)
    summary.append(f"MEETING PREP: {meeting['title']}")
    summary.append("=" * 60)
    summary.append(f"\nTime: {meeting['start_time']}")
    summary.append(f"Priority: {meeting['priority']}")

    if meeting.get('is_client_meeting'):
        summary.append("\n🔴 CLIENT MEETING - External attendees detected")

    summary.append(f"\nAttendees ({len(meeting['attendees'])}):")
    for attendee_email in meeting['attendees']:
        summary.append(f"  • {attendee_email}")

    if meeting.get('location'):
        summary.append(f"\nLocation: {meeting['location']}")

    if meeting.get('description'):
        summary.append(f"\nDescription:\n{meeting['description'][:200]}...")

    summary.append(f"\n\nRELEVANT EMAILS ({len(relevant_emails)}):")
    summary.append("-" * 60)

    for i, email in enumerate(relevant_emails[:5], 1):
        summary.append(f"\n{i}. From: {email.get('from', 'Unknown')}")
        summary.append(f"   Subject: {email.get('subject', 'No subject')}")
        summary.append(f"   Date: {email.get('date', 'Unknown date')}")
        summary.append(f"   Relevance: {email.get('relevance_score', 0):.2f}")
        if email.get('snippet'):
            summary.append(f"   Preview: {email['snippet'][:100]}...")

    summary.append("\n" + "=" * 60)

    return "\n".join(summary)


def main():
    logger.info("Starting Meeting Prep Assistant")

    try:
        auth_manager = GoogleAuthManager()
        calendar_service = auth_manager.get_calendar_service()
        gmail_service = auth_manager.get_gmail_service()

        calendar_tool = CalendarTool(calendar_service)
        gmail_tool = GmailTool(gmail_service)

        logger.info("Fetching upcoming meetings...")
        meetings = calendar_tool.get_upcoming_meetings()

        if not meetings:
            print("\nNo meetings requiring preparation in the next 24 hours.")
            return

        print(f"\nFound {len(meetings)} upcoming meeting(s):\n")

        for i, meeting in enumerate(meetings, 1):
            print(f"\n{'='*60}")
            print(f"Processing Meeting {i}/{len(meetings)}: {meeting['title']}")
            print(f"{'='*60}")

            relevant_emails = gmail_tool.search_relevant_emails(
                meeting=meeting,
                days=30,
                max_results=10
            )

            prep_summary = generate_meeting_prep_summary(meeting, relevant_emails)
            print(prep_summary)

            # TODO: add Gemini integration

        print(f"\nDone - processed {len(meetings)} meeting(s)")
        logger.info("Completed")

    except FileNotFoundError as e:
        logger.error(f"Config file not found: {e}")
        print(f"\nError: {e}")
        print("\nMake sure you have config/credentials.json and config/token.pickle")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()