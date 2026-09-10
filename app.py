
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Monitoraggio BLE Casa", layout="wide")

# --- AUTO-REFRESH OGNI 5 SECONDI (5000 ms) ---
st_autorefresh(interval=5000, limit=None, key="ble_monitor_refresh")

st.title("📡 Monitoraggio Presenze BLE Multi-Nodo - Planimetria Real-Time")

# --- PARAMETRI CONFIGURAZIONE GOOGLE SHEETS ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

# Posizioni fisse dei due scanner sulla mappa (X, Y in metri)
SCANNER_POS = {
    "Scanner_1": (10.0, 0.0),   # Ingresso Casa
    "Scanner_2": (0.0, 10.0)    # Lato Opposto / Interno
}

@st.cache_data(ttl=2)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"Errore caricamento dati da Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty and len(df.columns) >= 4:
    cols_lower = [c.lower() for c in df.columns]
    
    # Mappatura dinamica delle colonne
    col_mac = df.columns[[i for i, c in enumerate(cols_lower) if 'mac' in c or 'address' in c][0]] if any('mac' in c or 'address' in c for c in cols_lower) else df.columns[2]
    col_dist = df.columns[[i for i, c in enumerate(cols_lower) if 'dist' in c][0]] if any('dist' in c for c in cols_lower) else df.columns[4]
    col_event = df.columns[[i for i, c in enumerate(cols_lower) if 'event' in c or 'stato' in c][0]] if any('event' in c or 'stato' in c for c in cols_lower) else df.columns[5]
    col_name = df.columns[[i for i, c in enumerate(cols_lower) if 'nam' in c or 'nom' in c][0]] if any('nam' in c or 'nom' in c for c in cols_lower) else df.columns[1]
    
    # Cerca colonna del Gateway / Scanner ID
    gw_cols = [i for i, c in enumerate(cols_lower) if 'gateway' in c or 'scanner' in c or 'nodo' in c]
    col_gw = df.columns[gw_cols[0]] if gw_cols else None

    # Pre-elaborazione dati e conversione della distanza
    df[col_dist] = pd.to_numeric(df[col_dist].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    if col_gw:
        # Prende l'ultima rilevazione per ciascuna combinazione (MAC, Gateway)
        recent_devices = df.groupby([col_mac, col_gw]).last().reset_index()
    else:
        recent_devices = df.groupby(col_mac).last().reset_index()

    # --- COSTRUZIONE MAPPA PLANIMETRIA ---
    fig = go.Figure()

    # Perimetro casa (rettangolo 0,0 -> 10,10 metri)
    fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                  line=dict(color="White", width=3),
                  fillcolor="rgba(255, 255, 255, 0.05)")

    # Etichette zone
    fig.add_annotation(x=5, y=5, text="<b>CASA / INTERNO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=5, y=12.0, text="<b>STRADA / ESTERNO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=5, y=-2.0, text="<b>GIARDINO RETRO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=10, y=0, text="🚪 Ingresso", showarrow=False, font=dict(color="cyan", size=12))

    # Disegna i Nodi Scanner sulla Mappa
    for gw_name, pos in SCANNER_POS.items():
        fig.add_trace(go.Scatter(
            x=[pos[0]], y=[pos[1]],
            mode='markers+text',
            marker=dict(size=14, color='Cyan', symbol='diamond'),
            text=[f"<b>{gw_name}</b>"],
            textposition="top center",
            hoverinfo='text',
            name=gw_name
        ))

    # Calcolo coordinate X, Y reali dei dispositivi
    target_x, target_y, target_texts, colors = [], [], [], []

    for _, row in recent_devices.iterrows():
        dist = float(row[col_dist])
        evt_str = str(row[col_event]).upper()
        mac_str = str(row[col_mac])
        name_str = str(row[col_name])
        gw_id = str(row[col_gw]) if col_gw else "Scanner_1"

        # Recupera le coordinate base del gateway che legge il segnale
        base_x, base_y = SCANNER_POS.get(gw_id, (10.0, 0.0))

        # Calcolo posizione relativa in base all'evento e allo scanner
        if "ENTRATO" in evt_str:
            x, y = base_x - 0.5, base_y + 1.0
            color = "#ff0055"
        elif "PRESENTE" in evt_str:
            x, y = 5.0, 5.0
            color = "#ffcc00"
        elif "SPOSTATO" in evt_str:
            x = max(0.5, min(9.5, base_x + (dist * 0.5)))
            y = max(0.5, min(9.5, base_y + (dist * 0.5)))
            color = "#00ccff"
        elif "USCITO" in evt_str:
            x, y = base_x, 10.0 + min(dist, 8.0)
            color = "#00ff66"
        else: # FUORI_RAGGIO
            x, y = 1.0, 10.0 + min(dist, 8.0)
            color = "#888888"

        target_x.append(x)
        target_y.append(y)
        colors.append(color)
        target_texts.append(f"<b>{name_str}</b><br>Nodo: {gw_id}<br>MAC: {mac_str}<br>Stato: {evt_str}<br>Dist: {dist:.2f}m")

    # Disegna i dispositivi rilevati
    fig.add_trace(go.Scatter(
        x=target_x,
        y=target_y,
        mode='markers+text',
        marker=dict(size=18, color=colors, line=dict(width=2, color='White')),
        text=[t.split('<br>')[0].replace('<b>','').replace('</b>','') for t in target_texts],
        textposition="bottom center",
        hovertext=target_texts,
        hoverinfo='text',
        name='Dispositivi BLE'
    ))

    fig.update_layout(
        xaxis=dict(range=[-3, 13], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-3, 22], showgrid=False, zeroline=False, visible=False),
        width=800,
        height=650,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark",
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Registro dati
    st.subheader("📋 Registro Dispositivi Rilevati (Multi-Nodo)")
    display_cols = [col_name, col_mac, col_dist, col_event]
    if col_gw:
        display_cols.insert(0, col_gw)
        
    st.dataframe(recent_devices[display_cols], use_container_width=True)

else:
    st.warning("Verifica l'URL del foglio CSV o attendi l'arrivo dei primi dati da Google Sheets...")
