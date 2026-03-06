import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Reisvergoeding Calculator PRO", layout="wide")

st.title("📊 Reisvergoeding Analyse: Nieuw vs. Oud")
st.markdown("""
Vergelijking tussen de **Nieuwe Constructie** (Netto dagvergoeding) 
en de **Oude Constructie** (Loon + weekendvergoedingen).
""")

# --- SIDEBAR INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    start_datum = st.date_input("Startdatum reis", datetime.now().date())
    eind_datum = st.date_input("Einddatum reis", (datetime.now() + timedelta(days=6)).date())
    
    st.divider()
    st.subheader("Tarieven & Factoren")
    dagtarief_netto = st.number_input("Netto dagvergoeding (€)", value=50.0)
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    
    st.info("Oude Constructie Factoren:")
    doordeweeks_toeslag = st.slider("Doordeweekse toeslag (bijv. 30%)", 1.0, 2.0, 1.3, 0.05)
    overwerk_factor_zat = st.slider("Overwerk factor Zaterdag", 1.0, 2.0, 1.5, 0.1)

# --- DATA VOORBEREIDING ---
def genereer_datum_bereik(start, eind):
    dagen = []
    huidige = start
    while huidige <= eind:
        is_weekend = huidige.weekday() >= 5
        dagen.append({
            "Datum": huidige,
            "Dag": huidige.strftime('%A'),
            "Gewerkt": False if is_weekend else True,
            "Uren": 8 if huidige.weekday() < 5 else 0
        })
        huidige += timedelta(days=1)
    return pd.DataFrame(dagen)

if start_datum <= eind_datum:
    df_input = genereer_datum_bereik(start_datum, eind_datum)
    
    st.subheader("1. Controleer gewerkte uren")
    edited_df = st.data_editor(
        df_input,
        column_config={
            "Datum": st.column_config.DateColumn(format="DD-MM-YYYY"),
            "Gewerkt": st.column_config.CheckboxColumn("Gewerkt?"),
            "Uren": st.column_config.NumberColumn("Aantal uren", min_value=0, max_value=24)
        },
        disabled=["Datum", "Dag"],
        use_container_width=True
    )

    # --- BEREKENINGEN ---
    def bereken_logica(row):
        is_zaterdag = row['Datum'].weekday() == 5
        is_zondag = row['Datum'].weekday() == 6
        is_doordeweeks = row['Datum'].weekday() < 5
        
        # 1. NIEUWE CONSTRUCTIE
        # Altijd de vaste netto dagvergoeding [cite: 4]
        nieuw_totaal = dagtarief_netto
        
        # 2. OUDE CONSTRUCTIE
        oud_totaal = 0
        
        if is_zaterdag:
            if row['Gewerkt']:
                # Zaterdag gewerkt: Elk uur is overwerk 
                oud_totaal = row['Uren'] * (basis_uurloon * overwerk_factor_zat)
            else:
                # Zaterdag NIET gewerkt: 75% vergoeding [cite: 9]
                oud_totaal = (basis_uurloon * 8) * 0.75
        elif is_zondag:
            # Zondag: Altijd 75% vergoeding (indien niet gewerkt) [cite: 10]
            oud_totaal = (basis_uurloon * 8) * 0.75
        elif is_doordeweeks:
            # Doordeweeks: Basisloon + de 30% toeslag
            oud_totaal = row['Uren'] * (basis_uurloon * doordeweeks_toeslag)

        return pd.Series([nieuw_totaal, oud_totaal])

    # Berekeningen uitvoeren
    edited_df[['Nieuw (Netto)', 'Oud (Incl. Toeslagen)']] = edited_df.apply(bereken_logica, axis=1)

    # --- DISPLAY ---
    st.divider()
    st.subheader("2. Resultaten & Vergelijking")
    
    totaal_nieuw = edited_df['Nieuw (Netto)'].sum()
    totaal_oud = edited_df['Oud (Incl. Toeslagen)'].sum()
    verschil = totaal_nieuw - totaal_oud

    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw", f"€ {totaal_nieuw:,.2f}")
    c2.metric("Totaal Oud", f"€ {totaal_oud:,.2f}")
    c3.metric("Verschil", f"€ {verschil:,.2f}", delta=f"{verschil:,.2f}")

    # Formattering fix voor de tabel (voorkomt de ValueError uit het transcript) 
    numeric_cols = ['Nieuw (Netto)', 'Oud (Incl. Toeslagen)']
    st.dataframe(
        edited_df.style.format({col: "€ {:.2f}" for col in numeric_cols}),
        use_container_width=True
    )

else:
    st.error("De einddatum moet na de startdatum liggen.")
