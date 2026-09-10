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
    "Scanner_1": (5.0, 5.0)
}

COLOR_MAP = {
    "ENTRATO": "#ef4444",   # Rosso allarme
    "PRESENTE": "#f59e0b",  # Giallo avviso
    "SPOSTATO": "#06b6d4",  # Ciano dinamico
    "USCITO": "#10b981",    # Verde sicuro
    "SCONOSCIUTO": "#6b7280"# Grigio neutro
}

DOT_MAP = {
    "ENTRATO": "🔴",
    "PRESENTE": "🟡",
    "SPOSTATO": "🔵",
    "USCITO": "🟢",
    "SCONOSCIUTO": "⚪"
}

# --- BARRA LATERALE ---
st.sidebar.header("⚙️ Filtri & Configurazione")
filter_random_mac = st.sidebar.checkbox("Nascondi MAC casuali/temporanei", value=True)
max_distance_cutoff = st.sidebar.slider("Distanza Massima Radar (m)", 1.0, 20.0, 10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("🔴 Legenda Stati")
st.sidebar.markdown("""
* 🔴 **ENTRATO** - Allarme Intrusione
* 🟡 **PRESENTE** - Rilevato in zona
* 🔵 **SPOSTATO** - In movimento
* 🟢 **USCITO** - Fuori perimetro
* ⚪ **ALTRO** - Non definito
""")

# --- FUNZIONE CARICAMENTO DATI ---
@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception:
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

# Mappatura colonne
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

# Conversione e pulizia
df = df_raw.copy()
df[col_dist] = pd.to_numeric(df[col_dist].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

if filter_random_mac:
    df = df[~df[col_mac].apply(is_random_mac)]

df = df[df[col_dist] <= max_distance_cutoff]

recent_devices = df.groupby(col_mac).last().reset_index()

def get_status_dot(evt):
    evt_upper = str(evt).upper()
    for key, dot in DOT_MAP.items():
        if key in evt_upper:
            return f"{dot} {evt_upper}"
    return f"⚪ {evt_upper}"

# --- METRICHE E KPI ---
k1, k2, k3, k4 = st.columns(4)
active_alarms = sum(1 for e in recent_devices[col_event].astype(str) if "ENTRATO" in e.upper())
last_update = str(df[col_time].iloc[-1]) if col_time and not df.empty else "--"

k1.metric("Stato Perimetro", "🔴 INTRUSIONE" if active_alarms > 0 else "🟢 SICURO")
k2.metric("Dispositivi Attivi", f"🔵 {len(recent_devices)}")
k3.metric("Eventi Critici", f"🔴 {active_alarms}")
k4.metric("Ultimo Log", last_update)

# --- TABS INTERFACCIA ---
tab_map, tab_table = st.tabs(["🗺️ Radar Planimetria Interactive", "📋 Registro Dati Dettagliato"])

with tab_map:
    fig = go.Figure()

    # Cerchi concentrici Radar
    for r in [2, 4, 6, 8, 10]:
        fig.add_shape(type="circle", x0=5-r, y0=5-r, x1=5+r, y1=5+r,
                      line=dict(color="rgba(255, 255, 255, 0.1)", width=1, dash="dot"))
        fig.add_annotation(x=5, y=5+r, text=f"{r}m", showarrow=False, 
                           font=dict(color="rgba(255,255,255,0.3)", size=10), yanchor="bottom")

    # Plot dello Scanner
    sc_x, sc_y = SCANNER_POS["Scanner_1"]
    fig.add_trace(go.Scatter(
        x=[sc_x], y=[sc_y],
        mode='markers+text',
        marker=dict(size=20, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
        text=["<b>Scanner_1</b>"],
        textposition="top center",
        hoverinfo='text',
        name="Scanner_1"
    ))

    target_x, target_y, target_texts, point_labels, colors, marker_sizes = [], [], [], [], [], []
    np.random.seed(42)

    for _, row in recent_devices.iterrows():
        dist = float(row[col_dist])
        evt_str = str(row[col_event]).upper()
        mac_str = str(row[col_mac])
        name_str = str(row[col_name])

        dot_icon = "⚪"
        color = COLOR_MAP["SCONOSCIUTO"]
        for key in COLOR_MAP:
            if key in evt_str:
                color = COLOR_MAP[key]
                dot_icon = DOT_MAP[key]
                break

        # Disposizione polare
        angle = np.random.uniform(0, 2 * np.pi)
        calc_x = sc_x + (dist * np.cos(angle))
        calc_y = sc_y + (dist * np.sin(angle))

        target_x.append(calc_x)
        target_y.append(calc_y)
        colors.append(color)
        marker_sizes.append(18 if "ENTRATO" in evt_str else 12)
        
        # Etichetta visibile sulla mappa con il pallino ed il nome dispositivo
        point_labels.append(f"{dot_icon} {name_str}")

        target_texts.append(
            f"<b>Dispositivo:</b> {name_str}<br>"
            f"<b>MAC:</b> {mac_str}<br>"
            f"<b>Stato:</b> {dot_icon} {evt_str}<br>"
            f"<b>Distanza:</b> {dist:.2f} m"
        )

    # Dispositivi rilevati sul Radar (ora con mode='markers+text' per mostrare i pallini/nomi)
    if target_x:
        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers+text',
            marker=dict(size=marker_sizes, color=colors, opacity=0.9, line=dict(width=1.5, color='#ffffff')),
            text=point_labels,
            textposition="top center",
            textfont=dict(color="#ffffff", size=11),
            hovertext=target_texts,
            hoverinfo='text',
            name='Dispositivi BLE'
        ))

    fig.update_layout(
        xaxis=dict(range=[-6, 16], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-6, 16], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        height=650,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

with tab_table:
    st.subheader("📋 Registro Dettagliato Dispositivi")
    
    display_df = recent_devices.copy()
    display_df[col_event] = display_df[col_event].apply(get_status_dot)
    
    cols_to_show = [c for c in [col_time, col_name, col_mac, col_dist, col_event] if c is not None]
    
    st.dataframe(
        display_df[cols_to_show].sort_values(by=col_dist, ascending=True),
        use_container_width=True,
        height=550
    )
