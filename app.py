import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="BLE Radar Center", 
    page_icon="📡", 
    layout="wide"
)

# Custom CSS per interfaccia pulita
st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 12px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

st_autorefresh(interval=5000, limit=None, key="ble_refresh")

st.title("📡 BLE Intrusion Detection & Radar Center")

# --- SIDEBAR FILTRI ---
st.sidebar.header("⚙️ Filtri Visualizzazione")
filter_random_mac = st.sidebar.checkbox("Nascondi MAC casuali/temporanei", value=True)
selected_gateway = st.sidebar.selectbox("Filtra per Gateway", ["Tutti", "Scanner_1", "Scanner_2"])

SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

SCANNER_POS = {
    "Scanner_1": (10.0, 0.0),
    "Scanner_2": (0.0, 10.0)
}

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
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
    
    # Filtro MAC randomizzati (primo ottetto con bit locale attivo)
    if filter_random_mac:
        def is_random_mac(mac):
            try:
                first_byte = int(str(mac).split(':')[0], 16)
                return bool(first_byte & 2)
            except:
                return False
        df = df[~df[col_mac].apply(is_random_mac)]

    if col_gw and selected_gateway != "Tutti":
        df = df[df[col_gw] == selected_gateway]

    if col_gw:
        recent_devices = df.groupby([col_mac, col_gw]).last().reset_index()
    else:
        recent_devices = df.groupby(col_mac).last().reset_index()

    # --- KPI METRICHE ---
    k1, k2, k3, k4 = st.columns(4)
    active_alarms = sum(1 for e in recent_devices[col_event].astype(str) if "ENTRATO" in e.upper())
    
    k1.metric("Stato Allarme", "⚠️ ENTRATO" if active_alarms > 0 else "✅ SICURO")
    k2.metric("Dispositivi Rilevati", len(recent_devices))
    k3.metric("Eventi Intrusione", active_alarms)
    k4.metric("Ultimo Aggiornamento", df.iloc[-1][df.columns[0]] if not df.empty else "--")

    # --- TAB DIVISIONE MAPPA / TABELLA ---
    tab_map, tab_table = st.tabs(["🗺️ Radar Planimetria Interactive", "📋 Registro Dati Dettagliato"])

    with tab_map:
        fig = go.Figure()

        # Perimetro Casa (rettangolo 0,0 -> 10,10)
        fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                      line=dict(color="#38bdf8", width=3),
                      fillcolor="rgba(56, 189, 248, 0.05)")

        # ZONIZZAZIONE & ANNOTAZIONI
        fig.add_annotation(x=5, y=5, text="<b>CASA / INTERNO</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.3)", size=20))
        fig.add_annotation(x=5, y=12.5, text="<b>STRADA / ESTERNO</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.5)", size=13))
        fig.add_annotation(x=5, y=-2.5, text="<b>GIARDINO RETRO</b>", showarrow=False, font=dict(color="rgba(255,255,255,0.5)", size=13))

        # Scanner
        for gw_name, pos in SCANNER_POS.items():
            fig.add_trace(go.Scatter(
                x=[pos[0]], y=[pos[1]],
                mode='markers+text',
                marker=dict(size=16, color='#38bdf8', symbol='diamond', line=dict(color='white', width=2)),
                text=[f"<b>{gw_name}</b>"],
                textposition="top center",
                hoverinfo='text',
                name=gw_name
            ))

        target_x, target_y, target_texts, colors = [], [], [], []
        
        # Jittering controllato per sparpagliare i nodi vicini
        np.random.seed(10)

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
                x = max(0.5, min(9.5, base_x + (dist * 0.4)))
                y = max(0.5, min(9.5, base_y + (dist * 0.4)))
                color = "#06b6d4"
            elif "USCITO" in evt_str:
                x, y = base_x, 10.0 + min(dist, 4.0)
                color = "#22c55e"
            else:
                x, y = 1.0, 10.0 + min(dist, 4.0)
                color = "#64748b"

            # Sfalsamento casuale circolare per non accatastare i punti
            angle = np.random.uniform(0, 2 * np.pi)
            radius = np.random.uniform(0.1, 0.6)
            
            target_x.append(x + radius * np.cos(angle))
            target_y.append(y + radius * np.sin(angle))
            colors.append(color)
            
            target_texts.append(
                f"<b>Dispositivo:</b> {name_str}<br><b>Nodo:</b> {gw_id}<br><b>MAC:</b> {mac_str}<br><b>Stato:</b> {evt_str}<br><b>Dist:</b> {dist:.2f}m"
            )

        # Dispositivi BLE (Senza etichette testo dirette per massima pulizia)
        fig.add_trace(go.Scatter(
            x=target_x,
            y=target_y,
            mode='markers',
            marker=dict(size=14, color=colors, opacity=0.85, line=dict(width=1.5, color='#ffffff')),
            hovertext=target_texts,
            hoverinfo='text',
            name='Dispositivi BLE'
        ))

        fig.update_layout(
            xaxis=dict(range=[-3, 13], showgrid=False, zeroline=False, visible=False),
            yaxis=dict(range=[-4, 16], showgrid=False, zeroline=False, visible=False, scaleanchor="x", scaleratio=1),
            height=680,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False
        )

        st.plotly_chart(fig, use_container_width=True)

    with tab_table:
        st.subheader("📋 Registro Dettagliato Dispositivi")
        display_cols = [col_name, col_mac, col_dist, col_event]
        if col_gw:
            display_cols.insert(0, col_gw)

        st.dataframe(
            recent_devices[display_cols],
            use_container_width=True,
            height=600
        )

else:
    st.warning("In attesa di dati da Google Sheets...")
