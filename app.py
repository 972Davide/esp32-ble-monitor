import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from streamlit_autorun import autorun

# Aggiorna automaticamente la pagina ogni 5000 millisecondi (5 secondi)
autorun(interval=5000, key="ble_auto_refresh")

st.set_page_config(page_title="Monitoraggio BLE ESP32 - Advanced", layout="wide")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyxdcInWY2bY0aJEnHzmxamgQ6qo3I_CnI4quqypDoMrTOMoYuL16pQyVy8JsExb93K/exec"

st.title("🛡️ Dashboard Monitoraggio & Analytics BLE")

# -------------------------------------------------------------------------
# WHITELIST DISPOSITIVI
# -------------------------------------------------------------------------
with st.expander("📋 Dispositivi Autorizzati (Whitelist)", expanded=False):
    whitelist_data = {
        "Dispositivo": ["Dispositivo 1", "Dispositivo 2", "Dispositivo 3"],
        "MAC Address": ["1c:3d:48:d6:f1:f0", "de:cd:2f:73:96:d3", "12:fc:96:71:ac:84"],
        "Stato": ["Autorizzato", "Autorizzato", "Autorizzato"]
    }
    st.table(pd.DataFrame(whitelist_data))

# -------------------------------------------------------------------------
# FUNZIONE RECUPERO DATI (Con timeout esteso a 15s)
# -------------------------------------------------------------------------
@st.cache_data(ttl=5) # Mantiene la cache per 5 secondi per velocizzare il caricamento
def get_historical_data():
    try:
        headers = {"Accept": "application/json"}
        # Timeout aumentato a 15 secondi per evitare l'errore di Read Timeout
        response = requests.get(APPS_SCRIPT_URL, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)
                df["distance"] = pd.to_numeric(df["distance"], errors='coerce').fillna(0)
                df["rssi"] = pd.to_numeric(df["rssi"], errors='coerce').fillna(0)
                return df
            elif isinstance(data, dict):
                return pd.DataFrame([data])
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
    return pd.DataFrame()

df = get_historical_data()

# -------------------------------------------------------------------------
# METRICHE ISTANTANEE (ULTIMO EVENTO)
# -------------------------------------------------------------------------
st.subheader("📍 Stato Attuale in Tempo Reale")

if not df.empty:
    latest = df.iloc[-1]
    
    col1, col2, col3, col4 = st.columns(4)
    status_text = str(latest.get("status", "N/A"))
    
    if "ALLARME" in status_text.upper():
        col1.metric("Stato Allarme", status_text, delta="⚠️ Intrusione", delta_color="inverse")
    else:
        col1.metric("Stato Allarme", status_text)

    col2.metric("MAC Rilevato", latest.get("mac", "N/A"))
    col3.metric("Distanza Stimata", f"{latest.get('distance', 0)} m")
    col4.metric("RSSI", f"{latest.get('rssi', 0)} dBm")
    
    st.caption(f"Ultima sincronizzazione: {latest.get('timestamp', 'N/A')}")
else:
    st.warning("Nessun dato disponibile da Google Sheets.")

st.divider()

# -------------------------------------------------------------------------
# GRAFICI & ANALISI STORICA
# -------------------------------------------------------------------------
if not df.empty and len(df) > 1:
    st.subheader("📊 Grafici e Trend degli Eventi")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("##### 📈 Andamento Distanza e RSSI nel Tempo")
        fig_dist = px.line(
            df, 
            x="timestamp", 
            y="distance", 
            color="status",
            markers=True,
            labels={"distance": "Distanza (m)", "timestamp": "Ora Evento"},
            title="Variazione Distanza Bersaglio"
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    with col_chart2:
        st.markdown("##### 🍩 Distribuzione Rilevamenti per MAC Address")
        fig_mac = px.pie(
            df, 
            names="mac", 
            title="Frequenza di scansione per Dispositivo",
            hole=0.4
        )
        st.plotly_chart(fig_mac, use_container_width=True)

    st.divider()

    # -------------------------------------------------------------------------
    # TABELLA ULTIMI EVENTI REGISTRATI
    # -------------------------------------------------------------------------
    st.subheader("📜 Registro Ultimi Eventi")
    
    filtro_stato = st.multiselect(
        "Filtra per Stato Evento:",
        options=df["status"].unique(),
        default=df["status"].unique()
    )
    
    df_filtered = df[df["status"].isin(filtro_stato)]
    st.dataframe(df_filtered.iloc[::-1], use_container_width=True)

# Pulsante di Aggiornamento
if st.button("🔄 Aggiorna Dashboard"):
    st.cache_data.clear()
    st.rerun()
