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
    st.error("⚠️ Impossibile caricare i dati dal Google Sheet.")
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
col_tx = find_col(['tx', 'power'], 5)
col_uuid = find_col(['uuid', 'service'], 6)

df = df_raw.copy()
df['dist_clean'] = df[col_dist].apply(parse_distance)

# Conversione della colonna nome a stringa e forzatura nome per il Galaxy A52s-5G
TARGET_MAC = "12:6e:91:f8:2d:fa"
target_clean_mac = TARGET_MAC.replace("-", ":").lower()

if col_name is not None and col_mac is not None:
    df[col_name] = df[col_name].astype(str)
    mask_target = df[col_mac].astype(str).str.replace("-", ":").str.lower() == target_clean_mac
    df.loc[mask_target, col_name] = "Galaxy-A52s-5G"

# --- FILTRI NELLA BARRA LATERALE ---
st.sidebar.header("⚙️ Configurazione Centralino")

filter_night_hours = st.sidebar.checkbox("Escludi rilevazioni 00:00 - 04:00", value=True)
exclude_static_macs = st.sidebar.checkbox("Escludi MAC STATICI", value=False)
exclude_specific_macs = st.sidebar.checkbox("Escludi MAC specifici (Lista Nera)", value=True)

# Applicazione filtro orario (00:00 - 04:00)
if filter_night_hours and col_time is not None:
    times_parsed = pd.to_datetime(df[col_time], errors='coerce').dt.hour
    df = df[~((times_parsed >= 0) & (times_parsed < 4))]

# Applicazione filtro Esclusione MAC Statici
if exclude_static_macs:
    df = df[df[col_mac].apply(is_random_mac)]

# Applicazione filtro Esclusione MAC specifici (mantenendo immune il target)
if exclude_specific_macs and col_mac is not None:
    blacklisted_macs = {
        "52:c5:37:97:ce:18",
        "d8:85:ac:aa:11:b0",
        "de:cd:2f:73:96:d3",
        "dc:cd:2f:73:96:d3",
        "8c:4f:00:e0:95:12",
        "4c:a9:19:e2:71:b5",
        "d4:e9:f4:e9:53:d8"
    }
    blacklisted_clean = {m.replace("-", ":").lower() for m in blacklisted_macs}
    df = df[~df[col_mac].astype(str).str.replace("-", ":").str.lower().isin(blacklisted_clean)]

recent_devices = df.groupby(col_mac).last().reset_index()

mac_list = sorted(recent_devices[col_mac].dropna().astype(str).unique().tolist()) if not recent_devices.empty else []
my_mac = st.sidebar.selectbox("Seleziona il TUO MAC (Centro Radar):", mac_list) if mac_list else ""

max_detected = recent_devices['dist_clean'].max() if not recent_devices.empty else 5.0
radar_max_scale = float(max(10.0, np.ceil(max_detected / 5.0) * 5.0))

def get_status_dot(evt):
    evt_upper = str(evt).upper()
    for key, dot in DOT_MAP.items():
        if key in evt_upper:
            return f"{dot} {evt_upper}"
    return f"⚪ {evt_upper}"

# --- METRICHE ---
k1, k2, k3, k4 = st.columns(4)
active_alarms = sum(1 for e in recent_devices[col_event].astype(str) if "ENTRATO" in e.upper()) if not recent_devices.empty else 0
last_update = str(df[col_time].iloc[-1]) if col_time and not df.empty else "--"

k1.metric("Stato Perimetro", "🔴 INTRUSIONE" if active_alarms > 0 else "🟢 SICURO")
k2.metric("Dispositivi Totali", f"🔵 {len(recent_devices)}")
k3.metric("Eventi Critici", f"🔴 {active_alarms}")
k4.metric("Ultimo Log", last_update)

# --- TAB APPLICAZIONE ---
tab_map, tab_table, tab_new_mac, tab_target_mac = st.tabs([
    "🗺️ Radar Planimetria Interactive", 
    "📋 Registro Dati Dettagliato", 
    "🏷️ Tabella Nuovi MAC",
    "📱 Galaxy-A52s-5G (Target)"
])

