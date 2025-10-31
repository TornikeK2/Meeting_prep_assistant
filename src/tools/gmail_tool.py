"""
Gmail search and retrieval operations for meeting preparation
"""
import base64
import re
from typing import List, Dict
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


class GmailTool:
    """Search and retrieve emails for meetings"""

    def __init__(self, service):
        self.service = service

    def search_relevant_emails(
        self,
        meeting: Dict,
        days: int = 7,
        max_results: int = 10,
        project_keywords: List[str] = None,
        customer_name: str = None,
        customer_domain: str = None
    ) -> List[Dict]:
        """
        Search Gmail for relevant emails

        Args:
            meeting: Meeting dict with title, attendees, etc.
            days: How many days back to search
            max_results: Maximum number of emails to return
            project_keywords: Optional list of user-defined keywords for this project.
                            If provided, these override auto-extracted keywords from meeting title.
            customer_name: Optional customer name to filter emails (e.g., "Microsoft")
            customer_domain: Optional customer domain to filter emails (e.g., "microsoft.com")

        Returns:
            List of email dicts with relevance scores
        """
        query = self._build_search_query(meeting, days, project_keywords, customer_name, customer_domain)

        print(f"Gmail search query: {query}")

        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results * 2
            ).execute()

            messages = results.get('messages', [])

            print(f"Gmail search found {len(messages)} messages")

            if not messages:
                return []

            email_threads = []
            for msg in messages:
                email_data = self._get_message_details(msg['id'])
                if email_data:
                    email_threads.append(email_data)
                    print(f"Found email: '{email_data['subject']}' from {email_data['from']}")

            scored_emails = self._score_emails(email_threads, meeting, customer_name)
            print(f"Returning top {len(scored_emails[:max_results])} emails after scoring")
            return scored_emails[:max_results]

        except Exception as e:
            return []

    def _build_search_query(
        self,
        meeting: Dict,
        days: int = 7,
        project_keywords: List[str] = None,
        customer_name: str = None,
        customer_domain: str = None
    ) -> str:
        """
        Build Gmail query from meeting info

        Args:
            meeting: Meeting dict
            days: Days back to search
            project_keywords: Optional user-defined keywords (overrides auto-extraction)
            customer_name: Optional customer name to search for
            customer_domain: Optional customer domain to filter by

        Returns:
            Gmail search query string
        """
        query_parts = []

        # Search by customer domain if provided
        if customer_domain:
            domain_queries = []
            domain_queries.append(f"from:@{customer_domain}")
            domain_queries.append(f"to:@{customer_domain}")
            query_parts.append(f"({' OR '.join(domain_queries)})")
        else:
            # Search by attendees if no domain filter
            attendee_queries = []
            for email in meeting['attendees'][:10]:
                attendee_queries.append(f"from:{email}")
                attendee_queries.append(f"to:{email}")

            if attendee_queries:
                query_parts.append(f"({' OR '.join(attendee_queries)})")

        # Search by customer name or keywords
        if customer_name:
            # Use customer name as primary keyword
            name_queries = []
            name_queries.append(f'subject:"{customer_name}"')
            name_queries.append(f'"{customer_name}"')
            query_parts.append(f"({' OR '.join(name_queries)})")
        elif project_keywords:
            # Use user-defined project keywords
            keyword_queries = []
            for kw in project_keywords:
                keyword_queries.append(f'subject:"{kw}"')
                keyword_queries.append(f'"{kw}"')
            query_parts.append(f"({' OR '.join(keyword_queries)})")
        else:
            # Fallback to auto-extraction from meeting title
            keywords = self._extract_keywords(meeting['title'])
            if keywords:
                keyword_queries = []
                for kw in keywords:
                    keyword_queries.append(f'subject:"{kw}"')
                    keyword_queries.append(f'"{kw}"')
                query_parts.append(f"({' OR '.join(keyword_queries)})")

        query_parts.append(f"newer_than:{days}d")
        query_parts.append("-in:spam")
        query_parts.append("-in:trash")

        return ' '.join(query_parts)

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from meeting title"""
        stop_words = {
            'meeting', 'sync', 'call', 'discussion', 'review', 'update',
            'weekly', 'monthly', 'daily', 'standup', 'stand-up', 'stand',
            'the', 'and', 'or', 'with', 'for', 'about', 'on', 'in', 'at',
            'a', 'an', 'of', 'to', 'from', 'by', 'up'
        }

        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())

        # Filter out stop words and short words
        keywords = [
            w for w in words
            if w not in stop_words and len(w) > 2
        ]

        # Return top 4 keywords (avoid query being too long)
        return keywords[:4]

    def _get_message_details(self, message_id: str) -> Dict:
        """Get email details"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = message.get('payload', {}).get('headers', [])

            # Extract headers
            subject = self._get_header(headers, 'Subject')
            from_email = self._get_header(headers, 'From')
            to_email = self._get_header(headers, 'To')
            date = self._get_header(headers, 'Date')
            thread_id = message.get('threadId')

            # Extract body
            body = self._get_email_body(message)

            # Truncate very long emails
            if len(body) > 2000:
                body = body[:2000] + "\n...[email truncated for length]"

            return {
                'id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'from': from_email,
                'to': to_email,
                'date': date,
                'body': body,
                'snippet': message.get('snippet', ''),
                'gmail_link': f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
            }

        except Exception as e:
            print(f"Error fetching message {message_id}: {e}")
            return None

    def _get_header(self, headers: List[Dict], name: str) -> str:
        """Extract specific header value"""
        for header in headers:
            if header.get('name', '').lower() == name.lower():
                return header.get('value', '')
        return ''

    def _get_email_body(self, message: Dict) -> str:
        """Extract email body text"""
        payload = message.get('payload', {})

        # Try to get plain text part
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

                # Handle nested multipart
                if 'parts' in part:
                    for subpart in part['parts']:
                        if subpart.get('mimeType') == 'text/plain':
                            data = subpart.get('body', {}).get('data', '')
                            if data:
                                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

        # Fallback to body data
        data = payload.get('body', {}).get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

            # If HTML, strip tags
            if '<html' in text.lower() or '<body' in text.lower():
                soup = BeautifulSoup(text, 'html.parser')
                return soup.get_text(separator='\n', strip=True)

            return text

        # Last resort: use snippet
        return message.get('snippet', '')

    def _score_emails(self, emails: List[Dict], meeting: Dict, customer_name: str = None) -> List[Dict]:
        """Score emails by relevance"""
        scored = []

        meeting_keywords = self._extract_keywords(meeting['title'])
        meeting_attendees = [a.lower() for a in meeting['attendees']]

        for email in emails:
            score = 0.0

            # 1. Attendee match score (40%)
            email_from = email.get('from', '').lower()
            email_to = email.get('to', '').lower()

            for attendee in meeting_attendees:
                if attendee in email_from or attendee in email_to:
                    score += 0.5
                    break

            # 2. Keyword relevance (30%)
            email_text = f"{email.get('subject', '')} {email.get('body', '')}".lower()

            # Boost score if customer name is found
            if customer_name and customer_name.lower() in email_text:
                score += 0.3
            elif meeting_keywords:
                matching_keywords = sum(1 for kw in meeting_keywords if kw in email_text)
                keyword_score = matching_keywords / len(meeting_keywords)
                score += 0.3 * keyword_score

            # 3. Recency score (20%)
            date_str = email.get('date', '')
            if self._is_recent(date_str, days=3):
                score += 0.2
            elif self._is_recent(date_str, days=7):
                score += 0.1

            # 4. Thread activity (10%)
            body_length = len(email.get('body', ''))
            if body_length > 1000:
                score += 0.1
            elif body_length > 500:
                score += 0.05

            email['relevance_score'] = round(score, 2)
            scored.append(email)

        # Sort by score (highest first)
        scored.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return scored

    def _is_recent(self, date_str: str, days: int) -> bool:
        """Check if email is recent"""
        recent_indicators = ['hour', 'minute', 'today', 'yesterday']

        if any(indicator in date_str.lower() for indicator in recent_indicators):
            return True

        if 'day' in date_str.lower():
            try:
                nums = re.findall(r'\d+', date_str)
                if nums and int(nums[0]) <= days:
                    return True
            except:
                pass

        return False

    def send_email(self, to: str, subject: str, body: str, is_html: bool = True):
        """Send email via Gmail"""
        from email.mime.text import MIMEText

        try:
            # Create message
            if is_html:
                message = MIMEText(body, 'html')
            else:
                message = MIMEText(body, 'plain')

            message['to'] = to
            message['subject'] = subject

            # Encode and send
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

            send_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()

            print(f"Email sent successfully. Message ID: {send_message['id']}")
            return send_message['id']

        except Exception as e:
            print(f"Error sending email: {e}")
            return None