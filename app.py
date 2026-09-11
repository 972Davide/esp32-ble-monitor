import streamlit as st
import pandas as pd
import re
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="BLE Scanner", page_icon="📡", layout="wide")
st_autorefresh(interval=5000, key="refresh")

st.title("📡 BLE Scanner & Device List")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

# --- RUBRICA NOMI PERSONALIZZATI (MAC -> Nome Chiaro) ---
DEVICE_ALIAS_MAP = {
    "03:e9:c5:2f:f1:b2": "Galaxy-A52",
    # Aggiungi qui altri MAC: "xx:xx:xx:xx:xx:xx": "Nome Dispositivo"
}

def get_friendly_name(mac, raw_name):
    clean_mac = str(mac).replace("-", ":").lower()
    if clean_mac in DEVICE_ALIAS_MAP:
        return DEVICE_ALIAS_MAP[clean_mac]
    if pd.notna(raw_name):
        cleaned = str(raw_name).strip()
        if cleaned and cleaned.lower() not in ['nan', 'none', '', 'sconosciuto']:
            return cleaned
    return f"Dispositivo [{clean_mac[-5:].upper()}]"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

df = load_data(SHEET_CSV_URL)

if df.empty:
    st.warning("Nessun dato nel Google Sheet o URL non valido.")
    st.stop()

# Pulizia e mappatura colonne
cols = list(df.columns)
c_time, c_name, c_mac, c_dist, c_event = cols[0], cols[1], cols[2], cols[3], cols[4] if len(cols) > 4 else None

df['friendly_name'] = [get_friendly_name(m, n) for m, n in zip(df[c_mac], df[c_name])]

st.subheader("📋 Lista Dispositivi Rilevati")
display_df = df.groupby(c_mac).last().reset_index()
display_df[c_name] = display_df['friendly_name']

st.dataframe(
    display_df[[c_time, c_name, c_mac, c_dist, c_event]].sort_values(by=c_dist, ascending=True),
    use_container_width=True
)
