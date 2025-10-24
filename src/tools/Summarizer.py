from os import getenv
import google.generativeai as genai
from typing import List, Dict, Optional
from datetime import datetime


class MeetingSummarizer:
    """
    Generates AI-powered meeting briefs using Gemini
    Returns structured data (no HTML formatting)
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.0-flash-exp"):
        """Initialize the summarizer with Gemini API"""
        self.api_key = getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name

    def generate_meeting_brief(self, meeting: Dict, emails: List[Dict], max_emails: int = 5) -> Dict:
        """
        Generate AI summary - returns structured data, NOT HTML

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
            email_context = self._format_email_context(emails[:max_emails])
            prompt = self._build_prompt(meeting_context, email_context)

            response = self.model.generate_content(prompt)

            return {
                'success': True,
                'summary': response.text,
                'meeting': meeting,
                'emails': emails[:max_emails],
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
        return f"""Create a meeting brief with these sections:

{meeting_context}

{email_context}

Format:
## MEETING CONTEXT (2-3 sentences)
## KEY DISCUSSION POINTS (3-5 bullets)
## ACTION ITEMS (if any)
## RECOMMENDED PREPARATION (2-3 bullets)"""

    def _format_meeting_context(self, meeting):
        return f"Meeting: {meeting.get('title')}, {meeting.get('duration_minutes')}min"

    def _format_email_context(self, emails):
        if not emails:
            return "No relevant emails"
        return f"{len(emails)} relevant emails found"


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
        import json
        return json.dumps(brief_data, indent=2)

