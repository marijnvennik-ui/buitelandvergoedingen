import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
from dataclasses import dataclass

# ==========================================
# 1. DOMEIN LOGICA & INSTELLINGEN
# ==========================================
@dataclass
class Tarieven:
    basis_uurloon: float
    belasting_normaal: float
    belasting_bijzonder: float
    dagtarief_netto: float
    ovn_week: float
    ovn_weekend: float
    
    @property
    def maandsalaris(self) -> float:
        return self.basis_uurloon * 173.3

class Calculator:
    """Verantwoordelijk voor alle gevectoriseerde berekeningen op een uren-DataFrame."""
    def __init__(self, tarieven: Tarieven):
        self.t = tarieven

    def bereken_alles(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        res = df.copy()
        
        # Basis uren
        uren_totaal = res['N'] + res['O']
        is_weekend = res['Dag'].isin(['Zaterdag', 'Zondag'])
        
        # --- REISTIJD (Gevectoriseerd met Numpy) ---
        rt_uren = res['R'] / 60.0
        
        # Formule doordeweeks: min(uren, 1.25) * 0.607% + max(0, uren - 1.25) * 0.97%
        rt_doordeweeks = (np.minimum(rt_uren, 1.25) * 0.00607 * self.t.maandsalaris) + \
                         (np.maximum(0, rt_uren - 1.25) * 0.0097 * self.t.maandsalaris)
        # Formule weekend: uren * 1.21%
        rt_weekend = rt_uren * 0.0121 * self.t.maandsalaris
        
        rt_bruto = np.where(is_weekend, rt_weekend, rt_doordeweeks)
        res['Reistijd (Netto)'] = rt_bruto * (1 - self.t.belasting_bijzonder)
        
        # --- NIEUWE REGELING ---
        netto_basis = (uren_totaal * self.t.basis_uurloon) * (1 - self.t.belasting_normaal)
        res['Nieuw (Netto)'] = netto_basis + self.t.dagtarief_netto + res['Reistijd (Netto)']
        
        # --- OUDE REGELING ---
        # Doordeweeks: (Uren * Loon * 1.30) belast tegen normaal tarief
        bruto_oud_week = uren_totaal * self.t.basis_uurloon * 1.30
        netto_oud_week = (bruto_oud_week * (1 - self.t.belasting_normaal)) + \
                         (self.t.ovn_week * (1 - self.t.belasting_bijzonder)) + \
                         res['Reistijd (Netto)']
                         
        # Weekend: 2.11x bij werk, 75% van 8u bij geen werk, alles tegen bijzonder tarief
        bruto_oud_weekend = np.where(uren_totaal > 0, 
                                     uren_totaal * self.t.basis_uurloon * 2.11, 
                                     self.t.basis_uurloon * 8 * 0.75)
        netto_oud_weekend = (bruto_oud_weekend + self.t.ovn_weekend) * (1 - self.t.belasting_bijzonder) + \
                            res['Reistijd (Netto)']
        
        res['Oud (Netto)'] = np.where(is_weekend, netto_oud_weekend, netto_oud_week)
        res['Verschil'] = res['Nieuw (Netto)'] - res['Oud (Netto)']
        
        return res

# ==========================================
# 2. DATA EXTRACTIE (EXCEL PARSER)
# ==========================================
class ExcelParser:
    """Verantwoordelijk voor het veilig uitlezen en structureren van de Excel export."""
    DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
    
    def parse(self, file) -> pd.DataFrame:
        df_raw = pd.read_excel(file, header=None)
        
        rij_dagen, dag_kolommen = self._zoek_header_grenzen(df_raw)
        rij_labels, mapping = self._map_kolommen(df_raw, rij_dagen, dag_kolommen)
        
        return self._extraheer_project_data(df_raw, rij_labels, mapping)

    def _zoek_header_grenzen(self, df: pd.DataFrame):
        """Zoekt met RegEx naar de dagenrij en bepaalt de startkolom per dag/totaal."""
        for idx, row in df.head(30).iterrows():
            row_str = " ".join(row.astype(str).str.lower())
            if re.search(r'\bmaandag\b', row_str) and re.search(r'\bdinsdag\b', row_str):
                dag_starts = {}
                for col_idx, val in enumerate(row):
                    val_str = str(val).lower().strip()
                    # Zoek naar exacte dagen of de Totaal kolom
                    for zoekterm in self.DAGEN + ["totaal"]:
                        if re.search(fr'\b{zoekterm}\b', val_str) and zoekterm not in dag_starts:
                            dag_starts[zoekterm] = col_idx
                return idx, dag_starts
                
        raise ValueError("Fatale Parsing Fout: Kon de dagen-header ('Maandag', etc.) niet vinden.")

    def _map_kolommen(self, df: pd.DataFrame, rij_dagen: int, dag_starts: dict) -> tuple:
        """Koppelt de N, O, R kolommen aan de specifieke dag binnen zijn grenzen."""
        mapping = {dag: {"N": -1, "O": -1, "R": -1} for dag in self.DAGEN}
        
        # Zoek de sub-header (N, O, R) in de rijen er direct onder
        rij_labels = -1
        for r in range(rij_dagen + 1, min(rij_dagen + 5, len(df))):
            row_vals = df.iloc[r].astype(str).str.upper().str.strip().values
            if any(re.match(r'^(N|O|R)', v) for v in row_vals):
                rij_labels = r
                break
                
        if rij_labels == -1:
             raise ValueError("Fatale Parsing Fout: Kon de 'N', 'O', 'R' labels niet vinden onder de dagen.")

        sorted_starts = sorted(dag_starts.items(), key=lambda x: x[1])
        
        for i, (dag, start_col) in enumerate(sorted_starts):
            if dag == "totaal": continue
            
            end_col = sorted_starts[i+1][1] if i + 1 < len(sorted_starts) else min(start_col + 4, len(df.columns))
            
            # Zoek N, O, R binnen het domein van deze specifieke dag
            for col_idx in range(start_col, end_col):
                val = str(df.iloc[rij_labels, col_idx]).upper().strip()
                if re.match(r'^N\b', val): mapping[dag]["N"] = col_idx
                elif re.match(r'^O\b', val): mapping[dag]["O"] = col_idx
                elif re.match(r'^R\b|R->', val): mapping[dag]["R"] = col_idx

            # Fallback mechanisme als headers onvolledig zijn geëxporteerd
            if mapping[dag]["N"] == -1: mapping[dag]["N"] = start_col
            if mapping[dag]["O"] == -1 and start_col + 1 < end_col: mapping[dag]["O"] = start_col + 1
            if mapping[dag]["R"] == -1 and start_col + 2 < end_col: mapping[dag]["R"] = start_col + 2

        return rij_labels, mapping

    def _extraheer_project_data(self, df: pd.DataFrame, start_rij: int, mapping: dict) -> pd.DataFrame:
        """Bouwt een schone, platte DataFrame op van alle gevonden uren."""
        extracted_data = []
        
        # Snijd het irrelevante bovendeel van het dataframe af voor prestaties
        df_data = df.iloc[start_rij + 1:]
        
        for index, row in df_data.iterrows():
            col0 = str(row.iloc[0]).strip().lower()
            if col0 in ['nan', 'none', '', 'project', 'totaal', 'datum']:
                continue
                
            # Controleer of deze rij uren bevat in ANY gemapte kolom
            relevant_cols = [c for dag in mapping.values() for c in dag.values() if c != -1]
            uren_in_rij = pd.to_numeric(row.iloc[relevant_cols], errors='coerce').fillna(0)
            
            if uren_in_rij.sum() > 0:
                # Bouw projectnaam uit de eerste paar kolommen
                tekst_delen = [str(x).strip() for x in row.iloc[:8] if pd.notna(x) and str(x).strip().lower() != 'totaal']
                project_naam = f"Rij {index+1}: " + " | ".join(tekst_delen)
                if not tekst_delen:
                    project_naam = f"Rij {index+1}: Onbekend Project"
                
                # Voeg per dag een rij toe aan de platte tabel
                for dag, kolommen in mapping.items():
                    extracted_data.append({
                        "Project": project_naam,
                        "Dag": dag.capitalize(),
                        "N": pd.to_numeric(row.iloc[kolommen["N"]], errors='coerce') if kolommen["N"] != -1 else 0.0,
                        "O": pd.to_numeric(row.iloc[kolommen["O"]], errors='coerce') if kolommen["O"] != -1 else 0.0,
                        "R": pd.to_numeric(row.iloc[kolommen["R"]], errors='coerce') if kolommen["R"] != -1 else 0.0
                    })
                    
        if not extracted_data:
            raise ValueError("Fout: Structuur begrepen, maar geen rijen met uren gevonden.")
            
        # Zorg dat lege cellen keurig 0.0 zijn
        df_result = pd.DataFrame(extracted_data).fillna(0.0)
        return df_result

# ==========================================
# 3. PRESENTATIE (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="Enterprise Urenvergelijker", layout="wide")
st.title("📊 Urenvergelijker (Enterprise Edition)")

# -- Configuratie via Sidebar --
with st.sidebar:
    st.header("⚙️ Systeem Parameters")
    tarieven = Tarieven(
        basis_uurloon = st.number_input("Basis uurloon Bruto (€)", value=24.50, step=0.10),
        belasting_normaal = st.slider("Belasting Normaal (%)", 0.0, 50.0, 37.0) / 100,
        belasting_bijzonder = 0.505,
        dagtarief_netto = st.number_input("Nieuwe Netto dagvergoeding (€)", value=50.0),
        ovn_week = st.number_input("Oude Overnachting week (Bruto)", value=21.0),
        ovn_weekend = st.number_input("Oude Overnachting weekend (Bruto)", value=28.0)
    )
    st.info(f"Gehanteerd maandsalaris: € {tarieven.maandsalaris:,.2f}")

# -- Applicatie Logica --
uploaded_file = st.file_uploader("Upload Excel (.xlsx) export", type="xlsx")

if uploaded_file:
    try:
        parser = ExcelParser()
        df_parsed = parser.parse(uploaded_file)
        
        projecten_lijst = df_parsed['Project'].unique().tolist()
        st.success(f"Parsing succesvol. {len(projecten_lijst)} project(en) gevonden.")
        
        geselecteerd = st.multiselect("Selecteer Projecten:", options=projecten_lijst, default=projecten_lijst)
        
        if geselecteerd:
            # Filter op projecten en sommeer direct netjes per dag (Pandas groupby)
            df_gefilterd = df_parsed[df_parsed['Project'].isin(geselecteerd)]
            
            # Sorteer de dagen in de juiste week-volgorde
            dagen_cat = pd.CategoricalDtype(["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"], ordered=True)
            df_gefilterd['Dag'] = df_gefilterd['Dag'].astype(dagen_cat)
            
            df_agg = df_gefilterd.groupby('Dag', observed=False)[['N', 'O', 'R']].sum().reset_index()
            st.session_state.df_master = df_agg
            
    except ValueError as e:
        st.error("Bestand Parsing Mislukt.")
        st.warning(str(e))
        st.stop()

# -- Fallback en Data Editor --
if 'df_master' not in st.session_state:
    st.session_state.df_master = pd.DataFrame([
        {"Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

st.subheader("1. Urendata & Handmatige Correctie")
edited_df = st.data_editor(
    st.session_state.df_master,
    column_config={
        "Dag": st.column_config.TextColumn(disabled=True),
        "N": st.column_config.NumberColumn("Normale Uren (N)", format="%.1f"),
        "O": st.column_config.NumberColumn("Overuren (O)", format="%.1f"),
        "R": st.column_config.NumberColumn("Reisminuten (R)", format="%d")
    },
    use_container_width=True
)

# -- Reken-engine uitvoeren --
rekenmachine = Calculator(tarieven)
df_resultaat = rekenmachine.bereken_alles(edited_df)

# -- Resultaten Dashboard --
st.divider()
tot_nieuw = df_resultaat['Nieuw (Netto)'].sum()
tot_oud = df_resultaat['Oud (Netto)'].sum()
verschil = tot_nieuw - tot_oud

c1, c2, c3 = st.columns(3)
c1.metric("Netto Opbrengst (Nieuw)", f"€ {tot_nieuw:,.2f}")
c2.metric("Netto Opbrengst (Oud)", f"€ {tot_oud:,.2f}")
c3.metric("Definitief Verschil", f"€ {verschil:,.2f}", delta=f"{verschil:,.2f}")

st.subheader("Financiële Analyse per Dag")
st.dataframe(df_resultaat.style.format({
    "Nieuw (Netto)": "€ {:.2f}", 
    "Oud (Netto)": "€ {:.2f}", 
    "Reistijd (Netto)": "€ {:.2f}", 
    "Verschil": "€ {:.2f}"
}).background_gradient(subset=['Verschil'], cmap='RdYlGn'), use_container_width=True)

# -- Visualisatie --
fig, ax = plt.subplots(figsize=(10, 3.5))
x = np.arange(len(df_resultaat['Dag']))
width = 0.35
ax.bar(x - width/2, df_resultaat['Oud (Netto)'], width, label='Oud', color='#FF4B4B')
ax.bar(x + width/2, df_resultaat['Nieuw (Netto)'], width, label='Nieuw', color='#00CC96')
ax.set_xticks(x)
ax.set_xticklabels(df_resultaat['Dag'])
ax.legend()
st.pyplot(fig)
