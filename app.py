import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
import re
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
    "Scanner_1": (0.0, 0.0) # Posizionato all'origine del Radar
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

# --- FUNZIONE PARSER DISTANZA PROPORZIONALE ---
def parse_distance(val):
    if pd.isna(val):
        return 2.0
    val_str = str(val).replace(',', '.')
    numbers = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", val_str)
    if numbers:
        floats = [float(n) for n in numbers]
        avg = sum(floats) / len(floats)
        return max(avg, 0.5)
    return 2.0

# --- BARRA LATERALE ---
st.sidebar.header("⚙️ Filtri & Configurazione")
filter_random_mac = st.sidebar.checkbox("Nascondi MAC casuali/temporanei", value=False)
show_all_devices = st.sidebar.checkbox("Mostra TUTTI i dispositivi nel Radar", value=True)
max_distance_cutoff = st.sidebar.slider("Distanza Massima Visualizzata (m)", 1.0, 30.0, 15.0)

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

df = df_raw.copy()
df['dist_clean'] = df[col_dist].apply(parse_distance)

if filter_random_mac:
    df = df[~df[col_mac].apply(is_random_mac)]

if not show_all_devices:
    df = df[df['dist_clean'] <= max_distance_cutoff]

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
k2.metric("Dispositivi Rilevati", f"🔵 {len(recent_devices)}")
k3.metric("Eventi Critici", f"🔴 {active_alarms}")
k4.metric("Ultimo Log", last_update)

# --- TABS INTERFACCIA ---
tab_map, tab_table = st.tabs(["🗺️ Radar Planimetria Interactive", "📋 Registro Dati Dettagliato"])

with tab_map:
    fig = go.Figure()

    sc_x, sc_y = SCANNER_POS["Scanner_1"]

    # Raggio massimo proporzionale per il rendering dei cerchi
    max_detected_dist = recent_devices['dist_clean'].max() if not recent_devices.empty else 10.0
    radar_limit = max(10.0, float(np.ceil(max_detected_dist)))

    # Anelli concentrici di misurazione metri in scala esatta
    step = 2 if radar_limit <= 12 else 5
    for r in np.arange(step, radar_limit + step, step):
        fig.add_shape(
            type="circle", 
            x0=sc_x - r, y0=sc_y - r, x1=sc_x + r, y1=sc_y + r,
            line=dict(color="rgba(255, 255, 255, 0.15)", width=1, dash="dot")
        )
        fig.add_annotation(
            x=sc_x, y=sc_y + r, text=f"{int(r)}m", showarrow=False, 
            font=dict(color="rgba(255,255,255,0.4)", size=10), yanchor="bottom"
        )

    # Plot Scanner Centralizzatore
    fig.add_trace(go.Scatter(
        x=[sc_x], y=[sc_y],
        mode='markers+text',
        marker=dict(size=22, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
        text=["<b>Scanner_1</b>"],
        textposition="top center",
        hoverinfo='text',
        name="Scanner_1"
    ))

    target_x, target_y, target_texts, point_labels, marker_colors, marker_sizes = [], [], [], [], [], []

    # Raggruppamento dispositivi per distanza esatta per calcolare lo sfalsamento d'angolo
    grouped_by_dist = recent_devices.groupby('dist_clean')

    for dist, group in grouped_by_dist:
        count = len(group)
        # Sfasamento angolare uniforme per tutti i punti che hanno la medesima distanza
        angle_step = (2 * np.pi) / count
        start_angle = np.random.uniform(0, 2 * np.pi)

        for i, (_, row) in enumerate(group.iterrows()):
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

            # Calcolo Trigonometrico Proporzionale 1:1
            angle = start_angle + (i * angle_step)
            calc_x = sc_x + (dist * np.cos(angle))
            calc_y = sc_y + (dist * np.sin(angle))

            target_x.append(calc_x)
            target_y.append(calc_y)
            marker_colors.append(color)
            marker_sizes.append(15 if "ENTRATO" in evt_str else 11)

            label_text = name_str if pd.notna(name_str) and str(name_str).strip() != 'nan' else mac_str
            point_labels.append(f"{dot_icon} {label_text}")

            target_texts.append(
                f"<b>Dispositivo:</b> {name_str}<br>"
                f"<b>MAC:</b> {mac_str}<br>"
                f"<b>Stato:</b> {dot_icon} {evt_str}<br>"
                f"<b>Distanza Reale:</b> {dist:.2f} m"
            )

    # Rendering visivo dei punti sparpagliati in proporzione esatta
    if target_x:
        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers+text',
            marker=dict(
                size=marker_sizes, 
                color=marker_colors, 
                opacity=0.95, 
                line=dict(width=1.2, color='#ffffff')
            ),
            text=point_labels,
            textposition="top center",
            textfont=dict(color="#ffffff", size=9),
            hovertext=target_texts,
            hoverinfo='text',
            name='Dispositivi BLE'
        ))

    # Layout proporzionale rigido (1 metro X = 1 metro Y)
    pad = radar_limit + 2.0
    fig.update_layout(
        xaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        height=750,
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
