import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="BLE Tactical Radar", page_icon="📡", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    div[data-testid="stMetric"] { background-color: #161b22; border: 1px solid #30363d; padding: 14px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, limit=None, key="ble_refresh")
st.title("📡 BLE Intrusion Detection & Tactical Radar")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

COLOR_MAP = {"ENTRATO": "#ef4444", "PRESENTE": "#f59e0b", "SPOSTATO": "#06b6d4", "USCITO": "#10b981", "SCONOSCIUTO": "#6b7280"}
DOT_MAP = {"ENTRATO": "🔴", "PRESENTE": "🟡", "SPOSTATO": "🔵", "USCITO": "🟢", "SCONOSCIUTO": "⚪"}
TARGET_MAC = "03:e9:c5:2f:f1:b2"

def parse_distance(val):
    if pd.isna(val): return 1.0
    numbers = re.findall(r"\d+(?:\.\d+)?", str(val).replace(',', '.'))
    return max(sum(map(float, numbers)) / len(numbers), 0.1) if numbers else 1.0

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df.loc[:, ~df.columns.duplicated()]
    except:
        return pd.DataFrame()

df = load_data(SHEET_CSV_URL)
if df.empty:
    st.error("⚠️ Impossibile caricare i dati dal Google Sheet.")
    st.stop()

# Mapping colonne standard attese nel Google Sheet (Time, Name, Mac, Distance, Event, Tx, UUID)
cols = list(df.columns)
c_time, c_name, c_mac, c_dist, c_event = cols[0], cols[1], cols[2], cols[3], cols[4]
c_tx = cols[5] if len(cols) > 5 else None
c_uuid = cols[6] if len(cols) > 6 else None

df['dist_clean'] = df[c_dist].apply(parse_distance)
df.loc[df[c_mac].astype(str).str.replace("-", ":").str.lower() == TARGET_MAC, c_name] = "Galaxy-A52"

# --- FILTRI BARRA LATERALE ---
st.sidebar.header("⚙️ Configurazione")
if st.sidebar.checkbox("Escludi rilevazioni 00:00 - 04:00", value=True):
    times = pd.to_datetime(df[c_time], errors='coerce').dt.hour
    df = df[~((times >= 0) & (times < 4))]

recent_devices = df.groupby(c_mac).last().reset_index()
mac_list = sorted(recent_devices[c_mac].dropna().astype(str).unique().tolist())
my_mac = st.sidebar.selectbox("Centro Radar (Tuo MAC):", mac_list) if mac_list else ""

max_dist = recent_devices['dist_clean'].max() if not recent_devices.empty else 5.0
radar_scale = float(max(10.0, np.ceil(max_dist / 5.0) * 5.0))

# --- METRICHE PRINCIPALI ---
active_alarms = sum(1 for e in recent_devices[c_event].astype(str) if "ENTRATO" in e.upper())
k1, k2, k3, k4 = st.columns(4)
k1.metric("Stato Perimetro", "🔴 INTRUSIONE" if active_alarms > 0 else "🟢 SICURO")
k2.metric("Dispositivi Totali", len(recent_devices))
k3.metric("Eventi Critici", active_alarms)
k4.metric("Ultimo Log", str(df[c_time].iloc[-1]))

# --- TAB INTERFACCIA ---
tab_map, tab_table, tab_target = st.tabs(["🗺️ Radar Planimetria", "📋 Registro Dati", "📱 Galaxy-A52 (Target)"])

with tab_map:
    fig = go.Figure()
    for r in np.arange(5.0, radar_scale + 0.1, 5.0):
        fig.add_shape(type="circle", x0=-r, y0=-r, x1=r, y1=r, line=dict(color="rgba(255,255,255,0.25)", width=1, dash="dot"))
        fig.add_annotation(x=0, y=r, text=f"{int(r)}m", showarrow=False, font=dict(color="rgba(255,255,255,0.6)", size=11))

    # Centro (Tu)
    fig.add_trace(go.Scatter(x=[0], y=[0], mode='markers+text', marker=dict(size=18, color='#38bdf8', symbol='diamond'), text=["TU"], textposition="top center", name="Centro"))

    other_devices = recent_devices[recent_devices[c_mac].astype(str) != str(my_mac)]
    if not other_devices.empty:
        angles = np.linspace(0, 2 * np.pi, len(other_devices), endpoint=False)
        xs, ys, texts, labels, colors = [], [], [], [], []

        for i, (_, row) in enumerate(other_devices.iterrows()):
            dist = float(row['dist_clean'])
            evt = str(row[c_event]).upper()
            color = COLOR_MAP.get("ENTRATO" if "ENTRATO" in evt else "SCONOSCIUTO", "#6b7280")
            
            xs.append(dist * np.cos(angles[i]))
            ys.append(dist * np.sin(angles[i]))
            colors.append(color)
            labels.append(f"{row[c_name]} ({dist:.1f}m)")
            texts.append(f"<b>Nome:</b> {row[c_name]}<br><b>MAC:</b> {row[c_mac]}<br><b>Stato:</b> {evt}<br><b>Distanza:</b> {dist:.2f}m")

        fig.add_trace(go.Scatter(x=xs, y=ys, mode='markers+text', marker=dict(size=12, color=colors), text=labels, textposition="top center", hovertext=texts, hoverinfo='text'))

    fig.update_layout(xaxis=dict(range=[-radar_scale-1, radar_scale+1], visible=False), yaxis=dict(range=[-radar_scale-1, radar_scale+1], visible=False, scaleanchor="x"), height=650, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with tab_table:
    st.subheader("📋 Registro Dettagliato")
    st.dataframe(recent_devices[[c_time, c_name, c_mac, c_dist, c_event]].sort_values(by=c_dist), use_container_width=True)

with tab_target:
    st.subheader("📱 Monitoraggio Target: Galaxy-A52")
    df_target = df[df[c_mac].astype(str).str.replace("-", ":").str.lower() == TARGET_MAC]
    if not df_target.empty:
        latest = df_target.iloc[-1]
        m1, m2, m3 = st.columns(3)
        m1.metric("Distanza", f"{latest['dist_clean']:.2f} m")
        m2.metric("Ultimo Stato", str(latest[c_event]))
        m3.metric("Ultimo Rilevamento", str(latest[c_time]))
        
        st.markdown("### 📈 Storico Distanza")
        df_target['parsed_time'] = pd.to_datetime(df_target[c_time], errors='coerce')
        st.line_chart(df_target.sort_values('parsed_time').set_index('parsed_time')['dist_clean'])
    else:
        st.warning("Nessun dato trovato per il Galaxy-A52.")
        
