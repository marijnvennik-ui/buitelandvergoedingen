import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Verloningsvergelijker", layout="centered")
st.title("💶 Vergelijking van verloningsconstructies (wekelijks)")

# Sidebar met instellingen
st.sidebar.header("🔧 Instellingen")

bruto_maand = st.sidebar.number_input("Bruto maandloon beide constructies (€)", value=4000, step=100)
weken = st.sidebar.slider("Periode (weken)", min_value=1, max_value=12, value=12, step=1)
belasting_tarief = st.sidebar.slider("Belastingpercentage (%)", min_value=0, max_value=60, value=37, step=1) / 100

# Constructie A
vergoed_A_netto_per_dag = st.sidebar.slider("Constructie A: Netto vergoeding per dag (€)", min_value=0, max_value=500, value=50, step=5)

# Constructie B
bonus_multiplier_B = st.sidebar.slider("Constructie B: Loonverhoging factor (1.30 = +30%)", min_value=1.0, max_value=2.0, value=1.30, step=0.05)
vergoed_B_bruto_per_dag = st.sidebar.slider("Constructie B: Bruto extra vergoeding per dag (€)", min_value=0, max_value=200, value=25, step=5)

# Vaste parameters
werkdagen = 5
zaterdag_multiplier = 2.11
niet_gewerkt_multiplier_B = 0.75
dagen_per_week = 7  # voor constructie A

# Afgeleide berekeningen
bruto_week = bruto_maand / 4.33
dagloon_bruto_normaal = bruto_week / werkdagen  # 5 werkdagen in een week

# -----------------------------
# Constructie A – vaste netto vergoeding per dag
# -----------------------------
netto_A_per_week = vergoed_A_netto_per_dag * dagen_per_week
cumul_A = [0]  # start op week 0 = 0 euro
for i in range(weken):
    cumul_A.append(cumul_A[-1] + netto_A_per_week)

# -----------------------------
# Constructie B – bruto met bonussen
# -----------------------------
cumul_B = [0]  # start op week 0 = 0 euro
for i in range(weken):
    # weekstructuur
    zaterdagen = 1
    niet_gewerkte_dagen = 1  # zondag
    bruto_week_B = (
        (werkdagen * dagloon_bruto_normaal * bonus_multiplier_B)
        + (zaterdagen * dagloon_bruto_normaal * zaterdag_multiplier)
        + (niet_gewerkte_dagen * dagloon_bruto_normaal * niet_gewerkt_multiplier_B)
        + (7 * vergoed_B_bruto_per_dag)
    )
    netto_week_B = bruto_week_B * (1 - belasting_tarief)
    cumul_B.append(cumul_B[-1] + netto_week_B)

# -----------------------------
# Data en grafiek
# -----------------------------
weeks = list(range(0, weken + 1))
df = pd.DataFrame({
    "Week": weeks,
    "Constructie A (cumulatief netto)": cumul_A,
    "Constructie B (cumulatief netto)": cumul_B
})

st.subheader("📊 Resultaten per week")
st.dataframe(df.style.format("{:.2f}"))

# Plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Week"], df["Constructie A (cumulatief netto)"], label="Constructie A")
ax.plot(df["Week"], df["Constructie B (cumulatief netto)"], label="Constructie B")
ax.set_xlabel("Week")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking verloningsconstructies per week")
ax.legend()
ax.grid(True)
st.pyplot(fig)

verschil = df["Constructie B (cumulatief netto)"].iloc[-1] - df["Constructie A (cumulatief netto)"].iloc[-1]
if verschil > 0:
    st.succes
