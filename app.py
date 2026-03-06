import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Reisvergoeding Calculator PRO", layout="wide")

st.title("📊 Reisvergoeding Analyse: Nieuw vs. Oud")
st.markdown("""
In deze tool vergelijken we de **Nieuwe Constructie** (Netto dagvergoeding) 
met de **Oude Constructie** (75% loon doorbetaling in het weekend).
""")

# --- SIDEBAR INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    start_datum = st.date_input("Startdatum reis", datetime.now().date())
    eind_datum = st.date_input("Einddatum reis", (datetime.now() + timedelta(days=6)).date())
    
    st.divider()
    st.subheader("Tarieven")
    dagtarief_netto = st.number_input("Netto dagvergoeding (€)", value=50.0)
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    overwerk_factor = st.slider("Overwerk factor Zaterdag", 1.0, 2.0, 1.5, 0.1)

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

# Maak de interactieve tabel
if start_datum <= eind_datum:
    df_input = genereer_datum_bereik(start_datum, eind_datum)
    
    st.subheader("1. Voer je gewerkte uren in")
    st.info("Vink 'Gewerkt' aan voor de zaterdag om overuren te berekenen. Laat het uit voor de 75% vergoeding.")
    
    # Gebruik data_editor voor interactie
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
        
        # NIEUWE CONSTRUCTIE
        # Altijd netto dagvergoeding (ongeacht werk of weekend)
        nieuw_totaal = dagtarief_netto
        
        # OUDE CONSTRUCTIE
        oud_totaal = 0
        overwerk_loon = 0
        
        if is_zaterdag:
            if row['Gewerkt']:
                # Zaterdag gewerkt: Elk uur is overwerk (bijzonder tarief)
                overwerk_loon = row['Uren'] * (basis_uurloon * overwerk_factor)
                oud_totaal = overwerk_loon
            else:
                # Zaterdag NIET gewerkt: 75% van 8 uur basisloon
                oud_totaal = (basis_uurloon * 8) * 0.75
        elif is_zondag:
            # Zondag: Altijd 75% (tenzij er gewerkt wordt, maar conform jouw info is dit voor zaterdag)
            oud_totaal = (basis_uurloon * 8) * 0.75
        else:
            # Doordeweeks: Basisloon (voor de vergelijking houden we dit op 0 of basis)
            # In dit model focussen we op de extra's/verschillen
            oud_totaal = 0 

        return pd.Series([nieuw_totaal, oud_totaal, overwerk_loon])

    # Toepassen logica
    edited_df[['Nieuw (Netto)', 'Oud (Weekend/Extra)', 'Zaterdag Overwerk']] = edited_df.apply(bereken_logica, axis=1)

    # --- RESULTATEN ---
    st.divider()
    st.subheader("2. Analyse Resultaten")
    
    col1, col2, col3 = st.columns(3)
    totaal_nieuw = edited_df['Nieuw (Netto)'].sum()
    totaal_oud = edited_df['Oud (Weekend/Extra)'].sum()
    verschil = totaal_nieuw - totaal_oud

    col1.metric("Totaal Nieuw (Netto)", f"€ {totaal_nieuw:,.2f}")
    col2.metric("Totaal Oud (Incl. 75%)", f"€ {totaal_oud:,.2f}")
    col3.metric("Verschil", f"€ {verschil:,.2f}", delta=f"{verschil:,.2f}")

    # Tabel weergave met formatting fix
    st.dataframe(
        edited_df.style.format({
            "Nieuw (Netto)": "€ {:.2f}",
            "Oud (Weekend/Extra)": "€ {:.2f}",
            "Zaterdag Overwerk": "€ {:.2f}"
        }),
        use_container_width=True
    )

else:
    st.error("Selecteer een geldige datumreeks.")
