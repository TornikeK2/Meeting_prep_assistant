"""
Google OAuth 2.0 Authentication Manager
Handles authentication for Google Calendar and Gmail APIs
"""
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
    """
    Manages Google OAuth 2.0 authentication and API service creation
    """

    def __init__(
            self,
            credentials_file: str = 'config/credentials.json',
            token_file: str = 'config/token.pickle'
    ):
        """
        Initialize the authentication manager

        Args:
            credentials_file: Path to OAuth client secret JSON
            token_file: Path to store/load user tokens
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds: Optional[Credentials] = None

        # Validate credentials file exists
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_file}\n"
                f"Download it from Google Cloud Console and place it at this location."
            )

    def authenticate(self) -> Credentials:
        """
        Authenticate with Google using OAuth 2.0

        Flow:
        1. Check if valid token exists (from previous auth)
        2. If expired, refresh it
        3. If no token exists, run OAuth flow (opens browser)
        4. Save token for future use

        Returns:
            Credentials object for API access
        """
        # Load existing token if available
        if os.path.exists(self.token_file):
            print(f"Loading existing credentials from {self.token_file}")
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)

        # Check if credentials are valid
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # Refresh expired credentials
                print("Refreshing expired credentials...")
                try:
                    self.creds.refresh(Request())
                    print("Credentials refreshed successfully")
                except Exception as e:
                    print(f"Failed to refresh credentials: {e}")
                    print("Re-authenticating...")
                    self.creds = None

            # No valid credentials - run OAuth flow
            if not self.creds:
                print("\n=== Starting OAuth Authentication ===")
                print("A browser window will open for you to authorize the app.")
                print("Please sign in and grant the requested permissions.\n")

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file,
                    SCOPES
                )

                # Run local server to receive OAuth callback
                self.creds = flow.run_local_server(
                    port=0,  # Use random available port
                    prompt='consent',
                    success_message='Authentication successful! You can close this window.'
                )

                print("Authentication successful")

            # Save credentials for future use
            print(f"Saving credentials to {self.token_file}")
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
            print("Credentials saved\n")

        return self.creds

    def get_calendar_service(self):
        """
        Get authenticated Google Calendar API service

        Returns:
            Google Calendar API service object
        """
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
        """
        Get authenticated Gmail API service

        Returns:
            Gmail API service object
        """
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
        """
        Revoke current credentials and delete token file
        Useful for testing or switching accounts
        """
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
    """
    Test authentication flow
    """
    print("=== Google OAuth Authentication Test ===\n")

    try:
        # Create auth manager
        auth_manager = GoogleAuthManager()

        # Authenticate
        print("Step 1: Authenticating...")
        auth_manager.authenticate()

        # Test Calendar API
        print("\nStep 2: Testing Calendar API...")
        calendar_service = auth_manager.get_calendar_service()

        # Test Gmail API
        print("\nStep 3: Testing Gmail API...")
        gmail_service = auth_manager.get_gmail_service()

        print("\n--- All authentication tests passed! ---")
        return auth_manager

    except FileNotFoundError as e:
        print(f"\n Error: {e}")
        return None
    except Exception as e:
        print(f"\n Authentication failed: {e}")
        return None


if __name__ == "__main__":
    main()