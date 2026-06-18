# api_local.py

from fastapi import FastAPI, Request
from run import ejecutar_pipeline
import base64
import json

app = FastAPI()


@app.get("/")
def root():
    return {"service": "slave-api", "status": "online"}


@app.head("/")
def root_head():
    return None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run_pipeline():
    try:
        ejecutar_pipeline()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


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
            return {"status": "ignored", "reason": "empty_body"}

        body = json.loads(raw_body)

        # Estructura típica de Pub/Sub:
        # {
        #   "message": {
        #       "data": "base64..."
        #   }
        # }

        message = body.get("message", {})

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

            # Ejemplo de payload:
            # {
            #   "emailAddress": "...",
            #   "historyId": "123456"
            # }

            print("📩 Evento Gmail recibido:", payload)

            # --------------------------------------------------
            # 4. VALIDACIÓN MÍNIMA DEL EVENTO
            # --------------------------------------------------
            # Gmail SIEMPRE envía "historyId" cuando hay cambios reales
            # (nuevo correo, etiqueta, etc.)

            if "historyId" in payload:

                print("✅ Evento válido → ejecutando pipeline")

                # --------------------------------------------------
                # 5. DISPARAR EL PIPELINE
                # --------------------------------------------------
                # Aquí NO procesamos directamente el correo.
                # Solo llamamos al sistema principal que:
                #   - consulta Gmail
                #   - filtra por label "slave"
                #   - parsea
                #   - inserta en Mongo
                #
                # Esto evita duplicar lógica aquí.
                ejecutar_pipeline()

            else:
                # Evento raro o incompleto → ignoramos
                print("⛔ Evento ignorado (sin historyId)")

        else:
            # Caso en que Pub/Sub manda mensaje sin data
            print("⚠️ Evento sin data")

    except Exception as e:
        # --------------------------------------------------
        # 6. MANEJO DE ERRORES
        # --------------------------------------------------
        # Importante: NO romper el endpoint
        # porque Pub/Sub reintenta si falla

        print("⚠️ Error parseando Pub/Sub:", e)

    # --------------------------------------------------
    # 7. RESPUESTA A PUB/SUB
    # --------------------------------------------------
    # Siempre responder 200 OK
    # para evitar reintentos innecesarios

    return {"status": "ok"}
