# db.py

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from config import get_env


MONGO_URI = get_env("MONGO_URI")

if not MONGO_URI:
    raise ValueError("MONGO_URI no esta definida")


client = MongoClient(MONGO_URI)
db = client["slave"]
collection = db["capturas"]
state_collection = db["state"]

WATCH_STATE_ID = "gmail_watch"


# Una captura cambia semanticamente cuando cambia el mes o cualquiera de sus
# metricas. gmail_message_id identifica el correo, no necesariamente la captura:
# dos correos distintos pueden contener exactamente el mismo estado de Medallia.
CAMPOS_CAPTURA = (
    "mes",
    "csat",
    "csat_respuestas",
    "resolved",
    "resolved_respuestas",
    "nps",
    "nps_respuestas",
)


def _normalizar_numero(valor):
    """Genera una representacion estable para enteros y flotantes equivalentes."""
    if valor is None:
        return None

    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return str(valor)

    if not numero.is_finite():
        return str(valor)

    return format(numero.normalize(), "f")


def generar_captura_key(documento):
    """
    Huella deterministica de la captura.

    No incluye gmail_message_id ni timestamp_captura porque esos campos pueden
    variar cuando el mismo snapshot llega reenviado en otro correo.
    """
    contenido = {
        campo: (
            documento.get(campo)
            if campo == "mes"
            else _normalizar_numero(documento.get(campo))
        )
        for campo in CAMPOS_CAPTURA
    }
    serializado = json.dumps(
        contenido,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serializado.encode("utf-8")).hexdigest()


def crear_indice():
    """
    Mantiene dos defensas complementarias:

    1. gmail_message_id + mes evita reprocesar el mismo correo.
    2. captura_key evita guardar la misma captura desde correos distintos.

    El indice de captura_key es parcial para ser compatible con documentos
    historicos que todavia no contienen ese campo.
    """
    collection.create_index(
        [
            ("gmail_message_id", 1),
            ("mes", 1),
        ],
        name="gmail_message_id_1_mes_1",
        unique=True,
    )

    collection.create_index(
        [("captura_key", 1)],
        name="captura_key_unique",
        unique=True,
        partialFilterExpression={
            "captura_key": {"$type": "string"},
        },
    )

    print("Indices de idempotencia listos")


def insertar_documentos(documentos):
    insertados = 0
    ignorados = 0
    actualizados = 0
    errores = 0

    for documento in documentos:
        doc = dict(documento)
        # La key semantica hace que correos distintos con la misma captura no dupliquen.
        captura_key = generar_captura_key(doc)
        doc["captura_key"] = captura_key

        try:
            # Camino normal: operacion atomica protegida por el indice unico.
            existente = collection.find_one(
                {"captura_key": captura_key},
                {"_id": 1},
            )

            if existente:
                ignorados += 1
                continue

            # Compatibilidad: reconoce documentos previos al campo captura_key.
            filtro_semantico = {
                campo: doc.get(campo)
                for campo in CAMPOS_CAPTURA
            }
            legado = collection.find_one(
                filtro_semantico,
                {"_id": 1, "captura_key": 1},
            )

            if legado:
                resultado = collection.update_one(
                    {
                        "_id": legado["_id"],
                        "captura_key": {"$exists": False},
                    },
                    {"$set": {"captura_key": captura_key}},
                )

                if resultado.modified_count:
                    actualizados += 1
                else:
                    ignorados += 1
                continue

            resultado = collection.update_one(
                {"captura_key": captura_key},
                {"$setOnInsert": doc},
                upsert=True,
            )

            if resultado.upserted_id is not None:
                insertados += 1
            else:
                ignorados += 1

        except DuplicateKeyError:
            # Otra ejecucion concurrente inserto la misma identidad primero.
            ignorados += 1

        except Exception as error:
            errores += 1
            print(f"Error persistiendo captura: {error}")

    resumen = {
        "insertados": insertados,
        "ignorados": ignorados,
        "actualizados": actualizados,
        "errores": errores,
    }

    print("\n==============================")
    print(f"Insertados   : {insertados}")
    print(f"Ignorados    : {ignorados}")
    print(f"Actualizados : {actualizados}")
    print(f"Errores      : {errores}")
    print("==============================\n")

    return resumen


def _watch_expiration_datetime(expiration):
    if not expiration:
        return None

    try:
        return datetime.fromtimestamp(int(expiration) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def guardar_estado_watch(response, topic_name=None):
    """Persiste el ultimo estado conocido de Gmail Watch.

    Esta coleccion no participa en las capturas CSAT; solo deja trazabilidad
    operativa para saber que historyId entrego Gmail y cuando vence el watch.
    """
    history_id = response.get("historyId") if response else None
    expiration = response.get("expiration") if response else None

    estado = {
        "last_history_id": str(history_id) if history_id is not None else None,
        "watch_expiration": str(expiration) if expiration is not None else None,
        "watch_expiration_at": _watch_expiration_datetime(expiration),
        "watch_renewed_at": datetime.now(timezone.utc),
    }

    if topic_name:
        estado["topic_name"] = topic_name

    state_collection.update_one(
        {"_id": WATCH_STATE_ID},
        {
            "$set": estado,
            "$setOnInsert": {"_id": WATCH_STATE_ID},
        },
        upsert=True,
    )

    return {"_id": WATCH_STATE_ID, **estado}


def obtener_estado_watch():
    estado = state_collection.find_one(
        {"_id": WATCH_STATE_ID},
        {"_id": 0},
    )
    return estado

def obtener_ultimo(mes):
    return collection.find_one(
        {"mes": mes},
        sort=[("timestamp_captura", -1)],
    )


def obtener_todos(mes):
    return list(
        collection.find(
            {"mes": mes},
        ).sort("timestamp_captura", 1)
    )
