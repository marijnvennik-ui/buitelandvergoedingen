import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import timedelta, date

st.set_page_config(page_title="Buitenlandvergoedingen", layout="centered")
st.title("💶 Vergelijking nieuwe vs oude verloningsconstructies (per dag)")

# -----------------------------
# Sidebar instellingen
# -----------------------------
st.sidebar.header("🔧 Instellingen")

# Datumbereik voor de reis
startdatum = st.sidebar.date_input("Startdatum reis")
einddatum = st.sidebar.date_input("Einddatum reis")

if startdatum > einddatum:
    st.error("❌ De startdatum mag niet na de einddatum liggen.")
    st.stop()

# Input bruto uurloon
bruto_uurloon = st.sidebar.number_input("Bruto uurloon (€)", value=23.0, step=0.5)

# Belastingtarieven
belasting_normaal = st.sidebar.slider(
    "Normaal belastingpercentage (%)", min_value=0, max_value=60, value=37, step=1
) / 100
belasting_bijzonder = st.sidebar.slider(
    "Bijzondere belastingtarief (%)", min_value=0.0, max_value=60.0, value=49.5, step=0.5
) / 100

# Nieuwe constructie
vergoed_Nieuwe_netto_per_dag = st.sidebar.slider(
    "Nieuwe constructie: Netto vergoeding per dag (€)", min_value=0, max_value=100, value=50, step=5
)

# Oude constructie
bonus_multiplier_Oude = st.sidebar.slider(
    "Oude constructie: Loonverhoging factor doordeweekse uren (1.30 = +30%)",
    min_value=1.0, max_value=2.0, value=1.30, step=0.05
)
vergoed_Oude_bruto_per_dag = st.sidebar.slider(
    "Oude constructie: Bruto extra vergoeding per dag (€)", min_value=0, max_value=100, value=25, step=5
)

# Overuren
overuren_per_weekdag = st.sidebar.slider(
    "Doordeweekse overuren per dag (uren)", min_value=0.0, max_value=10.0, value=0.0, step=0.5
)

# Weekendinstellingen
weekend_werken = st.sidebar.checkbox("Zaterdag werken", value=True)
extra_zaterdag_uren = st.sidebar.slider(
    "Extra zaterdaguren (bovenop 8u)", min_value=0.0, max_value=8.0, value=0.0, step=0.5
)

# -----------------------------
# Vaste parameters
# -----------------------------
uren_per_dag = 8
zaterdag_multiplier = 2.11
zondag_multiplier = 0.75

# -----------------------------
# Functie om alle dagen te genereren
# -----------------------------
def daterange(start, end):
    for n in range((end - start).days + 1):
        yield start + timedelta(n)

# -----------------------------
# Dagelijkse berekening
# -----------------------------
records = []

for dag in daterange(startdatum, einddatum):
    weekdag = dag.weekday()  # maandag = 0, zondag = 6
    dagtype = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"][weekdag]

    # --- NIEUWE constructie ---
    netto = 0
    bruto_basis = bruto_uurloon * uren_per_dag
    overuren = overuren_per_weekdag * bruto_uurloon

    # Dagvergoeding geldt altijd
    netto += vergoed_Nieuwe_netto_per_dag

    # Doordeweekse dagen
    if weekdag < 5:  # Ma–Vr
        netto += bruto_basis * (1 - belasting_normaal)
        netto += overuren * (1 - belasting_bijzonder)

    # Zaterdag
    elif weekdag == 5:
        # Alleen werken indien aangevinkt
        if weekend_werken:
            bruto_extra = uren_per_dag * bruto_uurloon * zaterdag_multiplier
            netto += bruto_extra * (1 - belasting_bijzonder)
            if extra_zaterdag_uren > 0:
                bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
                netto += bruto_extra_zat * (1 - belasting_bijzonder)

    # Oude constructie
    netto_old = 0
    bruto_basis_old = bruto_uurloon * uren_per_dag
    overuren_old = overuren_per_weekdag * bruto_uurloon

    # Dagvergoeding geldt altijd
    netto_old += vergoed_Oude_bruto_per_dag * (1 - belasting_normaal)

    if weekdag < 5:
        # Normaal loon + toeslag
        bruto_total = bruto_basis_old * bonus_multiplier_Oude
        netto_old += bruto_total * (1 - belasting_normaal)
        netto_old += overuren_old * (1 - belasting_bijzonder)

    elif weekdag == 5:
        # 75% loon + zaterdagtoeslag + eventueel extra uren
        bruto_zat = uren_per_dag * bruto_uurloon * zondag_multiplier
        netto_old += bruto_zat * (1 - belasting_bijzonder)
        if weekend_werken:
            bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
            netto_old += bruto_extra_zat * (1 - belasting_bijzonder)

    # Zondag → alleen dagvergoeding
    # (geen extra's)

    records.append({
        "Datum": dag,
        "Dag": dagtype,
        "Nieuwe constructie (netto)": netto,
        "Oude constructie (netto)": netto_old,
        "Verschil (Oude - Nieuwe)": netto_old - netto,
        "Weekend": weekdag >= 5
    })

