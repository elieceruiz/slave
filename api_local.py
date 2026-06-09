# api_local.py

from fastapi import FastAPI, Request
from run import ejecutar_pipeline
import base64
import json

app = FastAPI()


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

    try:
        body = await request.json()

        message = body.get("message", {})
        data = message.get("data")

        if data:
            decoded = base64.b64decode(data).decode("utf-8")
            payload = json.loads(decoded)
            print("📩 Evento Gmail recibido:", payload)

        else:
            print("⚠️ Evento sin data")

    except Exception as e:
        print("⚠️ Error parseando Pub/Sub:", e)

    # 🔥 DISPARA TU PIPELINE
    ejecutar_pipeline()

    return {"status": "ok"}