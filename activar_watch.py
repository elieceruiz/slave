# activar_watch.py

from googleapiclient.discovery import build
from gmail_reader import get_gmail_creds

# 👇 TU TOPIC
TOPIC_NAME = "projects/slxvery/topics/gmail-events"

def activar_watch():
    creds = get_gmail_creds()

    service = build("gmail", "v1", credentials=creds)

    response = service.users().watch(
        userId="me",
        body={
            "labelIds": ["Label_4407997602573703894"],  # 👈 SOLO WATCH PARA ESTE LABEL
            "topicName": TOPIC_NAME
        }
    ).execute()

    print("Watch activado:")
    print(response)
    return response


if __name__ == "__main__":
    activar_watch()
