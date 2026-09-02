import streamlit as st
import pandas as pd

st.set_page_config(page_title="Monitoraggio ESP32 BLE", layout="wide")

st.title("🛡️ Dashboard Monitoraggio BLE")

st.subheader("Dispositivi Autorizzati (Whitelist)")
whitelist_data = [
    {"Dispositivo": "Dispositivo 1", "MAC Address": "1c:3d:48:d6:f1:f0", "Stato": "Autorizzato"},
    {"Dispositivo": "Dispositivo 2", "MAC Address": "de:cd:2f:73:96:d3", "Stato": "Autorizzato"},
    {"Dispositivo": "Dispositivo 3", "MAC Address": "12:fc:96:71:ac:84", "Stato": "Autorizzato"}
]
df_whitelist = pd.DataFrame(whitelist_data)
st.dataframe(df_whitelist, use_container_width=True)

st.subheader("Stato Rilevamento Intrusione")
st.info("Isteresi attiva: Ingresso 5m - 7m | Reset > 15m")