with tab_map:
    fig = go.Figure()

    step = 5.0
    for r in np.arange(step, radar_max_scale + 0.1, step):
        fig.add_shape(
            type="circle", 
            x0=-r, y0=-r, x1=r, y1=r,
            line=dict(color="rgba(255, 255, 255, 0.25)", width=1, dash="dot")
        )
        fig.add_annotation(
            x=0, y=r, text=f"{int(r)}m", showarrow=False, 
            font=dict(color="rgba(255,255,255,0.6)", size=11), yanchor="bottom"
        )

    my_device_row = recent_devices[recent_devices[col_mac].astype(str) == str(my_mac)] if my_mac else pd.DataFrame()
    other_devices = recent_devices[recent_devices[col_mac].astype(str) != str(my_mac)].copy() if my_mac else recent_devices.copy()

    my_name = my_device_row[col_name].values[0] if not my_device_row.empty and pd.notna(my_device_row[col_name].values[0]) else my_mac

    fig.add_trace(go.Scatter(
        x=[0], y=[0],
        mode='markers+text',
        marker=dict(size=18, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
        text=[f"<b>TU ({my_name})</b>" if my_mac else "<b>Centro</b>"],
        textposition="top center",
        hoverinfo='text',
        hovertext=f"<b>DISPOSITIVO CENTRALE</b><br>MAC: {my_mac}",
        name="Centro"
    ))

    target_x, target_y, target_texts, point_labels, marker_colors, marker_sizes = [], [], [], [], [], []

    num_others = len(other_devices)
    if num_others > 0:
        angles = np.linspace(0, 2 * np.pi, num_others, endpoint=False)

        for idx, (_, row) in enumerate(other_devices.iterrows()):
            r_dist = float(row['dist_clean'])
            evt_str = str(row[col_event]).upper()
            mac_str = str(row[col_mac])
            name_str = str(row[col_name])
            tx_val = row.get(col_tx, 'N/D') if col_tx and col_tx in row else 'N/D'
            uuid_val = row.get(col_uuid, 'N/D') if col_uuid and col_uuid in row else 'N/D'

            dot_icon = "⚪"
            color = COLOR_MAP["SCONOSCIUTO"]
            for key in COLOR_MAP:
                if key in evt_str:
                    color = COLOR_MAP[key]
                    dot_icon = DOT_MAP[key]
                    break

            angle = angles[idx]
            calc_x = r_dist * np.cos(angle)
            calc_y = r_dist * np.sin(angle)

            target_x.append(calc_x)
            target_y.append(calc_y)
            marker_colors.append(color)
            marker_sizes.append(14 if "ENTRATO" in evt_str else 10)

            label_name = name_str if pd.notna(name_str) and str(name_str).strip() != 'nan' else mac_str
            point_labels.append(f"{dot_icon} {label_name} ({r_dist:.1f}m)")

            target_texts.append(
                f"<b>Dispositivo:</b> {name_str}<br>"
                f"<b>MAC:</b> {mac_str}<br>"
                f"<b>Stato:</b> {dot_icon} {evt_str}<br>"
                f"<b>Distanza:</b> {r_dist:.2f} m<br>"
                f"<b>TX Power:</b> {tx_val} dBm<br>"
                f"<b>Service UUID:</b> {uuid_val}"
            )

    if target_x:
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
            name='Dispositivi BLE'
        ))

    pad = radar_max_scale + 1.0
    fig.update_layout(
        xaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-pad, pad], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
        height=700,
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
        display_df[col_event] = display_df[col_event].apply(get_status_dot)
        cols_to_show = [c for c in [col_time, col_name, col_mac, col_dist, col_tx, col_uuid, col_event] if c is not None]
        
        st.dataframe(
            display_df[cols_to_show].sort_values(by=col_dist, ascending=True),
            use_container_width=True,
            height=550
        )

with tab_new_mac:
    st.subheader("🏷️ Tabella Nuovi MAC Rilevati (Eventi di Ingresso)")
    if not df.empty and col_event is not None:
        new_entries_df = df[df[col_event].astype(str).str.upper().str.contains("ENTRATO")].copy()
        
        if not new_entries_df.empty:
            new_entries_df['status_formatted'] = new_entries_df[col_event].apply(get_status_dot)
            cols_to_show = [c for c in [col_time, col_name, col_mac, col_dist, col_tx, col_uuid, col_event] if c is not None]
            
            st.dataframe(
                new_entries_df[cols_to_show].drop_duplicates(subset=[col_mac]).sort_values(by=col_time, ascending=False),
                use_container_width=True,
                height=550
            )
        else:
            st.info("Nessun nuovo dispositivo contrassegnato come 'ENTRATO' trovato nei dati filtrati correnti.")
    else:
        st.warning("Dati non disponibili per popolare la tabella dei nuovi MAC.")

with tab_target_mac:
    st.subheader("📱 Monitoraggio Mirato: Galaxy-A52s-5G")
    
    df_target_history = df[df[col_mac].astype(str).str.replace("-", ":").str.lower() == target_clean_mac].copy()
    
    if not df_target_history.empty:
        latest_target_row = df_target_history.iloc[-1]
        t_name = latest_target_row.get(col_name, "Galaxy-A52s-5G")
        t_dist = latest_target_row.get('dist_clean', 0.0)
        t_event = latest_target_row.get(col_event, "N/D")
        t_tx = latest_target_row.get(col_tx, "N/D")
        t_uuid = latest_target_row.get(col_uuid, "N/D")
        t_time = latest_target_row.get(col_time, "N/D")
        
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
        if col_time is not None and not df_target_history.empty:
            df_target_history['parsed_time'] = pd.to_datetime(df_target_history[col_time], errors='coerce')
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
            
        st.markdown("### 🕒 Tabella Eventi del Galaxy-A52s-5G")
        display_target_df = df_target_history.copy()
        display_target_df[col_event] = display_target_df[col_event].apply(get_status_dot)
        cols_target_show = [c for c in [col_time, col_name, col_mac, col_dist, col_tx, col_uuid, col_event] if c is not None]
        
        st.dataframe(
            display_target_df[cols_target_show].sort_values(by=col_time, ascending=False),
            use_container_width=True,
            height=300
        )
    else:
        st.warning(f"Nessun dato registrato o trovato nel Google Sheet per il MAC `{TARGET_MAC}` (Galaxy-A52s-5G).")
