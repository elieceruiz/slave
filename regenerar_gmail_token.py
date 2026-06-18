# regenerar_gmail_token.py

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from gmail_reader import SCOPES


CREDENTIALS_PATH = Path("credentials.json")
TOKEN_PATH = Path("token.json")


def main():
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            "No existe credentials.json. Descárgalo desde Google Cloud "
            "y déjalo solo en esta carpeta local."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        SCOPES,
    )
    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent",
    )

    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

    data = json.loads(creds.to_json())
    refresh_token = data.get("refresh_token")
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    if not refresh_token:
        raise RuntimeError(
            "Google no devolvió refresh_token. Revoca el acceso anterior "
            "en tu cuenta Google y ejecuta este script de nuevo."
        )

    print("\nToken regenerado correctamente.\n")
    print("Actualiza estas variables en Render:")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={refresh_token}")
    print("\nNo subas credentials.json ni token.json a GitHub.")


if __name__ == "__main__":
    main()
