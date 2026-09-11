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

st_autorefresh(interval=5000, limit=None, key="ble_refresh")

st.title("📡 BLE Intrusion Detection & Tactical Radar")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

COLOR_MAP = {
    "ENTRATO": "#ef4444",   # Rosso
    "PRESENTE": "#f59e0b",  # Giallo
    "SPOSTATO": "#06b6d4",  # Ciano
    "USCITO": "#10b981",    # Verde
    "SCONOSCIUTO": "#6b7280"# Grigio
}

DOT_MAP = {
    "ENTRATO": "🔴",
    "PRESENTE": "🟡",
    "SPOSTATO": "🔵",
    "USCITO": "🟢",
    "SCONOSCIUTO": "⚪"
}

# --- RUBRICA DISPOSITIVI (Personalizza qui i nomi dei tuoi dispositivi) ---
DEVICE_ALIAS_MAP = {
    "03:e9:c5:2f:f1:b2": "Galaxy-A52",
    # Aggiungi qui altri MAC noti per forzare un nome specifico:
    # "aa:bb:cc:dd:ee:ff": "Cuffie Bluetooth",
}

TARGET_MAC = "03:e9:c5:2f:f1:b2"

def parse_distance(val):
    if pd.isna(val):
        return 1.0
    val_str = str(val).replace(',', '.')
    numbers = re.findall(r"\d+(?:\.\d+)?", val_str)
    if numbers:
        floats = [float(n) for n in numbers]
        avg = sum(floats) / len(floats)
        return max(avg, 0.1)
    return 1.0

def get_friendly_name(mac, raw_name):
    clean_mac = str(mac).replace("-", ":").lower()
    
    # 1. Priorità assoluta alla rubrica manuale
    if clean_mac in DEVICE_ALIAS_MAP:
        return DEVICE_ALIAS_MAP[clean_mac]
    
    # 2. Se l'ESP32 ha catturato un nome pulito e valido, usiamo quello
    if pd.notna(raw_name):
        cleaned = str(raw_name).strip()
        if cleaned and cleaned.lower() not in ['nan', 'none', '', 'null', 'unknown', 'sconosciuto']:
            return cleaned
            
    # 3. Fallback: nome strutturato basato sulle ultime cifre del MAC
    short_mac = clean_mac[-5:].upper() if len(clean_mac) >= 5 else clean_mac
    return f"BLE-Dev [{short_mac}]"

