# app.py

import os
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from pymongo import MongoClient


META_CSAT = 80.0
ZONA_COLOMBIA = ZoneInfo("America/Bogota")
VERSION_STREAMLIT = tuple(
    int(parte)
    for parte in st.__version__.split(".")[:2]
)
ANCHO_STRETCH = (
    {"width": "stretch"}
    if VERSION_STREAMLIT >= (1, 58)
    else {}
)


st.set_page_config(
    page_title="Faro 80",
    page_icon="S",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer {
        display: none;
    }

    [data-testid="stAppViewContainer"] {
        background: #0b0d14;
        color: #f2f0ea;
    }

    .block-container {
        max-width: 720px;
        padding-top: 0.75rem;
        padding-bottom: 3rem;
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

    .faro-header {
        margin-bottom: 0.55rem;
    }

    .faro-brand {
        color: #f2b95d;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.16em;
    }

    .faro-signal {
        color: #9299a8;
        font-size: 0.78rem;
        margin-top: 0.12rem;
    }

    .pulse-card {
        background:
            radial-gradient(
                circle at 78% 18%,
                rgba(242, 185, 93, 0.10),
                transparent 34%
            ),
            #121622;
        border: 1px solid #252b3b;
        border-radius: 1rem;
        margin: 0 0 1.1rem;
        padding: 1rem;
    }

    .pulse-main,
    .pulse-chip-grid {
        align-items: center;
        display: flex;
        justify-content: space-between;
    }

    .pulse-kicker,
    .pulse-meta,
    .pulse-chip-label {
        color: #9299a8;
        font-size: 0.78rem;
    }

    .pulse-kicker {
        color: #9ca8ff;
        font-weight: 600;
        letter-spacing: 0.09em;
        text-transform: uppercase;
    }

    .pulse-main {
        align-items: flex-end;
        gap: 1rem;
        margin-top: 0.65rem;
    }

    .pulse-value {
        color: #f2f0ea;
        font-size: 3.15rem;
        font-weight: 700;
        letter-spacing: -0.06em;
        line-height: 1;
    }

    .pulse-delta {
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
        padding: 0.3rem 0.55rem;
        white-space: nowrap;
    }

    .pulse-positive {
        background: rgba(105, 200, 156, 0.12);
        color: #69c89c;
    }

    .pulse-negative {
        background: rgba(219, 123, 131, 0.12);
        color: #db7b83;
    }

    .pulse-neutral {
        background: rgba(255, 255, 255, 0.07);
        color: rgba(250, 250, 250, 0.72);
    }

    .pulse-meta {
        margin-top: 0.4rem;
    }

    .horizon-map {
        margin-top: 1rem;
    }

    .horizon-labels {
        color: #9299a8;
        display: flex;
        font-size: 0.72rem;
        justify-content: space-between;
        margin-bottom: 0.35rem;
    }

    .horizon-track {
        background: #252b3b;
        border-radius: 999px;
        height: 4px;
        position: relative;
    }

    .horizon-progress {
        background: #9ca8ff;
        border-radius: 999px;
        height: 4px;
    }

    .horizon-marker {
        background: #9ca8ff;
        border: 3px solid #121622;
        border-radius: 50%;
        box-shadow: 0 0 0 1px rgba(156, 168, 255, 0.45);
        height: 12px;
        position: absolute;
        top: -4px;
        transform: translateX(-50%);
        width: 12px;
    }

    .horizon-target {
        background: #f2b95d;
        border-radius: 50%;
        box-shadow: 0 0 0 3px rgba(242, 185, 93, 0.12);
        height: 8px;
        left: 80%;
        position: absolute;
        top: -2px;
        transform: translateX(-50%);
        width: 8px;
    }

    .experiences {
        border-top: 1px solid #252b3b;
        margin-top: 1.1rem;
        padding-top: 1rem;
    }

    .experiences-title,
    .routes-title {
        color: #f2f0ea;
        font-size: 0.88rem;
        font-weight: 600;
    }

    .experience-dots {
        display: flex;
        flex-wrap: wrap;
        gap: 0.38rem;
        margin: 0.75rem 0 0.65rem;
    }

    .experience-dot {
        border-radius: 50%;
        height: 0.58rem;
        width: 0.58rem;
    }

    .experience-positive {
        background: #69c89c;
        box-shadow: 0 0 0 2px rgba(105, 200, 156, 0.08);
    }

    .experience-other {
        background: #555d70;
    }

    .experience-legend {
        color: #9299a8;
        font-size: 0.78rem;
    }

    .routes-title {
        margin-top: 1rem;
    }

    .pulse-chip-grid {
        gap: 0.55rem;
        margin-top: 0.55rem;
    }

    .pulse-chip {
        border: 1px solid #252b3b;
        border-radius: 0.7rem;
        flex: 1;
        padding: 0.65rem;
    }

    .pulse-chip-positive {
        background: rgba(105, 200, 156, 0.06);
    }

    .pulse-chip-negative {
        background: rgba(219, 123, 131, 0.06);
    }

    .route-list {
        display: grid;
        gap: 0.55rem;
    }

    .route-row {
        align-items: center;
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid #252b3b;
        border-radius: 0.75rem;
        display: grid;
        gap: 0.7rem;
        grid-template-columns: minmax(0, 1fr) auto;
        padding: 0.62rem 0.8rem;
    }

    .route-heading {
        align-items: center;
        display: flex;
        gap: 0.55rem;
        justify-content: space-between;
    }

    .route-name {
        color: #f2f0ea;
        font-size: 0.84rem;
        font-weight: 600;
    }

    .route-dots {
        display: inline-flex;
        flex-shrink: 0;
        gap: 0.28rem;
    }

    .route-dot {
        border-radius: 50%;
        height: 0.5rem;
        width: 0.5rem;
    }

    .route-dot-positive {
        background: #69c89c;
        box-shadow: 0 0 0 2px rgba(105, 200, 156, 0.08);
    }

    .route-dot-other {
        background: #555d70;
        border: 1px solid #737b8e;
    }

    .route-value {
        color: #f2f0ea;
        font-size: 1.05rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        white-space: nowrap;
    }

    @media (max-width: 480px) {
        .route-row {
            gap: 0.55rem;
            padding: 0.6rem 0.7rem;
        }

        .route-heading {
            align-items: flex-start;
        }

        div[data-testid="stMarkdownContainer"]:has(.monthly-table-anchor)
        + div [role="gridcell"] {
            padding-left: 0.3rem;
            padding-right: 0.3rem;
        }
    }

    .pulse-chip-value {
        font-size: 1.05rem;
        font-weight: 650;
        margin-top: 0.15rem;
    }

    @media (max-width: 700px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 0.6rem;
        }

        .pulse-card {
            padding: 0.85rem;
        }

        .pulse-value {
            font-size: 2.75rem;
        }

        .experience-dots {
            gap: 0.34rem;
        }

        .faro-header {
            margin-bottom: 0.45rem;
        }
    }

    @media (max-width: 390px) {
        .pulse-chip {
            padding: 0.55rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def obtener_coleccion():
    # Faro 80 solo observa Mongo; la escritura ocurre en el pipeline de Render.
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
    # El TTL evita consultas constantes; la pagina se actualiza en cada rerun.
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


def formatear_ultima_senal(valor):
    fecha = fecha_colombia(valor)
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
    return f"{fecha.day:02d} {meses[fecha.month - 1]} · {fecha:%H:%M}"


def nombre_mes(mes):
    meses = {
        "01": "enero",
        "02": "febrero",
        "03": "marzo",
        "04": "abril",
        "05": "mayo",
        "06": "junio",
        "07": "julio",
        "08": "agosto",
        "09": "septiembre",
        "10": "octubre",
        "11": "noviembre",
        "12": "diciembre",
    }
    return meses.get(str(mes).split("-")[-1], str(mes))


def valor_porcentaje(valor):
    return "—" if pd.isna(valor) else f"{valor:.1f}%"


def desglose_csat(csat, total):
    if pd.isna(csat) or not total:
        return 0, 0

    positivas = round(float(csat) * int(total) / 100)
    positivas = min(max(positivas, 0), int(total))
    return positivas, int(total) - positivas


def calcular_proyecciones_csat(csat, total):
    if pd.isna(csat) or pd.isna(total) or int(total) <= 0:
        return pd.DataFrame()

    total = int(total)
    positivas, _ = desglose_csat(csat, total)
    escenarios = []

    for cantidad in (1, 2, 3):
        total_proyectado = total + cantidad
        csat_positivo = (
            (positivas + cantidad) / total_proyectado
        ) * 100
        csat_negativo = (positivas / total_proyectado) * 100

        escenarios.append({
            "Escenario": (
                f"+{cantidad} positiva"
                if cantidad == 1
                else f"+{cantidad} positivas"
            ),
            "CSAT proyectado": csat_positivo,
            "Cambio vs actual": csat_positivo - float(csat),
        })
        escenarios.append({
            "Escenario": (
                f"+{cantidad} negativa"
                if cantidad == 1
                else f"+{cantidad} negativas"
            ),
            "CSAT proyectado": csat_negativo,
            "Cambio vs actual": csat_negativo - float(csat),
        })

    return pd.DataFrame(escenarios)


def positivas_para_meta(total, positivas):
    if not total:
        return 0

    meta = META_CSAT / 100
    x = 0

    while True:
        if (positivas + x) / (total + x) >= meta:
            return x
        x += 1

try:
    capturas = cargar_capturas()
except Exception:
    st.error("No fue posible recibir las señales.")
    st.stop()

if capturas.empty:
    st.info("Todavía no hay señales para mostrar.")
    st.stop()

mes_actual = capturas["mes"].max()
capturas_mes = capturas[capturas["mes"] == mes_actual].copy()
ultima = capturas_mes.iloc[-1]

csat_actual = ultima.get("csat")
muestras = ultima.get("csat_respuestas")
muestras = 0 if pd.isna(muestras) else int(muestras)
positivas, no_positivas = desglose_csat(csat_actual, muestras)
proyecciones = calcular_proyecciones_csat(csat_actual, muestras)

csat_anterior = None
if len(capturas_mes) > 1:
    valor_anterior = capturas_mes.iloc[-2].get("csat")
    if not pd.isna(valor_anterior):
        csat_anterior = float(valor_anterior)

if pd.isna(csat_actual) or csat_anterior is None:
    cambio_csat = None
    cambio_texto = "Sin señal anterior"
    cambio_clase = "pulse-neutral"
elif float(csat_actual) > csat_anterior:
    cambio_csat = float(csat_actual) - csat_anterior
    cambio_texto = f"Señal anterior · ↑ +{cambio_csat:.1f} pp"
    cambio_clase = "pulse-positive"
elif float(csat_actual) < csat_anterior:
    cambio_csat = float(csat_actual) - csat_anterior
    cambio_texto = f"Señal anterior · ↓ {cambio_csat:.1f} pp"
    cambio_clase = "pulse-negative"
else:
    cambio_csat = 0.0
    cambio_texto = "Señal anterior · sin cambio"
    cambio_clase = "pulse-neutral"

if proyecciones.empty:
    proxima_positiva = None
    proxima_negativa = None
else:
    proxima_positiva = proyecciones.iloc[0]["CSAT proyectado"]
    proxima_negativa = proyecciones.iloc[1]["CSAT proyectado"]

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

if pd.isna(csat_actual):
    resumen_meta = f"El horizonte está en {META_CSAT:.0f}%."
elif meta_alcanzada:
    resumen_meta = "Ya estás en el horizonte."
else:
    resumen_meta = (
        f"Faltan {faltantes_positivas} experiencias positivas "
        "para llegar al horizonte."
    )

ultima_colombia = fecha_colombia(ultima["timestamp_captura"])
ultima_senal_texto = formatear_ultima_senal(
    ultima["timestamp_captura"]
)
posicion_actual = (
    0
    if pd.isna(csat_actual)
    else min(max(float(csat_actual), 0), 100)
)
puntos_experiencias = (
    '<span class="experience-dot experience-positive"></span>' * positivas
    + '<span class="experience-dot experience-other"></span>' * no_positivas
)

st.markdown(
    f"""
    <!-- Portada silenciosa: orienta sin controles manuales. -->
    <div class="faro-header">
        <div class="faro-brand">FARO 80</div>
        <div class="faro-signal">
            Última señal: {ultima_senal_texto}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="pulse-card">
        <div class="pulse-kicker">Estás aquí</div>
        <div class="pulse-main">
            <div class="pulse-value">{valor_porcentaje(csat_actual)}</div>
            <div class="pulse-delta {cambio_clase}">{cambio_texto}</div>
        </div>
        <div class="horizon-map">
            <div class="horizon-labels">
                <span>Posición actual</span>
                <span>Horizonte · {META_CSAT:.0f}%</span>
            </div>
            <div class="horizon-track">
                <div class="horizon-progress" style="width: {posicion_actual:.1f}%"></div>
                <div class="horizon-marker" style="left: {posicion_actual:.1f}%"></div>
                <div class="horizon-target"></div>
            </div>
        </div>
        <div class="pulse-meta">{resumen_meta}</div>
        <div class="experiences">
            <div class="experiences-title">
                {muestras} experiencias registradas
            </div>
            <div class="experience-dots">{puntos_experiencias}</div>
            <div class="experience-legend">
                {positivas} positivas · {no_positivas} otras
            </div>
        </div>
        <div class="routes-title">Posibles rumbos</div>
        <div class="pulse-chip-grid">
            <div class="pulse-chip pulse-chip-positive">
                <div class="pulse-chip-label">Próxima experiencia positiva</div>
                <div class="pulse-chip-value">{
                    "—" if proxima_positiva is None else f"{proxima_positiva:.1f}%"
                }</div>
            </div>
            <div class="pulse-chip pulse-chip-negative">
                <div class="pulse-chip-label">Próxima experiencia no positiva</div>
                <div class="pulse-chip-value">{
                    "—" if proxima_negativa is None else f"{proxima_negativa:.1f}%"
                }</div>
            </div>
        </div>
        <div class="pulse-meta">
            Una experiencia mueve el recorrido, pero no lo define.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()
# La travesia aparece primero para mantener la narrativa de recorrido.
st.subheader(f"Travesía de {nombre_mes(mes_actual)}")
st.caption(
    f"{len(capturas_mes)} "
    f"{'señal' if len(capturas_mes) == 1 else 'señales'} en el recorrido"
)

if capturas_mes["csat"].notna().sum() > 1:
    grafico = capturas_mes.copy()
    grafico["timestamp_colombia"] = grafico["timestamp_captura"].dt.tz_convert(
        ZONA_COLOMBIA
    )
    st.line_chart(
        grafico.set_index("timestamp_colombia")[["csat"]],
        color=["#7c8cff"],
        height=350,
        y_label="CSAT",
        x_label="Señal",
        **ANCHO_STRETCH,
    )
else:
    st.info("La travesía aparecerá cuando existan al menos dos señales.")

tabla = capturas_mes.sort_values("timestamp_captura", ascending=False).copy()
tabla["Señal"] = tabla["timestamp_captura"].apply(formatear_fecha)
tabla["CSAT"] = tabla["csat"].apply(valor_porcentaje)
tabla["Experiencias"] = tabla["csat_respuestas"].fillna(0).astype(int)
desgloses = tabla.apply(
    lambda fila: desglose_csat(fila["csat"], fila["Experiencias"]),
    axis=1,
)
tabla["Positivas"] = desgloses.apply(lambda valor: valor[0])
tabla["No positivas"] = desgloses.apply(lambda valor: valor[1])

with st.expander("Bitácora", expanded=False):
    # Detalle tecnico plegado: disponible sin competir con la portada.
    st.dataframe(
        tabla[
            ["Señal", "CSAT", "Positivas", "No positivas", "Experiencias"]
        ],
        hide_index=True,
        column_config={
            "Señal": st.column_config.TextColumn("Señal"),
            "CSAT": st.column_config.TextColumn("CSAT"),
            "Positivas": st.column_config.NumberColumn(
                "Positivas",
                format="%d",
            ),
            "No positivas": st.column_config.NumberColumn(
                "Otras",
                format="%d",
            ),
            "Experiencias": st.column_config.NumberColumn(
                "Experiencias",
                format="%d",
            ),
        },
        **ANCHO_STRETCH,
    )
    st.caption(
        "Cada señal conserva la posición observada y las experiencias "
        "que formaron ese momento del recorrido."
    )

with st.expander("Otros rumbos", expanded=False):
    # Escenarios compactos; los calculos vienen de la misma tabla de proyecciones.
    if proyecciones.empty:
        st.warning(
            "No hay experiencias suficientes para calcular otros rumbos."
        )
    else:
        filas_rumbos = []
        for indice, rumbo in proyecciones.iterrows():
            cantidad = (indice // 2) + 1
            es_positivo = indice % 2 == 0
            tipo_experiencia = (
                "experiencia positiva"
                if cantidad == 1 and es_positivo
                else "experiencias positivas"
                if es_positivo
                else "otra experiencia"
                if cantidad == 1
                else "otras experiencias"
            )
            clase_punto = (
                "route-dot-positive"
                if es_positivo
                else "route-dot-other"
            )
            puntos = (
                f'<span class="route-dot {clase_punto}"></span>' * cantidad
            )
            filas_rumbos.append(
                '<div class="route-row">'
                '<div>'
                '<div class="route-heading">'
                f'<span class="route-name">+{cantidad} '
                f'{tipo_experiencia}</span>'
                f'<span class="route-dots">{puntos}</span>'
                '</div>'
                '</div>'
                f'<div class="route-value">'
                f'{rumbo["CSAT proyectado"]:.1f}%'
                '</div>'
                '</div>'
            )
        st.markdown(
            f'<div class="route-list">{"".join(filas_rumbos)}</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Cada experiencia abre un rumbo posible desde la señal actual."
        )

with st.expander("Otras señales", expanded=False):
    # Resolved, NPS e historico quedan como contexto secundario.
    resolved_muestras = int(ultima.get("resolved_respuestas") or 0)
    nps_muestras = int(ultima.get("nps_respuestas") or 0)

    complementaria_1, complementaria_2 = st.columns(2)
    with complementaria_1:
        st.metric("Resolved", valor_porcentaje(ultima.get("resolved")))
        st.caption(f"{resolved_muestras} experiencias de Resolved")

    with complementaria_2:
        st.metric(
            "NPS",
            "—" if pd.isna(ultima.get("nps")) else f"{ultima.get('nps'):.1f}",
        )
        st.caption(f"{nps_muestras} experiencias de NPS")

    st.caption("Recorrido mensual")
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
    historico["Experiencias"] = (
        historico["csat_respuestas"].fillna(0).astype(int)
    )

    st.markdown(
        '<div class="monthly-table-anchor"></div>',
        unsafe_allow_html=True,
    )
    st.dataframe(
        historico[["Mes", "CSAT", "Experiencias", "Resolved", "NPS"]],
        hide_index=True,
        column_config={
            "Experiencias": st.column_config.NumberColumn(
                "Exp.",
                format="%d",
            ),
            "Resolved": st.column_config.TextColumn("Res."),
        },
        **ANCHO_STRETCH,
    )
