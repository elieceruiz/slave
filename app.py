# app.py

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient


META_CSAT = 80.0
ZONA_COLOMBIA = ZoneInfo("America/Bogota")


st.set_page_config(
    page_title="Slave | CSAT",
    page_icon="S",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"] {
        display: none;
    }

    .block-container {
        max-width: 980px;
        padding-top: 2.25rem;
        padding-bottom: 4rem;
    }

    h1 {
        letter-spacing: -0.04em;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 0.9rem;
        padding: 1rem;
    }

    div[data-testid="stMetricLabel"] {
        color: rgba(250, 250, 250, 0.66);
    }

    div[data-testid="stMetricValue"] {
        letter-spacing: -0.04em;
    }

    .status-box {
        border-left: 4px solid #7c8cff;
        background: rgba(124, 140, 255, 0.08);
        border-radius: 0.35rem 0.8rem 0.8rem 0.35rem;
        margin: 0.4rem 0 1.25rem;
        padding: 0.9rem 1rem;
    }

    .status-box strong {
        display: block;
        font-size: 1.05rem;
        margin-bottom: 0.15rem;
    }

    .status-box span {
        color: rgba(250, 250, 250, 0.68);
    }

    .metric-grid {
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin-bottom: 1rem;
    }

    .metric-card {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-radius: 0.9rem;
        min-width: 0;
        padding: 1rem;
    }

    .metric-label {
        color: rgba(250, 250, 250, 0.66);
        font-size: 0.88rem;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        font-size: 1.75rem;
        font-weight: 600;
        letter-spacing: -0.04em;
        line-height: 1.15;
    }

    .metric-detail {
        color: rgba(250, 250, 250, 0.58);
        font-size: 0.78rem;
        margin-top: 0.35rem;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1.25rem;
        }

        .metric-grid {
            gap: 0.7rem;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .metric-card {
            padding: 0.85rem;
        }

        .metric-value {
            font-size: 1.4rem;
        }

        .status-box {
            padding: 0.8rem;
        }
    }

    @media (max-width: 390px) {
        .metric-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def obtener_coleccion():
    load_dotenv()
    mongo_uri = os.getenv("MONGO_URI")

    if not mongo_uri:
        raise RuntimeError("MONGO_URI no está definida.")

    cliente = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    cliente.admin.command("ping")
    return cliente["slave"]["capturas"]


@st.cache_data(ttl=60)
def cargar_capturas():
    campos = {
        "_id": 0,
        "timestamp_captura": 1,
        "mes": 1,
        "csat": 1,
        "csat_respuestas": 1,
        "resolved": 1,
        "resolved_respuestas": 1,
        "nps": 1,
        "nps_respuestas": 1,
    }
    documentos = list(
        obtener_coleccion().find({}, campos).sort("timestamp_captura", 1)
    )

    if not documentos:
        return pd.DataFrame(columns=list(campos.keys())[1:])

    df = pd.DataFrame(documentos)
    df["timestamp_captura"] = pd.to_datetime(
        df["timestamp_captura"], errors="coerce", utc=True
    )
    return (
        df.dropna(subset=["timestamp_captura", "mes"])
        .sort_values("timestamp_captura")
        .reset_index(drop=True)
    )


def formatear_fecha(valor):
    if pd.isna(valor):
        return "Sin fecha"

    fecha = (
        pd.Timestamp(valor)
        .tz_convert(ZONA_COLOMBIA)
        .to_pydatetime()
    )
    meses = (
        "ene",
        "feb",
        "mar",
        "abr",
        "may",
        "jun",
        "jul",
        "ago",
        "sep",
        "oct",
        "nov",
        "dic",
    )
    return f"{fecha.day:02d} {meses[fecha.month - 1]} {fecha:%Y · %H:%M}"


def fecha_colombia(valor):
    return pd.Timestamp(valor).tz_convert(ZONA_COLOMBIA)


def valor_porcentaje(valor):
    return "—" if pd.isna(valor) else f"{valor:.1f}%"


def desglose_csat(csat, total):
    if pd.isna(csat) or not total:
        return 0, 0

    positivas = round(float(csat) * int(total) / 100)
    positivas = min(max(positivas, 0), int(total))
    return positivas, int(total) - positivas

def positivas_para_meta(total, positivas):
    if not total:
        return 0

    meta = META_CSAT / 100
    x = 0

    while True:
        if (positivas + x) / (total + x) >= meta:
            return x
        x += 1

st.title("Slave")
st.caption("Seguimiento operativo de CSAT")

try:
    capturas = cargar_capturas()
except Exception as error:
    st.error("No fue posible conectar con MongoDB Atlas.")
    st.caption(str(error))
    st.stop()

if capturas.empty:
    st.info("MongoDB todavía no contiene capturas para mostrar.")
    st.stop()

mes_actual = capturas["mes"].max()
capturas_mes = capturas[capturas["mes"] == mes_actual].copy()
ultima = capturas_mes.iloc[-1]

csat_actual = ultima.get("csat")
muestras = ultima.get("csat_respuestas")
muestras = 0 if pd.isna(muestras) else int(muestras)
positivas, no_positivas = desglose_csat(csat_actual, muestras)
faltantes_positivas = positivas_para_meta(
    muestras,
    positivas
)
brecha_csat = (
    None
    if pd.isna(csat_actual)
    else max(META_CSAT - float(csat_actual), 0)
)
meta_alcanzada = brecha_csat == 0 if brecha_csat is not None else False
progreso = (
    0
    if pd.isna(csat_actual)
    else min(max(float(csat_actual) / META_CSAT, 0), 1)
)

if meta_alcanzada:
    mensaje_meta = f"Meta mínima de {META_CSAT:.0f}% alcanzada."
elif brecha_csat is None:
    mensaje_meta = "No hay un CSAT válido para calcular la brecha."
else:
    mensaje_meta = (
        f"Faltan {brecha_csat:.1f} puntos porcentuales "
        f"y {faltantes_positivas} positivas "
        f"para llegar al {META_CSAT:.0f}%."
    )

st.markdown(
    f"""
    <div class="status-box">
        <strong>{valor_porcentaje(csat_actual)} de CSAT: {positivas} positivas de {muestras}</strong>
        <span>{mensaje_meta}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

brecha_texto = (
    "Meta cumplida"
    if meta_alcanzada
    else ("—" if brecha_csat is None else f"{brecha_csat:.1f} pp")
)
ultima_colombia = fecha_colombia(ultima["timestamp_captura"])

st.markdown(
    f"""
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-label">CSAT actual</div>
            <div class="metric-value">{valor_porcentaje(csat_actual)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Positivas</div>
            <div class="metric-value">{positivas}</div>
            <div class="metric-detail">Usuarios satisfechos</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">No positivas</div>
            <div class="metric-value">{no_positivas}</div>
            <div class="metric-detail">Resto de respuestas</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Muestras CSAT</div>
            <div class="metric-value">{muestras}</div>
            <div class="metric-detail">Total de respuestas</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Brecha a 80%</div>
            <div class="metric-value">{brecha_texto}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Última actualización</div>
            <div class="metric-value">{ultima_colombia:%d/%m · %H:%M}</div>
            <div class="metric-detail">Hora Colombia</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.progress(progreso)
st.caption(f"Meta operativa: CSAT mínimo de {META_CSAT:.0f}%")

st.markdown("#### Métricas complementarias")
resolved_muestras = int(ultima.get("resolved_respuestas") or 0)
nps_muestras = int(ultima.get("nps_respuestas") or 0)

complementaria_1, complementaria_2 = st.columns(2)
with complementaria_1:
    st.metric("Resolved", valor_porcentaje(ultima.get("resolved")))
    st.caption(f"{resolved_muestras} muestras de Resolved")

with complementaria_2:
    st.metric(
        "NPS",
        "—" if pd.isna(ultima.get("nps")) else f"{ultima.get('nps'):.1f}",
    )
    st.caption(f"{nps_muestras} muestras de NPS")

st.divider()
st.subheader("Tendencia del mes")
st.caption(
    f"{mes_actual} · {len(capturas_mes)} "
    f"{'captura' if len(capturas_mes) == 1 else 'capturas'}"
)

if capturas_mes["csat"].notna().sum() > 1:
    grafico = capturas_mes.copy()
    grafico["timestamp_colombia"] = grafico["timestamp_captura"].dt.tz_convert(
        ZONA_COLOMBIA
    )
    st.line_chart(
        grafico.set_index("timestamp_colombia")[["csat"]],
        use_container_width=True,
        color=["#7c8cff"],
        height=350,
        y_label="CSAT",
        x_label="Captura",
    )
else:
    st.info("Se necesitan al menos dos capturas con CSAT para mostrar la tendencia.")

st.divider()
st.subheader("Capturas")

tabla = capturas_mes.sort_values("timestamp_captura", ascending=False).copy()
tabla["Captura"] = tabla["timestamp_captura"].apply(formatear_fecha)
tabla["CSAT"] = tabla["csat"].apply(valor_porcentaje)
tabla["Muestras"] = tabla["csat_respuestas"].fillna(0).astype(int)
desgloses = tabla.apply(
    lambda fila: desglose_csat(fila["csat"], fila["Muestras"]),
    axis=1,
)
tabla["Positivas"] = desgloses.apply(lambda valor: valor[0])
tabla["No positivas"] = desgloses.apply(lambda valor: valor[1])

st.dataframe(
    tabla[["Captura", "CSAT", "Positivas", "No positivas", "Muestras"]],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Captura": st.column_config.TextColumn("Captura"),
        "CSAT": st.column_config.TextColumn("CSAT"),
        "Positivas": st.column_config.NumberColumn("Positivas", format="%d"),
        "No positivas": st.column_config.NumberColumn(
            "No positivas",
            format="%d",
        ),
        "Muestras": st.column_config.NumberColumn("Muestras", format="%d"),
    },
)
st.caption(
    "Positivas y no positivas se derivan del porcentaje CSAT y del total "
    "de respuestas informado por Medallia."
)

with st.expander("Cuarto de San Alejo"):
    st.caption("Histórico mensual")

    historico = (
        capturas.sort_values("timestamp_captura")
        .groupby("mes", as_index=False)
        .tail(1)
        .sort_values("mes", ascending=False)
        .copy()
    )
    historico["Mes"] = historico["mes"]
    historico["CSAT"] = historico["csat"].apply(valor_porcentaje)
    historico["Resolved"] = historico["resolved"].apply(valor_porcentaje)
    historico["NPS"] = historico["nps"].apply(
        lambda valor: "—" if pd.isna(valor) else f"{valor:.1f}"
    )
    historico["Muestras"] = historico["csat_respuestas"].fillna(0).astype(int)

    st.dataframe(
        historico[["Mes", "CSAT", "Muestras", "Resolved", "NPS"]],
        hide_index=True,
        use_container_width=True,
    )

if st.button("Actualizar datos", use_container_width=True):
    cargar_capturas.clear()
    st.rerun()

st.caption(
    "Fuente: MongoDB Atlas · Horario: Colombia · "
    f"Vista actualizada {datetime.now(ZONA_COLOMBIA):%d/%m/%Y %H:%M}"
)
