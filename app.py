# app.py

import base64
import hashlib
import hmac
import html
import json
import os
import secrets as token_secrets
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import extra_streamlit_components as stx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2 import id_token
from pymongo import MongoClient


META_CSAT = 80.0
APP_BASE_URL_DEFAULT = "https://slavxx.streamlit.app"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH_STATE_TTL_SECONDS = 600
SESSION_COOKIE_NAME = "faro80_session"
SESSION_COOKIE_DAYS = 7
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

    .model-card {
        background:
            radial-gradient(
                circle at 18% 12%,
                rgba(105, 200, 156, 0.10),
                transparent 32%
            ),
            #10141f;
        border: 1px solid #252b3b;
        border-radius: 1rem;
        margin: 0 0 1.1rem;
        padding: 1rem;
    }

    .model-kicker {
        color: #69c89c;
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0.11em;
        text-transform: uppercase;
    }

    .model-title {
        color: #f2f0ea;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin-top: 0.35rem;
    }

    .model-copy {
        color: #9299a8;
        font-size: 0.82rem;
        margin-top: 0.3rem;
    }

    .model-grid {
        display: grid;
        gap: 0.55rem;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-top: 0.9rem;
    }

    .model-stat {
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid #252b3b;
        border-radius: 0.75rem;
        padding: 0.65rem;
    }

    .model-stat-value {
        color: #f2f0ea;
        font-size: 1.25rem;
        font-weight: 750;
        letter-spacing: -0.04em;
    }

    .model-stat-label {
        color: #9299a8;
        font-size: 0.72rem;
        margin-top: 0.1rem;
    }

    .model-bar {
        background: rgba(219, 123, 131, 0.20);
        border-radius: 999px;
        height: 5px;
        margin-top: 0.85rem;
        overflow: hidden;
    }

    .model-bar-positive {
        background: #69c89c;
        height: 5px;
    }

    .model-month-row,
    .model-review-card {
        background: rgba(255, 255, 255, 0.025);
        border: 1px solid #252b3b;
        border-radius: 0.75rem;
        margin-bottom: 0.55rem;
        padding: 0.7rem 0.8rem;
    }

    .model-month-row {
        align-items: center;
        display: grid;
        gap: 0.7rem;
        grid-template-columns: minmax(0, 1fr) auto;
    }

    .model-month-name,
    .model-review-date {
        color: #f2f0ea;
        font-size: 0.86rem;
        font-weight: 650;
    }

    .model-month-detail,
    .model-review-detail {
        color: #9299a8;
        font-size: 0.76rem;
        margin-top: 0.15rem;
    }

    .model-month-balance {
        display: grid;
        gap: 0.32rem;
        margin-top: 0.45rem;
    }

    .model-balance-line {
        align-items: center;
        display: flex;
        gap: 0.45rem;
        min-width: 0;
    }

    .model-balance-label {
        color: #9299a8;
        flex: 0 0 auto;
        font-size: 0.74rem;
        min-width: 6.2rem;
    }

    .model-balance-dots {
        display: flex;
        flex-wrap: wrap;
        gap: 0.22rem;
    }

    .model-balance-dot {
        border-radius: 50%;
        height: 0.38rem;
        width: 0.38rem;
    }

    .model-balance-positive {
        background: #69c89c;
        box-shadow: 0 0 0 2px rgba(105, 200, 156, 0.08);
    }

    .model-balance-other {
        background: #555d70;
    }

    .model-month-rate {
        color: #f2f0ea;
        font-size: 1rem;
        font-weight: 750;
        white-space: nowrap;
    }

    .model-review-card {
        border-left: 3px solid #555d70;
    }

    .model-review-card.model-review-green {
        border-left-color: #69c89c;
    }

    .model-review-card.model-review-red {
        border-left-color: #db7b83;
    }

    .model-review-text {
        color: #d7d9e0;
        font-size: 0.82rem;
        margin-top: 0.45rem;
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

        .model-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }

        .model-month-row {
            align-items: flex-start;
            grid-template-columns: 1fr;
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
            margin-bottom: 0.25rem;
        }



    }

    .auth-card {
        background: #121622;
        border: 1px solid #252b3b;
        border-radius: 1rem;
        margin-top: 2rem;
        padding: 1.1rem;
    }

    .auth-title {
        color: #f2f0ea;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin-bottom: 0.35rem;
    }

    .auth-copy {
        color: #9299a8;
        font-size: 0.88rem;
        margin-bottom: 0.8rem;
    }

    .auth-login-button {
        align-items: center;
        background: #f2b95d;
        border: 1px solid rgba(242, 185, 93, 0.55);
        border-radius: 0.65rem;
        color: #11131a !important;
        display: inline-flex;
        font-size: 0.9rem;
        font-weight: 700;
        justify-content: center;
        margin-top: 0.85rem;
        padding: 0.55rem 0.9rem;
        text-decoration: none !important;
    }

    .auth-login-button:hover {
        background: #ffd07a;
        border-color: #ffd07a;
        color: #11131a !important;
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


cookie_manager = stx.CookieManager()


def obtener_config(nombre, default=None):
    load_dotenv()
    valor = os.getenv(nombre)

    if valor:
        return valor

    try:
        valor = st.secrets.get(nombre)
    except Exception:
        valor = None

    return valor or default


def _base64_urlsafe(data):
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _base64_urlsafe_decode(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def crear_oauth_state(cookie_secret):
    payload = {
        "iat": int(time.time()),
        "nonce": token_secrets.token_urlsafe(18),
    }
    payload_b64 = _base64_urlsafe(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    firma = hmac.new(
        cookie_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_base64_urlsafe(firma)}"


def crear_cookie_sesion(usuario, cookie_secret):
    payload = {
        "email": usuario.get("email"),
        "name": usuario.get("name", ""),
        "exp": int(time.time()) + SESSION_COOKIE_DAYS * 24 * 60 * 60,
    }
    payload_b64 = _base64_urlsafe(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    firma = hmac.new(
        cookie_secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{payload_b64}.{_base64_urlsafe(firma)}"


def validar_cookie_sesion(valor, cookie_secret, allowed_email):
    if not valor:
        return None

    try:
        payload_b64, firma_b64 = valor.split(".", 1)
        firma_esperada = hmac.new(
            cookie_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        firma_recibida = _base64_urlsafe_decode(firma_b64)

        if not hmac.compare_digest(firma_esperada, firma_recibida):
            return None

        payload = json.loads(_base64_urlsafe_decode(payload_b64))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None

        if payload.get("email") != allowed_email:
            return None

        return {
            "email": payload.get("email"),
            "name": payload.get("name", ""),
        }
    except Exception:
        return None


def guardar_cookie_sesion(usuario, cookie_secret):
    cookie_manager.set(
        SESSION_COOKIE_NAME,
        crear_cookie_sesion(usuario, cookie_secret),
        expires_at=datetime.now() + timedelta(days=SESSION_COOKIE_DAYS),
    )


def restaurar_cookie_sesion(cookie_secret, allowed_email):
    if st.session_state.pop("logout_en_proceso", False):
        return None

    cookie_sesion = cookie_manager.get(SESSION_COOKIE_NAME)

    if not cookie_sesion and not st.session_state.get("cookie_lookup_done"):
        # El componente de cookies necesita un ciclo del navegador para hidratarse.
        st.session_state["cookie_lookup_done"] = True
        st.rerun()

    usuario = validar_cookie_sesion(
        cookie_sesion,
        cookie_secret,
        allowed_email,
    )

    if usuario:
        st.session_state["usuario_google"] = usuario

    return usuario


def borrar_cookie_sesion():
    try:
        cookie_manager.delete(SESSION_COOKIE_NAME)
    except Exception:
        try:
            cookie_manager.set(
                SESSION_COOKIE_NAME,
                "",
                expires_at=datetime.now() - timedelta(days=1),
            )
        except Exception:
            pass


def cerrar_sesion():
    st.session_state.pop("usuario_google", None)
    st.session_state["cookie_lookup_done"] = True
    st.session_state["logout_en_proceso"] = True
    borrar_cookie_sesion()
    limpiar_query_params()
    st.rerun()


def validar_oauth_state(state, cookie_secret):
    try:
        payload_b64, firma_b64 = state.split(".", 1)
        firma_esperada = hmac.new(
            cookie_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        firma_recibida = _base64_urlsafe_decode(firma_b64)

        if not hmac.compare_digest(firma_esperada, firma_recibida):
            return False

        payload = json.loads(_base64_urlsafe_decode(payload_b64))
        return int(time.time()) - int(payload.get("iat", 0)) <= OAUTH_STATE_TTL_SECONDS
    except Exception:
        return False


def construir_url_login(client_id, redirect_uri, cookie_secret):
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": crear_oauth_state(cookie_secret),
        "prompt": "select_account",
        "access_type": "online",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def intercambiar_codigo_google(code, client_id, client_secret, redirect_uri):
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    request = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def limpiar_query_params():
    try:
        st.query_params.clear()
    except Exception:
        pass


def obtener_query_param(nombre):
    valor = st.query_params.get(nombre)
    if isinstance(valor, list):
        return valor[0] if valor else None
    return valor


def mostrar_login_google(auth_url):
    st.markdown(
        """
        <div class="faro-header">
            <div class="faro-brand">FARO 80</div>
            <div class="faro-signal">Acceso privado</div>
        </div>
        <div class="auth-card">
            <div class="auth-title">Entrar con Google</div>
            <div class="auth-copy">
                Google confirma la identidad antes de abrir Faro 80;
                la app no recibe tu contraseña.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.link_button("Entrar con Google", auth_url, type="primary")
    st.stop()

def requerir_login_google():
    client_id = obtener_config("GOOGLE_CLIENT_ID")
    client_secret = obtener_config("GOOGLE_CLIENT_SECRET")
    allowed_email = obtener_config("ALLOWED_EMAIL", "eliecer.ruiz@udea.edu.co")
    cookie_secret = obtener_config("COOKIE_SECRET")
    redirect_uri = obtener_config("APP_BASE_URL", APP_BASE_URL_DEFAULT).rstrip("/")

    faltantes = [
        nombre
        for nombre, valor in {
            "GOOGLE_CLIENT_ID": client_id,
            "GOOGLE_CLIENT_SECRET": client_secret,
            "ALLOWED_EMAIL": allowed_email,
            "COOKIE_SECRET": cookie_secret,
        }.items()
        if not valor
    ]

    if faltantes:
        st.error(
            "Faltan secrets para habilitar el acceso privado: "
            + ", ".join(faltantes)
        )
        st.stop()

    usuario = st.session_state.get("usuario_google")
    if usuario:
        if usuario.get("email") == allowed_email:
            return usuario
        st.error("Acceso no autorizado para esta cuenta.")
        st.stop()

    usuario = restaurar_cookie_sesion(cookie_secret, allowed_email)
    if usuario:
        return usuario

    error = obtener_query_param("error")
    if error:
        limpiar_query_params()
        st.error(f"Google no autorizo el acceso: {error}")
        st.stop()

    code = obtener_query_param("code")
    state = obtener_query_param("state")

    if code:
        if not state or not validar_oauth_state(state, cookie_secret):
            limpiar_query_params()
            st.error("No fue posible validar la sesion de acceso.")
            st.stop()

        try:
            token_response = intercambiar_codigo_google(
                code,
                client_id,
                client_secret,
                redirect_uri,
            )
            info = id_token.verify_oauth2_token(
                token_response["id_token"],
                GoogleRequest(),
                client_id,
            )
        except Exception:
            limpiar_query_params()
            st.error("No fue posible confirmar tu identidad con Google.")
            st.stop()

        email = info.get("email")
        email_verified = bool(info.get("email_verified"))

        if not email_verified or email != allowed_email:
            limpiar_query_params()
            st.error("Acceso no autorizado para esta cuenta.")
            st.stop()

        usuario = {
            "email": email,
            "name": info.get("name", ""),
        }
        st.session_state["usuario_google"] = usuario
        guardar_cookie_sesion(usuario, cookie_secret)
        limpiar_query_params()
        st.rerun()

    mostrar_login_google(
        construir_url_login(client_id, redirect_uri, cookie_secret),
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


@st.cache_resource
def obtener_coleccion_reviews_historicas():
    # Dataset independiente: no se mezcla con las capturas vivas de Faro 80.
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
    return cliente["slave"]["reviews_historicas"]


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


@st.cache_data(ttl=300)
def cargar_reviews_historicas():
    campos = {
        "_id": 0,
        "review_key": 1,
        "dataset": 1,
        "posted": 1,
        "posted_dt": 1,
        "sent": 1,
        "mes": 1,
        "month_name": 1,
        "color": 1,
        "classification_reason": 1,
        "comment": 1,
        "excellence": 1,
        "improve": 1,
        "resolved": 1,
        "resolution_comment": 1,
        "channel": 1,
        "brand": 1,
        "area": 1,
        "contact_id": 1,
        "area_type": 1,
        "issue_type_1": 1,
        "tags": 1,
        "agent": 1,
        "has_comment": 1,
        "has_resolution_comment": 1,
        "excellence_count": 1,
        "improve_count": 1,
    }
    documentos = list(
        obtener_coleccion_reviews_historicas()
        .find({"dataset": "driver_applicant_support_2025"}, campos)
        .sort("posted_dt", -1)
    )

    if not documentos:
        return pd.DataFrame(columns=list(campos.keys())[1:])

    df = pd.DataFrame(documentos)
    df["posted_dt"] = pd.to_datetime(df["posted_dt"], errors="coerce")
    return (
        df.dropna(subset=["posted_dt", "mes"])
        .sort_values("posted_dt", ascending=False)
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


def nombre_mes_largo(mes):
    valor = str(mes)
    nombre = nombre_mes(valor).capitalize()
    year = valor.split("-")[0] if "-" in valor else ""
    return f"{nombre} {year}".strip()


def valor_texto(valor, fallback="Sin registro"):
    if valor is None or pd.isna(valor):
        return fallback
    texto = str(valor).strip()
    return texto or fallback


def unir_lista(valor):
    if isinstance(valor, list):
        return ", ".join(str(item) for item in valor if item)
    if valor is None or pd.isna(valor):
        return ""
    return str(valor)


def formatear_fecha_simple(valor):
    if pd.isna(valor):
        return "Sin fecha"
    fecha = pd.Timestamp(valor)
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


def puntos_balance(cantidad, clase):
    cantidad = int(cantidad or 0)
    return f'<span class="model-balance-dot {clase}"></span>' * cantidad


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

usuario_google = requerir_login_google()

try:
    capturas = cargar_capturas()
except Exception:
    st.error("No fue posible recibir las señales.")
    st.stop()

try:
    reviews_historicas = cargar_reviews_historicas()
except Exception:
    reviews_historicas = pd.DataFrame()

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

if not reviews_historicas.empty:
    total_reviews = len(reviews_historicas)
    green_reviews = int((reviews_historicas["color"] == "green").sum())
    red_reviews = int((reviews_historicas["color"] == "red").sum())
    positive_rate = (
        (green_reviews / total_reviews) * 100
        if total_reviews
        else 0
    )
    bar_width = min(max(positive_rate, 0), 100)

    st.markdown(
        f"""
        <div class="model-card">
            <div class="model-kicker">Modelo replicable</div>
            <div class="model-title">
                Piloto histórico · DAS 2025
            </div>
            <div class="model-copy">
                Una muestra completa para convertir feedback en diagnóstico
                auditable, antes de replicarlo sobre conversaciones actuales.
            </div>
            <div class="model-grid">
                <div class="model-stat">
                    <div class="model-stat-value">{total_reviews}</div>
                    <div class="model-stat-label">experiencias</div>
                </div>
                <div class="model-stat">
                    <div class="model-stat-value">{green_reviews}</div>
                    <div class="model-stat-label">positivas</div>
                </div>
                <div class="model-stat">
                    <div class="model-stat-value">{red_reviews}</div>
                    <div class="model-stat-label">no positivas</div>
                </div>
                <div class="model-stat">
                    <div class="model-stat-value">{positive_rate:.1f}%</div>
                    <div class="model-stat-label">señal positiva</div>
                </div>
            </div>
            <div class="model-bar">
                <div class="model-bar-positive" style="width: {bar_width:.1f}%"></div>
            </div>
            <div class="model-copy">
                Dataset separado de Faro 80 actual; conserva comentarios,
                etiquetas, resolución, canal, caso y evidencia individual.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Modelo Replicable", expanded=False):
        resumen_mensual = (
            reviews_historicas
            .groupby("mes", as_index=False)
            .agg(
                experiencias=("review_key", "count"),
                green=("color", lambda serie: int((serie == "green").sum())),
                red=("color", lambda serie: int((serie == "red").sum())),
            )
            .sort_values("mes", ascending=False)
        )
        resumen_mensual["resultado"] = (
            resumen_mensual["green"]
            / resumen_mensual["experiencias"]
            * 100
        )

        filas_meses = []
        for _, fila_mes in resumen_mensual.iterrows():
            total_mes = int(fila_mes["experiencias"])
            positivas_mes = int(fila_mes["green"])
            no_positivas_mes = int(fila_mes["red"])
            filas_meses.append(
                '<div class="model-month-row">'
                '<div>'
                f'<div class="model-month-name">{nombre_mes_largo(fila_mes["mes"])}</div>'
                f'<div class="model-month-detail">{total_mes} experiencias</div>'
                '<div class="model-month-balance">'
                '<div class="model-balance-line">'
                f'<span class="model-balance-label">{positivas_mes}</span>'
                '<span class="model-balance-dots">'
                f'{puntos_balance(positivas_mes, "model-balance-positive")}'
                '</span>'
                '</div>'
                '<div class="model-balance-line">'
                f'<span class="model-balance-label">{no_positivas_mes}</span>'
                '<span class="model-balance-dots">'
                f'{puntos_balance(no_positivas_mes, "model-balance-other")}'
                '</span>'
                '</div>'
                '</div>'
                '</div>'
                f'<div class="model-month-rate">{fila_mes["resultado"]:.1f}%</div>'
                '</div>'
            )

        st.markdown(
            f'<div class="model-month-list">{"".join(filas_meses)}</div>',
            unsafe_allow_html=True,
        )

        meses_disponibles = ["__placeholder__"] + resumen_mensual["mes"].tolist()
        mes_seleccionado = st.selectbox(
            "Explorar evidencia por mes",
            meses_disponibles,
            format_func=lambda mes: (
                "Selecciona un mes"
                if mes == "__placeholder__"
                else nombre_mes_largo(mes)
            ),
            index=0,
        )

        if mes_seleccionado == "__placeholder__":
            st.caption(
                "Elige un mes para abrir sus experiencias individuales."
            )
        else:
            casos_mes = (
                reviews_historicas[
                    reviews_historicas["mes"] == mes_seleccionado
                ]
                .sort_values("posted_dt", ascending=False)
            )

            tarjetas = []
            for _, review in casos_mes.iterrows():
                color = "green" if review.get("color") == "green" else "red"
                comentario = valor_texto(
                    review.get("comment"),
                    valor_texto(
                        review.get("resolution_comment"),
                        "No comments by the Applicant.",
                    ),
                )
                etiquetas = unir_lista(review.get("excellence"))
                mejoras = unir_lista(review.get("improve"))
                senales = etiquetas or mejoras or valor_texto(
                    review.get("classification_reason")
                )
                detalle = valor_texto(review.get("tags"), "")
                tarjetas.append(
                    f'<div class="model-review-card model-review-{color}">'
                    f'<div class="model-review-date">'
                    f'{html.escape(formatear_fecha_simple(review.get("posted_dt")))}'
                    '</div>'
                    f'<div class="model-review-detail">{html.escape(detalle)}</div>'
                    f'<div class="model-review-text">{html.escape(comentario)}</div>'
                    f'<div class="model-review-detail">{html.escape(senales)}</div>'
                    '</div>'
                )

            st.markdown(
                "".join(tarjetas),
                unsafe_allow_html=True,
            )
            st.caption(
                "Experiencias del mes seleccionado, ordenadas de la más "
                "reciente a la más antigua."
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
