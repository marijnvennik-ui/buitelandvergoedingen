import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURATIE ---
st.set_page_config(page_title="Urenvergelijker (Extreme Scan)", layout="wide")
st.title("📊 Urenvergelijker (Auto-Scan V3)")

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

# --- EXCEL PARSER (EXTREME SCAN) ---
def scan_projecten_extreem(file):
    df_raw = pd.read_excel(file, header=None)
    
    # STAP 1: Zoek de dagen
    dagen_namen = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
    rij_dagen = -1
    dag_starts = {}
    
    for idx, row in df_raw.iterrows():
        # Maak van de hele rij één lange string om te zoeken
        row_str = " ".join([str(x).lower() for x in row.values])
        if "maandag" in row_str and "dinsdag" in row_str:
            rij_dagen = idx
            for col_idx, val in enumerate(row.values):
                val_str = str(val).lower().strip()
                for dag in dagen_namen:
                    if dag in val_str and dag not in dag_starts:
                        dag_starts[dag] = col_idx
            break
            
    if rij_dagen == -1:
        return None, None, "Fout 1: Kon de rij met de namen van de dagen ('Maandag', etc.) niet vinden."

    # STAP 2: Zoek N, O, R
    mapping = {dag: {"N": -1, "O": -1, "R": -1} for dag in dagen_namen}
    rij_labels = -1
    sorted_dagen = sorted(dag_starts.items(), key=lambda x: x[1])

    # Scan maximaal 10 rijen onder de dagen voor de letters
    for r in range(rij_dagen + 1, min(rij_dagen + 10, len(df_raw))):
        row_vals = [str(x).upper().strip() for x in df_raw.iloc[r].values]
        # Zoek naar alles wat op onze kolommen lijkt
        if any(v.startswith("N") or v.startswith("O") or v.startswith("R") for v in row_vals if len(v) <= 3):
            rij_labels = r
            break

    if rij_labels == -1:
        return None, None, "Fout 2: Kon de letters N, O, R niet vinden in de rijen onder de dagen."

    # Koppel de letters aan de juiste kolommen per dag
    for i, (dag, start_col) in enumerate(sorted_dagen):
        end_col = sorted_dagen[i+1][1] if i + 1 < len(sorted_dagen) else len(df_raw.columns)
        for col_idx in range(start_col, end_col):
            if col_idx < len(df_raw.columns):
                val = str(df_raw.iloc[rij_labels, col_idx]).upper().strip()
                if val == "N" or val.startswith("N"): mapping[dag]["N"] = col_idx
                elif val == "O" or val.startswith("O"): mapping[dag]["O"] = col_idx
                elif val == "R" or val.startswith("R"): mapping[dag]["R"] = col_idx

    # STAP 3: Vind projecten onafhankelijk van layout vooraan
    gevonden_projecten = {}
    for index, row in df_raw.iterrows():
        if index <= rij_labels:
            continue
            
        heeft_uren = False
        uren_som = 0
        for dag, kolommen in mapping.items():
            for type_uur, col_idx in kolommen.items():
                if col_idx != -1:
                    val = safe_float(row, col_idx)
                    if val > 0:
                        heeft_uren = True
                        uren_som += val

        if heeft_uren:
            # Verzamel alle tekst in de eerste 8 kolommen om een naam te bouwen
            tekst_delen = []
            for c in range(min(8, len(row))):
                val = str(row.iloc[c]).strip()
                if val.lower() not in ['nan', 'none', '', 'totaal']:
                    tekst_delen.append(val)
                    
            naam = f"Rij {index+1}: " + " | ".join(tekst_delen)
            if not tekst_delen:
                naam = f"Rij {index+1}: Onbekend Project (Totaal: {uren_som}u)"
                
            gevonden_projecten[naam] = row
            
    if not gevonden_projecten:
        return None, None, "Fout 3: Dagen en N/O/R structuur zijn gevonden, maar er staan geen getallen in die kolommen op de regels eronder."

    return gevonden_projecten, mapping, "Succes"

# --- APP FLOW ---
uploaded_file = st.file_uploader("Sleep hier je .xlsx urenlijst naar binnen", type="xlsx")

if uploaded_file:
    projecten_dict, mapping, status_msg = scan_projecten_extreem(uploaded_file)
    
    if projecten_dict and mapping:
        st.success(f"Bestand uitgelezen! Er zijn {len(projecten_dict)} projectregels met uren gevonden.")
        
        geselecteerde_projecten = st.multiselect(
            "Selecteer de te analyseren projecten:",
            options=list(projecten_dict.keys()),
            default=list(projecten_dict.keys())
        )
        
        dagen_display = ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
        geaggregeerde_data = []
        
        for dag in dagen_display:
            n_tot, o_tot, r_tot = 0.0, 0.0, 0.0
            dag_lower = dag.lower()
            
            if dag_lower in mapping:
                for p_naam in geselecteerde_projecten:
                    row = projecten_dict[p_naam]
                    n_tot += safe_float(row, mapping[dag_lower]["N"])
                    o_tot += safe_float(row, mapping[dag_lower]["O"])
                    r_tot += safe_float(row, mapping[dag_lower]["R"])
                
            geaggregeerde_data.append({"Dag": dag, "N": n_tot, "O": o_tot, "R": r_tot})
            
        st.session_state.df_data = pd.DataFrame(geaggregeerde_data)
        
    else:
        st.error("Het bestand kon niet worden verwerkt.")
        st.warning(f"Systeemmelding: {status_msg}")

# Fallback data
if 'df_data' not in st.session_state:
    st.session_state.df_data = pd.DataFrame([
        {"Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

# --- TABEL WEERGAVE ---
st.subheader("1. Urenoverzicht (N, O, R)")
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
