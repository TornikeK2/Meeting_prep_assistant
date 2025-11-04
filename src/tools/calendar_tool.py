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
                    meetings.append(meeting)

            return meetings

        except Exception as e:
            return []

    def identify_client_meetings(self, hours_ahead_min=4, hours_ahead_max=24):
        """Get client meetings only"""
        all_meetings = self.get_upcoming_meetings(hours_ahead_min, hours_ahead_max)
        client_meetings = [m for m in all_meetings if m['is_client_meeting']]
        return client_meetings

    def get_meetings_by_date_range(self, start_date, end_date, customer_domain=None, project_keywords=None, customer_name=None):
        """
        Get meetings within a specific date range, optionally filtered by customer domain, project keywords, or customer name

        Args:
            start_date: Start date in format 'YYYY-MM-DD'
            end_date: End date in format 'YYYY-MM-DD'
            customer_domain: Optional domain to filter meetings (e.g., 'microsoft.com')
            project_keywords: Optional list of project keywords to filter by (e.g., ['alpha', 'mobile'])
            customer_name: Optional customer name to filter by (e.g., 'Microsoft')

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

                    # Filter by customer domain, project keywords, or customer name
                    should_include = True

                    if customer_domain:
                        # Strict domain filter - attendee must be from that domain
                        should_include = self._has_attendee_from_domain(meeting, customer_domain)
                    elif project_keywords:
                        # Project filter - title/description must contain project keywords
                        should_include = self._matches_project_keywords(meeting, project_keywords)
                    elif customer_name:
                        # Customer name filter - title/description/attendees must match
                        should_include = self._matches_customer_name(meeting, customer_name)

                    if should_include:
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

    def _matches_project_keywords(self, meeting, keywords):
        """
        Check if meeting title or description contains any of the project keywords

        Args:
            meeting: Meeting dict with title and description
            keywords: List of keywords to search for (e.g., ['alpha', 'mobile', 'app'])

        Returns:
            True if any keyword is found in title or description
        """
        if not keywords:
            return False

        title = meeting.get('title', '').lower()
        description = meeting.get('description', '').lower()
        search_text = f"{title} {description}"

        # Check if any keyword matches
        for keyword in keywords:
            if keyword.lower() in search_text:
                return True

        return False

    def _matches_customer_name(self, meeting, customer_name):
        """
        Check if customer name appears in meeting title, description, or attendee domains

        This provides comprehensive matching - finds meetings whether the customer name
        appears in the meeting content OR in attendee email domains.

        Args:
            meeting: Meeting dict with title, description, and attendees
            customer_name: Customer name to search for (e.g., 'Microsoft')

        Returns:
            True if customer name found in title, description, or attendee domains
        """
        if not customer_name:
            return False

        customer_lower = customer_name.lower()

        # Check title and description
        title = meeting.get('title', '').lower()
        description = meeting.get('description', '').lower()
        if customer_lower in title or customer_lower in description:
            return True

        # Check attendee domains
        for attendee_email in meeting['attendees']:
            if '@' in attendee_email:
                domain = attendee_email.split('@')[1].lower()
                company = domain.split('.')[0]  # "microsoft.com" → "microsoft"
                if customer_lower in domain or customer_lower == company:
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
