from datetime import datetime, timedelta
from typing import List, Dict
import pytz


class CalendarTool:
    """
    Tool for interacting with Google Calendar API
    Detects meetings, filters them, and identifies client meetings
    """

    def __init__(self, service, internal_domains=None):
        """
        Initialize CalendarTool

        Args:
            service: Authenticated Google Calendar service
            internal_domains: List of internal email domains (e.g., ['example.com'])
        """
        self.service = service
        self.internal_domains = internal_domains or ['example.com']

    def get_upcoming_meetings(self, hours_ahead_min=4, hours_ahead_max=24):
        """
        Fetch meetings that need preparation (4-24 hours ahead)

        Args:
            hours_ahead_min: Minimum hours ahead to look
            hours_ahead_max: Maximum hours ahead to look

        Returns:
            List of meeting dictionaries with classification
        """
        now = datetime.utcnow()
        time_min = (now + timedelta(hours=hours_ahead_min)).isoformat() + 'Z'
        time_max = (now + timedelta(hours=hours_ahead_max)).isoformat() + 'Z'

        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=50,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            meetings = []

            for event in events:
                if self._should_prepare_meeting(event):
                    meeting = self._parse_event(event)
                    # Add client meeting classification
                    meeting['is_client_meeting'] = self._is_external_meeting(meeting)
                    meeting['priority'] = self._calculate_priority(meeting)
                    meetings.append(meeting)

            return meetings

        except Exception as e:
            print(f"Error fetching calendar events: {e}")
            return []

    def identify_client_meetings(self, hours_ahead_min=4, hours_ahead_max=24):
        """
        Identify which meetings are with external clients

        Returns:
            List of client meetings only
        """
        all_meetings = self.get_upcoming_meetings(hours_ahead_min, hours_ahead_max)
        client_meetings = [m for m in all_meetings if m['is_client_meeting']]

        print(f"Found {len(client_meetings)} client meetings out of {len(all_meetings)} total meetings")
        return client_meetings

    def _should_prepare_meeting(self, event: Dict) -> bool:
        """
        Filter logic: determine if meeting needs preparation

        Skip:
        - All-day events
        - Meetings < 15 minutes
        - Declined meetings
        - Standup/social keywords
        - Events with < 3 attendees (1-on-1s)
        """
        # Skip all-day events
        if 'date' in event.get('start', {}):
            return False

        # Check duration
        start = event.get('start', {}).get('dateTime')
        end = event.get('end', {}).get('dateTime')

        if start and end:
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            duration_minutes = (end_dt - start_dt).total_seconds() / 60

            if duration_minutes < 15:
                return False

        # Check response status
        if event.get('status') == 'cancelled':
            return False

        attendees = event.get('attendees', [])
        my_response = None
        for attendee in attendees:
            if attendee.get('self'):
                my_response = attendee.get('responseStatus')
                break

        if my_response == 'declined':
            return False

        # Check keywords to skip
        skip_keywords = ['standup', 'stand-up', 'lunch', 'coffee', 'social',
                         'birthday', 'happy hour', 'team building']
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()

        if any(keyword in title or keyword in description for keyword in skip_keywords):
            return False

        # Require at least 3 attendees (including self) for internal meetings
        # Client meetings (1 external) are always prepared
        if len(attendees) < 2:  # Just you, no one else
            return False

        return True

    def _is_external_meeting(self, meeting: Dict) -> bool:
        """
        Check if meeting includes external attendees (clients)

        Args:
            meeting: Parsed meeting dictionary

        Returns:
            True if meeting has external attendees
        """
        for attendee_email in meeting['attendees']:
            if '@' in attendee_email:
                domain = attendee_email.split('@')[1].lower()
                # Check if domain is NOT in internal domains
                if domain not in [d.lower() for d in self.internal_domains]:
                    return True

        return False

    def _calculate_priority(self, meeting: Dict) -> str:
        """
        Calculate meeting priority

        Priority levels:
        - HIGH: Client meetings (external attendees)
        - MEDIUM: Large internal meetings (5+ people)
        - LOW: Small internal meetings
        """
        if meeting.get('is_client_meeting'):
            return 'HIGH'
        elif len(meeting['attendees']) >= 5:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _parse_event(self, event: Dict) -> Dict:
        """Extract relevant meeting metadata"""
        attendees = event.get('attendees', [])
        attendee_emails = [a.get('email') for a in attendees if a.get('email')]

        start_time = event.get('start', {}).get('dateTime')
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))

        return {
            'id': event.get('id'),
            'title': event.get('summary', 'Untitled Meeting'),
            'description': event.get('description', ''),
            'start_time': start_dt,
            'attendees': attendee_emails,
            'location': event.get('location', ''),
            'organizer': event.get('organizer', {}).get('email', ''),
            'html_link': event.get('htmlLink', '')
        }
