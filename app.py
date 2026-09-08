import streamlit as st
import pandas as pd
import requests

# Configurazione Pagina Streamlit
st.set_page_config(page_title="Dashboard BLE", layout="wide")

URL = "https://script.google.com/macros/s/AKfycbyW6iY08lTa5ET3M9nsIm-J393Tawv9K_52xE_hyYKydK69Q-j9ywlAgTcFhRYzrYGc/exec?format=json"

st.title("🚦 Dashboard Monitoraggio & Analytics BLE")

try:
    response = requests.get(URL)
    data = response.json()
    
    if len(data) > 0:
        df = pd.DataFrame(data)
        
        # --- 1. METRICHE E KPI ---
        col1, col2, col3 = st.columns(3)
        
        # Ultimo evento
        last_event = df.iloc[0]['Evento'] if 'Evento' in df.columns else "N/D"
        col1.metric("Stato Attuale", last_event)
        
        # Totale allarmi
        entrati = df[df['Evento'].astype(str).str.contains('ENTRATO', na=False)]
        col2.metric("Totale Allarmi (ENTRATO)", len(entrati))
        
        # Dispositivi Unici
        unique_macs = df['MAC'].nunique() if 'MAC' in df.columns else 0
        col3.metric("Dispositivi Unici Rilevati", unique_macs)
        
        st.divider()

        # --- 2. GRAFICI ---
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("📊 Distribuzione Eventi")
            if 'Evento' in df.columns:
                event_counts = df['Evento'].value_counts()
                st.bar_chart(event_counts)

        with col_chart2:
            st.subheader("📈 Cronologia Rilevamenti")
            if 'Distanza' in df.columns:
                # Conversione della colonna Distanza in numerico
                df['Distanza_Num'] = pd.to_numeric(df['Distanza'], errors='coerce')
                st.line_chart(df[['Distanza_Num']])

        st.divider()

        # --- 3. TABELLA EVENTI RECENTI ---
        st.subheader("📊 Ultimi Transiti Rilevati")
        st.dataframe(df, use_container_width=True)

    else:
        st.info("Nessun dato disponibile nel foglio di calcolo.")

except Exception as e:
    st.error(f"Errore nella lettura da Google Sheets: {e}")
