# label_id.py

from googleapiclient.discovery import build
from gmail_reader import get_gmail_creds

creds = get_gmail_creds()
service = build("gmail", "v1", credentials=creds)

labels = service.users().labels().list(userId="me").execute()

for label in labels["labels"]:
    print(label["name"], "→", label["id"])