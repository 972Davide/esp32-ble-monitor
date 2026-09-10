
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="BLE Radar & Control Center", 
    page_icon="📡", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Style CSS Custom per card e UI moderna
st.markdown("""
<style>
    .stApp { background-color: #0b0f19; }
    div[data-testid="stMetric"] {
        background-color: #161e2e;
        border: 1px solid #283548;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] > label {
        color: #8b9dc3 !important;
        font-size: 0.85rem !important;
        font-weight: 600;
    }
    div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-size: 1.8rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Auto-refresh ogni 5 secondi
st_autorefresh(interval=5000, limit=None, key="ble_refresh")

st.title("📡 BLE Intrusion Detection & Radar Center")

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

SCANNER_POS = {
    "Scanner_1": (10.0, 0.0),   # Ingresso
    "Scanner_2": (0.0, 10.0)    # Interno / Lato opposto
}

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Errore durante il caricamento dati: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty and len(df.columns) >= 4:
    cols_lower = [c.lower() for c in df.columns]
    
    col_mac = df.columns[[i for i, c in enumerate(cols_lower) if 'mac' in c or 'address' in c][0]] if any('mac' in c or 'address' in c for c in cols_lower) else df.columns[2]
    col_dist = df.columns[[i for i, c in enumerate(cols_lower) if 'dist' in c][0]] if any('dist' in c for c in cols_lower) else df.columns[4]
    col_event = df.columns[[i for i, c in enumerate(cols_lower) if 'event' in c or 'stato' in c][0]] if any('event' in c or 'stato' in c for c in cols_lower) else df.columns[5]
    col_name = df.columns[[i for i, c in enumerate(cols_lower) if 'nam' in c or 'nom' in c][0]] if any('nam' in c or 'nom' in c for c in cols_lower) else df.columns[1]
    
    gw_cols = [i for i, c in enumerate(cols_lower) if 'gateway' in c or 'scanner' in c or 'nodo' in c]
    col_gw = df.columns[gw_cols[0]] if gw_cols else None

    df[col_dist] = pd.to_numeric(df[col_dist].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    if col_gw:
        recent_devices = df.groupby([col_mac, col_gw]).last().reset_index()
    else:
        recent_devices = df.groupby(col_mac).last().reset_index()

    # --- KPI METRICHS ROW ---
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    total_devices = len(recent_devices)
    active_alarms = sum(1 for e in recent_devices[col_event].astype(str) if "ENTRATO" in e.upper())
    
    last_row = df.iloc[-1] if not df.empty else None
    last_event_text = str(last_row[col_event]) if last_row is not None else "--"

    col_kpi1.metric("Stato Sistema", "⚠️ ALLARME" if active_alarms > 0 else "✅ SICURO")
    col_kpi2.metric("Dispositivi Unici", total_devices)
    col_kpi3.metric("Eventi ENTRATO", active_alarms)
    col_kpi4.metric("Ultimo Evento", last_event_text)

    st.markdown("---")

    # --- MAIN CONTENT ROW (MAPPA + REGISTRO) ---
    col_map, col_list = st.columns([7, 5])

    with col_map:
        st.subheader("🗺️ Radar Planimetria (Coordinate Mappa)")
        
        fig = go.Figure()

        # Perimetro Casa (rettangolo 0,0 -> 10,10)
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                      line=dict(color="#38bdf8", width=3),
                      fillcolor="rgba(56, 189, 248, 0.03)")

        # ZONIZZAZIONE & ANNOTAZIONI
        fig.add_annotation(x=5, y=5, text="CASA / INTERNO", showarrow=False, font=dict(color="rgba(255,255,255,0.25)", size=18))
        fig.add_annotation(x=5, y=12.0, text="STRADA / ESTERNO", showarrow=False, font=dict(color="rgba(255,255,255,0.4)", size=12))
        fig.add_annotation(x=5, y=-2.0, text="GIARDINO RETRO", showarrow=False, font=dict(color="rgba(255,255,255,0.4)", size=12))
        fig.add_annotation(x=10, y=0, text="🚪 Ingresso", showarrow=False, font=dict(color="#38bdf8", size=13))

        # Scanner
        for gw_name, pos in SCANNER_POS.items():
            fig.add_trace(go.Scatter(
                x=[pos[0]], y=[pos[1]],
                mode='markers+text',
                marker=dict(size=14, color='#38bdf8', symbol='diamond', line=dict(color='white', width=1)),
                text=[f"<b>{gw_name}</b>"],
                textposition="top center",
                hoverinfo='text',
                name=gw_name
            ))

        target_x, target_y, target_texts, colors, display_labels = [], [], [], [], []
        
        # Algoritmo di offset per evitare sovrapposizioni (Jittering)
        np.random.seed(42)

        for _, row in recent_devices.iterrows():
            dist = float(row[col_dist])
            evt_str = str(row[col_event]).upper()
            mac_str = str(row[col_mac])
            name_str = str(row[col_name])
            gw_id = str(row[col_gw]) if col_gw else "Scanner_1"

            base_x, base_y = SCANNER_POS.get(gw_id, (10.0, 0.0))

            if "ENTRATO" in evt_str:
                x, y = base_x - 0.5, base_y + 1.0
                color = "#ff0055"
            elif "PRESENTE" in evt_str:
                x, y = 5.0, 5.0
                color = "#eab308"
            elif "SPOSTATO" in evt_str:
                x = max(0.5, min(9.5, base_x + (dist * 0.5)))
                y = max(0.5, min(9.5, base_y + (dist * 0.5)))
                color = "#06b6d4"
            elif "USCITO" in evt_str:
                x, y = base_x, 10.0 + min(dist, 8.0)
                color = "#22c55e"
            else:
                x, y = 1.0, 10.0 + min(dist, 8.0)
                color = "#64748b"

            # Aggiunge un leggero sfalsamento (jitter) per evitare pallini perfettamente sovrapposti
            jitter_x = np.random.uniform(-0.35, 0.35)
            jitter_y = np.random.uniform(-0.35, 0.35)

            target_x.append(x + jitter_x)
            target_y.append(y + jitter_y)
            colors.append(color)
            
            # Etichetta breve se il nome è lungo o sconosciuto
            short_name = name_str if name_str != "Sconosciuto" else mac_str[-5:]
            display_labels.append(short_name)
            
            target_texts.append(
                f"<b>{name_str}</b><br>Nodo: {gw_id}<br>MAC: {mac_str}<br>Stato: {evt_str}<br>Distanza: {dist:.2f}m"
            )

        # Dispositivi BLE
        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers+text',
            marker=dict(size=16, color=colors, line=dict(width=1.5, color='#ffffff')),
            text=display_labels,
            textposition="top center",
            textfont=dict(size=10, color="#ffffff"),
            hovertext=target_texts,
            hoverinfo='text',
            name='Dispositivi BLE'
        ))

        fig.update_layout(
            xaxis=dict(range=[-4, 14], showgrid=False, zeroline=False, visible=False),
            yaxis=dict(range=[-4, 20], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
            height=580,
            margin=dict(l=10, r=10, t=20, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

    with col_list:
        st.subheader("📋 Registro Dispositivi")
        
        display_cols = [col_name, col_mac, col_dist, col_event]
        if col_gw:
            display_cols.insert(0, col_gw)

        st.dataframe(
            recent_devices[display_cols],
            use_container_width=True,
            height=530
        )

else:
    st.warning("In attesa dei primi dati dal foglio Google Sheets...")
