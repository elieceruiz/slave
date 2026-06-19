# label_id.py

from googleapiclient.discovery import build
from gmail_reader import get_gmail_creds


def listar_labels():
    # Diagnostico operativo: confirma que "slave" siga apuntando al labelId esperado.
    creds = get_gmail_creds()
    service = build("gmail", "v1", credentials=creds)
    labels = service.users().labels().list(userId="me").execute()
    return labels.get("labels", [])


if __name__ == "__main__":
    for label in listar_labels():
        print(label["name"], "->", label["id"])
