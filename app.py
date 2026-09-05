import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Monitoraggio BLE ESP32", layout="wide")

# URL aggiornato della tua Web App su Google Apps Script
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyxdcInWY2bY0aJEnHzmxamgQ6qo3I_CnI4quqypDoMrTOMoYuL16pQyVy8JsExb93K/exec"

st.title("🛡️ Dashboard Monitoraggio BLE")

# Tabella Dispositivi Autorizzati (Whitelist)
st.subheader("Dispositivi Autorizzati (Whitelist)")
whitelist_data = {
    "Dispositivo": ["Dispositivo 1", "Dispositivo 2", "Dispositivo 3"],
    "MAC Address": ["1c:3d:48:d6:f1:f0", "de:cd:2f:73:96:d3", "12:fc:96:71:ac:84"],
    "Stato": ["Autorizzato", "Autorizzato", "Autorizzato"]
}
st.table(pd.DataFrame(whitelist_data))

st.subheader("Stato Rilevamento Intrusione")
st.info("Isteresi attiva: Ingresso 5m - 7m | Reset > 15m")

status_container = st.empty()

def get_latest_data():
    try:
        headers = {"Accept": "application/json"}
        response = requests.get(APPS_SCRIPT_URL, headers=headers, timeout=5, allow_redirects=True)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Google Apps Script ha restituito il codice HTTP: {response.status_code}")
    except requests.exceptions.JSONDecodeError:
        st.error("Errore: Google Apps Script ha restituito HTML anziché JSON. Verifica di aver aggiornato la distribuzione su Google.")
    except Exception as e:
        st.error(f"Errore di connessione: {e}")
    return None

data = get_latest_data()

with status_container.container():
    if data:
        col1, col2, col3, col4 = st.columns(4)
        
        status = str(data.get("status", "N/A"))
        if "ALLARME" in status.upper():
            col1.metric("Stato Allarme", status, delta="Rilevato", delta_color="inverse")
        else:
            col1.metric("Stato Allarme", status)

        mac = data.get("mac", "N/A")
        col2.metric("MAC Rilevato", mac)

        # Gestione sicura del formato per Distanza e RSSI
        raw_distance = data.get("distance", 0)
        raw_rssi = data.get("rssi", 0)

        dist_val = f"{raw_distance} m" if str(raw_distance) != "N/D" else "N/D"
        rssi_val = f"{raw_rssi} dBm" if str(raw_rssi) != "N/D" else "N/D"

        col3.metric("Distanza Stimata", dist_val)
        col4.metric("RSSI", rssi_val)
        
        if "timestamp" in data:
            st.caption(f"Ultimo aggiornamento registrato: {data['timestamp']}")
    else:
        st.warning("Impossibile recuperare i dati da Google Sheets. Verifica la nuova distribuzione su Apps Script.")

# Pulsante di aggiornamento manuale
if st.button("Aggiorna Dati"):
    st.rerun()
