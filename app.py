import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Netto Reisvergelijker PRO", layout="wide")
st.title("📊 Interactieve Netto Vergelijking")
st.markdown("Pas de vergoedingen aan in de zijbalk om de impact van indexering te zien.")

# --- SIDEBAR (Zelf aanpasbare vergoedingen) ---
with st.sidebar:
    st.header("⚙️ Instellingen & Indexering")
    start_datum = st.date_input("Startdatum reis", datetime.now().date())
    eind_datum = st.date_input("Einddatum reis", (datetime.now() + timedelta(days=6)).date())
    
    st.divider()
    st.subheader("Uurlonen & Belasting")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0, step=0.5)
    belasting_normaal = st.slider("Normale belasting (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = st.slider("Bijzonder tarief weekend (%)", 0.0, 60.0, 50.5) / 100
    
    st.divider()
    st.subheader("Nieuwe Regeling")
    dagtarief_netto = st.number_input("Netto dagvergoeding (€)", value=50.0, step=1.0)
    
    st.subheader("Oude Regeling (Aanpasbaar)")
    ovn_week = st.number_input("Overnachting doordeweeks (€)", value=21.0, step=0.5)
    ovn_weekend = st.number_input("Overnachting weekend (€)", value=28.0, step=0.5)
    factor_doordeweeks = st.number_input("Loonfactor doordeweeks (1.3 = +30%)", value=1.3, step=0.05)
    factor_zat = st.number_input("Overuren factor zaterdag", value=1.68, step=0.01)

# --- DATA GENERATIE ---
def genereer_data(start, eind):
    dagen = []
    huidige = start
    while huidige <= eind:
        is_weekend = huidige.weekday() >= 5
        dagen.append({
            "Datum": huidige,
            "Dag": huidige.strftime('%A'),
            "Gewerkt": not is_weekend,
            "Uren": 8 if not is_weekend else 0
        })
        huidige += timedelta(days=1)
    return pd.DataFrame(dagen)

if start_datum <= eind_datum:
    df_input = genereer_data(start_datum, eind_datum)
    
    st.subheader("1. Invoer: Pas uren/dagen aan")
    edited_df = st.data_editor(
        df_input,
        column_config={
            "Datum": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Gewerkt": st.column_config.CheckboxColumn("Gewerkt?"),
            "Uren": st.column_config.NumberColumn("Uren", min_value=0, max_value=24)
        },
        disabled=["Datum", "Dag"],
        use_container_width=True
    )

    # --- DE REKENLOGICA ---
    def apply_logic(row):
        is_weekend = row['Datum'].weekday() >= 5
        is_doordeweeks = not is_weekend
        
        # --- NIEUWE REGELING (NETTO) ---
        netto_loon_normaal = (row['Uren'] * basis_uurloon) * (1 - belasting_normaal)
        nieuw_totaal_netto = netto_loon_normaal + dagtarief_netto
        
        # --- OUDE REGELING (NETTO) ---
        if is_doordeweeks:
            # Loon inclusief toeslag factor (1.3)
            bruto_loon = (row['Uren'] * basis_uurloon) * factor_doordeweeks
            # Netto resultaat: loon (normaal tarief) + overnachting (bijzonder tarief)
            netto_oud = (bruto_loon * (1 - belasting_normaal)) + (ovn_week * (1 - belasting_bijzonder))
            
        else: # Weekend
            if row['Gewerkt']:
                # Gewerkt: Overuren factor
                bruto_loon = row['Uren'] * (basis_uurloon * factor_zat)
            else:
                # Niet gewerkt: 75% van 8 uur basisloon
                bruto_loon = (basis_uurloon * 8) * 0.75
            
            # Alles in het weekend (loon + overnachting) tegen bijzonder tarief
            netto_oud = (bruto_loon + ovn_weekend) * (1 - belasting_bijzonder)
                
        return pd.Series([nieuw_totaal_netto, netto_oud])

    # Uitvoeren
    edited_df[['Nieuw (Netto)', 'Oud (Netto)']] = edited_df.apply(apply_logic, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw (Netto)'] - edited_df['Oud (Netto)']

    # --- VISUALISATIE ---
    st.divider()
    t_nieuw = edited_df['Nieuw (Netto)'].sum()
    t_oud = edited_df['Oud (Netto)'].sum()
    v = t_nieuw - t_oud

    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw (Netto)", f"€ {t_nieuw:,.2f}")
    c2.metric("Totaal Oud (Netto)", f"€ {t_oud:,.2f}")
    c3.metric("Verschil", f"€ {v:,.2f}", delta=f"{v:,.2f}")

    # Grafiek voor indexering vergelijking
    st.subheader("Verloop van het netto verschil")
    st.bar_chart(data=edited_df, x="Datum", y="Verschil", color="#28a745" if v > 0 else "#dc3545")

    # Tabel
    st.subheader("Gedetailleerd overzicht")
    money_cols = ['Nieuw (Netto)', 'Oud (Netto)', 'Verschil']
    st.dataframe(
        edited_df.style.format({col: "€ {:.2f}" for col in money_cols})
                       .background_gradient(subset=['Verschil'], cmap='RdYlGn'),
        use_container_width=True
    )

else:
    st.error("Selecteer een geldige datumreeks.")
