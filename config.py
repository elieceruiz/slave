# config.py

import os
from dotenv import load_dotenv

def get_env(key: str):

    # Precedencia: secretos administrados por plataforma antes que .env local.
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass

    load_dotenv()
    return os.getenv(key)
