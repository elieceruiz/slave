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

SLAVE_LABEL_ID = "Label_4407997602573703894"
TIMESTAMP_SUBJECT_MARKER = "timestamp_captura:"


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


def _header(headers, nombre):
    for header in headers:
        if header.get("name", "").lower() == nombre.lower():
            return header.get("value", "")
    return ""


def _correo_desde_detalle(detalle):
    gmail_message_id = detalle["id"]
    payload = detalle.get("payload", {})
    headers = payload.get("headers", [])

    fecha_recepcion = datetime.fromtimestamp(
        int(detalle["internalDate"]) / 1000,
        tz=timezone.utc
    )

    return {
        "gmail_message_id": gmail_message_id,
        "asunto": _header(headers, "Subject"),
        "fecha_correo": _header(headers, "Date"),
        "fecha_recepcion": fecha_recepcion,
        "contenido": extraer_texto(payload),
    }


def _cumple_criterios_operativos(detalle, asunto):
    label_ids = set(detalle.get("labelIds", []))
    asunto_normalizado = asunto.strip().lower()

    return (
        SLAVE_LABEL_ID in label_ids
        or TIMESTAMP_SUBJECT_MARKER in asunto_normalizado
        or asunto.strip() == "2026"
    )


def _ids_desde_history(history_items):
    ids = []
    vistos = set()

    def agregar(message_id):
        if message_id and message_id not in vistos:
            vistos.add(message_id)
            ids.append(message_id)

    for item in history_items:
        for agregado in item.get("messagesAdded", []):
            agregar(agregado.get("message", {}).get("id"))

        for etiquetado in item.get("labelsAdded", []):
            label_ids = etiquetado.get("labelIds", [])
            if SLAVE_LABEL_ID in label_ids:
                agregar(etiquetado.get("message", {}).get("id"))

    return ids

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
        inicio = perf_counter()
        try:
            detalle = service.users().messages().get(
                userId="me",
                id=mensaje_id,
                format="full"
            ).execute()
            duracion_get = _duracion(inicio)
        except Exception as e:
            print(
                f"[GMAIL] get {i}/{total} ERROR en {_duracion(inicio)} "
                f"| id={mensaje_id} | {e}"
            )
            raise

        gmail_message_id = detalle["id"]

        inicio = perf_counter()
        try:
            correo = _correo_desde_detalle(detalle)
            asunto = correo["asunto"]
            contenido = correo["contenido"]
            duracion_contenido = _duracion(inicio)
        except Exception as e:
            print(
                f"[GMAIL] contenido {i}/{total} ERROR en {_duracion(inicio)} "
                f"| id={gmail_message_id} | {e}"
            )
            raise
        print(
            f"[GMAIL] correo {i}/{total} OK "
            f"| id={gmail_message_id} "
            f"| asunto={asunto} "
            f"| get={duracion_get} "
            f"| contenido={duracion_contenido} "
            f"| chars={len(contenido)}"
        )

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
            pass

        # ==================================================
        # OUTPUT PARA PARSER
        # ==================================================

        correos_procesados.append(correo)

    # ======================================================
    # RESUMEN FINAL
    # ======================================================

    print(f"[GMAIL] total correos procesados={len(correos_procesados)}")
    print(f"\nTotal correos procesados: {len(correos_procesados)}")

    return correos_procesados


def obtener_correos_desde_history(start_history_id, end_history_id=None):
    creds = get_gmail_creds()

    print("Autenticacion exitosa")
    print(
        "[GMAIL] history inicio "
        f"| startHistoryId={start_history_id} "
        f"| eventHistoryId={end_history_id}"
    )

    if end_history_id is not None:
        try:
            if int(end_history_id) <= int(start_history_id):
                print("[GMAIL] history omitido | evento ya cubierto")
                return []
        except (TypeError, ValueError):
            pass

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

    history_items = []
    page_token = None
    pagina = 1

    while True:
        inicio = perf_counter()
        try:
            params = {
                "userId": "me",
                "startHistoryId": str(start_history_id),
                "labelId": SLAVE_LABEL_ID,
                "historyTypes": ["messageAdded", "labelAdded"],
            }
            if page_token:
                params["pageToken"] = page_token

            request = service.users().history().list(**params)
            resultado = request.execute()
        except Exception as e:
            print(
                f"[GMAIL] history list ERROR en {_duracion(inicio)} "
                f"| pagina={pagina} | {e}"
            )
            raise

        lote = resultado.get("history", [])
        history_items.extend(lote)
        print(
            f"[GMAIL] history list OK en {_duracion(inicio)} "
            f"| pagina={pagina} | eventos={len(lote)}"
        )

        page_token = resultado.get("nextPageToken")
        if not page_token:
            break
        pagina += 1

    mensaje_ids = _ids_desde_history(history_items)
    print(f"[GMAIL] history mensajes candidatos={len(mensaje_ids)}")

    correos_procesados = []

    for i, mensaje_id in enumerate(mensaje_ids, start=1):
        total = len(mensaje_ids)
        inicio = perf_counter()
        try:
            detalle = service.users().messages().get(
                userId="me",
                id=mensaje_id,
                format="full"
            ).execute()
            duracion_get = _duracion(inicio)
        except Exception as e:
            print(
                f"[GMAIL] history get {i}/{total} ERROR en {_duracion(inicio)} "
                f"| id={mensaje_id} | {e}"
            )
            raise

        inicio = perf_counter()
        correo = _correo_desde_detalle(detalle)
        duracion_contenido = _duracion(inicio)

        if not _cumple_criterios_operativos(detalle, correo["asunto"]):
            print(
                f"[GMAIL] history correo {i}/{total} ignorado "
                f"| id={mensaje_id} | asunto={correo['asunto']}"
            )
            continue

        correos_procesados.append(correo)
        print(
            f"[GMAIL] history correo {i}/{total} OK "
            f"| id={mensaje_id} "
            f"| asunto={correo['asunto']} "
            f"| get={duracion_get} "
            f"| contenido={duracion_contenido} "
            f"| chars={len(correo['contenido'])}"
        )

    print(f"[GMAIL] history total correos procesados={len(correos_procesados)}")
    return correos_procesados
