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
        
        uren_totaal = res['N'] + res['O']
        is_weekend = res['Dag'].isin(['Zaterdag', 'Zondag'])
        
        # --- REISTIJD (Gevectoriseerd met Numpy) ---
        rt_uren = res['R'] / 60.0
        rt_doordeweeks = (np.minimum(rt_uren, 1.25) * 0.00607 * self.t.maandsalaris) + \
                         (np.maximum(0, rt_uren - 1.25) * 0.0097 * self.t.maandsalaris)
        rt_weekend = rt_uren * 0.0121 * self.t.maandsalaris
        
        rt_bruto = np.where(is_weekend, rt_weekend, rt_doordeweeks)
        res['Reistijd (Netto)'] = rt_bruto * (1 - self.t.belasting_bijzonder)
        
        # --- NIEUWE REGELING ---
        netto_basis = (uren_totaal * self.t.basis_uurloon) * (1 - self.t.belasting_normaal)
        res['Nieuw (Netto)'] = netto_basis + self.t.dagtarief_netto + res['Reistijd (Netto)']
        
        # --- OUDE REGELING ---
        bruto_oud_week = uren_totaal * self.t.basis_uurloon * 1.30
        netto_oud_week = (bruto_oud_week * (1 - self.t.belasting_normaal)) + \
                         (self.t.ovn_week * (1 - self.t.belasting_bijzonder)) + \
                         res['Reistijd (Netto)']
                         
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
    
    def parse(self, file) -> tuple:
        """Retourneert een tuple: (DataFrame met uren, String met label zoals '2026 - Week 2')"""
        df_raw = pd.read_excel(file, header=None)
        
        # 1. Haal meta-data (Jaar en Week) op
        label_week = self._zoek_metadata(df_raw, file.name)
        
        # 2. Zoek grenzen en uren
        rij_dagen, dag_kolommen = self._zoek_header_grenzen(df_raw)
        rij_labels, mapping = self._map_kolommen(df_raw, rij_dagen, dag_kolommen)
        
        df_extracted = self._extraheer_project_data(df_raw, rij_labels, mapping)
        return df_extracted, label_week

    def _zoek_metadata(self, df: pd.DataFrame, fallback_naam: str) -> str:
        """Scant de eerste 15 rijen voor 'Jaar' en 'Week' en maakt er een strak label van."""
        jaar, week = None, None
        
        for r in range(min(15, len(df))):
            # Voeg alle cellen in de rij samen tot één string (negeer linebreaks)
            row_str = " ".join(df.iloc[r].astype(str).str.replace('\n', ' ', regex=False))
            
            # Slim zoeken: kijkt door celgrenzen heen (bijv. "Jaar: 2026.0")
            jaar_match = re.search(r'jaar[:\s]+(\d{4})', row_str, re.IGNORECASE)
            week_match = re.search(r'week[:\s]+(\d{1,2})', row_str, re.IGNORECASE)
            
            if jaar_match and not jaar:
                jaar = jaar_match.group(1)
            if week_match and not week:
                week = week_match.group(1)
                
            if jaar and week:
                break
                
        if jaar and week:
            return f"{jaar} - Week {week}"
        elif week:
            return f"Week {week}"
        else:
            return fallback_naam # Val terug op bestandsnaam als het mislukt

    def _zoek_header_grenzen(self, df: pd.DataFrame):
        for idx, row in df.head(30).iterrows():
            row_str = " ".join(row.astype(str).str.lower())
            if re.search(r'\bmaandag\b', row_str) and re.search(r'\bdinsdag\b', row_str):
                dag_starts = {}
                for col_idx, val in enumerate(row):
                    val_str = str(val).lower().strip()
                    for zoekterm in self.DAGEN + ["totaal"]:
                        if re.search(fr'\b{zoekterm}\b', val_str) and zoekterm not in dag_starts:
                            dag_starts[zoekterm] = col_idx
                return idx, dag_starts
        raise ValueError("Fatale Parsing Fout: Kon de dagen-header ('Maandag', etc.) niet vinden.")

    def _map_kolommen(self, df: pd.DataFrame, rij_dagen: int, dag_starts: dict) -> tuple:
        mapping = {dag: {"N": -1, "O": -1, "R": -1} for dag in self.DAGEN}
        
        rij_labels = -1
        for r in range(rij_dagen + 1, min(rij_dagen + 5, len(df))):
            row_vals = df.iloc[r].astype(str).str.upper().str.strip().values
            if any(re.match(r'^(N|O|R|S)', v) for v in row_vals):
                rij_labels = r
                break
                
        if rij_labels == -1:
             raise ValueError("Fatale Parsing Fout: Kon de 'N', 'O', 'R' labels niet vinden onder de dagen.")

        sorted_starts = sorted(dag_starts.items(), key=lambda x: x[1])
        
        for i, (dag, start_col) in enumerate(sorted_starts):
            if dag == "totaal": continue
            
            end_col = sorted_starts[i+1][1] if i + 1 < len(sorted_starts) else min(start_col + 4, len(df.columns))
            
            for col_idx in range(start_col, end_col):
                val = str(df.iloc[rij_labels, col_idx]).upper().strip()
                if val == 'N' or val.startswith('N ') or val.startswith('N-'): 
                    mapping[dag]["N"] = col_idx
                elif val == 'O' or val.startswith('O ') or val.startswith('O-'): 
                    mapping[dag]["O"] = col_idx
                elif val == 'R' or val.startswith('R ') or val.startswith('R-'): 
                    mapping[dag]["R"] = col_idx

        return rij_labels, mapping

    def _extraheer_project_data(self, df: pd.DataFrame, start_rij: int, mapping: dict) -> pd.DataFrame:
        extracted_data = []
        df_data = df.iloc[start_rij + 1:]
        
        for index, row in df_data.iterrows():
            row_start = " ".join([str(x).lower() for x in row.iloc[:3] if pd.notna(x)])
            if 'totaal' in row_start or 'datum' in row_start:
                continue
                
            relevant_cols = [c for dag in mapping.values() for c in dag.values() if c != -1]
            if not relevant_cols:
                continue
                
            cell_values = row.iloc[relevant_cols].astype(str).str.replace(',', '.')
            uren_in_rij = pd.to_numeric(cell_values, errors='coerce').fillna(0)
            
            if uren_in_rij.sum() > 0:
                tekst_delen = [str(x).strip() for x in row.iloc[:8] if pd.notna(x) and str(x).strip().lower() not in ['nan', 'none', '']]
                project_naam = f"Rij {index+1}: " + " | ".join(tekst_delen)
                if not tekst_delen:
                    project_naam = f"Rij {index+1}: Onbekend Project"
                
                for dag, kolommen in mapping.items():
                    n_str = str(row.iloc[kolommen["N"]]).replace(',', '.') if kolommen["N"] != -1 else '0'
                    o_str = str(row.iloc[kolommen["O"]]).replace(',', '.') if kolommen["O"] != -1 else '0'
                    r_str = str(row.iloc[kolommen["R"]]).replace(',', '.') if kolommen["R"] != -1 else '0'
                    
                    n_val = pd.to_numeric(n_str, errors='coerce')
                    o_val = pd.to_numeric(o_str, errors='coerce')
                    r_val = pd.to_numeric(r_str, errors='coerce')
                    
                    extracted_data.append({
                        "Project": project_naam,
                        "Dag": dag.capitalize(),
                        "N": n_val if pd.notna(n_val) else 0.0,
                        "O": o_val if pd.notna(o_val) else 0.0,
                        "R": r_val if pd.notna(r_val) else 0.0
                    })
                    
        if not extracted_data:
            raise ValueError("Fout: Structuur begrepen, maar geen rijen met uren gevonden.")
            
        return pd.DataFrame(extracted_data).fillna(0.0)

