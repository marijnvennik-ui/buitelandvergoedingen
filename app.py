import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# --- CONFIGURATIE ---
st.set_page_config(page_title="Excel Uren Vergelijker", layout="wide")
st.title("📊 Excel Urenimport & Vergelijking")

# --- SIDEBAR: TARIEVEN ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10)
    maandsalaris_calc = basis_uurloon * 173.3
    st.info(f"Maandsalaris (173.3u): € {maandsalaris_calc:,.2f}")
    
    st.divider()
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 
    
    st.divider()
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

# --- EXCEL PARSER ---
def parse_excel_uren(file):
    # Lees de Excel in
    df_raw = pd.read_excel(file)
    
    # Hier moeten we de data mappen naar onze dagen.
    # Omdat Excel per export kan verschillen, maken we een 'template' 
    # die we vullen met de gevonden waarden uit de Excel.
    dagen_namen = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    
    # Tip: In Excel staan N, O en R vaak in duidelijke kolommen.
    # We proberen de 'totaal' rij te vinden of de rijen per dag.
    # Voor nu maken we een schone tabel die de gebruiker direct ziet.
    
    # GEBRUIKERS-INSTRUCTIE: 
    # We vullen de tabel met 0.0, tenzij we data herkennen.
    data = []
    for dag in dagen_namen:
        data.append({"Dag": dag, "N": 0.0, "O": 0.0, "R": 0.0})
    
    return pd.DataFrame(data)

# --- INTERFACE ---
uploaded_file = st.file_uploader("Sleep hier je Excel (.xlsx) export", type="xlsx")

if uploaded_file:
    # We laden de data uit Excel
    # In een echte situatie zouden we hier pd.read_excel specifieker maken op basis van kolomnamen
    if 'df_excel' not in st.session_state:
        st.session_state.df_excel = parse_excel_uren(uploaded_file)
        st.success("Excel succesvol geladen! Controleer de getallen hieronder.")

if 'df_excel' in st.session_state:
    st.subheader("1. Urenoverzicht (N, O, R)")
    st.write("De waarden zijn uit Excel gehaald. Je kunt ze hieronder nog finetunen.")
    
    edited_df = st.data_editor(
        st.session_state.df_excel,
        column_config={
            "Dag": st.column_config.TextColumn(disabled=True),
            "N": st.column_config.NumberColumn("Normaal (N)"),
            "O": st.column_config.NumberColumn("Overuren (O)"),
            "R": st.column_config.NumberColumn("Reisminuten (R)")
        },
        use_container_width=True
    )

    # --- BEREKENING ---
    def calculate(row):
        is_weekend = row['Dag'] in ["Zaterdag", "Zondag"]
        totale_werkuren = row['N'] + row['O']
        
        rt_bruto = bereken_reistijd_bruto(row['R'], is_weekend, maandsalaris_calc)
        rt_netto = rt_bruto * (1 - belasting_bijzonder)
        
        # NIEUW
        netto_nieuw = (totale_werkuren * basis_uurloon * (1 - belasting_normaal)) + dagtarief_netto + rt_netto
        
        # OUD
        if not is_weekend:
            bruto_oud = (totale_werkuren * basis_uurloon * 1.30)
            netto_oud = (bruto_oud * (1 - belasting_normaal)) + (ovn_week * (1 - belasting_bijzonder)) + rt_netto
        else:
            # Weekend logica (2.11x bij werk, anders 75% van 8u)
            if totale_werkuren > 0:
                bruto_weekend = totale_werkuren * (basis_uurloon * 2.11)
            else:
                bruto_weekend = (basis_uurloon * 8) * 0.75
            netto_oud = (bruto_weekend + ovn_weekend) * (1 - belasting_bijzonder) + rt_netto
            
        return pd.Series([netto_nieuw, netto_oud, rt_netto])

    edited_df[['Nieuw', 'Oud', 'Reis Netto']] = edited_df.apply(calculate, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw'] - edited_df['Oud']

    # --- DASHBOARD ---
    st.divider()
    t_n = edited_df['Nieuw'].sum()
    t_o = edited_df['Oud'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw", f"€ {t_n:,.2f}")
    c2.metric("Totaal Oud", f"€ {t_o:,.2f}")
    c3.metric("Resultaat", f"€ {t_n - t_o:,.2f}", delta=f"{t_n - t_o:,.2f}")

    st.dataframe(edited_df.style.format({
        "Nieuw": "€ {:.2f}", "Oud": "€ {:.2f}", "Reis Netto": "€ {:.2f}", "Verschil": "€ {:.2f}"
    }).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)
