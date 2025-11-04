import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Verloningsvergelijker", layout="centered")
st.title("💶 Vergelijking van verloningsconstructies")

# Invoerparameters
st.sidebar.header("🔧 Instellingen")

bruto_maand = st.sidebar.number_input("Bruto maandloon beide constructies (€)", value=4000, step=100)
maanden = st.sidebar.slider("Periode (maanden)", min_value=1, max_value=3, value=3, step=1)
belasting_tarief = st.sidebar.slider("Belastingpercentage (%)", min_value=0, max_value=60, value=37, step=1) / 100

# Constructie A
vergoed_A_netto_per_dag = st.sidebar.slider("Constructie A: Netto vergoeding per dag (€)", min_value=0, max_value=500, value=50, step=5)

# Constructie B
bonus_multiplier_B = st.sidebar.slider("Constructie B: Loonverhoging factor (1.30 = +30%)", min_value=1.0, max_value=2.0, value=1.30, step=0.05)
vergoed_B_bruto_per_dag = st.sidebar.slider("Constructie B: Bruto extra vergoeding per dag (€)", min_value=0, max_value=200, value=25, step=5)

# Vaste parameters
werkdagen = 5
dagen_per_week = 6  # ma–za
zaterdag_multiplier = 2.11
niet_gewerkt_multiplier_B = 0.75

# Berekeningen
weken = maanden * (52 / 12)
werkdagen_per_maand = werkdagen * (52 / 12)
dagloon_bruto_normaal = bruto_maand / werkdagen_per_maand

# Constructie A
netto_A_per_maand = vergoed_A_netto_per_dag * (7 * 4.33)  # 7 dagen per week, 4.33 weken/maand
cumul_A = [netto_A_per_maand * (i + 1) for i in range(maanden)]

# Constructie B
netto_B_list = []
cumul_B = []
cum = 0
for m in range(maanden):
    zaterdagen = 4  # vereenvoudiging
    niet_gewerkte_dagen = (30 - (werkdagen + zaterdagen))
    bruto_maand_B = (
        (werkdagen * dagloon_bruto_normaal * bonus_multiplier_B)
        + (zaterdagen * dagloon_bruto_normaal * zaterdag_multiplier)
        + (niet_gewerkte_dagen * dagloon_bruto_normaal * niet_gewerkt_multiplier_B)
        + (30 * vergoed_B_bruto_per_dag)
    )
    netto_maand_B = bruto_maand_B * (1 - belasting_tarief)
    netto_B_list.append(netto_maand_B)
    cum += netto_maand_B
    cumul_B.append(cum)

# Dataframe
df = pd.DataFrame({
    "Maand": range(1, maanden + 1),
    "Constructie A (cumulatief netto)": cumul_A,
    "Constructie B (cumulatief netto)": cumul_B
})

st.subheader("📊 Resultaten per maand")
st.dataframe(df.style.format("{:.2f}"))

# Plot
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Maand"], df["Constructie A (cumulatief netto)"], label="Constructie A")
ax.plot(df["Maand"], df["Constructie B (cumulatief netto)"], label="Constructie B")
ax.set_xlabel("Maanden")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking verloningsconstructies")
ax.legend()
ax.grid(True)
st.pyplot(fig)

verschil = df["Constructie B (cumulatief netto)"].iloc[-1] - df["Constructie A (cumulatief netto)"].iloc[-1]
if verschil > 0:
    st.success(f"✅ Constructie B levert na {maanden} maanden **€{verschil:,.2f}** meer op.")
else:
    st.warning(f"⚠️ Constructie A levert na {maanden} maanden **€{abs(verschil):,.2f}** meer op.")
