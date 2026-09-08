import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go

# 1. CONFIGURAZIONE PAGINA
st.set_page_config(
    page_title="SOC // BLE TACTICAL MAP",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. STILE CYBERPUNK / HACKER TERMINAL (CSS)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600;700&display=swap');

    html, body, [class*="css"], .stApp {
        background-color: #080c10 !important;
        font-family: 'Fira Code', monospace !important;
        color: #00ff66 !important;
    }

    h1, h2, h3, h4 {
        font-family: 'Fira Code', monospace !important;
        color: #00f0ff !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        text-shadow: 0 0 8px rgba(0, 240, 255, 0.4);
    }

    div[data-testid="stMetric"] {
        background: #0d131a !important;
        border: 1px solid #00f0ff !important;
        box-shadow: 0 0 10px rgba(0, 240, 255, 0.15) !important;
        border-radius: 4px !important;
        padding: 12px !important;
    }

    div[data-testid="stMetricLabel"] { color: #88a0b0 !important; font-size: 0.8rem !important; }
    div[data-testid="stMetricValue"] { color: #00ff66 !important; text-shadow: 0 0 10px rgba(0, 255, 102, 0.5) !important; }

    .status-alert {
        padding: 12px; border-radius: 4px; font-weight: bold; text-align: center; letter-spacing: 1px;
    }
    .status-danger {
        background-color: rgba(255, 0, 85, 0.2); border: 1px solid #ff0055; color: #ff0055; box-shadow: 0 0 15px rgba(255, 0, 85, 0.4);
    }
    .status-safe {
        background-color: rgba(0, 255, 102, 0.1); border: 1px solid #00ff66; color: #00ff66; box-shadow: 0 0 12px rgba(0, 255, 102, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# 3. INTESTAZIONE TERMINALE
st.markdown("### 📡 [SOC] BLE RADAR & HOUSE PERIMETER MAP")
st.caption("TACTICAL DISPLAY // REAL-TIME SPATIAL PROXIMITY TRACKING")

# ⚠️ SOSTITUISCI CON IL TUO ID SCRIPT REALE DI GOOGLE APPS SCRIPT
URL = "https://script.google.com/macros/sAKfycbyW6iY08lTa5ET3M9nsIm-J393Tawv9K_52xE_hyYKydK69Q-j9ywlAgTcFhRYzrYGc/exec?format=json"

# --- FUNZIONE FRAGMENT PER AUTO-REFRESH NATIVO OGNI 3 SECONDI ---
@st.fragment(run_every=3)
def render_live_dashboard():
    try:
        response = requests.get(URL, timeout=10, allow_redirects=True)
        
        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                df = pd.DataFrame(data)

                col_event = next((c for c in df.columns if 'event' in str(c).lower() or 'evento' in str(c).lower()), df.columns[1] if len(df.columns) > 1 else None)
                col_mac = next((c for c in df.columns if 'mac' in str(c).lower()), df.columns[3] if len(df.columns) > 3 else None)
                col_dist = next((c for c in df.columns if 'dist' in str(c).lower()), df.columns[5] if len(df.columns) > 5 else None)
                col_name = next((c for c in df.columns if 'name' in str(c).lower() or 'nome' in str(c).lower()), df.columns[2] if len(df.columns) > 2 else None)

                last_event = str(df[col_event].iloc[0]) if col_event and not df.empty else "NO_DATA"
                is_alarm = "ENTRATO" in last_event.upper()

                if is_alarm:
                    st.markdown(f'<div class="status-alert status-danger">⚠️ INTRUDER BREACH DETECTED // STATE: {last_event}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="status-alert status-safe">🛡️ PERIMETER SECURE // STATE: {last_event}</div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col_map, col_stats = st.columns([2, 1])

                with col_map:
                    st.markdown("#### 📐 PLANIMETRIA CASA & PERIMETRO BLE")

                    fig = go.Figure()

                    # 1. Sagoma Edificio Principale
                    house_x = [-5, 5, 5, -5, -5]
                    house_y = [-6, -6, 6, 6, -6]

                    fig.add_trace(go.Scatter(
                        x=house_x, y=house_y,
                        fill="toself",
                        fillcolor="rgba(0, 240, 255, 0.12)",
                        line=dict(color='#00f0ff', width=3),
                        name='Abitazione',
                        hoverinfo='text',
                        text='🏠 EDIFICIO PRINCIPALE'
                    ))

                    # 2. Delimitazione Strada (EST)
                    fig.add_trace(go.Scatter(
                        x=[9, 9], y=[-15, 15],
                        mode='lines',
                        line=dict(color='rgba(255, 255, 255, 0.3)', width=4, dash='dash'),
                        name='Strada',
                        hoverinfo='text',
                        text='🛣️ STRADA / VIA PUBBLICA (EST)'
                    ))

                    # 3. Etichette Cardinali
                    fig.add_annotation(x=0, y=6.8, text="<b>NORD (Retro)</b>", showarrow=False, font=dict(color="#00f0ff", size=10))
                    fig.add_annotation(x=0, y=-6.8, text="<b>SUD (Casa dei Gelsi)</b>", showarrow=False, font=dict(color="#00f0ff", size=10))
                    fig.add_annotation(x=-5.8, y=0, text="<b>OVEST (Giardino)</b>", showarrow=False, font=dict(color="#00f0ff", size=10), textangle=-90)
                    fig.add_annotation(x=5.8, y=0, text="<b>EST (Ingresso / Strada)</b>", showarrow=False, font=dict(color="#00f0ff", size=10), textangle=90)

                    # 4. Centralina ESP32
                    fig.add_trace(go.Scatter(
                        x=[0], y=[0],
                        mode='markers+text',
                        marker=dict(size=14, color='#00ff66', symbol='hexagram-open', line=dict(width=2, color='#00ff66')),
                        text=['ESP32 GATEWAY'],
                        textposition='top center',
                        textfont=dict(color='#00ff66', family='Fira Code', size=11),
                        name='Gateway'
                    ))

                    # 5. Anelli Radar
                    angles = np.linspace(0, 2*np.pi, 100)
                    for r in [5, 8, 15]:
                        fig.add_trace(go.Scatter(
                            x=r*np.cos(angles), y=r*np.sin(angles),
                            mode='lines',
                            line=dict(color='rgba(0, 240, 255, 0.15)', width=1, dash='dot'),
                            showlegend=False, hoverinfo='none'
                        ))

                    # 6. Target BLE
                    if col_mac and col_dist:
                        df['Distanza_Num'] = pd.to_numeric(df[col_dist], errors='coerce').fillna(0)
                        recent_devices = df.drop_duplicates(subset=[col_mac]).head(8)

                        np.random.seed(42)
                        angles_assigned = np.linspace(0.3, 2*np.pi - 0.3, len(recent_devices))

                        target_x, target_y, target_texts, colors = [], [], [], []

                        for idx, (_, row) in enumerate(recent_devices.iterrows()):
                            dist = row['Distanza_Num']
                            if dist <= 0: dist = 2.0
                            
                            angle = angles_assigned[idx]
                            x = dist * np.cos(angle)
                            y = dist * np.sin(angle)

                            mac_str = str(row[col_mac])
                            evt_str = str(row[col_event]) if col_event else ""

                            target_x.append(x)
                            target_y.append(y)
                            target_texts.append(f"MAC: {mac_str}<br>Dist: {dist:.2f}m<br>Evento: {evt_str}")

                            if "ENTRATO" in evt_str.upper():
                                colors.append('#ff0055')
                            elif "PRESENTE" in evt_str.upper():
                                colors.append('#ffcc00')
                            else:
                                colors.append('#00ff66')

                        fig.add_trace(go.Scatter(
                            x=target_x, y=target_y,
                            mode='markers+text',
                            marker=dict(size=16, color=colors, line=dict(width=2, color='#ffffff')),
                            text=[f"  {row[col_mac]}" for _, row in recent_devices.iterrows()],
                            textposition='top right',
                            textfont=dict(color='#ffffff', family='Fira Code', size=10),
                            hoverinfo='text',
                            hovertext=target_texts,
                            name='Dispositivi BLE'
                        ))

                    fig.update_layout(
                        paper_bgcolor='#080c10',
                        plot_bgcolor='#080c10',
                        margin=dict(l=20, r=20, t=30, b=20),
                        xaxis=dict(
                            range=[-18, 18], showgrid=False, zeroline=False, showticklabels=False,
                            title=dict(text="<b>◄ OVEST (Giardino)                   EST (Strada) ►</b>", font=dict(color='#00f0ff', size=11))
                        ),
                        yaxis=dict(
                            range=[-18, 18], showgrid=False, zeroline=False, showticklabels=False,
                            title=dict(text="<b>◄ SUD (Gelsi)                   NORD (Retro) ►</b>", font=dict(color='#00f0ff', size=11))
                        ),
                        showlegend=False,
                        height=580
                    )

                    st.plotly_chart(fig, use_container_width=True)

                with col_stats:
                    st.markdown("#### 📊 TELEMETRY STATS")
                    st.metric(label="DEVICES IN RANGE", value=f"{len(recent_devices):02d}" if 'recent_devices' in locals() else "0")
                    
                    total_alarms = len(df[df[col_event].astype(str).str.contains('ENTRATO', na=False, case=False)]) if col_event else 0
                    st.metric(label="TOTAL BREACHES", value=f"{total_alarms:02d}")

                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown("#### 📑 ACTIVE TARGETS LOG")
                    
                    if 'recent_devices' in locals():
                        display_cols = [c for c in [col_mac, col_event, col_dist] if c is not None]
                        st.dataframe(recent_devices[display_cols], hide_index=True, use_container_width=True)

            else:
                st.warning("[!] Nessun dato restituito dall'endpoint Google Sheet.")
        else:
            st.error(f"[!] Errore HTTP {response.status_code}: Impossibile connettersi all'endpoint Google Apps Script.")

    except requests.exceptions.JSONDecodeError:
        st.error("[!] SYSTEM ERROR: Risposta ricevuta non in formato JSON. Controlla l'URL di Apps Script.")
    except Exception as e:
        st.error(f"[!] SYSTEM ERROR: {e}")

# Esecuzione del Fragment live
render_live_dashboard()
