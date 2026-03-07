import streamlit as st
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
import numpy as np
import re

# --- CONFIGURATIE ---
st.set_page_config(page_title="Uren & Reisvergelijker PRO", layout="wide")
st.title("📊 Sleep je PDF voor Directe Vergelijking")

# --- SIDEBAR: INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Tarieven")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10)
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

# --- PDF PARSER VOOR JOUW SPECIFIEKE LAYOUT ---
def parse_custom_pdf(file):
    days_names = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    extracted_data = []
    
    with pdfplumber.open(file) as pdf:
        table = pdf.pages[0].extract_table()
        if not table:
            return None
        
        # We zoeken de rij die begint met een projectnummer (bijv. 32510032)
        project_row = None
        for row in table:
            if row[0] and re.match(r'^\d{4,}', str(row[0])):
                project_row = row
                break
        
        if project_row:
            # In de PDF staan de dagen van Ma t/m Zo vanaf kolom-index 3 t/m 9
            for i in range(7):
                cell = project_row[i+3] if (i+3) < len(project_row) else ""
                n_val, o_val, r_val = 0.0, 0.0, 0.0
                
                if cell:
                    # Split op regeleinden (\n) zoals in jouw PDF
                    parts = [p.strip().replace(',', '.') for p in str(cell).split('\n')]
                    
                    # Logica op basis van jouw PDF structuur:
                    # De N staat vaak bovenaan, maar bij overuren staat O soms boven N.
                    # We gebruiken een slimme filter om getallen te vinden
                    nums = [float(p) for p in parts if re.match(r'^\d+(\.\d+)?$', p)]
                    
                    # Toewijzing op basis van positie en dag
                    is_weekend = i >= 5
                    if not is_weekend:
                        n_val = nums[0] if len(nums) > 0 else 0.0
                        # Als er 2 getallen staan doordeweeks: 2e is vaak Reisminuten (R) of Overuren (O)
                        if len(nums) > 1:
                            if nums[1] > 24: r_val = nums[1] # Reisminuten zijn vaak grote getallen
                            else: o_val = nums[1]
                    else:
                        # In het weekend telt elk uur als Overuur (O)
                        o_val = sum(nums)
                
                extracted_data.append({"Dag": days_names[i], "N": n_val, "O": o_val, "R": r_val})
    
    return pd.DataFrame(extracted_data) if extracted_data else None

# --- APP FLOW ---
uploaded_file = st.file_uploader("Sleep hier je 'Week 2.pdf' urenlijst naar binnen", type="pdf")

if uploaded_file:
    parsed_df = parse_custom_pdf(uploaded_file)
    if parsed_df is not None:
        st.success("PDF succesvol uitgelezen!")
        st.session_state.df_data = parsed_df
    else:
        st.error("Kon de uren-tabel niet vinden in deze PDF. Controleer het formaat.")

# Als er data is (uit PDF of handmatig)
if 'df_data' in st.session_state:
    st.subheader("1. Gecontroleerde uren uit PDF")
    
    # Gebruiker kan nog steeds editen voor de zekerheid
    edited_df = st.data_editor(
        st.session_state.df_data,
        column_config={
            "Dag": st.column_config.TextColumn(disabled=True),
            "N": st.column_config.NumberColumn("Normaal (N)"),
            "O": st.column_config.NumberColumn("Overuren (O)"),
            "R": st.column_config.NumberColumn("Reisminuten (R)")
        },
        use_container_width=True
    )

    # --- BEREKENINGEN ---
    def run_calc(row):
        is_weekend = row['Dag'] in ["Zaterdag", "Zondag"]
        uren_totaal = row['N'] + row['O']
        
        rt_bruto = bereken_reistijd_bruto(row['R'], is_weekend, maandsalaris_calc)
        rt_netto = rt_bruto * (1 - belasting_bijzonder)
        
        # NIEUW
        netto_basis = (uren_totaal * basis_uurloon) * (1 - belasting_normaal)
        nieuw_totaal = netto_basis + dagtarief_netto + rt_netto
        
        # OUD
        if not is_weekend:
            bruto_oud = (uren_totaal * basis_uurloon * 1.30)
            netto_oud = (bruto_oud * (1 - belasting_normaal)) + (ovn_week * (1 - belasting_bijzonder)) + rt_netto
        else:
            if uren_totaal > 0:
                bruto_weekend = uren_totaal * (basis_uurloon * 2.11)
            else:
                bruto_weekend = (basis_uurloon * 8) * 0.75
            netto_oud = (bruto_weekend + ovn_weekend) * (1 - belasting_bijzonder) + rt_netto
            
        return pd.Series([nieuw_totaal, netto_oud, rt_netto])

    edited_df[['Nieuw', 'Oud', 'Reis Netto']] = edited_df.apply(run_calc, axis=1)
    edited_df['Verschil'] = edited_df['Nieuw'] - edited_df['Oud']

    # --- DASHBOARD ---
    st.divider()
    t_nieuw = edited_df['Nieuw'].sum()
    t_oud = edited_df['Oud'].sum()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Totaal Nieuw", f"€ {t_nieuw:,.2f}")
    col2.metric("Totaal Oud", f"€ {t_oud:,.2f}")
    col3.metric("Netto Verschil", f"€ {t_nieuw - t_oud:,.2f}", delta=f"{t_nieuw - t_oud:,.2f}")

    st.subheader("Gedetailleerde Analyse")
    st.dataframe(edited_df.style.format({
        "Nieuw": "€ {:.2f}", "Oud": "€ {:.2f}", "Reis Netto": "€ {:.2f}", "Verschil": "€ {:.2f}"
    }).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)