@st.cache_data(ttl=2)
def load_data(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df.loc[:, ~df.columns.duplicated()]
    except Exception:
        return pd.DataFrame()

# --- CARICAMENTO E PREPARAZIONE DATI ---
df = load_data(SHEET_CSV_URL)

if df.empty:
    st.error("⚠️ Impossibile caricare i dati dal Google Sheet.")
    st.stop()

cols = list(df.columns)
c_time = cols[0] if len(cols) > 0 else None
c_name = cols[1] if len(cols) > 1 else None
c_mac = cols[2] if len(cols) > 2 else None
c_dist = cols[3] if len(cols) > 3 else None
c_event = cols[4] if len(cols) > 4 else None
c_tx = cols[5] if len(cols) > 5 else None
c_uuid = cols[6] if len(cols) > 6 else None

df = df.loc[:, ~df.columns.duplicated()]
df['dist_clean'] = df[c_dist].apply(parse_distance) if c_dist else 1.0

# Applicazione della logica di nome pulito/rubrica su tutto il DataFrame
if c_name is not None and c_mac is not None:
    df['friendly_name'] = [get_friendly_name(m, n) for m, n in zip(df[c_mac], df[c_name])]
else:
    df['friendly_name'] = "Dispositivo Sconosciuto"

# --- FILTRI NELLA BARRA LATERALE ---
st.sidebar.header("⚙️ Configurazione")

filter_night_hours = st.sidebar.checkbox("Escludi rilevazioni 00:00 - 04:00", value=True)

if filter_night_hours and c_time is not None:
    times_parsed = pd.to_datetime(df[c_time], errors='coerce').dt.hour
    df = df[~((times_parsed >= 0) & (times_parsed < 4))]

recent_devices = df.groupby(c_mac).last().reset_index() if c_mac is not None else pd.DataFrame()

mac_list = []
mac_to_name_dict = {}
if not recent_devices.empty and c_mac:
    for _, row in recent_devices.iterrows():
        m_val = str(row[c_mac])
        f_name = row['friendly_name']
        mac_list.append(m_val)
        mac_to_name_dict[m_val] = f_name

my_mac = st.sidebar.selectbox(
    "Centro Radar (Tuo Dispositivo):", 
    mac_list, 
    format_func=lambda x: f"{mac_to_name_dict.get(x, x)} ({x})"
) if mac_list else ""

max_detected = recent_devices['dist_clean'].max() if not recent_devices.empty and 'dist_clean' in recent_devices.columns else 5.0
radar_max_scale = float(max(10.0, np.ceil(max_detected / 5.0) * 5.0))

def get_status_dot(evt):
    evt_upper = str(evt).upper()
    for key, dot in DOT_MAP.items():
        if key in evt_upper:
            return f"{dot} {evt_upper}"
    return f"⚪ {evt_upper}"

# --- METRICHE ---
active_alarms = sum(1 for e in recent_devices[c_event].astype(str) if "ENTRATO" in e.upper()) if not recent_devices.empty and c_event else 0
last_update = str(df[c_time].iloc[-1]) if c_time and not df.empty else "--"

k1, k2, k3, k4 = st.columns(4)
k1.metric("Stato Perimetro", "🔴 INTRUSIONE" if active_alarms > 0 else "🟢 SICURO")
k2.metric("Dispositivi Totali", f"🔵 {len(recent_devices)}")
k3.metric("Eventi Critici", f"🔴 {active_alarms}")
k4.metric("Ultimo Log", last_update)

# --- TAB APPLICAZIONE ---
tab_map, tab_table, tab_target_mac = st.tabs([
    "🗺️ Radar Planimetria Interactive", 
    "📋 Registro Dati Dettagliato", 
    "📱 Galaxy-A52 (Target)"
])

with tab_map:
    fig = go.Figure()

    step = 5.0
    for r in np.arange(step, radar_max_scale + 0.1, step):
        fig.add_shape(
            type="circle", x0=-r, y0=-r, x1=r, y1=r,
            line=dict(color="rgba(255, 255, 255, 0.20)", width=1, dash="dot")
        )
        fig.add_annotation(
            x=0, y=r, text=f"{int(r)}m", showarrow=False, 
            font=dict(color="rgba(255,255,255,0.5)", size=10), yanchor="bottom"
        )

    fig.add_shape(type="line", x0=-radar_max_scale, y0=0, x1=radar_max_scale, y1=0, line=dict(color="rgba(255,255,255,0.1)", width=1))
    fig.add_shape(type="line", x0=0, y0=-radar_max_scale, x1=0, y1=radar_max_scale, line=dict(color="rgba(255,255,255,0.1)", width=1))

    my_name = mac_to_name_dict.get(my_mac, "Centro") if my_mac else "Centro"

    fig.add_trace(go.Scatter(
        x=[0], y=[0],
        mode='markers+text',
        marker=dict(size=16, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
        text=[f"<b>TU ({my_name})</b>" if my_mac else "<b>Centro</b>"],
        textposition="top center",
        textfont=dict(color="#38bdf8", size=11),
        hoverinfo='text',
        hovertext=f"<b>DISPOSITIVO CENTRALE</b><br>Nome: {my_name}<br>MAC: {my_mac if my_mac else 'Non selezionato'}",
        name="Centro"
    ))

    other_devices = recent_devices[recent_devices[c_mac].astype(str) != str(my_mac)].copy() if my_mac and c_mac else recent_devices.copy()

    if not other_devices.empty:
        target_x, target_y, target_texts, point_labels, marker_colors, marker_sizes = [], [], [], [], [], []

        for _, row in other_devices.iterrows():
            r_dist = float(row['dist_clean'])
            evt_str = str(row[c_event]).upper() if c_event else ""
            mac_str = str(row[c_mac]) if c_mac else ""
            friendly_n = row['friendly_name']
            tx_val = row.get(c_tx, 'N/D') if c_tx and c_tx in row else 'N/D'
            uuid_val = row.get(c_uuid, 'N/D') if c_uuid and c_uuid in row else 'N/D'

            mac_hash = sum(ord(c) for c in mac_str)
            angle = (mac_hash % 360) * (np.pi / 180.0)

            calc_x = r_dist * np.cos(angle)
            calc_y = r_dist * np.sin(angle)

            dot_icon = "⚪"
            color = COLOR_MAP["SCONOSCIUTO"]
            for key in COLOR_MAP:
                if key in evt_str:
                    color = COLOR_MAP[key]
                    dot_icon = DOT_MAP[key]
                    break

            target_x.append(calc_x)
            target_y.append(calc_y)
            marker_colors.append(color)
            marker_sizes.append(14 if "ENTRATO" in evt_str else 10)

            point_labels.append(f"{dot_icon} {friendly_n} ({r_dist:.1f}m)")

            target_texts.append(
                f"<b>Dispositivo:</b> {friendly_n}<br>"
                f"<b>MAC:</b> {mac_str}<br>"
                f"<b>Stato:</b> {dot_icon} {evt_str}<br>"
                f"<b>Distanza:</b> {r_dist:.2f} m<br>"
                f"<b>TX Power:</b> {tx_val} dBm<br>"
                f"<b>Service UUID:</b> {uuid_val}"
            )

        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers+text',
            marker=dict(
                size=marker_sizes, 
                color=marker_colors, 
                opacity=0.9, 
                line=dict(width=1, color='#ffffff')
            ),
            text=point_labels,
            textposition="top center",
            textfont=dict(color="#ffffff", size=9),
            hovertext=target_texts,
            hoverinfo='text',
            name='Target BLE'
        ))

    pad = radar_max_scale + 1.0
    fig.update_layout(
        xaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        height=680,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

with tab_table:
    st.subheader("📋 Registro Dettagliato Dispositivi")
    display_df = recent_devices.copy()
    if not display_df.empty:
        if c_event:
            display_df[c_event] = display_df[c_event].apply(get_status_dot)
        
        if c_name in display_df.columns:
            display_df[c_name] = display_df['friendly_name']

        cols_to_show = [c for c in [c_time, c_name, c_mac, c_dist, c_tx, c_uuid, c_event] if c is not None]
        cols_to_show = list(dict.fromkeys(cols_to_show))
        
        st.dataframe(
            display_df[cols_to_show].sort_values(by=c_dist, ascending=True),
            use_container_width=True,
            height=550
        )

with tab_target_mac:
    st.subheader("📱 Monitoraggio Mirato: Galaxy-A52")
    
    target_clean_mac = TARGET_MAC.replace("-", ":").lower()
    df_target_history = df[df[c_mac].astype(str).str.replace("-", ":").str.lower() == target_clean_mac].copy() if c_mac else pd.DataFrame()
    
    if not df_target_history.empty:
        latest_target_row = df_target_history.iloc[-1]
        t_name = latest_target_row.get('friendly_name', "Galaxy-A52")
        t_dist = latest_target_row.get('dist_clean', 0.0)
        t_event = latest_target_row.get(c_event, "N/D") if c_event else "N/D"
        t_tx = latest_target_row.get(c_tx, "N/D") if c_tx else "N/D"
        t_uuid = latest_target_row.get(c_uuid, "N/D") if c_uuid else "N/D"
        t_time = latest_target_row.get(c_time, "N/D") if c_time else "N/D"
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Nome", str(t_name))
        m2.metric("Distanza Attuale", f"{t_dist:.2f} m")
        m3.metric("Ultimo Stato", str(t_event))
        m4.metric("Ultimo Rilevamento", str(t_time))
        
        st.markdown("---")
        
        c_info1, c_info2 = st.columns(2)
        c_info1.info(f"**MAC Address:** `{TARGET_MAC}`")
        c_info2.info(f"**TX Power:** `{t_tx}` dBm | **Service UUID:** `{t_uuid}`")
        
        st.markdown("### 📈 Storico Distanza")
        if c_time is not None and not df_target_history.empty:
            df_target_history['parsed_time'] = pd.to_datetime(df_target_history[c_time], errors='coerce')
            df_target_history = df_target_history.sort_values('parsed_time')
            
            fig_target = go.Figure()
            fig_target.add_trace(go.Scatter(
                x=df_target_history['parsed_time'],
                y=df_target_history['dist_clean'],
                mode='lines+markers',
                name='Distanza (m)',
                line=dict(color='#38bdf8', width=2),
                marker=dict(size=6)
            ))
            fig_target.update_layout(
                xaxis_title="Tempo",
                yaxis_title="Distanza stimata (metri)",
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_target, use_container_width=True)
            
        st.markdown("### 🕒 Tabella Eventi del Galaxy-A52")
        display_target_df = df_target_history.copy()
        if c_event:
            display_target_df[c_event] = display_target_df[c_event].apply(get_status_dot)
        if c_name in display_target_df.columns:
            display_target_df[c_name] = display_target_df['friendly_name']
            
        cols_target_show = [c for c in [c_time, c_name, c_mac, c_dist, c_tx, c_uuid, c_event] if c is not None]
        cols_target_show = list(dict.fromkeys(cols_target_show))
        
        st.dataframe(
            display_target_df[cols_target_show].sort_values(by=c_time, ascending=False),
            use_container_width=True,
            height=300
        )
    else:
        st.warning(f"Nessun dato registrato o trovato nel Google Sheet per il MAC `{TARGET_MAC}` (Galaxy-A52).")
