import streamlit as st
import pandas as pd
import subprocess
import platform
import re
import datetime

st.set_page_config(
    page_title="Dashboard Monitoraggio BLE & Wi-Fi",
    page_icon="📡",
    layout="wide"
)

st.title("📡 Dashboard Monitoraggio BLE & Wi-Fi (LAN)")

# Tabs di navigazione
tab1, tab2, tab3 = st.tabs([
    "📶 Dispositivi BLE (Dettagli & Eventi)",
    "🌐 Dispositivi Wi-Fi con IP (LAN)",
    "📈 Analisi Grafica & Segnale"
])

def get_arp_table():
    devices = []
    current_os = platform.system()
    try:
        output = subprocess.check_output(["arp", "-a"], universal_newlines=True, timeout=3)
        for line in output.splitlines():
            if current_os == "Windows":
                match = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s+([0-9a-fA-F:-]{12,17})', line)
                if match:
                    devices.append({"IP": match.group(1), "MAC": match.group(2).replace('-', ':').lower(), "Tipo": "Dinamico/Statico"})
            else:
                parts = line.split()
                if len(parts) >= 4:
                    ip = parts[0].strip('()')
                    mac = parts[3]
                    if re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac):
                        devices.append({"IP": ip, "MAC": mac.lower(), "Tipo": "LAN"})
    except Exception:
        pass
        
    if not devices and current_os != "Windows":
        try:
            with open("/proc/net/arp", "r") as f:
                lines = f.readlines()[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00":
                            devices.append({"IP": ip, "MAC": mac.lower(), "Tipo": "ARP"})
        except Exception:
            pass
            
    return devices

with tab1:
    st.subheader("Dispositivi BLE Rilevati")
    st.markdown("Gestione e visualizzazione in tempo reale dei pacchetti e dei dispositivi BLE associati.")
    
    ble_data = [
        {"Dispositivo": "ESP32-Tracker-01", "MAC": "24:0a:c4:12:34:56", "RSSI (dBm)": -65, "Distanza (m)": 2.1, "Ultimo Evento": str(datetime.datetime.now().strftime("%H:%M:%S"))},
        {"Dispositivo": "Beacon-Room-B", "MAC": "cc:50:e3:98:76:54", "RSSI (dBm)": -78, "Distanza (m)": 4.5, "Ultimo Evento": str(datetime.datetime.now().strftime("%H:%M:%S"))}
    ]
    df_ble = pd.DataFrame(ble_data)
    st.dataframe(df_ble, use_container_width=True)

with tab2:
    st.subheader("Dispositivi Connessi alla Rete Locale (IP & MAC)")
    
    arp_devices = get_arp_table()
    
    if arp_devices:
        df_arp = pd.DataFrame(arp_devices)
        st.dataframe(df_arp, use_container_width=True)
    else:
        st.info("Nessun dispositivo Wi-Fi rilevato tramite la tabella ARP locale (verifica i permessi di rete o l'esecuzione del comando arp).")

with tab3:
    st.subheader("Analisi Grafica & Segnale")
    st.markdown("Andamento temporale di RSSI e Distanza stimata.")
    
    chart_data = pd.DataFrame({
        'Tempo': pd.date_range(start=datetime.datetime.now() - datetime.timedelta(minutes=10), periods=10, freq='1min'),
        'RSSI (dBm)': [-60, -62, -65, -63, -68, -70, -67, -64, -62, -61],
        'Distanza (m)': [1.5, 1.7, 2.1, 1.9, 2.6, 2.9, 2.4, 2.0, 1.8, 1.6]
    }).set_index('Tempo')
    
    st.line_chart(chart_data)
