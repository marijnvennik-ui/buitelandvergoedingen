import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Netto Reisvergelijker PRO", layout="wide")
st.title("📊 Definitieve Netto Vergelijking")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    start_datum = st.date_input("Startdatum reis", datetime.now().date())
    eind_datum = st.date_input("Einddatum reis", (datetime.now() + timedelta(days=6)).date())
    
    st.divider()
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    belasting_normaal = st.slider("Normale inkomstenbelasting (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 # Vastgesteld op 50,5%
    
    st.divider()
    st.subheader("Nieuwe Regeling")
    dagtarief_netto = st.number_input("Netto dagvergoeding (€)", value=50.0)
    
    st.subheader("Oude Regeling Factoren")
    toeslag_doordeweeks = 1.30
    factor_overuren_zat = 1.68  # Gecorrigeerd naar 1.68

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
    
    st.subheader("1. Invoer: Pas gewerkte uren/dagen aan")
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

    # --- DE REKENLOGICA (NETTO) ---
    def apply_logic(row):
        is_weekend = row['Datum'].weekday() >= 5
        is_doordeweeks = row['Datum'].weekday() < 5
        
        # --- NIEUWE REGELING (NETTO) ---
        # Normaal loon na normale belasting + de onbelaste netto vergoeding
        netto_loon_normaal = (row['Uren'] * basis_uurloon) * (1 - belasting_normaal)
        nieuw_totaal_netto = netto_loon_normaal + dagtarief_netto
        
        # --- OUDE REGELING (NETTO) ---
        oud_totaal_netto = 0
        
        if is_doordeweeks:
            # (Loon * 1.3) minus normale belasting
            bruto_doordeweeks = (row['Uren'] * basis_uurloon) * toeslag_doordeweeks
            oud_totaal_netto = bruto_doordeweeks * (1 - belasting_normaal)
            
        else: # Weekend (Zaterdag of Zondag)
            if row['Gewerkt']:
                # Weekend GEWERKT: (Loon * 1.68) minus bijzonder tarief
                bruto_weekend = row['Uren'] * (basis_uurloon * factor_overuren_zat)
                oud_totaal_netto = bruto_weekend * (1 - belasting_bijzonder)
            else:
                # Weekend NIET GEWERKT: (75% van 8u) minus bijzonder tarief
                bruto_weekend_75 = (basis_uurloon * 8) * 0.75
                oud_totaal_netto = bruto_weekend_75 * (1 - belasting_bijzonder)
                
        return pd.Series([nieuw_totaal_netto, oud_totaal_netto])

    # Berekening toepassen
    edited_df[['Nieuw (Netto)', 'Oud (Netto)']] = edited_df.apply(apply_logic, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw (Netto)'] - edited_df['Oud (Netto)']

    # --- DISPLAY ---
    st.divider()
    t_nieuw = edited_df['Nieuw (Netto)'].sum()
    t_oud = edited_df['Oud (Netto)'].sum()
    v = t_nieuw - t_oud

    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw (Netto)", f"€ {t_nieuw:,.2f}")
    c2.metric("Totaal Oud (Netto)", f"€ {t_oud:,.2f}")
    c3.metric("Netto Verschil", f"€ {v:,.2f}", delta=f"{v:,.2f}")

    st.subheader("2. Gedetailleerde Netto Berekening")
    money_cols = ['Nieuw (Netto)', 'Oud (Netto)', 'Verschil']
    
    st.dataframe(
        edited_df.style.format({col: "€ {:.2f}" for col in money_cols})
                       .background_gradient(subset=['Verschil'], cmap='RdYlGn'),
        use_container_width=True
    )

    st.warning(f"Info: Overuren en weekendvergoedingen zijn belast tegen het bijzondere tarief van {belasting_bijzonder*100}% (bruto naar netto).")

else:
    st.error("Selecteer een geldige datumreeks.")
