# gmail_reader.py

# ==========================================================
# IMPORTS
# ==========================================================

import os
import base64
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import get_env


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]


# ==========================================================
# AUTENTICACIÓN GOOGLE (DUAL MODE)
# ==========================================================

def get_gmail_creds():

    refresh_token = get_env("GMAIL_REFRESH_TOKEN")

    if refresh_token:
        return Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=get_env("GMAIL_CLIENT_ID"),
            client_secret=get_env("GMAIL_CLIENT_SECRET"),
            scopes=SCOPES,
        )

    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


# ==========================================================
# EXTRAER TEXTO DEL CORREO
# ==========================================================

def extraer_texto(payload):

    if "body" in payload:

        data = payload["body"].get("data")

        if data:
            return base64.urlsafe_b64decode(
                data
            ).decode("utf-8", errors="ignore")

    for parte in payload.get("parts", []):

        mime = parte.get("mimeType", "")

        if mime == "text/plain":

            data = parte["body"].get("data")

            if data:
                return base64.urlsafe_b64decode(
                    data
                ).decode("utf-8", errors="ignore")

    return ""


# ==========================================================
# 🔥 FUNCIÓN ENVOLTORIO (CLAVE PARA RENDER)
# ==========================================================

def obtener_correos():

    # ======================================================
    # OBTENER CREDENCIALES
    # ======================================================

    creds = get_gmail_creds()

    print("✓ Autenticación exitosa")

    # ======================================================
    # CONEXIÓN GMAIL
    # ======================================================

    service = build(
        "gmail",
        "v1",
        credentials=creds
    )

    # ======================================================
    # BÚSQUEDA DE CORREOS
    # ======================================================

    resultado = service.users().messages().list(
        userId="me",
        q='subject:"timestamp_captura:"'
    ).execute()

    mensajes = resultado.get("messages", [])

    modo_busqueda = "asunto timestamp_captura"

    # ======================================================
    # FALLBACK: etiqueta slave
    # ======================================================

    if len(mensajes) == 0:

        resultado = service.users().messages().list(
            userId="me",
            q="label:slave"
        ).execute()

        mensajes = resultado.get("messages", [])

        modo_busqueda = "etiqueta slave"

    print(f"\nModo búsqueda: {modo_busqueda}")
    print(f"Encontrados: {len(mensajes)} correos\n")

    # ======================================================
    # SALIDA PARA PARSER
    # ======================================================

    correos_procesados = []

    # ======================================================
    # RECORRER CORREOS
    # ======================================================

    for i, mensaje in enumerate(mensajes, start=1):

        detalle = service.users().messages().get(
            userId="me",
            id=mensaje["id"],
            format="full"
        ).execute()

        gmail_message_id = detalle["id"]

        fecha_recepcion = datetime.fromtimestamp(
            int(detalle["internalDate"]) / 1000,
            tz=timezone.utc
        )

        headers = detalle["payload"]["headers"]

        asunto = ""
        fecha = ""

        for header in headers:

            if header["name"] == "Subject":
                asunto = header["value"]

            elif header["name"] == "Date":
                fecha = header["value"]

        contenido = extraer_texto(detalle["payload"])

        print(f"[{i}]")
        print(f"ID     : {gmail_message_id}")
        print(f"Asunto: {asunto}")
        print(f"Fecha : {fecha}")

        # ==================================================
        # HISTÓRICO
        # ==================================================

        if asunto.strip() == "2026":

            historico_path = "historico_2026.md"

            if not os.path.exists(historico_path):

                with open(
                    historico_path,
                    "w",
                    encoding="utf-8"
                ) as archivo:

                    archivo.write(contenido)

                print("\n✓ Histórico creado")

            else:
                print("\n✓ Histórico ya existe")
                print("✓ Se omite creación")

            print(f"✓ Longitud: {len(contenido)} caracteres")

        # ==================================================
        # CAPTURAS
        # ==================================================

        else:

            print("\n--- PREVIEW DEL CONTENIDO ---\n")
            print(contenido[:1000])

        print("\n" + "=" * 80 + "\n")

        # ==================================================
        # OUTPUT PARA PARSER
        # ==================================================

        correos_procesados.append({
            "gmail_message_id": gmail_message_id,
            "asunto": asunto,
            "fecha_correo": fecha,
            "fecha_recepcion": fecha_recepcion,
            "contenido": contenido
        })

    # ======================================================
    # RESUMEN FINAL
    # ======================================================

    print(f"\n✓ Total correos procesados: {len(correos_procesados)}")

    return correos_procesados