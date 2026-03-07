import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Reisvergoeding Calculator", layout="wide")
st.title("📊 Definitieve Vergelijking: Nieuw vs. Oud")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    start_datum = st.date_input("Startdatum reis", datetime.now().date())
    eind_datum = st.date_input("Einddatum reis", (datetime.now() + timedelta(days=6)).date())
    
    st.divider()
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    dagtarief_netto = st.number_input("Nieuwe Netto dagvergoeding (€)", value=50.0)
    
    st.divider()
    st.subheader("Oude Regeling Factoren")
    toeslag_doordeweeks = 0.30  # De 30% extra bovenop loon
    factor_overuren_zat = st.slider("Overwerk factor Zaterdag", 1.0, 2.0, 1.5, 0.1)

# --- DATA GENERATIE ---
def genereer_data(start, eind):
    dagen = []
    huidige = start
    while huidige <= eind:
        # Standaard: doordeweeks 8 uur gewerkt, weekend 0 uur
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
    
    st.subheader("1. Invoer: Pas gewerkte uren/dagen aan")
    st.info("Vink 'Gewerkt' aan op zaterdag om overuren te berekenen. Laat het uit voor de 75% regeling.")
    
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
        is_zaterdag = row['Datum'].weekday() == 5
        is_zondag = row['Datum'].weekday() == 6
        is_doordeweeks = row['Datum'].weekday() < 5
        
        # --- NIEUWE REGELING ---
        # Loon voor gewerkte uren + de vaste netto dagvergoeding (altijd)
        loon_werk = row['Uren'] * basis_uurloon
        nieuw_totaal = loon_werk + dagtarief_netto
        
        # --- OUDE REGELING ---
        oud_totaal = 0
        
        if is_doordeweeks:
            # Normaal loon + 30% bruto extra
            oud_totaal = loon_werk + (loon_werk * toeslag_doordeweeks)
            
        elif is_zaterdag:
            if row['Gewerkt']:
                # Zaterdag GEWERKT: Elk uur is overwerk tarief
                oud_totaal = row['Uren'] * (basis_uurloon * factor_overuren_zat)
            else:
                # Zaterdag NIET GEWERKT: 75% van dagloon (8u)
                oud_totaal = (basis_uurloon * 8) * 0.75
                
        elif is_zondag:
            if row['Gewerkt']:
                # Zondag GEWERKT: Meestal ook overwerk, maar conform instructie:
                # (Mocht zondag een ander tarief hebben, pas factor_overuren_zat hierop aan)
                oud_totaal = row['Uren'] * (basis_uurloon * factor_overuren_zat)
            else:
                # Zondag NIET GEWERKT: 75% van dagloon (8u)
                oud_totaal = (basis_uurloon * 8) * 0.75
                
        return pd.Series([nieuw_totaal, oud_totaal])

    # Berekening toepassen
    edited_df[['Nieuwe Regeling', 'Oude Regeling']] = edited_df.apply(apply_logic, axis=1)
    edited_df['Verschil'] = edited_df['Nieuwe Regeling'] - edited_df['Oude Regeling']

    # --- VISUALISATIE & TOTALEN ---
    st.divider()
    t_nieuw = edited_df['Nieuwe Regeling'].sum()
    t_oud = edited_df['Oude Regeling'].sum()
    v = t_nieuw - t_oud

    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw (Loon + Netto)", f"€ {t_nieuw:,.2f}")
    c2.metric("Totaal Oud (Loon + Toeslag/75%)", f"€ {t_oud:,.2f}")
    c3.metric("Netto Verschil", f"€ {v:,.2f}", delta=f"{v:,.2f}")

    st.subheader("2. Details per dag")
    money_cols = ['Nieuwe Regeling', 'Oude Regeling', 'Verschil']
    
    # Formattering fix voor de datum-error
    st.dataframe(
        edited_df.style.format({col: "€ {:.2f}" for col in money_cols})
                       .applymap(lambda x: 'background-color: #d4edda' if x > 0 else 'background-color: #f8d7da', subset=['Verschil']),
        use_container_width=True
    )

else:
    st.error("Selecteer een geldige datumreeks.")
