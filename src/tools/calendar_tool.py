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

    def get_meetings_by_date_range(self, start_date, end_date, customer_domain=None):
        """
        Get meetings within a specific date range, optionally filtered by customer domain

        Args:
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'
            customer_domain: Optional domain to filter meetings (e.g., 'microsoft.com')

        Returns:
            List of meeting dicts
        """
        try:
            # Parse dates and convert to RFC3339 format
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            # Set time to start of day for start_date and end of day for end_date
            start_dt = start_dt.replace(hour=0, minute=0, second=0)
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

            time_min = start_dt.isoformat() + 'Z'
            time_max = end_dt.isoformat() + 'Z'

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=100,
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

                    # Filter by customer domain if specified
                    if customer_domain:
                        if self._has_attendee_from_domain(meeting, customer_domain):
                            meetings.append(meeting)
                    else:
                        meetings.append(meeting)

            return meetings

        except Exception as e:
            print(f"Error fetching meetings by date range: {e}")
            return []

    def _has_attendee_from_domain(self, meeting, domain):
        """Check if any attendee is from the specified domain"""
        domain = domain.lower().strip()
        for attendee_email in meeting['attendees']:
            if '@' in attendee_email:
                attendee_domain = attendee_email.split('@')[1].lower()
                if attendee_domain == domain:
                    return True
        return False

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
        # elif meeting.get('is_internal_meeting') and len(meeting['attendees']) <= 3:
        #     return 'INTERNAL'
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