# ==========================================
# 3. PRESENTATIE (STREAMLIT UI)
# ==========================================
st.set_page_config(page_title="Enterprise Urenvergelijker", layout="wide")
st.title("📊 Multi-Week Urenvergelijker")

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

uploaded_files = st.file_uploader("Upload Excel (.xlsx) exports", type="xlsx", accept_multiple_files=True)

if uploaded_files:
    try:
        parser = ExcelParser()
        alle_bestanden_data = []
        labels_gevonden = []
        
        for file in uploaded_files:
            # We ontvangen nu ook het label vanuit de parser
            df_parsed, label = parser.parse(file)
            
            df_parsed.insert(0, 'Week', label)
            alle_bestanden_data.append(df_parsed)
            labels_gevonden.append(label)
            
        df_gecombineerd = pd.concat(alle_bestanden_data, ignore_index=True)
        
        projecten_lijst = df_gecombineerd['Project'].unique().tolist()
        st.success(f"Geüpload: {', '.join(labels_gevonden)}. ({len(projecten_lijst)} projecten verwerkt).")
        
        geselecteerd = st.multiselect("Selecteer Projecten om te filteren:", options=projecten_lijst, default=projecten_lijst)
        
        if geselecteerd:
            df_gefilterd = df_gecombineerd[df_gecombineerd['Project'].isin(geselecteerd)]
            dagen_cat = pd.CategoricalDtype(["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"], ordered=True)
            df_gefilterd['Dag'] = df_gefilterd['Dag'].astype(dagen_cat)
            
            df_agg = df_gefilterd.groupby(['Week', 'Dag'], observed=False)[['N', 'O', 'R']].sum().reset_index()
            st.session_state.df_master = df_agg
            
    except ValueError as e:
        st.error("Bestand Parsing Mislukt.")
        st.warning(str(e))
        st.stop()

