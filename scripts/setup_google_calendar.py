"""One-time OAuth setup for Google Calendar.

Usage:
    python scripts/setup_google_calendar.py <path-to-client-secret.json>

Opens a browser for Google login, then writes the authorized credentials
into ~/.jarvis-v2/config/runtime.json under 'google_calendar_credentials'.
"""
import json
import sys
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/calendar"]
RUNTIME_JSON = Path.home() / ".jarvis-v2" / "config" / "runtime.json"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/setup_google_calendar.py <client-secret.json>")
        sys.exit(1)

    client_secret_file = Path(sys.argv[1]).expanduser().resolve()
    if not client_secret_file.exists():
        print(f"File not found: {client_secret_file}")
        sys.exit(1)

    from google_auth_oauthlib.flow import InstalledAppFlow

    print("Opening browser for Google login...")
    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
    creds = flow.run_local_server(port=0)

    creds_dict = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }

    # Read existing runtime.json
    runtime = {}
    if RUNTIME_JSON.exists():
        runtime = json.loads(RUNTIME_JSON.read_text(encoding="utf-8"))

    runtime["google_calendar_credentials"] = json.dumps(creds_dict)
    RUNTIME_JSON.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_JSON.write_text(json.dumps(runtime, indent=2), encoding="utf-8")

    print(f"\nCredentials saved to {RUNTIME_JSON}")
    print("Google Calendar tools are now active in Jarvis.")


if __name__ == "__main__":
    main()
