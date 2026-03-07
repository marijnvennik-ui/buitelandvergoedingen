import streamlit as st
import pandas as pd
import pdfplumber
import re
from datetime import datetime, timedelta

# --- CONFIGURATIE ---
st.set_page_config(page_title="Uren & Reisvergelijker Master", layout="wide")
st.title("📊 PDF Analyse: Vergelijking Nieuw vs. Oud")

# --- SIDEBAR: ALLE TARIEVEN ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    maandsalaris = st.number_input("Vast maandsalaris (€)", value=3500.0)
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 # 50,5%
    
    st.divider()
    st.subheader("Vergoedingen")
    dagtarief_netto = st.number_input("Nieuwe Netto dagvergoeding (€)", value=50.0)
    ovn_week = st.number_input("Oude Overnachting week (€)", value=21.0)
    ovn_weekend = st.number_input("Oude Overnachting weekend (€)", value=28.0)

# --- REISTIJD FORMULE (0.607% / 0.97% / 1.21%) ---
def bereken_reistijd_bruto(minuten, is_weekend, salaris):
    uren = minuten / 60
    if not is_weekend:
        deel1 = min(uren, 1.25)
        deel2 = max(0, uren - 1.25)
        return (deel1 * (0.00607 * salaris)) + (deel2 * (0.0097 * salaris))
    else:
        return uren * (0.0121 * salaris)

# --- PDF PARSER (GEOPTIMALISEERD VOOR N, O, R) ---
def parse_uren_pdf(file):
    dagen_namen = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    data = []
    
    with pdfplumber.open(file) as pdf:
        text = pdf.pages[0].extract_text()
        # We zoeken de regel die begint met 'totaal'
        lines = text.split('\n')
        totaal_line = [l for l in lines if "totaal" in l.lower()]
        
        if totaal_line:
            # Zoek alle getallen (ook met komma's)
            getallen = re.findall(r"\d+(?:,\d+)?", totaal_line[0])
            getallen = [g.replace(',', '.') for g in getallen]
            
            # Op basis van de PDF snippet: N en R/O staan vaak om en om
            # We maken een veilige mapping, maar de gebruiker kan editen
            for i, dag in enumerate(dagen_namen):
                data.append({
                    "Dag": dag,
                    "N (Normaal)": float(getallen[i+1]) if (i+1) < len(getallen) else 0.0,
                    "O (Overuren)": 0.0,
                    "R (Reisminuten)": 0.0,
                    "Gewerkt": False
                })
        else:
            # Fallback leeg schema
            for dag in dagen_namen:
                data.append({"Dag": dag, "N (Normaal)": 0.0, "O (Overuren)": 0.0, "R (Reisminuten)": 0.0, "Gewerkt": False})
    
    return pd.DataFrame(data)

# --- INTERFACE ---
uploaded_file = st.file_uploader("Upload urenlijst PDF", type="pdf")

if uploaded_file:
    if 'df_data' not in st.session_state:
        st.session_state.df_data = parse_uren_pdf(uploaded_file)
    
    st.subheader("1. Ingelezen Gegevens (N, O, R)")
    st.info("Check de waarden. S (standplaats) is genegeerd. Vul bij 'R' de reisminuten in (bijv. 450).")
    
    edited_df = st.data_editor(
        st.session_state.df_data,
        column_config={
            "Dag": st.column_config.TextColumn(disabled=True),
            "N (Normaal)": st.column_config.NumberColumn("Uren (N)"),
            "O (Overuren)": st.column_config.NumberColumn("Overuren (O)"),
            "R (Reisminuten)": st.column_config.NumberColumn("Reisminuten (R)"),
            "Gewerkt": st.column_config.CheckboxColumn("Weekend Werk?")
        },
        use_container_width=True
    )

    # --- BEREKENING ---
    def calculate_comparison(row):
        is_weekend = row['Dag'] in ["Zaterdag", "Zondag"]
        uren_totaal = row['N (Normaal)'] + row['O (Overuren)']
        
        # Reistijd Netto
        rt_bruto = bereken_reistijd_bruto(row['R (Reisminuten)'], is_weekend, maandsalaris)
        rt_netto = rt_bruto * (1 - belasting_bijzonder)
        
        # NIEUW
        netto_basis = (uren_totaal * basis_uurloon) * (1 - belasting_normaal)
        nieuw_totaal = netto_basis + dagtarief_netto + rt_netto
        
        # OUD
        if not is_weekend:
            bruto_oud = (uren_totaal * basis_uurloon * 1.30)
            netto_oud = (bruto_oud * (1 - belasting_normaal)) + (ovn_week * (1 - belasting_bijzonder)) + rt_netto
        else:
            if row['Gewerkt'] or uren_totaal > 0:
                bruto_weekend = uren_totaal * (basis_uurloon * 2.11)
            else:
                bruto_weekend = (basis_uurloon * 8) * 0.75
            netto_oud = (bruto_weekend + ovn_weekend) * (1 - belasting_bijzonder) + rt_netto
            
        return pd.Series([nieuw_totaal, netto_oud, rt_netto])

    edited_df[['Nieuw (Netto)', 'Oud (Netto)', 'Reistijd (Netto)']] = edited_df.apply(calculate_comparison, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw (Netto)'] - edited_df['Oud (Netto)']

    # --- TOTALEN ---
    st.divider()
    t_n = edited_df['Nieuw (Netto)'].sum()
    t_o = edited_df['Oud (Netto)'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw", f"€ {t_n:,.2f}")
    c2.metric("Totaal Oud", f"€ {t_o:,.2f}")
    c3.metric("Resultaat", f"€ {t_n - t_o:,.2f}", delta=f"{t_n - t_o:,.2f}")

    st.subheader("Gedetailleerd overzicht")
    st.dataframe(edited_df.style.format({
        "Nieuw (Netto)": "€ {:.2f}", 
        "Oud (Netto)": "€ {:.2f}", 
        "Verschil": "€ {:.2f}",
        "Reistijd (Netto)": "€ {:.2f}"
    }).background_gradient(subset=['Verschil'], cmap='RdYlGn'))
