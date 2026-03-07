import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="Urenvergelijker Nieuw vs. Oud", layout="wide")
st.title("📊 Definitieve Urenvergelijker (Excel Import)")

# --- SIDEBAR: INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Salaris & Belasting")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10)
    
    # Maandsalaris wordt automatisch berekend voor de reistijd-formule
    maandsalaris_calc = basis_uurloon * 173.3
    st.info(f"Berekend maandsalaris (173.3u): € {maandsalaris_calc:,.2f}")
    
    st.divider()
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 # Vast tarief voor overuren/reistijd/weekend
    
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

# --- EXCEL PARSER (Specifiek voor Rij 23) ---
def parse_excel_uren(file):
    try:
        # header=None voorkomt dat de parser in de war raakt door samengevoegde titels
        df_raw = pd.read_excel(file, header=None)
        
        if len(df_raw) < 23:
            st.error("Let op: Het Excel-bestand heeft minder dan 23 rijen.")
            return None

        # Rij 23 is index 22 in pandas
        rij_23 = df_raw.iloc[22]
        
        dagen_namen = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        data = []
        
        # Aanname: Data begint in kolom C (index 2). 
        # Maandag = index 2(N), 3(O), 4(R). Dinsdag = index 5(N), 6(O), 7(R) etc.
        start_kolom = 2 
        
        def safe_float(waarde):
            try:
                if pd.notna(waarde):
                    if isinstance(waarde, str):
                        waarde = waarde.replace(',', '.')
                    return float(waarde)
                return 0.0
            except ValueError:
                return 0.0

        for i, dag in enumerate(dagen_namen):
            idx_n = start_kolom + (i * 3)
            idx_o = start_kolom + (i * 3) + 1
            idx_r = start_kolom + (i * 3) + 2
            
            try:
                n_val = safe_float(rij_23[idx_n])
                o_val = safe_float(rij_23[idx_o])
                r_val = safe_float(rij_23[idx_r])
            except IndexError:
                n_val, o_val, r_val = 0.0, 0.0, 0.0
                
            data.append({
                "Dag": dag, 
                "N": n_val, 
                "O": o_val, 
                "R": r_val
            })
        
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fout bij het uitlezen van Excel: {e}")
        return None

# --- APP FLOW & DATA INITIALISATIE ---
uploaded_file = st.file_uploader("Sleep hier je .xlsx urenlijst naar binnen", type="xlsx")

if uploaded_file:
    parsed_df = parse_excel_uren(uploaded_file)
    if parsed_df is not None:
        st.session_state.df_data = parsed_df
        st.success("Excel succesvol uitgelezen vanaf rij 23!")

# Fallback data als er nog geen bestand is geüpload
if 'df_data' not in st.session_state:
    st.session_state.df_data = pd.DataFrame([
        {"Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

# --- TABEL WEERGAVE ---
st.subheader("1. Urenoverzicht (N, O, R)")
st.write("Controleer de uitgelezen data of pas deze handmatig aan.")

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
    
    # --- NIEUWE REGELING ---
    netto_basis = (uren_totaal * basis_uurloon) * (1 - belasting_normaal)
    nieuw_totaal = netto_basis + dagtarief_netto + rt_netto
    
    # --- OUDE REGELING ---
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

edited_df[['Nieuw (Netto)', 'Oud (Netto)', 'Reistijd (Netto)']] = edited_df.apply(calculate_all, axis=1)
edited_df['Verschil'] = edited_df['Nieuw (Netto)'] - edited_df['Oud (Netto)']

# --- DASHBOARD & VISUALISATIE ---
st.divider()
t_nieuw = edited_df['Nieuw (Netto)'].sum()
t_oud = edited_df['Oud (Netto)'].sum()

c1, c2, c3 = st.columns(3)
c1.metric("Totaal Nieuw (Netto)", f"€ {t_nieuw:,.2f}")
c2.metric("Totaal Oud (Netto)", f"€ {t_oud:,.2f}")
c3.metric("Netto Verschil", f"€ {t_nieuw - t_oud:,.2f}", delta=f"{t_nieuw - t_oud:,.2f}")

# Grafiek
st.subheader("Visuele Vergelijking per Dag")
fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(len(edited_df['Dag']))
width = 0.35
ax.bar(x - width/2, edited_df['Oud (Netto)'], width, label='Oude Regeling', color='#FF4B4B')
ax.bar(x + width/2, edited_df['Nieuw (Netto)'], width, label='Nieuwe Regeling', color='#00CC96')
ax.set_xticks(x)
ax.set_xticklabels(edited_df['Dag'])
ax.legend()
st.pyplot(fig)

# Detail tabel
st.subheader("2. Gedetailleerde Analyse")
st.dataframe(edited_df.style.format({
    "Nieuw (Netto)": "€ {:.2f}", 
    "Oud (Netto)": "€ {:.2f}", 
    "Reistijd (Netto)": "€ {:.2f}", 
    "Verschil": "€ {:.2f}"
}).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)
