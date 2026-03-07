import streamlit as st
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="Uren & Reisvergelijker Master", layout="wide")
st.title("📊 Definitieve Vergelijking: Nieuw vs. Oud")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10)
    # De 173.3 regel
    maandsalaris_calc = basis_uurloon * 173.3
    st.info(f"Berekend maandsalaris: € {maandsalaris_calc:,.2f}")
    
    st.divider()
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 
    
    st.divider()
    st.subheader("Vergoedingen")
    dagtarief_netto = st.number_input("Nieuwe Netto dagvergoeding (€)", value=50.0)
    ovn_week = st.number_input("Oude Overnachting week (Bruto)", value=21.0)
    ovn_weekend = st.number_input("Oude Overnachting weekend (Bruto)", value=28.0)

# --- REISTIJD FORMULE ---
def bereken_reistijd_bruto(minuten, is_weekend, salaris):
    uren = minuten / 60
    if not is_weekend:
        deel1 = min(uren, 1.25)
        deel2 = max(0, uren - 1.25)
        return (deel1 * (0.00607 * salaris)) + (deel2 * (0.0097 * salaris))
    else:
        return uren * (0.0121 * salaris)

# --- DATA INITIALISATIE (Week 2 uren) ---
if 'df_data' not in st.session_state:
    data = [
        {"Dag": "Maandag", "N": 8.0, "O": 0.0, "R": 450.0},
        {"Dag": "Dinsdag", "N": 8.0, "O": 0.0, "R": 450.0},
        {"Dag": "Woensdag", "N": 8.0, "O": 3.5, "R": 0.0},
        {"Dag": "Donderdag", "N": 8.0, "O": 3.0, "R": 0.0},
        {"Dag": "Vrijdag", "N": 8.0, "O": 2.5, "R": 0.0},
        {"Dag": "Zaterdag", "N": 0.0, "O": 6.5, "R": 0.0},
        {"Dag": "Zondag", "N": 0.0, "O": 0.0, "R": 0.0},
    ]
    st.session_state.df_data = pd.DataFrame(data)

# --- INTERFACE ---
st.subheader("1. Urenoverzicht (N, O, R)")
edited_df = st.data_editor(
    st.session_state.df_data,
    column_config={
        "Dag": st.column_config.TextColumn(disabled=True),
        "N": st.column_config.NumberColumn("Normaal (N)", format="%.1f"),
        "O": st.column_config.NumberColumn("Overuren (O)", format="%.1f"),
        "R": st.column_config.NumberColumn("Reisminuten (R)", format="%d")
    },
    use_container_width=True
)

# --- BEREKENING LOGICA ---
def calculate_all(row):
    is_weekend = row['Dag'] in ["Zaterdag", "Zondag"]
    uren_totaal = row['N'] + row['O']
    
    # Reistijd Netto
    rt_bruto = bereken_reistijd_bruto(row['R'], is_weekend, maandsalaris_calc)
    rt_netto = rt_bruto * (1 - belasting_bijzonder)
    
    # --- NIEUW ---
    netto_basis = (uren_totaal * basis_uurloon) * (1 - belasting_normaal)
    nieuw_totaal = netto_basis + dagtarief_netto + rt_netto
    
    # --- OUD ---
    if not is_weekend:
        bruto_oud_loon = (uren_totaal * basis_uurloon * 1.30)
        netto_oud = (bruto_oud_loon * (1 - belasting_normaal)) + (ovn_week * (1 - belasting_bijzonder)) + rt_netto
    else:
        # Weekend: 2.11 bij werk, 75% vergoeding bij rust
        if uren_totaal > 0:
            bruto_weekend = uren_totaal * (basis_uurloon * 2.11)
        else:
            bruto_weekend = (basis_uurloon * 8) * 0.75
        netto_oud = (bruto_weekend + ovn_weekend) * (1 - belasting_bijzonder) + rt_netto
            
    return pd.Series([nieuw_totaal, netto_oud, rt_netto])

edited_df[['Nieuw', 'Oud', 'Reis Netto']] = edited_df.apply(calculate_all, axis=1)
edited_df['Verschil'] = edited_df['Nieuw'] - edited_df['Oud']

# --- VISUALISATIE ---
st.divider()
c1, c2, c3 = st.columns(3)
t_nieuw = edited_df['Nieuw'].sum()
t_oud = edited_df['Oud'].sum()
c1.metric("Totaal Nieuw (Netto)", f"€ {t_nieuw:,.2f}")
c2.metric("Totaal Oud (Netto)", f"€ {t_oud:,.2f}")
c3.metric("Netto Verschil", f"€ {t_nieuw - t_oud:,.2f}", delta=f"{t_nieuw - t_oud:,.2f}")

# Grafiek
st.subheader("Visuele Vergelijking per Dag")
fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(len(edited_df['Dag']))
width = 0.35
ax.bar(x - width/2, edited_df['Oud'], width, label='Oud', color='#FF4B4B')
ax.bar(x + width/2, edited_df['Nieuw'], width, label='Nieuw', color='#00CC96')
ax.set_xticks(x)
ax.set_xticklabels(edited_df['Dag'])
ax.legend()
st.pyplot(fig)

st.subheader("2. Gedetailleerde Tabel")
st.dataframe(edited_df.style.format({
    "Nieuw": "€ {:.2f}", "Oud": "€ {:.2f}", "Reis Netto": "€ {:.2f}", "Verschil": "€ {:.2f}"
}).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)
