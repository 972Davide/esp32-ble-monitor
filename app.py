import streamlit as st
import pandas as pd
import subprocess
import re
import socket
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="BLE & Wi-Fi IP Scanner", page_icon="📡", layout="wide")
st_autorefresh(interval=5000, key="refresh")

st.title("📡 BLE & Wi-Fi IP Integrated Scanner")

SHEET_CSV_URL = "INSERISCI_QUI_URL_CSV_GOOGLE_SHEET"

# --- RUBRICA NOMI PERSONALIZZATI (MAC -> Nome Chiaro) ---
DEVICE_ALIAS_MAP = {
    "03:e9:c5:2f:f1:b2": "Galaxy-A52",
    "52:c5:37:97:ce:18": "OPPO Reno8 T",
    # Aggiungi qui altri MAC noti (sia BLE che Wi-Fi):
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
def load_ble_data(url):
    try:
        return pd.read_csv(url)
    except:
        return pd.DataFrame()

# --- FUNZIONE PER SCANSIONE IP / ARP LOCALE (Wi-Fi) ---
def get_wifi_devices():
    wifi_devices = []
    try:
        # Esegue il comando arp -a su Linux (Ubuntu) per leggere i dispositivi attivi in LAN
        output = subprocess.check_output(["arp", "-n"], universal_newlines=True)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[2].lower()
                if mac != "<incomplete>" and mac != "address":
                    # Prova a risolvere il nome hostname se possibile
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = "Sconosciuto"
                    
                    friendly = DEVICE_ALIAS_MAP.get(mac, hostname if hostname != "Sconosciuto" else f"IP-Dev [{mac[-5:].upper()}]")
                    wifi_devices.append({
                        "IP": ip,
                        "MAC": mac,
                        "Nome": friendly,
                        "Tipo": "Wi-Fi (IP)"
                    })
    except Exception as e:
        # Fallback se eseguito su sistemi diversi o senza permessi arp
        pass
    return pd.DataFrame(wifi_devices)

# --- CARICAMENTO DATI BLE ---
df_ble = load_ble_data(SHEET_CSV_URL)

# --- CARICAMENTO DATI WIFI (IP) ---
df_wifi = get_wifi_devices()

# Visualizzazione a Tab
tab_ble, tab_wifi = st.tabs(["📶 Dispositivi BLE (Età/Distanza)", "🌐 Dispositivi Wi-Fi con IP (LAN)"])

with tab_ble:
    st.subheader("📋 Rilevamenti Bluetooth Low Energy (BLE)")
    if not df_ble.empty:
        cols = list(df_ble.columns)
        c_time, c_name, c_mac, c_dist, c_event = cols[0], cols[1], cols[2], cols[3], cols[4] if len(cols) > 4 else None
        
        df_ble['friendly_name'] = [get_friendly_name(m, n) for m, n in zip(df_ble[c_mac], df_ble[c_name])]
        display_ble = df_ble.groupby(c_mac).last().reset_index()
        display_ble[c_name] = display_ble['friendly_name']
        
        st.dataframe(
            display_ble[[c_time, c_name, c_mac, c_dist, c_event]].sort_values(by=c_dist, ascending=True),
            use_container_width=True
        )
    else:
        st.warning("Nessun dato BLE disponibile dal foglio.")

with tab_wifi:
    st.subheader("🌐 Dispositivi Connessi al Wi-Fi (Indirizzo IP & MAC)")
    if not df_wifi.empty:
        st.dataframe(df_wifi[['IP', 'MAC', 'Nome', 'Tipo']], use_container_width=True)
    else:
        st.info("Nessun dispositivo Wi-Fi rilevato tramite tabella ARP locale (o script eseguito su ambiente non compatibile).")
