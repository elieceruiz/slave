# config.py

import os
from dotenv import load_dotenv

def get_env(key: str):

    # 1. Streamlit Cloud
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except:
        pass

    # 2. Local (.env)
    load_dotenv()
    return os.getenv(key)