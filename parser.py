# parser.py

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo


# ==========================================================
# MAPA DE MESES
# ==========================================================

MESES = {
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12"
}

ZONA_COLOMBIA = ZoneInfo("America/Bogota")


# ==========================================================
# TIMESTAMP CAPTURA
# ==========================================================

def obtener_timestamp(asunto, fecha_correo, fecha_recepcion=None):

    # internalDate de Gmail representa la recepción real del mensaje.
    if fecha_recepcion:
        return fecha_recepcion

    if fecha_correo:
        return parsedate_to_datetime(fecha_correo)

    match = re.search(
        r"timestamp_captura:\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})",
        asunto
    )

    if match:
        return datetime.strptime(
            match.group(1),
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=ZONA_COLOMBIA)

    raise ValueError("El correo no contiene una fecha utilizable")


# ==========================================================
# EXTRAER MÉTRICAS DE UN BLOQUE (CORREGIDO)
# ==========================================================

def extraer_metricas(texto):

    def buscar(pattern):
        match = re.search(pattern, texto, re.DOTALL)
        return float(match.group(1)) if match else None

    def buscar_int(pattern):
        match = re.search(pattern, texto, re.DOTALL)
        return int(match.group(1)) if match else None

    return {
        # CSAT
        "csat": buscar(r"Percent Positive:\s*\**\s*([\d\.]+)%"),
        "csat_respuestas": buscar_int(r"Percent Positive:.*?based on (\d+) responses"),

        # RESOLVED
        "resolved": buscar(r"Percent Resolved:\s*\**\s*([\d\.]+)%"),
        "resolved_respuestas": buscar_int(r"Percent Resolved:.*?based on (\d+) responses"),

        # NPS
        "nps": buscar(r"Net Promoter Score.*?:\s*\**\s*([-\d\.]+)"),
        "nps_respuestas": buscar_int(r"Net Promoter Score.*?based on (\d+) responses")
    }


# ==========================================================
# PARSEAR HISTÓRICO (VARIOS MESES)
# ==========================================================

def parsear_historico(contenido, timestamp):

    bloques = re.split(r"# (\w+ \d{4})", contenido)

    resultados = []

    for i in range(1, len(bloques), 2):

        titulo = bloques[i]
        cuerpo = bloques[i + 1]

        mes_nombre, año = titulo.split()
        mes_num = MESES.get(mes_nombre)

        if not mes_num:
            continue

        mes = f"{año}-{mes_num}"

        metricas = extraer_metricas(cuerpo)

        resultados.append({
            "timestamp_captura": timestamp,
            "mes": mes,
            **metricas
        })

    return resultados


# ==========================================================
# PARSEAR CAPTURA NORMAL (UN SOLO MES)
# ==========================================================

def parsear_captura(contenido, timestamp):

    match = re.search(r"# (\w+) (\d{4})", contenido)

    if not match:
        return []

    mes_nombre = match.group(1)
    año = match.group(2)

    mes_num = MESES.get(mes_nombre)

    if not mes_num:
        return []

    mes = f"{año}-{mes_num}"

    metricas = extraer_metricas(contenido)

    return [{
        "timestamp_captura": timestamp,
        "mes": mes,
        **metricas
    }]


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================

def parsear_correo(correo):

    asunto = correo["asunto"]
    fecha_correo = correo["fecha_correo"]
    fecha_recepcion = correo.get("fecha_recepcion")
    contenido = correo["contenido"]

    timestamp = obtener_timestamp(
        asunto,
        fecha_correo,
        fecha_recepcion
    )

    if asunto.strip() == "2026":
        return parsear_historico(contenido, timestamp)

    return parsear_captura(contenido, timestamp)


# ==========================================================
# PROCESAR LISTA COMPLETA
# ==========================================================

def parsear_correos(correos):

    todos = []

    for correo in correos:

        docs = parsear_correo(correo)

        for d in docs:
            d["gmail_message_id"] = correo["gmail_message_id"]

        todos.extend(docs)

    return todos
