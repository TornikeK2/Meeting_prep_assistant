from datetime import datetime, timedelta
from typing import List, Dict
import pytz


class CalendarTool:
    """Interact with Google Calendar API"""

    def __init__(self, service, internal_domains=None):
        self.service = service
        self.internal_domains = internal_domains or ['gmail.com']

    def get_upcoming_meetings(self, hours_ahead_min=4, hours_ahead_max=24):
        """Get meetings that need prep"""
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
                    meeting['is_client_meeting'] = self._is_external_meeting(meeting)
                    meeting['priority'] = self._calculate_priority(meeting)
                    meetings.append(meeting)

            return meetings

        except Exception as e:
            return []

    def identify_client_meetings(self, hours_ahead_min=4, hours_ahead_max=24):
        """Get client meetings only"""
        all_meetings = self.get_upcoming_meetings(hours_ahead_min, hours_ahead_max)
        client_meetings = [m for m in all_meetings if m['is_client_meeting']]
        return client_meetings

    def _should_prepare_meeting(self, event: Dict) -> bool:
        """Check if meeting needs prep"""
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

        skip_keywords = ['standup', 'stand-up', 'lunch', 'coffee', 'social',
                         'birthday', 'happy hour', 'team building']
        title = event.get('summary', '').lower()
        description = event.get('description', '').lower()

        if any(keyword in title or keyword in description for keyword in skip_keywords):
            return False

        if len(attendees) < 2:
            return False

        return True

    def _is_external_meeting(self, meeting: Dict) -> bool:
        """Check if meeting has external attendees"""
        for attendee_email in meeting['attendees']:
            if '@' in attendee_email:
                domain = attendee_email.split('@')[1].lower()
                if domain not in [d.lower() for d in self.internal_domains]:
                    return True
        return False

    def _calculate_priority(self, meeting: Dict) -> str:
        """Calculate meeting priority"""
        if meeting.get('is_client_meeting'):
            return 'HIGH'
        elif len(meeting['attendees']) >= 5:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _parse_event(self, event: Dict) -> Dict:
        """Parse event data"""
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
