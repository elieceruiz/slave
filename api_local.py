# api_local.py

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from activar_watch import activar_watch
from config import get_env
from db import (
    actualizar_estado_history,
    guardar_evento_webhook,
    obtener_estado_watch,
)
from label_id import listar_labels
from run import PipelineStageError, ejecutar_pipeline, ejecutar_pipeline_incremental
import base64
import json

app = FastAPI()


def _history_ya_cubierto(event_history_id, start_history_id):
    try:
        return int(event_history_id) <= int(start_history_id)
    except (TypeError, ValueError):
        return False


def _guardar_evento_webhook_seguro(**kwargs):
    try:
        guardar_evento_webhook(**kwargs)
    except Exception as error:
        print(f"[WEBHOOK] no se pudo guardar diagnostico | error={error}")


def validar_admin_token(x_admin_token: str | None = Header(default=None)):
    # Protege acciones operativas; no es autenticacion de usuarios finales.
    admin_token = get_env("ADMIN_TOKEN")

    if not admin_token:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN no esta definido",
        )

    if x_admin_token != admin_token:
        raise HTTPException(
            status_code=401,
            detail="admin token invalido",
        )

@app.get("/")
def root():
    return {"service": "slave-api", "status": "online"}

@app.head("/")
def root_head():
    return None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    return "User-agent: *\nDisallow: /\n"

@app.get("/favicon.ico")
def favicon():
    return Response(status_code=204)

@app.post("/admin/activar-watch")
def admin_activar_watch(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")
):
    # Renueva Gmail Watch desde Render, donde viven las credenciales operativas.
    validar_admin_token(x_admin_token)
    response = activar_watch()
    return {"status": "ok", "watch": response}

@app.get("/admin/watch-state")
def admin_watch_state(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")
):
    # Expone el ultimo estado guardado del Gmail Watch sin renovar nada.
    validar_admin_token(x_admin_token)
    return {"status": "ok", "watch_state": obtener_estado_watch()}

@app.get("/admin/labels")
def admin_labels(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")
):
    # Permite verificar el labelId real de Gmail sin depender del entorno local.
    validar_admin_token(x_admin_token)
    labels = listar_labels()
    return {"status": "ok", "labels": labels}

@app.post("/run")
def run_pipeline():
    try:
        ejecutar_pipeline()
        return {"status": "ok"}
    except PipelineStageError as e:
        return {
            "status": "error",
            "stage": e.stage,
            "detail": str(e.original_error),
        }
    except Exception as e:
        return {
            "status": "error",
            "stage": "unknown",
            "detail": str(e),
        }


