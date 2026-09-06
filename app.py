import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

# 1. Configurazione della pagina (deve essere la prima istruzione Streamlit)
st.set_page_config(page_title="Monitoraggio BLE ESP32 - Advanced", layout="wide")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyxdcInWY2bY0aJEnHzmxamgQ6qo3I_CnI4quqypDoMrTOMoYuL16pQyVy8JsExb93K/exec"

# -------------------------------------------------------------------------
# SIDEBAR - CONFIGURAZIONI E FILTRI
# -------------------------------------------------------------------------
st.sidebar.title("⚙️ Impostazioni Dashboard")
auto_refresh = st.sidebar.checkbox("Attiva Auto-Refresh Real-Time", value=True)
refresh_interval = st.sidebar.slider("Intervallo di aggiornamento (sec):", 3, 20, 5)

st.sidebar.divider()
st.sidebar.subheader("🔍 Filtri Dati")
filtro_notte = st.sidebar.checkbox("🌙 Solo fascia notturna (22:00 - 07:00)", value=False)
max_records = st.sidebar.slider("Numero massimo di eventi da analizzare:", 10, 500, 100)

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
# FUNZIONE RECUPERO DATI
# -------------------------------------------------------------------------
@st.cache_data(ttl=2)
def get_historical_data():
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(APPS_SCRIPT_URL, headers=headers, timeout=15, allow_redirects=True)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                df_res = pd.DataFrame(data)
                df_res["distance"] = pd.to_numeric(df_res["distance"], errors='coerce').fillna(0)
                df_res["rssi"] = pd.to_numeric(df_res["rssi"], errors='coerce').fillna(0)
                
                # Conversione Timestamp in Datetime reale
                df_res["dt"] = pd.to_datetime(df_res["timestamp"], format="%d/%m/%Y %H:%M:%S", errors='coerce')
                return df_res
            elif isinstance(data, dict):
                return pd.DataFrame([data])
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
    return pd.DataFrame()

df_raw = get_historical_data()

# Applicazione Filtro Orario Notturno (22:00 - 07:00)
if not df_raw.empty and "dt" in df_raw.columns:
    if filtro_notte:
        condizione_notte = (df_raw["dt"].dt.hour >= 22) | (df_raw["dt"].dt.hour < 7)
        df_filtered_time = df_raw[condizione_notte].copy()
    else:
        df_filtered_time = df_raw.copy()
    
    # Limita ai record scelti dall'utente
    df = df_filtered_time.tail(max_records)
else:
    df = df_raw

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
    st.warning("Nessun dato disponibile con i filtri selezionati.")

st.divider()

