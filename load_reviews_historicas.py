import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path


DB_NAME = "slave"
COLLECTION_NAME = "reviews_historicas"
DATASET = "driver_applicant_support_2025"
SOURCE = "historical_json"
MODEL_VERSION = "color_v1"

MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def load_dotenv_if_present(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def parse_dt(value):
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def normalized_list(value):
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def classification_reason(review):
    excellence = normalized_list(review.get("excellence"))
    improve = normalized_list(review.get("improve"))

    if excellence:
        return "excellence_present"
    if improve:
        return "improve_present"
    if review.get("resolved") is True:
        return "resolved_true_no_labels"
    if review.get("resolved") is False:
        return "resolved_false_no_labels"
    if review.get("comment") or review.get("resolution_comment"):
        return "comment_present_no_labels"
    return "no_signal_default_red"


def build_review_key(review):
    parts = [
        DATASET,
        str(review.get("contact_id") or ""),
        str(review.get("posted") or ""),
        str(review.get("sent") or ""),
        str(review.get("agent") or ""),
        str(review.get("tags") or ""),
    ]
    base = "|".join(parts)

    if not any(parts[1:]):
        base = json.dumps(review, sort_keys=True, ensure_ascii=False)

    digest = hashlib.sha256(base.encode("utf-8")).hexdigest()[:24]
    return f"{DATASET}:{digest}"


def enrich_review(review):
    raw = deepcopy(review)
    posted_dt = parse_dt(review.get("posted"))
    sent_dt = parse_dt(review.get("sent"))
    excellence = normalized_list(review.get("excellence"))
    improve = normalized_list(review.get("improve"))
    color = review.get("color")

    if color not in {"green", "red"}:
        color = "green" if excellence or review.get("resolved") is True else "red"

    mes = posted_dt.strftime("%Y-%m") if posted_dt else None
    year = posted_dt.year if posted_dt else None
    month = posted_dt.month if posted_dt else None

    document = {
        "dataset": DATASET,
        "source": SOURCE,
        "model_version": MODEL_VERSION,
        "business_context": "driver_applicant_support",
        "review_key": build_review_key(review),
        "color": color,
        "classification_reason": classification_reason(review),
        "posted": review.get("posted"),
        "posted_dt": posted_dt,
        "sent": review.get("sent"),
        "sent_dt": sent_dt,
        "mes": mes,
        "year": year,
        "month": month,
        "month_name": MONTH_NAMES.get(month),
        "comment": review.get("comment"),
        "excellence": excellence,
        "improve": improve,
        "resolved": review.get("resolved"),
        "resolution_comment": review.get("resolution_comment"),
        "channel": review.get("channel"),
        "brand": review.get("brand"),
        "area": review.get("area"),
        "contact_id": review.get("contact_id"),
        "area_type": review.get("area_type"),
        "issue_type_1": review.get("issue_type_1"),
        "tags": review.get("tags"),
        "agent": review.get("agent"),
        "has_comment": bool(review.get("comment")),
        "has_resolution_comment": bool(review.get("resolution_comment")),
        "excellence_count": len(excellence),
        "improve_count": len(improve),
        "raw": raw,
    }

    for key, value in review.items():
        document.setdefault(key, value)

    return document


def load_reviews(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("El archivo JSON debe contener una lista de reviews.")
    return [enrich_review(item) for item in data]


def print_summary(documents):
    colors = Counter(doc.get("color") for doc in documents)
    months = defaultdict(Counter)

    for doc in documents:
        months[doc.get("mes")][doc.get("color")] += 1

    total = len(documents)
    green = colors.get("green", 0)
    red = colors.get("red", 0)
    positive_rate = (green / total * 100) if total else 0

    print("Resumen dry-run")
    print("================")
    print(f"Dataset    : {DATASET}")
    print(f"Coleccion  : {DB_NAME}.{COLLECTION_NAME}")
    print(f"Total      : {total}")
    print(f"Green      : {green}")
    print(f"Red        : {red}")
    print(f"Resultado  : {positive_rate:.1f}%")
    print()
    print("Meses descendentes")
    print("==================")

    for mes in sorted((m for m in months if m), reverse=True):
        month_total = sum(months[mes].values())
        month_green = months[mes].get("green", 0)
        month_red = months[mes].get("red", 0)
        month_rate = (month_green / month_total * 100) if month_total else 0
        print(
            f"{mes} | total={month_total} | green={month_green} | "
            f"red={month_red} | resultado={month_rate:.1f}%"
        )


def write_to_mongo(documents):
    try:
        from pymongo import MongoClient, UpdateOne
    except ImportError as exc:
        raise RuntimeError("Falta instalar pymongo para escribir en MongoDB.") from exc

    mongo_uri = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise RuntimeError("Falta MONGO_URI o MONGODB_URI en variables de entorno.")

    client = MongoClient(mongo_uri)
    collection = client[DB_NAME][COLLECTION_NAME]
    collection.create_index("review_key", unique=True)
    collection.create_index([("dataset", 1), ("posted_dt", -1)])
    collection.create_index([("dataset", 1), ("mes", -1), ("color", 1)])

    operations = [
        UpdateOne(
            {"review_key": doc["review_key"]},
            {"$set": doc},
            upsert=True,
        )
        for doc in documents
    ]

    if not operations:
        print("No hay documentos para cargar.")
        return

    result = collection.bulk_write(operations, ordered=False)
    print("Carga Mongo completada")
    print("======================")
    print(f"Matched   : {result.matched_count}")
    print(f"Modified  : {result.modified_count}")
    print(f"Upserted  : {result.upserted_count}")


def main():
    parser = argparse.ArgumentParser(
        description="Carga reviews historicas 2025 en MongoDB sin tocar capturas."
    )
    parser.add_argument(
        "json_path",
        nargs="?",
        default="eliecer_ruiz_reviews_colored.json",
        help="Ruta al JSON coloreado.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe en MongoDB. Sin esta bandera solo imprime diagnostico.",
    )
    args = parser.parse_args()

    load_dotenv_if_present()
    documents = load_reviews(args.json_path)
    print_summary(documents)

    if args.apply:
        print()
        write_to_mongo(documents)
    else:
        print()
        print("Dry-run: no se escribio nada en MongoDB.")
        print("Para cargar: python load_reviews_historicas.py --apply")


if __name__ == "__main__":
    main()