df = pd.DataFrame(records)
df["Cumulatief Nieuwe"] = df["Nieuwe constructie (netto)"].cumsum()
df["Cumulatief Oude"] = df["Oude constructie (netto)"].cumsum()
df["Cumulatief Verschil"] = df["Verschil (Oude - Nieuwe)"].cumsum()

# -----------------------------
# Resultatenoverzicht
# -----------------------------
st.subheader("📅 Dagelijkse resultaten")
st.dataframe(df[["Datum", "Dag", "Nieuwe constructie (netto)", "Oude constructie (netto)", "Verschil (Oude - Nieuwe)"]].style.format("{:.2f}"))

# -----------------------------
# Cumulatieve grafiek
# -----------------------------
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(df["Datum"], df["Cumulatief Nieuwe"], label="Nieuwe constructie", linewidth=2)
ax.plot(df["Datum"], df["Cumulatief Oude"], label="Oude constructie", linewidth=2)
ax.set_xlabel("Datum")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking nieuwe vs oude constructie over de reisperiode")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# -----------------------------
# Weekendanalyse
# -----------------------------
st.subheader("🗓️ Weekendimpact")

weekend_df = df[df["Weekend"]]
if weekend_df.empty:
    st.info("Geen weekenddagen in deze periode.")
else:
    totaal_verschil_weekend = weekend_df["Verschil (Oude - Nieuwe)"].sum()
    aantal_weekenden = len(weekend_df) / 2  # ongeveer 2 dagen per weekend
    gemiddeld_per_weekend = totaal_verschil_weekend / max(aantal_weekenden, 1)

    st.write(f"💡 Totaal verschil op weekenddagen: **€{totaal_verschil_weekend:,.2f}**")
    st.write(f"Gemiddeld per weekend: **€{gemiddeld_per_weekend:,.2f}**")

    fig2, ax2 = plt.subplots(figsize=(8, 4))
    ax2.bar(weekend_df["Datum"], weekend_df["Verschil (Oude - Nieuwe)"], color="orange")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_title("Verschil per weekenddag (Oude - Nieuwe)")
    ax2.set_ylabel("Netto verschil (€)")
    ax2.grid(True, axis="y", linestyle="--", alpha=0.7)
    st.pyplot(fig2)

# -----------------------------
# Samenvatting
# -----------------------------
totaal_nieuw = df["Nieuwe constructie (netto)"].sum()
totaal_oud = df["Oude constructie (netto)"].sum()
verschil_totaal = totaal_oud - totaal_nieuw

st.subheader("💰 Samenvatting")
col1, col2, col3 = st.columns(3)
col1.metric("Nieuwe constructie totaal", f"€{totaal_nieuw:,.2f}")
col2.metric("Oude constructie totaal", f"€{totaal_oud:,.2f}")
col3.metric("Verschil (Oude - Nieuwe)", f"€{verschil_totaal:,.2f}")

if verschil_totaal > 0:
    st.success(f"✅ De **oude constructie** levert over deze periode €{verschil_totaal:,.2f} meer op.")
else:
    st.warning(f"⚠️ De **nieuwe constructie** levert over deze periode €{abs(verschil_totaal):,.2f} meer op.")
