# Copyright (c) 2026 HackerTMJ (门牌号3号)
# OpenAGI — Autonomous Intelligence System
# MIT License — https://github.com/HackerTMJ/OpenAGI

"""
google_integration.py — Google API integration

OAuth2 with google-api-python-client.
GOOGLE_CREDENTIALS_PATH env → google_credentials.json.

Methods:
- authenticate()
- get_unread_emails(max=10)
- get_today_events()
- get_upcoming_events(days=7)
- send_email(to, subject, body)
- create_event(title, start, end)
- search_drive(query)
- get_pipeline_leads()

Handle RefreshError → delete token → re-auth.
If no credentials: return mock data with instructions message.
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

log = logging.getLogger("Google")

CREDENTIALS_PATH = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", "./workspace/google_credentials.json"))
TOKEN_PATH = Path("./workspace/google_token.json")


class GoogleIntegration:
    def __init__(self):
        self._creds = None
        self._gmail = None
        self._calendar = None
        self._drive = None

    def _authenticate(self):
        """Authenticate with Google APIs."""
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow

            if not CREDENTIALS_PATH.exists():
                return False

            SCOPES = [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/drive.readonly'
            ]

            if TOKEN_PATH.exists():
                self._creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

            if not self._creds or not self._creds.valid:
                if self._creds and self._creds.expired and self._creds.refresh_token:
                    try:
                        self._creds.refresh(Request())
                    except Exception:
                        # Refresh failed, delete token and re-auth
                        TOKEN_PATH.unlink()
                        self._creds = None

                if not self._creds:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDENTIALS_PATH), SCOPES)
                    self._creds = flow.run_local_server(port=0)

                TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                TOKEN_PATH.write_text(self._creds.to_json())

            return True
        except Exception as e:
            log.warning(f"Google auth failed: {e}")
            return False

    def _get_gmail(self):
        if self._gmail is None:
            try:
                from googleapiclient.discovery import build
                if self._authenticate():
                    self._gmail = build('gmail', 'v1', credentials=self._creds)
            except Exception as e:
                log.debug(f"Gmail init failed: {e}")
        return self._gmail

    def _get_calendar(self):
        if self._calendar is None:
            try:
                from googleapiclient.discovery import build
                if self._authenticate():
                    self._calendar = build('calendar', 'v3', credentials=self._creds)
            except Exception as e:
                log.debug(f"Calendar init failed: {e}")
        return self._calendar

    def _get_drive(self):
        if self._drive is None:
            try:
                from googleapiclient.discovery import build
                if self._authenticate():
                    self._drive = build('drive', 'v3', credentials=self._creds)
            except Exception as e:
                log.debug(f"Drive init failed: {e}")
        return self._drive

    def get_unread_emails(self, max_results=10) -> list:
        """Get unread emails from inbox."""
        try:
            service = self._get_gmail()
            if not service:
                return [{"message": "Set GOOGLE_CREDENTIALS_PATH and run Google auth"}]
            result = service.users().messages().list(
                userId='me', q='is:unread in:inbox', maxResults=max_results
            ).execute()
            messages = result.get('messages', [])
            emails = []
            for msg in messages[:max_results]:
                m = service.users().messages().get(userId='me', id=msg['id']).execute()
                headers = m.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                emails.append({"subject": subject, "from": sender, "snippet": m.get('snippet', '')[:100]})
            return emails
        except Exception as e:
            log.error(f"Get emails failed: {e}")
            return []

    def get_today_events(self) -> list:
        """Get calendar events for today."""
        try:
            service = self._get_calendar()
            if not service:
                return []
            now = datetime.utcnow().isoformat() + 'Z'
            end_of_day = (datetime.utcnow() + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary', timeMin=now, timeMax=end_of_day,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            return [{"summary": e.get('summary', 'No title'), "start": e['start'].get('dateTime', e['start'].get('date')), "end": e['end'].get('dateTime', e['end'].get('date'))} for e in events]
        except Exception as e:
            log.error(f"Get events failed: {e}")
            return []

    def get_upcoming_events(self, days=7) -> list:
        """Get upcoming calendar events."""
        try:
            service = self._get_calendar()
            if not service:
                return []
            now = datetime.utcnow().isoformat() + 'Z'
            future = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary', timeMin=now, timeMax=future,
                singleEvents=True, orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])[:10]
            return [{"summary": e.get('summary', 'No title'), "start": e['start'].get('dateTime', e['start'].get('date'))} for e in events]
        except Exception as e:
            log.error(f"Get upcoming events failed: {e}")
            return []

    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send an email."""
        try:
            import base64
            from email.mime.text import MIMEText
            service = self._get_gmail()
            if not service:
                return {"success": False, "error": "Not authenticated"}
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return {"success": True, "to": to, "subject": subject}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_event(self, title: str, start: str, end: str) -> dict:
        """Create a calendar event."""
        try:
            service = self._get_calendar()
            if not service:
                return {"success": False, "error": "Not authenticated"}
            event = {'summary': title, 'start': {'dateTime': start}, 'end': {'dateTime': end}}
            result = service.events().insert(calendarId='primary', body=event).execute()
            return {"success": True, "event_id": result.get('id'), "link": result.get('htmlLink')}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_drive(self, query: str) -> list:
        """Search Google Drive files."""
        try:
            service = self._get_drive()
            if not service:
                return []
            results = service.files().list(q=f"name contains '{query}'", pageSize=10).execute()
            files = results.get('files', [])
            return [{"name": f['name'], "id": f['id'], "type": f['mimeType']} for f in files]
        except Exception as e:
            log.error(f"Drive search failed: {e}")
            return []

    def get_pipeline_leads(self) -> list:
        """Get pipeline leads (placeholder - would read from specific Drive folder or Sheet)."""
        return self.search_drive("lead") or self.search_drive("opportunity")
