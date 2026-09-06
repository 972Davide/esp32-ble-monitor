import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

st.set_page_config(page_title="Monitoraggio BLE ESP32 - Advanced", layout="wide")

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyxdcInWY2bY0aJEnHzmxamgQ6qo3I_CnI4quqypDoMrTOMoYuL16pQyVy8JsExb93K/exec"

# -------------------------------------------------------------------------
# SIDEBAR - CONFIGURAZIONE & FILTRI
# -------------------------------------------------------------------------
st.sidebar.title("⚙️ Impostazioni Dashboard")
auto_refresh = st.sidebar.checkbox("Attiva Auto-Refresh Real-Time", value=True)
refresh_interval = st.sidebar.slider("Intervallo di aggiornamento (sec):", 3, 20, 5)

st.sidebar.divider()
st.sidebar.subheader("🔍 Filtro Storico Dati")
max_records = st.sidebar.slider("Numero di ultimi eventi da analizzare:", 10, 200, 50)

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
                df = pd.DataFrame(data)
                df["distance"] = pd.to_numeric(df["distance"], errors='coerce').fillna(0)
                df["rssi"] = pd.to_numeric(df["rssi"], errors='coerce').fillna(0)
                return df
            elif isinstance(data, dict):
                return pd.DataFrame([data])
    except Exception as e:
        st.error(f"Errore caricamento dati: {e}")
    return pd.DataFrame()

df_raw = get_historical_data()

# Applica il limite massimo di record impostato nella sidebar
df = df_raw.tail(max_records) if not df_raw.empty else df_raw

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
        st.markdown("##### 📈 Andamento Distanza nel Tempo")
        
        # 1. Conversione del timestamp in vero formato Datetime per ordinare l'asse X
        df_chart = df.copy()
        df_chart["timestamp_dt"] = pd.to_datetime(df_chart["timestamp"], format="%d/%m/%Y %H:%M:%S", errors='coerce')
        df_chart = df_chart.dropna(subset=["timestamp_dt"]).sort_values("timestamp_dt")

        # 2. Escludi o gestisci i valori 0 m (Disconnessioni) per non falsare il grafico delle distanze
        df_valid_dist = df_chart[df_chart["distance"] > 0]

        # 3. Mappa Colori Personalizzata per Stato
        color_map = {
            "ALLARME (5m-7m)": "#FF4B4B",       # Rosso
            "Reset (Fuori Portata)": "#00C0F2",  # Azzurro
            "Reset (Disconnesso)": "#7E828A"    # Grigio
        }

        # 4. Creazione Grafico Plotly Ottimizzato
        fig_dist = px.line(
            df_valid_dist, 
            x="timestamp_dt", 
            y="distance", 
            color="status",
            markers=True,
            color_discrete_map=color_map,
            labels={"distance": "Distanza (m)", "timestamp_dt": "Data e Ora"},
            title="Distanza Bersaglio nel Tempo"
        )

        # 5. Formattazione Asse X e Layout
        fig_dist.update_xaxes(
            type='date',
            tickformat="%d/%m %H:%M",
            dtick="auto"
        )
        fig_dist.update_traces(marker=dict(size=8))
        fig_dist.update_layout(
            hovermode="x unified",
            legend_title_text="Stato Evento",
            margin=dict(l=20, r=20, t=40, b=20)
        )

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

    with st.expander("📊 Tabella Conteggio Dettagliato MAC Address", expanded=False):
        st.dataframe(mac_counts, use_container_width=True)

    st.divider()

    # -------------------------------------------------------------------------
    # CALCOLO TEMPI DI PERMANENZA (DWELL TIME)
    # -------------------------------------------------------------------------
    st.subheader("⏱️ Tempi di Permanenza Dispositivi")

    # Assicuriamo che i timestamp siano in formato datetime per i calcoli matematici
    df_calc = df.copy()
    df_calc["dt"] = pd.to_datetime(df_calc["timestamp"], format="%d/%m/%Y %H:%M:%S", errors='coerce')
    df_calc = df_calc.dropna(subset=["dt"]).sort_values("dt")

    if not df_calc.empty:
        # Raggruppamento per MAC Address per calcolare inizio, fine e durata totale
        permanenza = df_calc.groupby("mac").agg(
            Primo_Avvistamento=("dt", "min"),
            Ultimo_Avvistamento=("dt", "max"),
            Rilevazioni_Totali=("status", "count"),
            Distanza_Media=("distance", "mean"),
            Ultimo_Stato=("status", "last")
        ).reset_index()

        # Calcolo durata in minuti e secondi
        permanenza["Durata_Delta"] = permanenza["Ultimo_Avvistamento"] - permanenza["Primo_Avvistamento"]
        permanenza["Permanenza (Minuti)"] = (permanenza["Durata_Delta"].dt.total_seconds() / 60).round(1)
        permanenza["Distanza_Media"] = permanenza["Distanza_Media"].round(2)

        # Formattazione per la visualizzazione
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
                title="Tempo Totale di Permanenza nel Raggio d'Azione"
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
        st.markdown("  ")
        # Pulsante per scaricare i dati in formato CSV
        csv_data = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Scarica Dati (CSV)",
            data=csv_data,
            file_name="storico_rilevamenti_ble.csv",
            mime="text/csv"
        )
    
    st.dataframe(df_filtered.iloc[::-1], use_container_width=True)

# -------------------------------------------------------------------------
# TIMER AUTO-REFRESH NATIVO
# -------------------------------------------------------------------------
if auto_refresh:
    time.sleep(refresh_interval)
    st.cache_data.clear()
    st.rerun()
