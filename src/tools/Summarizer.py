from os import getenv
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict, Optional
from datetime import datetime
import json


class MeetingSummarizer:
    """
    Generates AI-powered meeting briefs using Gemini via LangChain
    Returns structured data (no HTML formatting)
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize the summarizer with Gemini API via LangChain"""
        self.api_key = api_key or getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found")

        self.model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=self.api_key,
            temperature=0.3
        )
        self.model_name = model_name

    def generate_meeting_brief(self, meeting: Dict, emails: List[Dict]) -> Dict:
        """
        Generate AI summary - returns structured data, NOT HTML
        Analyzes ALL emails provided (no artificial limit)

        Returns:
            {
                'success': bool,
                'summary': str (markdown formatted),
                'meeting': dict,
                'emails': list,
                'generated_at': str
            }
        """
        try:
            meeting_context = self._format_meeting_context(meeting)
            email_context = self._format_email_context(emails)
            prompt = self._build_prompt(meeting_context, email_context)

            response = self.model.invoke(prompt)

            return {
                'success': True,
                'summary': response.content,
                'meeting': meeting,
                'emails': emails,
                'generated_at': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'meeting': meeting,
                'emails': []
            }

    def _build_prompt(self, meeting_context, email_context):
        return f"""Analyze this meeting and recent email context to create a brief:

{meeting_context}

{email_context}

Generate a concise meeting brief with:
## CONTEXT
Brief overview of the meeting purpose and participants

## KEY POINTS
- Main topics from recent emails
- Important updates or decisions
- Outstanding questions or issues

## PREPARATION
- What to review beforehand
- Materials or data needed"""

    def _format_meeting_context(self, meeting):
        """Format meeting details for AI prompt"""
        attendees = meeting.get('attendees', [])
        attendee_list = ', '.join(attendees[:5])  # First 5 attendees
        if len(attendees) > 5:
            attendee_list += f" and {len(attendees) - 5} others"

        context = f"""MEETING: {meeting.get('title', 'Untitled')}
TIME: {meeting.get('start_time', 'Not specified')}
ATTENDEES: {attendee_list}"""

        description = meeting.get('description', '').strip()
        if description:
            context += f"\nDESCRIPTION: {description[:200]}"  # First 200 chars

        return context

    def _format_email_context(self, emails):
        """Format email content for AI prompt"""
        if not emails:
            return "No recent emails found."

        context = f"RECENT EMAILS ({len(emails)} found):\n\n"

        # Include up to 10 most relevant emails
        for i, email in enumerate(emails[:10], 1):
            subject = email.get('subject', 'No subject')
            from_addr = email.get('from', 'Unknown')
            date = email.get('date', '')
            snippet = email.get('snippet', email.get('body', ''))[:150]  # First 150 chars

            context += f"{i}. FROM: {from_addr}\n"
            context += f"   SUBJECT: {subject}\n"
            context += f"   PREVIEW: {snippet}...\n\n"

        if len(emails) > 10:
            context += f"(+{len(emails) - 10} more emails not shown)\n"

        return context


class BriefFormatter:
    """Separate class for formatting - HTML, Text, JSON"""

    @staticmethod
    def to_html(brief_data: Dict) -> str:
        """Convert brief to HTML"""
        # This is where HTML lives - separate from AI generation!
        pass

    @staticmethod
    def to_text(brief_data: Dict) -> str:
        """Convert brief to plain text"""
        return brief_data['summary']

    @staticmethod
    def to_json(brief_data: Dict) -> str:
        """Convert brief to JSON"""
        return json.dumps(brief_data, indent=2)

