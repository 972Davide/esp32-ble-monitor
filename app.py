import streamlit as st
import pandas as pd
import requests

# 1. PAGE CONFIG
st.set_page_config(
    page_title="SOC // BLE INTRUSION DETECTION",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. HACKER / CYBERPUNK CSS INJECTION
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&display=swap');

    /* Global styling */
    html, body, [class*="css"], .stApp {
        background-color: #080c10 !important;
        font-family: 'Fira Code', monospace !important;
        color: #00ff66 !important;
    }

    /* Titles and Headers */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Fira Code', monospace !important;
        color: #00f0ff !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
    }

    /* Custom Cards / Containers */
    div[data-testid="stMetric"] {
        background: #0d131a !important;
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.15) !important;
        border-radius: 4px !important;
        padding: 15px !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #88a0b0 !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
    }

    div[data-testid="stMetricValue"] {
        color: #00ff66 !important;
        text-shadow: 0 0 10px rgba(0, 255, 102, 0.5) !important;
        font-family: 'Fira Code', monospace !important;
    }

    /* Terminal Alert Badges */
    .status-alert {
        padding: 12px;
        border-radius: 4px;
        font-weight: bold;
        text-align: center;
        letter-spacing: 1px;
        font-size: 0.95rem;
    }
    .status-danger {
        background-color: rgba(255, 0, 85, 0.15);
        border: 1px solid #ff0055;
        color: #ff0055;
        box-shadow: 0 0 12px rgba(255, 0, 85, 0.4);
    }
    .status-safe {
        background-color: rgba(0, 255, 102, 0.1);
        border: 1px solid #00ff66;
        color: #00ff66;
        box-shadow: 0 0 12px rgba(0, 255, 102, 0.3);
    }

    /* Dataframe / Table styling */
    div[data-testid="stDataFrame"] {
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.1) !important;
    }

    /* Dividers */
    hr {
        border-color: #00f0ff !important;
        opacity: 0.3;
    }
    </style>
""", unsafe_allow_html=True)

# 3. HEADER TERMINAL
st.markdown("### 📡 [SOC] BLE RECONNAISSANCE & INTRUSION CONSOLE")
st.caption("SYSTEM STATUS: ONLINE // PROTOCOL: ESP32-BLE-GATEWAY // INTERFACE: LIVE LOGS")

URL = "https://script.google.com/macros/s/AKfycbyW6iY08lTa5ET3M9nsIm-J393Tawv9K_52xE_hyYKydK69Q-j9ywlAgTcFhRYzrYGc/exec?format=json"

try:
    response = requests.get(URL, timeout=8)
    data = response.json()

    if len(data) > 0:
        df = pd.DataFrame(data)

        # Mappatura automatica colonne
        col_event = next((c for c in df.columns if 'event' in str(c).lower() or 'evento' in str(c).lower()), df.columns[1] if len(df.columns) > 1 else None)
        col_mac = next((c for c in df.columns if 'mac' in str(c).lower()), df.columns[3] if len(df.columns) > 3 else None)
        col_dist = next((c for c in df.columns if 'dist' in str(c).lower()), df.columns[5] if len(df.columns) > 5 else None)

        # --- METRICHE SECURITY OPERATIONS ---
        m1, m2, m3, m4 = st.columns(4)

        last_event = str(df[col_event].iloc[0]) if col_event and not df.empty else "NO_DATA"
        is_alarm = "ENTRATO" in last_event.upper()

        with m1:
            st.metric(label="CURRENT DEFCON STATUS", value="CRITICAL" if is_alarm else "NORMAL")

        with m2:
            total_alarms = len(df[df[col_event].astype(str).str.contains('ENTRATO', na=False, case=False)]) if col_event else 0
            st.metric(label="INTRUSION EVENTS", value=f"{total_alarms:02d}")

        with m3:
            unique_macs = df[col_mac].nunique() if col_mac else 0
            st.metric(label="TARGET MACS DETECTED", value=f"{unique_macs:02d}")

        with m4:
            st.metric(label="ACTIVE GATEWAY", value="ESP32_NODE_01")

        st.markdown("<br>", unsafe_allow_html=True)

        # BANNER STATO LIVE
        if is_alarm:
            st.markdown(f'<div class="status-alert status-danger">⚠️ INTRUDER DETECTED IN RANGE // EVENT: {last_event}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="status-alert status-safe">🛡️ PERIMETER CLEAR // LAST STATE: {last_event}</div>', unsafe_allow_html=True)

        st.divider()

        # --- GRAFICI STYLE TERMINALE ---
        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 📊 EVENT DISTRIBUTION ANALYTICS")
            if col_event:
                event_counts = df[col_event].astype(str).value_counts()
                st.bar_chart(event_counts, color="#00f0ff")

        with c2:
            st.markdown("#### 📈 PROXIMITY TRACKING METRICS (m)")
            if col_dist:
                df['Distanza_Num'] = pd.to_numeric(df[col_dist], errors='coerce')
                st.line_chart(df['Distanza_Num'].dropna(), color="#ff0055")

        st.divider()

        # --- TABELLA DATED FORENSICS LOGS ---
        st.markdown("#### 📑 REAL-TIME FORENSIC PACKET LOGS")
        st.dataframe(df, use_container_width=True, hide_index=False)

    else:
        st.warning("[!] TERMINAL ALERT: Zero records returned from Google Sheets Endpoint.")

except Exception as e:
    st.error(f"[!] SYSTEM EXCEPTION CAUGHT: {e}")
