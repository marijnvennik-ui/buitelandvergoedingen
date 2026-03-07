import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="Dynamische Urenvergelijker", layout="wide")
st.title("📊 Dynamische Urenvergelijker (Project Scan)")

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
        if idx != -1 and idx < len(row):
            val = row.iloc[idx]
            if pd.notna(val):
                if isinstance(val, str):
                    val = val.replace(',', '.')
                return float(val)
    except (ValueError, TypeError, IndexError):
        pass
    return 0.0

# --- EXCEL PARSER (DYNAMISCHE KOLOMHERKENNING) ---
def scan_projecten_dynamisch(file):
    df_raw = pd.read_excel(file, header=None)
    
    rij_dagen = -1
    rij_labels = -1
    
    # 1. Zoek de header rijen (Dagen en N/O/R/S) in de eerste 30 rijen
    for i in range(min(30, len(df_raw))):
        row_vals = [str(x).lower().strip() for x in df_raw.iloc[i].values]
        if "maandag" in row_vals and "dinsdag" in row_vals:
            rij_dagen = i
            rij_labels = i + 1 # De N, O, R labels staan er vrijwel altijd direct onder
            break
            
    if rij_dagen == -1:
        st.error("Kon de dagen (Maandag, Dinsdag, etc.) niet vinden in het bestand.")
        return None, None
        
    # 2. Map de kolommen per dag
    dagen_namen = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
    dag_kolommen = {dag: {"N": -1, "O": -1, "R": -1} for dag in dagen_namen}
    
    dag_starts = {}
    for col_idx, val in enumerate(df_raw.iloc[rij_dagen].values):
        val_str = str(val).lower().strip()
        if val_str in dagen_namen:
            dag_starts[val_str] = col_idx
            
    # Bepaal het bereik van elke dag en zoek N, O, R
    sorted_dagen = sorted(dag_starts.items(), key=lambda x: x[1])
    for i, (dag, start_col) in enumerate(sorted_dagen):
        end_col = sorted_dagen[i+1][1] if i + 1 < len(sorted_dagen) else len(df_raw.columns)
        
        for col_idx in range(start_col, end_col):
            if col_idx < len(df_raw.iloc[rij_labels]):
                label = str(df_raw.iloc[rij_labels, col_idx]).upper().strip()
                if label == "N" or label.startswith("N"): dag_kolommen[dag]["N"] = col_idx
                elif label == "O" or label.startswith("O"): dag_kolommen[dag]["O"] = col_idx
                elif label == "R" or label.startswith("R"): dag_kolommen[dag]["R"] = col_idx

    # 3. Zoek de projecten met uren
    gevonden_projecten = {}
    for index, row in df_raw.iterrows():
        # Sla de header rijen over
        if index <= rij_labels:
            continue
            
        col0 = str(row.iloc[0]).strip()
        col1 = str(row.iloc[1]).strip() if len(row) > 1 else ""
        
        if col0.lower() in ['nan', 'none', '', 'project', 'totaal', 'datum', 'medewerker']:
            continue
            
        heeft_uren = False
        # Check of in een van de gevonden N, O, R kolommen een getal staat
        for dag, kolommen in dag_kolommen.items():
            for type_uur, col_idx in kolommen.items():
                if col_idx != -1 and safe_float(row, col_idx) > 0:
                    heeft_uren = True
                    break
            if heeft_uren: break
                
        if heeft_uren:
            naam = f"Rij {index+1}: {col0}"
            if col1.lower() not in ['nan', 'none', '']:
                naam += f" - {col1}"
            gevonden_projecten[naam] = row
            
    return gevonden_projecten, dag_kolommen

# --- APP FLOW & DATA INITIALISATIE ---
uploaded_file = st.file_uploader("Sleep hier je .xlsx urenlijst naar binnen", type="xlsx")

if uploaded_file:
    projecten_dict, mapping = scan_projecten_dynamisch(uploaded_file)
    
    if projecten_dict and mapping:
        st.success(f"Er zijn {len(projecten_dict)} projecten met uren gevonden!")
        
        geselecteerde_projecten = st.multiselect(
            "Selecteer het project (of meerdere) om te analyseren:",
            options=list(projecten_dict.keys()),
            default=list(projecten_dict.keys())[0]
        )
        
        # Aggregeer de uren met de dynamische kolom-mapping
        dagen_display = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        geaggregeerde_data = []
        
        for dag in dagen_display:
            n_tot, o_tot, r_tot = 0.0, 0.0, 0.0
            dag_lower = dag.lower()
            
            for p_naam in geselecteerde_projecten:
                row = projecten_dict[p_naam]
                
                n_tot += safe_float(row, mapping[dag_lower]["N"])
                o_tot += safe_float(row, mapping[dag_lower]["O"])
                r_tot += safe_float(row, mapping[dag_lower]["R"])
                
            geaggregeerde_data.append({"Dag": dag, "N": n_tot, "O": o_tot, "R": r_tot})
            
        st.session_state.df_data = pd.DataFrame(geaggregeerde_data)
        
    else:
        st.error("Bestand uitgelezen, maar geen werkbare uren of structuur gevonden.")

# Fallback data
if 'df_data' not in st.session_state:
    st.session_state.df_data = pd.DataFrame([
        {"Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

# --- TABEL WEERGAVE ---
st.subheader("1. Urenoverzicht (N, O, R)")
st.write("Uren zijn dynamisch ingelezen. Controleer of alles klopt.")
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
