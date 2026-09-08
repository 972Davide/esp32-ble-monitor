import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Dashboard BLE", layout="wide")
URL = "https://script.google.com/macros/s/AKfycbyW6iY08lTa5ET3M9nsIm-J393Tawv9K_52xE_hyYKydK69Q-j9ywlAgTcFhRYzrYGc/exec?format=json"

st.title("🚦 Dashboard Monitoraggio & Analytics BLE")

try:
    response = requests.get(URL)
    data = response.json()

    if len(data) > 0:
        df = pd.DataFrame(data)

        # Normalizzazione dei nomi delle colonne
        col_event = next((c for c in df.columns if 'event' in str(c).lower() or 'evento' in str(c).lower()), None)
        col_mac = next((c for c in df.columns if 'mac' in str(c).lower()), None)
        col_dist = next((c for c in df.columns if 'dist' in str(c).lower()), None)

        # Se non trova per nome, usa l'indice numerico di fallback
        if not col_event and len(df.columns) > 1:
            col_event = df.columns[1]
        if not col_mac and len(df.columns) > 3:
            col_mac = df.columns[3]
        if not col_dist and len(df.columns) > 5:
            col_dist = df.columns[5]

        # --- 1. METRICHE E KPI ---
        col1, col2, col3 = st.columns(3)

        last_event = str(df[col_event].iloc[0]) if col_event and not df.empty else "N/D"
        col1.metric("Stato Attuale", last_event)

        if col_event:
            entrati = df[df[col_event].astype(str).str.contains('ENTRATO', na=False, case=False)]
            col2.metric("Totale Allarmi (ENTRATO)", len(entrati))
        else:
            col2.metric("Totale Allarmi (ENTRATO)", "N/D")

        unique_macs = df[col_mac].nunique() if col_mac else "N/D"
        col3.metric("Dispositivi Unici Rilevati", unique_macs)

        st.divider()

        # --- 2. GRAFICI ---
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            st.subheader("📊 Distribuzione Eventi")
            if col_event:
                event_counts = df[col_event].astype(str).value_counts()
                st.bar_chart(event_counts)

        with col_chart2:
            st.subheader("📈 Cronologia Distanze (m)")
            if col_dist:
                df['Distanza_Num'] = pd.to_numeric(df[col_dist], errors='coerce')
                st.line_chart(df['Distanza_Num'].dropna())

        st.divider()

        # --- 3. TABELLA COMPLETA ---
        st.subheader("📊 Ultimi Transiti Rilevati")
        st.dataframe(df, use_container_width=True)

    else:
        st.info("Nessun dato disponibile nel foglio di calcolo.")

except Exception as e:
    st.error(f"Errore durante l'elaborazione dei dati: {e}")