if 'df_master' not in st.session_state:
    st.session_state.df_master = pd.DataFrame([
        {"Week": "Upload Data", "Dag": d, "N": 0.0, "O": 0.0, "R": 0.0} 
        for d in ["Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag", "Zondag"]
    ])

st.subheader("1. Urendata & Handmatige Correctie")
edited_df = st.data_editor(
    st.session_state.df_master,
    column_config={
        "Week": st.column_config.TextColumn("Week / Periode", disabled=True),
        "Dag": st.column_config.TextColumn(disabled=True),
        "N": st.column_config.NumberColumn("Normale Uren (N)", format="%.1f"),
        "O": st.column_config.NumberColumn("Overuren (O)", format="%.1f"),
        "R": st.column_config.NumberColumn("Reisminuten (R)", format="%d")
    },
    use_container_width=True
)

rekenmachine = Calculator(tarieven)
df_resultaat = rekenmachine.bereken_alles(edited_df)

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
}).background_gradient(subset=['Verschil'], cmap='RdYlGn').hide(axis="index"), use_container_width=True)

# Bouw de grafiek as met de daadwerkelijke data uit de Excelsheet
df_resultaat['Grafiek_Label'] = df_resultaat['Week'].astype(str) + "\n" + df_resultaat['Dag'].astype(str)

fig, ax = plt.subplots(figsize=(max(10, len(df_resultaat) * 0.5), 4))
x = np.arange(len(df_resultaat['Grafiek_Label']))
width = 0.35
ax.bar(x - width/2, df_resultaat['Oud (Netto)'], width, label='Oud', color='#FF4B4B')
ax.bar(x + width/2, df_resultaat['Nieuw (Netto)'], width, label='Nieuw', color='#00CC96')
ax.set_xticks(x)
ax.set_xticklabels(df_resultaat['Grafiek_Label'], rotation=45, ha='right', fontsize=9)
ax.legend()
plt.tight_layout()
st.pyplot(fig)
