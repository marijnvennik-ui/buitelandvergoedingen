import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="Slimme Urenvergelijker", layout="wide")
st.title("📊 Slimme Urenvergelijker (Project Scan)")

# --- SIDEBAR: INSTELLINGEN ---
with st.sidebar:
    st.header("⚙️ Salaris & Belasting")
    basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10)
    maandsalaris_calc = basis_uurloon * 173.3
    st.info(f"Berekend maandsalaris: € {maandsalaris_calc:,.2f}")
    
    st.divider()
    belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100
    belasting_bijzonder = 0.505 
    
    st.divider()
    st.subheader("Excel Scanner")
    st.write("In welke kolom begint Maandag 'N'?")
    start_kolom = st.number_input("Kolom-index (A=0, B=1, C=2, D=3, E=4...)", min_value=1, max_value=20, value=4, step=1)
    
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

# --- HULPFUNCTIE: VEILIG GETALLEN LEZEN ---
def safe_float(row, idx):
    try:
        if idx < len(row):
            val = row.iloc[idx]
            if pd.notna(val):
                if isinstance(val, str):
                    val = val.replace(',', '.')
                return float(val)
    except (ValueError, TypeError, IndexError):
        pass
    return 0.0

# --- EXCEL PARSER (ZOEKT AUTOMATISCH PROJECTEN) ---
def scan_projecten(file, start_idx):
    df_raw = pd.read_excel(file, header=None)
    gevonden_projecten = {}
    
    for index, row in df_raw.iterrows():
        col0 = str(row.iloc[0]).strip()
        col1 = str(row.iloc[1]).strip() if len(row) > 1 else ""
        
        # Sla lege rijen of duidelijke headers over
        if col0.lower() in ['nan', 'none', '', 'project', 'totaal', 'datum', 'medewerker']:
            continue
            
        # Controleer of er in de uren-kolommen (Ma t/m Zo) ergens een getal staat groter dan 0
        heeft_uren = False
        for col_idx in range(start_idx, min(start_idx + 21, len(row))):
            if safe_float(row, col_idx) > 0:
                heeft_uren = True
                break
                
        if heeft_uren:
            # Maak een herkenbare naam voor in het menu
            naam = f"Rij {index+1}: {col0}"
            if col1.lower() not in ['nan', 'none', '']:
                naam += f" - {col1}"
            gevonden_projecten[naam] = row
            
    return gevonden_projecten

# --- APP FLOW & DATA INITIALISATIE ---
uploaded_file = st.file_uploader("Sleep hier je .xlsx urenlijst naar binnen", type="xlsx")

if uploaded_file:
    projecten_dict = scan_projecten(uploaded_file, int(start_kolom))
    
    if projecten_dict:
        st.success(f"Er zijn {len(projecten_dict)} projecten met uren gevonden in dit bestand!")
        
        # Laat de gebruiker de projecten kiezen
        geselecteerde_projecten = st.multiselect(
            "Selecteer het project (of meerdere) om te analyseren:",
            options=list(projecten_dict.keys()),
            default=list(projecten_dict.keys())[0] # Selecteer standaard de eerste
        )
        
        # Aggregeer de uren van de geselecteerde projecten
        dagen_namen = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        geaggregeerde_data = []
        
        for i, dag in enumerate(dagen_namen):
            n_tot, o_tot, r_tot = 0.0, 0.0, 0.0
            
            for p_naam in geselecteerde_projecten:
                row = projecten_dict[p_naam]
                idx_n = int(start_kolom) + (i * 3)
                idx_o = int(start_kolom) + (i * 3) + 1
                idx_r = int(start_kolom) + (i * 3) + 2
                
                n_tot += safe_float(row, idx_n)
                o_tot += safe_float(row, idx_o)
                r_tot += safe_float(row, idx_r)
                
            geaggregeerde_data.append({"Dag": dag, "N": n_tot, "O": o_tot, "R": r_tot})
            
        st.session_state.df_data = pd.DataFrame(geaggregeerde_data)
        
    else:
        st.error("Geen rijen gevonden met projectnummers én uren. Check de start-kolom in de zijbalk.")

# Fallback data als er geen bestand is of bij opstarten
if 'df_data' not in st.session_state:
    st.session_state.df_data = pd.DataFrame([
        {"Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

# --- TABEL WEERGAVE ---
st.subheader("1. Urenoverzicht (N, O, R)")
st.write("De uren van de geselecteerde projecten zijn samengevoegd. Je kunt ze hieronder nog handmatig aanpassen.")

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
    
    rt_bruto = bereken_reistijd_bruto(row['R'], is_weekend, maandsalaris_calc)
    rt_netto = rt_bruto * (1 - belasting_bijzonder)
    
    # NIEUWE REGELING
    netto_basis = (uren_totaal * basis_uurloon) * (1 - belasting_normaal)
    nieuw_totaal = netto_basis + dagtarief_netto + rt_netto
    
    # OUDE REGELING
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

st.subheader("2. Gedetailleerde Analyse")
st.dataframe(edited_df.style.format({
    "Nieuw (Netto)": "€ {:.2f}", 
    "Oud (Netto)": "€ {:.2f}", 
    "Reistijd (Netto)": "€ {:.2f}", 
    "Verschil": "€ {:.2f}"
}).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)
