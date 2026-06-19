# gmail_reader.py

# ==========================================================
# IMPORTS
# ==========================================================

import os
import base64
from datetime import datetime, timezone
from time import perf_counter

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


def _duracion(inicio):
    return f"{perf_counter() - inicio:.2f}s"


# ==========================================================
# AUTENTICACIÓN GOOGLE (DUAL MODE)
# ==========================================================

def get_gmail_creds():

    refresh_token = get_env("GMAIL_REFRESH_TOKEN")

    if refresh_token:
        # En Render y en local parametrizado se evita token.json y navegador OAuth.
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
        # Fallback local para desarrollo; no debe existir como secreto en GitHub.
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

    print("Autenticacion exitosa")

    # ======================================================
    # CONEXIÓN GMAIL
    # ======================================================

    print("[GMAIL] build service inicio")
    inicio = perf_counter()
    try:
        service = build(
            "gmail",
            "v1",
            credentials=creds
        )
        print(f"[GMAIL] build service OK en {_duracion(inicio)}")
    except Exception as e:
        print(f"[GMAIL] build service ERROR en {_duracion(inicio)} | {e}")
        raise

    # ======================================================
    # BÚSQUEDA DE CORREOS
    # ======================================================

    # Esta prioridad de lectura no dispara Render; el disparo viene del Watch.
    query_principal = 'subject:"timestamp_captura:"'
    print(f"[GMAIL] query: {query_principal}")
    print("[GMAIL] list inicio")
    inicio = perf_counter()
    try:
        resultado = service.users().messages().list(
            userId="me",
            q=query_principal
        ).execute()
        mensajes = resultado.get("messages", [])
        print(
            f"[GMAIL] list OK en {_duracion(inicio)} "
            f"| mensajes={len(mensajes)}"
        )
    except Exception as e:
        print(f"[GMAIL] list ERROR en {_duracion(inicio)} | {e}")
        raise

    modo_busqueda = "asunto timestamp_captura"

    # ======================================================
    # FALLBACK: etiqueta slave
    # ======================================================

    if len(mensajes) == 0:

        print("[GMAIL] list principal sin mensajes | mensajes=0")

        # Fallback operativo: si no hay asunto nuevo, procesa lo etiquetado slave.
        query_fallback = "label:slave"
        print(f"[GMAIL] query: {query_fallback}")
        print("[GMAIL] list fallback inicio")
        inicio = perf_counter()
        try:
            resultado = service.users().messages().list(
                userId="me",
                q=query_fallback
            ).execute()
            mensajes = resultado.get("messages", [])
            print(
                f"[GMAIL] list fallback OK en {_duracion(inicio)} "
                f"| mensajes={len(mensajes)}"
            )
        except Exception as e:
            print(f"[GMAIL] list fallback ERROR en {_duracion(inicio)} | {e}")
            raise

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

        total = len(mensajes)
        mensaje_id = mensaje["id"]

        print(f"[GMAIL] get {i}/{total} inicio id={mensaje_id}")
        inicio = perf_counter()
        try:
            detalle = service.users().messages().get(
                userId="me",
                id=mensaje_id,
                format="full"
            ).execute()
            print(f"[GMAIL] get {i}/{total} OK en {_duracion(inicio)}")
        except Exception as e:
            print(
                f"[GMAIL] get {i}/{total} ERROR en {_duracion(inicio)} "
                f"| id={mensaje_id} | {e}"
            )
            raise

        gmail_message_id = detalle["id"]

        # internalDate es la recepcion real en Gmail, mas confiable que el header Date.
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

        print(f"[GMAIL] asunto {i}/{total}: {asunto}")
        print(f"[GMAIL] fecha {i}/{total}: {fecha}")

        inicio = perf_counter()
        try:
            contenido = extraer_texto(detalle["payload"])
            print(
                f"[GMAIL] contenido {i}/{total} OK en {_duracion(inicio)} "
                f"| chars={len(contenido)}"
            )
        except Exception as e:
            print(
                f"[GMAIL] contenido {i}/{total} ERROR en {_duracion(inicio)} "
                f"| id={gmail_message_id} | {e}"
            )
            raise

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

                print("\nHistorico creado")

            else:
                print("\nHistorico ya existe")
                print("Se omite creacion")

            print(f"Longitud: {len(contenido)} caracteres")

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
        print(
            f"[GMAIL] append {i}/{total} OK "
            f"| gmail_message_id={gmail_message_id}"
        )

    # ======================================================
    # RESUMEN FINAL
    # ======================================================

    print(f"[GMAIL] total correos procesados={len(correos_procesados)}")
    print(f"\nTotal correos procesados: {len(correos_procesados)}")

    return correos_procesados
