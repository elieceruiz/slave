# api_local.py

from fastapi import FastAPI
from run import ejecutar_pipeline

app = FastAPI()


@app.post("/run")
def run_pipeline():
    try:
        ejecutar_pipeline()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}