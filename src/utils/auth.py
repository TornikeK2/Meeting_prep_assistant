"""Google OAuth authentication"""
import os
import pickle
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# OAuth 2.0 scopes for Calendar and Gmail
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]


class GoogleAuthManager:
    """Manage Google OAuth and API services"""

    def __init__(
            self,
            credentials_file: str = 'config/credentials.json',
            token_file: str = 'config/token.pickle'
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds: Optional[Credentials] = None

        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

    def authenticate(self) -> Credentials:
        """Authenticate with Google OAuth"""
        if os.path.exists(self.token_file):
            print(f"Loading existing credentials from {self.token_file}")
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                print("Refreshing expired credentials...")
                try:
                    self.creds.refresh(Request())
                    print("Credentials refreshed successfully")
                except Exception as e:
                    self.creds = None

            if not self.creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    SCOPES
                )
                self.creds = flow.run_local_server(port=0, prompt='consent')

            print(f"Saving credentials to {self.token_file}")
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            print("Credentials saved\n")

        return self.creds

    def get_calendar_service(self):
        """Get Calendar API service"""
        if not self.creds or not self.creds.valid:
            self.authenticate()

        try:
            service = build('calendar', 'v3', credentials=self.creds)
            print("Calendar API service created")
            return service
        except HttpError as error:
            print(f"Error creating Calendar service: {error}")
            raise

    def get_gmail_service(self):
        """Get Gmail API service"""
        if not self.creds or not self.creds.valid:
            self.authenticate()

        try:
            service = build('gmail', 'v1', credentials=self.creds)
            print("Gmail API service created")
            return service
        except HttpError as error:
            print(f"Error creating Gmail service: {error}")
            raise

    def revoke_credentials(self):
        """Revoke credentials and delete token"""
        if self.creds:
            try:
                self.creds.revoke(Request())
                print("Credentials revoked")
            except Exception as e:
                print(f"Note: Could not revoke credentials: {e}")

        if os.path.exists(self.token_file):
            os.remove(self.token_file)
            print(f"Token file deleted: {self.token_file}")

        self.creds = None
        print("Authentication reset complete")


def main():
    """Test auth flow"""
    print("Testing Google OAuth\n")

    try:
        auth_manager = GoogleAuthManager()
        auth_manager.authenticate()
        calendar_service = auth_manager.get_calendar_service()
        gmail_service = auth_manager.get_gmail_service()

        print("\nAll tests passed")
        return auth_manager

    except FileNotFoundError as e:
        print(f"\nError: {e}")
        return None
    except Exception as e:
        print(f"\nFailed: {e}")
        return None


if __name__ == "__main__":
    main()