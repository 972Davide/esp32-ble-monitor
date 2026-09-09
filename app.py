import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Monitoraggio BLE Casa", layout="wide")

st.title("📡 Monitoraggio Presenze BLE - Planimetria Real-Time")

# --- PARAMETRI CONFIGURAZIONE GOOGLE SHEETS ---
# Sostituisci questo URL con il link CSV del tuo foglio Google Pubblicato sul Web
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQfyw4jBL1NZwI9KC4KaYEIVzcJPBOfabbBgBdF0j35liabae4rn0NbYU2lrY6-4NYsEY-MFaP0OSl8/pub?output=csv"

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(SHEET_CSV_URL)
        return df
    except Exception as e:
        st.error(f"Errore caricamento dati da Google Sheets: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # Identificazione automatica colonne
    col_mac = [c for c in df.columns if 'mac' in c.lower() or 'address' in c.lower()][0]
    col_dist = [c for c in df.columns if 'dist' in c.lower()][0]
    col_event = [c for c in df.columns if 'event' in c.lower() or 'stato' in c.lower()][0]
    col_name = [c for c in df.columns if 'name' in c.lower() or 'nome' in c.lower()][0]

    # Pre-elaborazione dati
    df[col_dist] = pd.to_numeric(df[col_dist].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    # Prende l'ultimo record registrato per ciascun indirizzo MAC
    recent_devices = df.groupby(col_mac).last().reset_index()

    # --- COSTRUZIONE MAPPA PLANIMETRIA ---
    fig = go.Figure()

    # 1. Disegna i muri perimetrali della casa (rettangolo centrale 0,0 -> 10,10 metri)
    fig.add_shape(type="rect", x0=0, y0=0, x1=10, y1=10,
                  line=dict(color="White", width=3),
                  fillcolor="rgba(255, 255, 255, 0.05)")

    # 2. Inserisce le etichette delle zone della proprietà
    fig.add_annotation(x=5, y=5, text="<b>CASA / INTERNO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=5, y=11.5, text="<b>STRADA / ESTERNO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=5, y=-1.5, text="<b>GIARDINO RETRO</b>", showarrow=False, font=dict(color="gray", size=14))
    fig.add_annotation(x=10, y=0, text="🚪 Ingresso", showarrow=False, font=dict(color="cyan", size=12))

    # 3. Posizionamento dei nodi BLE in coordinate ortogonali (X, Y)
    target_x, target_y, target_texts, colors = [], [], [], []

    for _, row in recent_devices.iterrows():
        dist = float(row[col_dist])
        evt_str = str(row[col_event]).upper()
        mac_str = str(row[col_mac])
        name_str = str(row[col_name])

        # Assegnazione coordinata reale sulla planimetria in base allo stato
        if "ENTRATO" in evt_str:
            # Posizionato vicino alla porta d'ingresso (X=10, Y=1)
            x, y = 9.5, 1.0
            color = "#ff0055" # Rosso
        elif "PRESENTE" in evt_str:
            # Posizionato all'interno dell'immobile (es. Soggiorno)
            x, y = 5.0, 5.0
            color = "#ffcc00" # Giallo
        elif "USCITO" in evt_str:
            # Posizionato all'esterno lungo la strada in base alla distanza effettiva
            x, y = 5.0, 10.0 + min(dist, 10.0)
            color = "#00ff66" # Verde
        else: # FUORI_RAGGIO
            x, y = 1.0, 10.0 + min(dist, 10.0)
            color = "#888888" # Grigio

        target_x.append(x)
        target_y.append(y)
        colors.append(color)
        target_texts.append(f"<b>{name_str}</b><br>MAC: {mac_str}<br>Evento: {evt_str}<br>Dist: {dist:.2f}m")

    # Aggiunta dei punti sulla mappa Plotly
    fig.add_trace(go.Scatter(
        x=target_x,
        y=target_y,
        mode='markers+text',
        marker=dict(size=18, color=colors, line=dict(width=2, color='White')),
        text=[t.split('<br>')[0].replace('<b>','').replace('</b>','') for t in target_texts],
        textposition="bottom center",
        hovertext=target_texts,
        hoverinfo='text'
    ))

    # Layout mappa
    fig.update_layout(
        xaxis=dict(range=[-3, 13], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(range=[-3, 22], showgrid=False, zeroline=False, visible=False),
        width=800,
        height=650,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark"
    )

    st.plotly_chart(fig, use_container_width=True)

    # Tabella riassuntiva dispositivi
    st.subheader("📋 Registro Dispositivi Rilevati")
    st.dataframe(recent_devices[[col_name, col_mac, col_dist, col_event]], use_container_width=True)

else:
    st.warning("Nessun dato trovato o in attesa di caricamento da Google Sheets...")
