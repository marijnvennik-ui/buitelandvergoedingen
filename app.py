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

# Oude constructie (bruto + bonus + weekend correcties)
bonus_multiplier_Oude = st.sidebar.slider(
    "Oude constructie: Loonverhoging factor (1.30 = +30%)", min_value=1.0, max_value=2.0, value=1.30, step=0.05
)
vergoed_Oude_bruto_per_dag = st.sidebar.slider(
    "Oude constructie: Bruto extra vergoeding per dag (€)", min_value=0, max_value=200, value=25, step=5
)

# Vaste parameters
werkdagen = 5
uren_per_dag = 8
zaterdag_multiplier = 2.11
zondag_multiplier = 0.75
dagen_per_week = 7  # ma–zo

# Bereken dagloon normaal
dagloon_bruto_normaal = bruto_uurloon * uren_per_dag

# -----------------------------
# Nieuwe constructie
# -----------------------------
netto_per_week_Nieuwe = vergoed_Nieuwe_netto_per_dag * dagen_per_week
cumul_Nieuwe = [0]  # start bij week 0
for i in range(weken):
    cumul_Nieuwe.append(cumul_Nieuwe[-1] + netto_per_week_Nieuwe)

# -----------------------------
# Oude constructie
# -----------------------------
cumul_Oude = [0]  # start bij week 0
for i in range(weken):
    # Werkdagen (ma–vr)
    bruto_werkdagen = werkdagen * dagloon_bruto_normaal * bonus_multiplier_Oude
    netto_werkdagen = bruto_werkdagen * (1 - belasting_normaal)

    # Zaterdag (overuren)
    bruto_zaterdag = dagloon_bruto_normaal * zaterdag_multiplier
    netto_zaterdag = bruto_zaterdag * (1 - belasting_hoog)

    # Zondag (niet gewerkt, 75%)
    bruto_zondag = dagloon_bruto_normaal * zondag_multiplier
    netto_zondag = bruto_zondag * (1 - belasting_hoog)

    # Dagvergoeding (geldt alle dagen, met normaal tarief)
    bruto_vergoed = dagen_per_week * vergoed_Oude_bruto_per_dag
    netto_vergoed = bruto_vergoed * (1 - belasting_normaal)

    # Totaal weekloon oude constructie
    netto_week_Oude = netto_werkdagen + netto_zaterdag + netto_zondag + netto_vergoed
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

# Plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Week"], df["Nieuwe constructie (cumulatief netto)"], label="Nieuwe constructie", linewidth=2)
ax.plot(df["Week"], df["Oude constructie (cumulatief netto)"], label="Oude constructie", linewidth=2)
ax.set_xlabel("Week")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking oude vs nieuwe verloningsconstructies per week")
ax.legend()
ax.grid(True)
st.pyplot(fig)

verschil = df["Oude constructie (cumulatief netto)"].iloc[-1] - df["Nieuwe constructie (cumulatief netto)"].iloc[-1]
if verschil > 0:
    st.success(f"✅ Oude constructie levert na {weken} weken **€{verschil:,.2f}** meer op.")
else:
    st.warning(f"⚠️ Nieuwe constructie levert na {weken} weken **€{abs(verschil):,.2f}** meer op.")
