
import streamlit as st
import pandas as pd
import requests

# Inserisci qui l'URL della tua Web App Google Apps Script
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbz6vMrIZZCm1m2QFxT_9Dl4m-HAtRpl-LmZaJP5kSBavTJr-Rrika9NgvcoAKQ9dsc/exec"

@st.cache_data(ttl=5)  # Aggiorna i dati ogni 5 secondi
def get_historical_data():
    try:
        # Richiede il formato JSON passando ?format=json
        response = requests.get(
            APPS_SCRIPT_URL, 
            params={"format": "json"}, 
            allow_redirects=True, 
            timeout=10
        )
        
        # Verifica che la risposta sia valida
        response.raise_for_status()
        
        # Parsa i dati JSON
        data = response.json()
        
        if not data or len(data) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(data)
        return df

    except Exception as e:
        st.error(f"Errore nella lettura da Google Sheets: {e}")
        return pd.DataFrame()

# Caricamento e visualizzazione
st.title("🚦 Dashboard Monitoraggio & Analytics BLE")

df = get_historical_data()

if not df.empty:
    st.write("### 📊 Ultimi Transiti Rilevati", df)
else:
    st.info("Nessun dato disponibile nel foglio di calcolo.")
