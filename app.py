import streamlit as st
import pandas as pd
import subprocess
import socket
from streamlit_autorefresh import st_autorefresh

# Configurazione della pagina Streamlit in modalità wide
st.set_page_config(
    page_title="ESP32 Advanced BLE & Wi-Fi Scanner", 
    page_icon="📡", 
    layout="wide"
)

# Autorefresh ogni 5 secondi per mantenere i dati in tempo reale
st_autorefresh(interval=5000, key="datarefresh")

st.title("📡 ESP32 Advanced BLE & Wi-Fi Network Dashboard")
st.markdown("Monitoraggio in tempo reale dei dispositivi Bluetooth Low Energy (con stima della distanza e RSSI esteso) e dei client connessi in Wi-Fi (IP/LAN).")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

# --- RUBRICA NOMI PERSONALIZZATI (MAC -> Nome Chiaro) ---
DEVICE_ALIAS_MAP = {
    "03:e9:c5:2f:f1:b2": "Galaxy-A52",
    "52:c5:37:97:ce:18": "OPPO Reno8 T",
    # Aggiungi qui altri MAC personalizzati se necessario
}

def get_friendly_name(mac, raw_name):
    clean_mac = str(mac).replace("-", ":").lower()
    if clean_mac in DEVICE_ALIAS_MAP:
        return DEVICE_ALIAS_MAP[clean_mac]
    if pd.notna(raw_name):
        cleaned = str(raw_name).strip()
        if cleaned and cleaned.lower() not in ['nan', 'none', '', 'sconosciuto']:
            return cleaned
    return f"Device [{clean_mac[-5:].upper()}]"

@st.cache_data(ttl=2)
def load_ble_data(url):
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return pd.DataFrame()

# --- FUNZIONE PER SCANSIONE IP / ARP LOCALE (Wi-Fi) su Ubuntu ---
def get_wifi_devices():
    wifi_devices = []
    try:
        output = subprocess.check_output(["arp", "-n"], universal_newlines=True)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                ip = parts[0]
                mac = parts[2].lower()
                if mac != "<incomplete>" and mac != "address":
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
    except Exception:
        pass
    return pd.DataFrame(wifi_devices)

# Caricamento dei dataset
df_ble = load_ble_data(SHEET_CSV_URL)
df_wifi = get_wifi_devices()

# --- SEZIONE METRICHE GLOBALI IN ALTO ---
col_m1, col_m2, col_m3 = st.columns(3)
total_ble_devices = df_ble['mac'].nunique() if not df_ble.empty and 'mac' in df_ble.columns else 0
total_wifi_devices = len(df_wifi) if not df_wifi.empty else 0

col_m1.metric("📶 Dispositivi BLE Unici Rilevati", total_ble_devices)
col_m2.metric("🌐 Dispositivi Wi-Fi con IP attivi", total_wifi_devices)
col_m3.metric("📊 Stato del Sistema", "Online / In Ascolto" if not df_ble.empty else "In attesa dati")

st.markdown("---")

# Visualizzazione a Tab
tab_ble, tab_wifi, tab_charts = st.tabs([
    "📶 Dispositivi BLE (Dettagli & Eventi)", 
    "🌐 Dispositivi Wi-Fi con IP (LAN)", 
    "📈 Analisi Grafica & Segnale"
])

with tab_ble:
    st.subheader("📋 Tabella Completa Rilevamenti Bluetooth Low Energy")
    if not df_ble.empty:
        # Pulizia e mappatura colonne basate sulla struttura inviata dall'ESP32
        # Campi attesi nel Google Sheet: Timestamp (o simile), name, mac, rssi, tx_power, service_uuid, distance, event
        cols = list(df_ble.columns)
        
        # Gestione flessibile delle colonne del foglio
        c_time = cols[0] if len(cols) > 0 else 'Timestamp'
        c_name = 'name' if 'name' in cols else cols[1]
        c_mac = 'mac' if 'mac' in cols else cols[2]
        c_rssi = 'rssi' if 'rssi' in cols else 'RSSI'
        c_dist = 'distance' if 'distance' in cols else 'Distance'
        c_event = 'event' if 'event' in cols else 'Event'

        # Applica i nomi puliti della rubrica
        df_ble['friendly_name'] = [get_friendly_name(m, n) for m, n in zip(df_ble[c_mac], df_ble[c_name])]
        
        # Filtra per mostrare l'ultimo stato noto di ogni dispositivo
        display_ble = df_ble.groupby(c_mac).last().reset_index()
        display_ble[c_name] = display_ble['friendly_name']

        # Filtri interattivi laterali o superiori
        search_query = st.text_input("🔍 Filtra per Nome o MAC BLE:", "")
        if search_query:
            display_ble = display_ble[
                display_ble[c_name].str.contains(search_query, case=False, na=False) |
                display_ble[c_mac].str.contains(search_query, case=False, na=False)
            ]

        # Tabella pulita e ordinata per vicinanza (distanza stimata)
        st.dataframe(
            display_ble[[c_time, c_name, c_mac, c_rssi, c_dist, c_event]].sort_values(by=c_dist, ascending=True),
            use_container_width=True
        )
    else:
        st.warning("⚠️ Nessun dato BLE disponibile dal Google Sheet. Verifica che l'ESP32 stia inviando correttamente i dati.")

with tab_wifi:
    st.subheader("🌐 Dispositivi Connessi alla Rete Locale (IP & MAC)")
    if not df_wifi.empty:
        st.dataframe(df_wifi[['IP', 'MAC', 'Nome', 'Tipo']], use_container_width=True)
    else:
        st.info("ℹ️ Nessun dispositivo Wi-Fi rilevato tramite tabella ARP locale (verifica i permessi di esecuzione su Ubuntu).")

with tab_charts:
    st.subheader("📊 Analisi Grafica dei Dispositivi BLE")
    if not df_ble.empty and 'distance' in df_ble.columns and 'rssi' in df_ble.columns:
        chart_data = df_ble.groupby('mac').last().reset_index()
        chart_data['friendly_name'] = [get_friendly_name(m, n) for m, n in zip(chart_data['mac'], chart_data['name'])]

        col_c1, col_c2 = st.columns(2)

        with col_c1:
            st.markdown("##### 📏 Stima Distanza per Dispositivo (metri)")
            if not chart_data.empty:
                st.bar_chart(chart_data.set_index('friendly_name')['distance'])

        with col_c2:
            st.markdown("##### 📶 Potenza del Segnale RSSI (dBm)")
            if not chart_data.empty:
                st.bar_chart(chart_data.set_index('friendly_name')['rssi'])
    else:
        st.info("Dati insufficienti per generare i grafici statistici.")
