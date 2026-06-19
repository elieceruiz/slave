# activar_watch.py

from googleapiclient.discovery import build
from gmail_reader import get_gmail_creds
from db import guardar_estado_watch

# Debe coincidir con el topic autorizado para Gmail Push en Pub/Sub.
TOPIC_NAME = "projects/slxvery/topics/gmail-events"

def activar_watch():
    creds = get_gmail_creds()

    service = build("gmail", "v1", credentials=creds)

    response = service.users().watch(
        userId="me",
        body={
            # Label_4407997602573703894 corresponde a la etiqueta Gmail "slave".
            "labelIds": ["Label_4407997602573703894"],
            "topicName": TOPIC_NAME
        }
    ).execute()

    # Gmail devuelve historyId y expiration; expiration permite renovar a tiempo.
    estado = guardar_estado_watch(response, TOPIC_NAME)

    print("Watch activado:")
    print(response)
    print("Estado watch guardado:")
    print(estado)
    return response


if __name__ == "__main__":
    activar_watch()
