import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Buitenlandvergoedingen", layout="centered")
st.title("💶 Vergelijking van oude vs nieuwe verloningsconstructies (wekelijks)")

# Sidebar instellingen
st.sidebar.header("🔧 Instellingen")

# Input bruto uurloon
bruto_uurloon = st.sidebar.number_input("Bruto uurloon (€)", value=23.0, step=0.5)

# Periode in weken
weken = st.sidebar.slider("Periode (weken)", min_value=1, max_value=12, value=12, step=1)

# Belastingtarieven
belasting_normaal = st.sidebar.slider(
    "Belastingpercentage normaal (%)", min_value=0, max_value=60, value=37, step=1
) / 100

belasting_hoog = st.sidebar.slider(
    "Belastingpercentage overuren/weekend (%)", min_value=0.0, max_value=60.0, value=49.5, step=0.5
) / 100

# Nieuwe constructie (vaste netto dagvergoeding)
vergoed_Nieuwe_netto_per_dag = st.sidebar.slider(
    "Nieuwe constructie: Netto vergoeding per dag (€)", min_value=0, max_value=500, value=50, step=5
)

# Oude constructie (30% toeslag op doordeweekse uren + dagvergoeding)
bonus_multiplier_Oude = st.sidebar.slider(
    "Oude constructie: Loonverhoging factor doordeweekse uren (1.30 = +30%)",
    min_value=1.0, max_value=2.0, value=1.30, step=0.05
)
vergoed_Oude_bruto_per_dag = st.sidebar.slider(
    "Oude constructie: Bruto extra vergoeding per dag (€)", min_value=0, max_value=200, value=25, step=5
)

# Nieuwe slider: doordeweekse overuren
overuren_per_weekdag = st.sidebar.slider(
    "Doordeweekse overuren per dag (uren)", min_value=0.0, max_value=10.0, value=0.0, step=0.5
)

# Vaste parameters
werkdagen = 5
uren_per_dag = 8
zaterdag_multiplier = 2.11
zondag_multiplier = 0.75
dagen_per_week = 7  # ma–zo

# Bereken dagloon normaal
dagloon_bruto_normaal = bruto_uurloon * uren_per_dag
dagloon_bruto_overuren = bruto_uurloon * overuren_per_weekdag  # per dag

# -----------------------------
# Nieuwe constructie
# -----------------------------
netto_per_week_Nieuwe = vergoed_Nieuwe_netto_per_dag * dagen_per_week
cumul_Nieuwe = [0]  # start bij week 0
for i in range(weken):
    # Voeg doordeweekse overuren toe
    bruto_overuren_week = werkdagen * dagloon_bruto_overuren
    netto_overuren_week = bruto_overuren_week * (1 - belasting_hoog)

    cumul_Nieuwe.append(cumul_Nieuwe[-1] + netto_per_week_Nieuwe + netto_overuren_week)

# -----------------------------
# Oude constructie
# -----------------------------
cumul_Oude = [0]  # start bij week 0
for i in range(weken):
    # Werkdagen (ma–vr) normaal + 30% toeslag
    bruto_werkdagen = werkdagen * dagloon_bruto_normaal
    toeslag_werkdagen = werkdagen * dagloon_bruto_normaal * (bonus_multiplier_Oude - 1)
    netto_werkdagen = (bruto_werkdagen + toeslag_werkdagen) * (1 - belasting_normaal)

    # Voeg doordeweekse overuren toe
    bruto_overuren_week = werkdagen * dagloon_bruto_overuren
    netto_overuren_week = bruto_overuren_week * (1 - belasting_hoog)

    # Zaterdag (overuren)
    bruto_zaterdag = dagloon_bruto_normaal * zaterdag_multiplier
    netto_zaterdag = bruto_zaterdag * (1 - belasting_hoog)

    # Zondag (75% van normale dag)
    bruto_zondag = dagloon_bruto_normaal * zondag_multiplier
    netto_zondag = bruto_zondag * (1 - belasting_hoog)

    # Extra dagvergoeding (alle dagen)
    bruto_vergoed = dagen_per_week * vergoed_Oude_bruto_per_dag
    netto_vergoed = bruto_vergoed * (1 - belasting_normaal)

    # Netto week totaal
    netto_week_Oude = netto_werkdagen + netto_overuren_week + netto_zaterdag + netto_zondag + netto_vergoed
    cumul_Oude.append(cumul_Oude[-1] + netto_week_Oude)

# -----------------------------
# Dataframe & grafiek
# -----------------------------
weeks = list(range(0, weken + 1))
df = pd.DataFrame({
    "Week": weeks,
    "Nieuwe constructie (cumulatief netto)": cumul_Nieuwe,
    "Oude constructie (cumulatief netto)": cumul_Oude
})

st.subheader("📊 Resultaten per week")
st.dataframe(df.style.format("{:.2f}"))

# Hoofdgrafiek
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Week"], df["Nieuwe constructie (cumulatief netto)"], label="Nieuwe constructie", linewidth=2)
ax.plot(df["Week"], df["Oude constructie (cumulatief netto)"], label="Oude constructie", linewidth=2)
ax.set_xlabel("Week")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking oude vs nieuwe constructies per week")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# -----------------------------
# Verschil-grafiek per week
# -----------------------------
df["Verschil (Oude - Nieuwe)"] = df["Oude constructie (cumulatief netto)"] - df["Nieuwe constructie (cumulatief netto)"]

st.subheader("📈 Verschil per week (Oude - Nieuwe)")
fig2, ax2 = plt.subplots(figsize=(8, 4))
ax2.bar(df["Week"], df["Verschil (Oude - Nieuwe)"], color="orange")
ax2.axhline(0, color='black', linewidth=0.8)
ax2.set_xlabel("Week")
ax2.set_ylabel("Netto verschil (€)")
ax2.set_title("Wekelijks verschil tussen oude en nieuwe constructie")
ax2.grid(True, axis='y', linestyle='--', alpha=0.7)
st.pyplot(fig2)

# Verschil totaal na X weken
verschil_totaal = df["Verschil (Oude - Nieuwe)"].iloc[-1]
if verschil_totaal > 0:
    st.success(f"✅ Oude constructie levert na {weken} weken **€{verschil_totaal:,.2f}** meer op.")
else:
    st.warning(f"⚠️ Nieuwe constructie levert na {weken} weken **€{abs(verschil_totaal):,.2f}** meer op.")
