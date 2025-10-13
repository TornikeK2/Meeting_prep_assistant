"""
Test script for Gmail API integration
Searches your Gmail and displays results
"""
from src.utils.auth import GoogleAuthManager


def test_gmail_search():
    """Test Gmail search functionality"""
    print("--- Testing Gmail API ---\n")

    # Authenticate
    auth = GoogleAuthManager()
    gmail_service = auth.get_gmail_service()

    # Test search: recent emails from last 7 days
    query = "newer_than:7d -in:spam -in:trash"

    print(f"Searching Gmail with query: {query}\n")

    try:
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=5
        ).execute()

        messages = results.get('messages', [])

        if not messages:
            print("No messages found.")
            return

        print(f"Found {len(messages)} recent messages:\n")
        print("-" * 80)

        for msg in messages:
            # Get message details
            message = gmail_service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()

            headers = message.get('payload', {}).get('headers', [])

            # Extract header values
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')

            print(f"\n {subject}")
            print(f"   From: {from_email}")
            print(f"   Date: {date}")
            print(f"   ID: {msg['id']}")

        print("\n" + "-" * 80)
        print(f"\n✓ Successfully searched and retrieved {len(messages)} emails!")

        # Test profile access
        print("\nTesting profile access...")
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f" Connected as: {profile['emailAddress']}")
        print(f"   Total messages: {profile['messagesTotal']}")
        print(f"   Total threads: {profile['threadsTotal']}")

    except Exception as e:
        print(f"✗ Error accessing Gmail API: {e}")
        raise


if __name__ == "__main__":
    test_gmail_search()