# -------------------------------------------------------------------------
# GRAFICI & ANALISI STORICA
# -------------------------------------------------------------------------
if not df.empty and len(df) > 1:
    st.subheader("📊 Grafici e Trend degli Eventi")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("##### 📈 Andamento Distanza nel Tempo")
        
        # Filtro per ordinare temporalmente l'asse X ed escludere le disconnessioni 0m
        df_chart = df.dropna(subset=["dt"]).sort_values("dt")
        df_valid_dist = df_chart[df_chart["distance"] > 0]

        color_map = {
            "ALLARME (5m-7m)": "#FF4B4B",
            "Reset (Fuori Portata)": "#00C0F2",
            "Reset (Disconnesso)": "#7E828A"
        }

        fig_dist = px.line(
            df_valid_dist, 
            x="dt", 
            y="distance", 
            color="status",
            markers=True,
            color_discrete_map=color_map,
            labels={"distance": "Distanza (m)", "dt": "Data e Ora"},
            title="Variazione Distanza Bersaglio"
        )
        fig_dist.update_xaxes(type='date', tickformat="%d/%m %H:%M")
        fig_dist.update_traces(marker=dict(size=7))
        fig_dist.update_layout(hovermode="x unified", margin=dict(l=20, r=20, t=40, b=20))

        st.plotly_chart(fig_dist, use_container_width=True)

    with col_chart2:
        st.markdown("##### 🏆 Ranking MAC Address (Dal più frequente)")
        mac_counts = df["mac"].value_counts().reset_index()
        mac_counts.columns = ["MAC Address", "Conteggio"]

        fig_mac = px.bar(
            mac_counts,
            x="Conteggio",
            y="MAC Address",
            orientation="h",
            text="Conteggio",
            color="Conteggio",
            color_continuous_scale="Reds",
            title="Frequenza Rilevamenti per MAC"
        )
        fig_mac.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig_mac, use_container_width=True)

    # -------------------------------------------------------------------------
    # TEMPI DI PERMANENZA (DWELL TIME)
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("⏱️ Tempi di Permanenza Dispositivi")

    df_calc = df.dropna(subset=["dt"]).sort_values("dt")
    if not df_calc.empty:
        permanenza = df_calc.groupby("mac").agg(
            Primo_Avvistamento=("dt", "min"),
            Ultimo_Avvistamento=("dt", "max"),
            Rilevazioni_Totali=("status", "count"),
            Distanza_Media=("distance", "mean"),
            Ultimo_Stato=("status", "last")
        ).reset_index()

        permanenza["Durata_Delta"] = permanenza["Ultimo_Avvistamento"] - permanenza["Primo_Avvistamento"]
        permanenza["Permanenza (Minuti)"] = (permanenza["Durata_Delta"].dt.total_seconds() / 60).round(1)
        permanenza["Distanza_Media"] = permanenza["Distanza_Media"].round(2)

        permanenza["Primo Avvistamento"] = permanenza["Primo_Avvistamento"].dt.strftime("%d/%m %H:%M:%S")
        permanenza["Ultimo Avvistamento"] = permanenza["Ultimo_Avvistamento"].dt.strftime("%d/%m %H:%M:%S")

        col_perm1, col_perm2 = st.columns([2, 1])

        with col_perm1:
            st.markdown("##### ⏳ Durata Permanenza per Dispositivo (Minuti)")
            fig_perm = px.bar(
                permanenza.sort_values("Permanenza (Minuti)", ascending=False),
                x="mac",
                y="Permanenza (Minuti)",
                color="Ultimo_Stato",
                text="Permanenza (Minuti)",
                labels={"mac": "MAC Address", "Permanenza (Minuti)": "Tempo Totale (min)"},
                title="Tempo Totale nel Raggio d'Azione"
            )
            fig_perm.update_traces(texttemplate='%{text} min', textposition='outside')
            st.plotly_chart(fig_perm, use_container_width=True)

        with col_perm2:
            st.markdown("##### 📌 Dettagli Permanenza")
            st.dataframe(
                permanenza[[
                    "mac", 
                    "Permanenza (Minuti)", 
                    "Distanza_Media", 
                    "Primo Avvistamento", 
                    "Ultimo Avvistamento"
                ]].rename(columns={
                    "mac": "MAC Address", 
                    "Distanza_Media": "Dist. Media (m)"
                }),
                use_container_width=True,
                hide_index=True
            )

    st.divider()

    # -------------------------------------------------------------------------
    # TABELLA EVENTI & ESPORTAZIONE DATI
    # -------------------------------------------------------------------------
    st.subheader("📜 Registro Ultimi Eventi")
    
    col_filter, col_export = st.columns([3, 1])
    
    with col_filter:
        filtro_stato = st.multiselect(
            "Filtra per Stato Evento:",
            options=df["status"].unique(),
            default=df["status"].unique()
        )
    
    df_filtered = df[df["status"].isin(filtro_stato)]
    
    with col_export:
        st.markdown(" ")
        csv_data = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Scarica Dati (CSV)",
            data=csv_data,
            file_name="storico_rilevamenti_ble.csv",
            mime="text/csv"
        )
    
    st.dataframe(df_filtered.iloc[::-1], use_container_width=True)

# -------------------------------------------------------------------------
# AUTO-REFRESH NATIVO
# -------------------------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_interval)
    st.cache_data.clear()
    st.rerun()
