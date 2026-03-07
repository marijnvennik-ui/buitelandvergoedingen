import streamlit as st
import pandas as pd
import pdfplumber
import re

# --- CONFIGURATIE ---
st.set_page_config(page_title="Uren & Reisvergelijker PRO", layout="wide")
st.title("📊 PDF Uren Analyse (N, O, R)")

# --- SIDEBAR: INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Tarieven & Belasting")
    maandsalaris = st.number_input("Vast maandsalaris (€)", value=3500.0)
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=20.0)
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505
    
    st.divider()
    dagtarief_netto = st.number_input("Nieuwe Netto dagvergoeding (€)", value=50.0)
    ovn_week = st.number_input("Oude Overnachting week (€)", value=21.0)
    ovn_weekend = st.number_input("Oude Overnachting weekend (€)", value=28.0)

# --- LOGICA: REISTIJD ---
def bereken_reistijd_bruto(minuten, is_weekend, salaris):
    uren = minuten / 60
    if not is_weekend:
        deel1 = min(uren, 1.25)
        deel2 = max(0, uren - 1.25)
        return (deel1 * (0.00607 * salaris)) + (deel2 * (0.0097 * salaris))
    else:
        return uren * (0.0121 * salaris)

# --- VERBETERDE PDF PARSER (VOOR GESTAPELDE RIJEN) ---
def extract_data_from_pdf(file):
    days_data = []
    days_names = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    
    with pdfplumber.open(file) as pdf:
        # We extraheren de tabel direct (pdfplumber is goed in tabel-lijnen herkennen)
        table = pdf.pages[0].extract_table()
        
        if table:
            # We zoeken naar de rij waar de uren in staan (vaak onder de dag-headers)
            # In jouw PDF is dit meestal de rij met het projectnummer
            for row in table:
                if row[0] and row[0].isdigit(): # Checkt of eerste cel een projectnummer is
                    # De kolommen in jouw PDF zijn vaak gegroepeerd per dag
                    # We mappen de kolommen naar de dagen
                    for i in range(7):
                        cell_content = row[i+3] if (i+3) < len(row) else "" # Uren starten vaak bij index 3
                        if cell_content:
                            # Split de gestapelde waarden (N, O, R) die pdfplumber vaak als \n ziet
                            parts = cell_content.split('\n')
                            n_val = float(parts[0].replace(',', '.')) if len(parts) > 0 and parts[0].strip().replace(',','').isdigit() else 0.0
                            r_val = float(parts[1].replace(',', '.')) if len(parts) > 1 and parts[1].strip().replace(',','').isdigit() else 0.0
                            # S overslaan (meestal 3e positie in de stapel)
                            
                            days_data.append({
                                "Dag": days_names[i],
                                "N (Normaal)": n_val,
                                "O (Overuren)": 0.0, # Kan ook in parts zitten
                                "R (Reisminuten)": r_val if r_val > 10 else 0.0, # Filter voor S-vlaggen
                                "Gewerkt": False
                            })
                    break

    if not days_data: # Fallback
        for name in days_names:
            days_data.append({"Dag": name, "N (Normaal)": 0.0, "O (Overuren)": 0.0, "R (Reisminuten)": 0.0, "Gewerkt": False})
    
    return pd.DataFrame(days_data)

# --- UI ---
uploaded_file = st.file_uploader("Upload Week PDF", type="pdf")

if uploaded_file:
    if 'df_uren' not in st.session_state:
        st.session_state.df_uren = extract_data_from_pdf(uploaded_file)
    
    st.subheader("1. Ingelezen Gegevens (N, O, R)")
    st.info("De software heeft de gestapelde rijen uit de PDF gelezen. Controleer de waarden hieronder.")
    
    edited_df = st.data_editor(
        st.session_state.df_uren,
        column_config={
            "Dag": st.column_config.TextColumn(disabled=True),
            "N (Normaal)": st.column_config.NumberColumn("Uren (N)"),
            "O (Overuren)": st.column_config.NumberColumn("Overuren (O)"),
            "R (Reisminuten)": st.column_config.NumberColumn("Reisminuten (R)"),
            "Gewerkt": st.column_config.CheckboxColumn("Weekend Gewerkt?")
        },
        use_container_width=True
    )

    # --- BEREKENING ---
    def calculate(row):
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

    edited_df[['Nieuw', 'Oud', 'Reis Netto']] = edited_df.apply(calculate, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw'] - edited_df['Oud']

    # --- TOTALEN ---
    st.divider()
    t_n = edited_df['Nieuw'].sum()
    t_o = edited_df['Oud'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Totaal Nieuw", f"€ {t_n:,.2f}")
    c2.metric("Totaal Oud", f"€ {t_o:,.2f}")
    c3.metric("Netto Verschil", f"€ {t_n - t_o:,.2f}", delta=f"{t_n - t_o:,.2f}")

    st.dataframe(edited_df.style.format({
        "Nieuw": "€ {:.2f}", "Oud": "€ {:.2f}", "Reis Netto": "€ {:.2f}", "Verschil": "€ {:.2f}"
    }))
