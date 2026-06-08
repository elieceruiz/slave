# db.py

# ==========================================================
# IMPORTS
# ==========================================================

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from config import get_env


# ==========================================================
# VARIABLES DE ENTORNO (LOCAL + CLOUD)
# ==========================================================

MONGO_URI = get_env("MONGO_URI")

if not MONGO_URI:
    raise ValueError("❌ MONGO_URI no está definida")

# ==========================================================
# CONEXIÓN MONGO
# ==========================================================

client = MongoClient(MONGO_URI)

db = client["slave"]
collection = db["capturas"]


# ==========================================================
# ÍNDICE ÚNICO
# ==========================================================

def crear_indice():

    collection.create_index(
        [
            ("gmail_message_id", 1),
            ("mes", 1)
        ],
        unique=True
    )

    print("✓ Índice compuesto listo")


# ==========================================================
# INSERTAR DOCUMENTOS
# ==========================================================

def insertar_documentos(documentos):

    insertados = 0
    ignorados = 0
    errores = 0

    for doc in documentos:

        try:
            collection.insert_one(doc)
            insertados += 1

        except DuplicateKeyError:
            ignorados += 1

        except Exception as e:
            errores += 1
            print(f"❌ Error real: {e}")

    print("\n==============================")
    print(f"✓ Insertados: {insertados}")
    print(f"✓ Ignorados : {ignorados}")
    print(f"⚠️ Errores   : {errores}")
    print("==============================\n")


# ==========================================================
# CONSULTAS
# ==========================================================

def obtener_ultimo(mes):

    return collection.find_one(
        {"mes": mes},
        sort=[("timestamp_captura", -1)]
    )


def obtener_todos(mes):

    return list(
        collection.find(
            {"mes": mes}
        ).sort("timestamp_captura", 1)
    )