# 🔥 NUEVO ENDPOINT (NO TOCAR LO DE ARRIBA)
@app.post("/webhook")
async def gmail_webhook(request: Request):

    """
    Endpoint que recibe eventos desde Google Pub/Sub (Gmail Watch).

    Flujo:
    Gmail detecta cambio → Pub/Sub → POST a este endpoint

    IMPORTANTE:
    - Este endpoint NO recibe el correo directamente
    - Solo recibe una notificación (evento)
    - El procesamiento real lo hace el pipeline (run.py)
    """

    try:
        # --------------------------------------------------
        # 1. Obtener el cuerpo del request enviado por Pub/Sub
        # --------------------------------------------------
        raw_body = await request.body()

        if not raw_body:
            print("Evento ignorado: body vacío")
            _guardar_evento_webhook_seguro(
                action="ignored",
                reason="empty_body",
            )
            return {"status": "ignored", "reason": "empty_body"}

        body = json.loads(raw_body)

        # Estructura típica de Pub/Sub:
        # {
        #   "message": {
        #       "data": "base64..."
        #   }
        # }

        message = body.get("message", {})
        pubsub_message_id = message.get("messageId")

        # --------------------------------------------------
        # 2. Extraer la data codificada en base64
        # --------------------------------------------------
        data = message.get("data")

        if data:
            # --------------------------------------------------
            # 3. Decodificar el payload
            # --------------------------------------------------
            decoded = base64.b64decode(data).decode("utf-8")

            # Convertir a JSON
            payload = json.loads(decoded)

            print(
                "[WEBHOOK] evento Gmail recibido "
                f"| historyId={payload.get('historyId')} "
                f"| email={payload.get('emailAddress')}"
            )

            if "historyId" in payload:

                event_history_id = payload.get("historyId")
                email = payload.get("emailAddress")
                estado_watch = obtener_estado_watch() or {}
                start_history_id = estado_watch.get("last_history_id")

                if start_history_id and _history_ya_cubierto(
                    event_history_id,
                    start_history_id,
                ):
                    print(
                        "[WEBHOOK] evento ignorado | historyId ya cubierto "
                        f"| startHistoryId={start_history_id}"
                    )
                    _guardar_evento_webhook_seguro(
                        action="ignored",
                        history_id=event_history_id,
                        email=email,
                        reason="history_already_covered",
                        pubsub_message_id=pubsub_message_id,
                    )
                    return {
                        "status": "ignored",
                        "reason": "history_already_covered",
                    }

                if start_history_id:
                    print(
                        "[WEBHOOK] evento valido | ejecutando pipeline incremental "
                        f"| startHistoryId={start_history_id}"
                    )
                    _guardar_evento_webhook_seguro(
                        action="incremental_started",
                        history_id=event_history_id,
                        email=email,
                        pubsub_message_id=pubsub_message_id,
                    )

                    try:
                        ejecutar_pipeline_incremental(
                            start_history_id,
                            event_history_id,
                        )
                        _guardar_evento_webhook_seguro(
                            action="incremental_completed",
                            history_id=event_history_id,
                            email=email,
                            pubsub_message_id=pubsub_message_id,
                        )
                    except Exception as error:
                        print(
                            "[WEBHOOK] incremental fallo | fallback pipeline completo "
                            f"| error={error}"
                        )
                        _guardar_evento_webhook_seguro(
                            action="fallback_started",
                            history_id=event_history_id,
                            email=email,
                            reason=str(error),
                            pubsub_message_id=pubsub_message_id,
                        )
                        ejecutar_pipeline()
                        actualizar_estado_history(
                            event_history_id,
                            source="webhook_fallback",
                        )
                        _guardar_evento_webhook_seguro(
                            action="fallback_completed",
                            history_id=event_history_id,
                            email=email,
                            pubsub_message_id=pubsub_message_id,
                        )
                else:
                    print("[WEBHOOK] sin cursor previo | ejecutando pipeline completo")
                    _guardar_evento_webhook_seguro(
                        action="full_started",
                        history_id=event_history_id,
                        email=email,
                        reason="no_cursor",
                        pubsub_message_id=pubsub_message_id,
                    )
                    ejecutar_pipeline()
                    actualizar_estado_history(
                        event_history_id,
                        source="webhook_full_no_cursor",
                    )
                    _guardar_evento_webhook_seguro(
                        action="full_completed",
                        history_id=event_history_id,
                        email=email,
                        pubsub_message_id=pubsub_message_id,
                    )

            else:
                # Evento raro o incompleto → ignoramos
                print("[WEBHOOK] evento ignorado | sin historyId")
                _guardar_evento_webhook_seguro(
                    action="ignored",
                    reason="missing_history_id",
                    pubsub_message_id=pubsub_message_id,
                )

        else:
            # Caso en que Pub/Sub manda mensaje sin data
            print("[WEBHOOK] evento ignorado | sin data")
            _guardar_evento_webhook_seguro(
                action="ignored",
                reason="missing_data",
                pubsub_message_id=pubsub_message_id,
            )

    except Exception as e:
        # --------------------------------------------------
        # 6. MANEJO DE ERRORES
        # --------------------------------------------------
        # Importante: NO romper el endpoint
        # porque Pub/Sub reintenta si falla

        print("[WEBHOOK] error parseando Pub/Sub:", e)

    # --------------------------------------------------
    # 7. RESPUESTA A PUB/SUB
    # --------------------------------------------------
    # Siempre responder 200 OK
    # para evitar reintentos innecesarios

    return {"status": "ok"}
