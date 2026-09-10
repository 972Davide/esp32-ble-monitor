import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="BLE Tactical Radar", 
    page_icon="📡", 
    layout="wide"
)

# --- STILE CSS PERSONALIZZATO ---
st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 14px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f2937 !important;
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8;
    }
</style>
""", unsafe_allow_html=True)

# Autorefresh ogni 5 secondi
st_autorefresh(interval=5000, limit=None, key="ble_refresh")

st.title("📡 BLE Intrusion Detection & Tactical Radar")

# --- PARAMETRI FISSI & COSTANTI ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

SCANNER_POS = {
    "Scanner_1": (10.0, 0.0),
    "Scanner_2": (0.0, 10.0)
}

COLOR_MAP = {
    "ENTRATO": "#ef4444",   # Rosso allarme
    "PRESENTE": "#f59e0b",  # Giallo avviso
    "SPOSTATO": "#06b6d4",  # Ciano dinamico
    "USCITO": "#10b981",    # Verde sicuro
    "SCONOSCIUTO": "#6b7280"# Grigio neutro
}

# --- BARRA LATERALE ---
st.sidebar.header("⚙️ Filtri & Configurazione")
filter_random_mac = st.sidebar.checkbox("Nascondi MAC casuali/temporanei", value=True)
selected_gateway = st.sidebar.selectbox("Filtra per Gateway", ["Tutti"] + list(SCANNER_POS.keys()))
max_distance_cutoff = st.sidebar.slider("Distanza Massima Radar (m)", 1.0, 30.0, 15.0)

# --- FUNZIONE CARICAMENTO DATI ---
@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        return pd.DataFrame()

def is_random_mac(mac):
    try:
        first_byte = int(str(mac).replace("-", ":").split(':')[0], 16)
        return bool(first_byte & 2)
    except:
        return False

# --- ELABORAZIONE DATI ---
df_raw = load_data(SHEET_CSV_URL)

if df_raw.empty:
    st.error("⚠️ Impossibile caricare i dati dal Google Sheet. Verifica l'URL o la connessione.")
    st.stop()

# Mappatura tollerante delle colonne
cols_lower = [c.lower() for c in df_raw.columns]

def find_col(keywords, default_idx):
    for idx, c in enumerate(cols_lower):
        if any(kw in c for kw in keywords):
            return df_raw.columns[idx]
    return df_raw.columns[default_idx] if len(df_raw.columns) > default_idx else None

col_time = find_col(['time', 'data', 'ora', 'timestamp'], 0)
col_name = find_col(['nam', 'nom', 'dev'], 1)
col_mac = find_col(['mac', 'address', 'indirizzo'], 2)
col_dist = find_col(['dist', 'rssi', 'metri'], 3)
col_event = find_col(['event', 'stato', 'status', 'allarme'], 4)
col_gw = find_col(['gateway', 'scanner', 'nodo'], 5)

# Conversione e pulizia tipi
df = df_raw.copy()
df[col_dist] = pd.to_numeric(df[col_dist].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

if filter_random_mac:
    df = df[~df[col_mac].apply(is_random_mac)]

if col_gw and selected_gateway != "Tutti":
    df = df[df[col_gw] == selected_gateway]

# Estrazione ultimi eventi registrati per ciascun dispositivo
if col_gw:
    recent_devices = df.groupby([col_mac, col_gw]).last().reset_index()
else:
    recent_devices = df.groupby(col_mac).last().reset_index()

# --- METRICHE E KPI ---
k1, k2, k3, k4 = st.columns(4)
active_alarms = sum(1 for e in recent_devices[col_event].astype(str) if "ENTRATO" in e.upper())
last_update = str(df[col_time].iloc[-1]) if col_time and not df.empty else "--"

k1.metric("Stato Perimetro", "⚠️ INTRUSIONE" if active_alarms > 0 else "✅ SICURO")
k2.metric("Dispositivi Attivi", len(recent_devices))
k3.metric("Eventi Critici", active_alarms)
k4.metric("Ultimo Log", last_update)

# --- TABS INTERFACCIA ---
tab_map, tab_table = st.tabs(["🗺️ Radar Planimetria Interactive", "📋 Registro Dati Dettagliato"])

with tab_map:
    fig = go.Figure()

    # Perimetro Area Protetta (0,0 -> 10,10)
    fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                  line=dict(color="#38bdf8", width=2, dash="dash"),
                  fillcolor="rgba(56, 189, 248, 0.03)")

    # Cerchi concentrici Radar di riferimento
    for r in [3, 6, 9, 12]:
        fig.add_shape(type="circle", x0=-r+5, y0=-r+5, x1=r+5, y1=r+5,
                      line=dict(color="rgba(255, 255, 255, 0.08)", width=1))

    # Etichette Zone
    fig.add_annotation(x=5, y=5, text="<b>ZONA INTERNA</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.2)", size=18))
    fig.add_annotation(x=5, y=11.5, text="<b>PERIMETRO ESTERNO</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.4)", size=12))

    # Plot dei Gateway
    for gw_name, pos in SCANNER_POS.items():
        fig.add_trace(go.Scatter(
            x=[pos[0]], y=[pos[1]],
            mode='markers+text',
            marker=dict(size=18, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
            text=[f"<b>{gw_name}</b>"],
            textposition="top center",
            hoverinfo='text',
            name=gw_name
        ))

    target_x, target_y, target_texts, colors, marker_sizes = [], [], [], [], []
    np.random.seed(42)  # Seed fisso per evitare jittering erratico ad ogni refresh

    for _, row in recent_devices.iterrows():
        dist = float(row[col_dist])
        evt_str = str(row[col_event]).upper()
        mac_str = str(row[col_mac])
        name_str = str(row[col_name])
        gw_id = str(row[col_gw]) if col_gw and row[col_gw] in SCANNER_POS else "Scanner_1"

        base_x, base_y = SCANNER_POS.get(gw_id, (5.0, 5.0))

        # Logica di posizionamento vettoriale basata sulla distanza
        if "ENTRATO" in evt_str:
            color = COLOR_MAP["ENTRATO"]
            vec_x, vec_y = (0.5, 0.5)
            d_mod = min(dist, 4.0)
        elif "PRESENTE" in evt_str:
            color = COLOR_MAP["PRESENTE"]
            vec_x, vec_y = (0.0, 0.0)
            d_mod = 0.0
        elif "USCITO" in evt_str:
            color = COLOR_MAP["USCITO"]
            vec_x, vec_y = (0.0, 1.0)
            d_mod = max(dist, 10.0)
        else:
            color = COLOR_MAP["SCONOSCIUTO"]
            vec_x, vec_y = (1.0, 0.0)
            d_mod = dist

        # Calcolo coordinate con sparpagliamento angolare
        angle = np.random.uniform(0, 2 * np.pi)
        jitter = np.random.uniform(0.2, 0.5)
        
        calc_x = base_x + (d_mod * vec_x) + (jitter * np.cos(angle))
        calc_y = base_y + (d_mod * vec_y) + (jitter * np.sin(angle))

        target_x.append(calc_x)
        target_y.append(calc_y)
        colors.append(color)
        marker_sizes.append(18 if "ENTRATO" in evt_str else 12)

        target_texts.append(
            f"<b>Dispositivo:</b> {name_str}<br>"
            f"<b>MAC:</b> {mac_str}<br>"
            f"<b>Stato:</b> {evt_str}<br>"
            f"<b>Distanza:</b> {dist:.2f} m<br>"
            f"<b>Gateway:</b> {gw_id}"
        )

    # Marker dei Dispositivi BLE
    if target_x:
        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers',
            marker=dict(size=marker_sizes, color=colors, opacity=0.9, line=dict(width=1.5, color='#ffffff')),
            hovertext=target_texts,
            hoverinfo='text',
            name='Dispositivi BLE'
        ))

    fig.update_layout(
        xaxis=dict(range=[-5, 15], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-5, 15], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        height=650,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

with tab_table:
    st.subheader("📋 Registro Dettagliato Dispositivi")
    
    cols_to_show = [c for c in [col_time, col_gw, col_name, col_mac, col_dist, col_event] if c is not None]
    
    st.dataframe(
        recent_devices[cols_to_show].sort_values(by=col_dist, ascending=True),
        use_container_width=True,
        height=550
    )
