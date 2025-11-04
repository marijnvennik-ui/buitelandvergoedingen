import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Verloningsvergelijker", layout="centered")
st.title("💶 Vergelijking van verloningsconstructies (wekelijks)")

# Sidebar instellingen
st.sidebar.header("🔧 Instellingen")

bruto_maand = st.sidebar.number_input("Bruto maandloon beide constructies (€)", value=4000, step=100)
weken = st.sidebar.slider("Periode (weken)", min_value=1, max_value=12, value=12, step=1)

# Belastingtarieven
belasting_normaal = st.sidebar.slider(
    "Belastingpercentage normaal (%)",
    min_value=0, max_value=60, value=37, step=1
) / 100

belasting_hoog = st.sidebar.slider(
    "Belastingpercentage overuren/weekend (%)",
    min_value=0.0, max_value=60.0, value=49.5, step=0.5
) / 100


# Constructie A
vergoed_A_netto_per_dag = st.sidebar.slider("Constructie A: Netto vergoeding per dag (€)", min_value=0, max_value=500, value=50, step=5)

# Constructie B
bonus_multiplier_B = st.sidebar.slider("Constructie B: Loonverhoging factor (1.30 = +30%)", min_value=1.0, max_value=2.0, value=1.30, step=0.05)
vergoed_B_bruto_per_dag = st.sidebar.slider("Constructie B: Bruto extra vergoeding per dag (€)", min_value=0, max_value=200, value=25, step=5)

# Vaste parameters
werkdagen = 5
zaterdag_multiplier = 2.11
zondag_multiplier = 0.75
dagen_per_week = 7  # ma–zo

# Afgeleide berekeningen
bruto_week = bruto_maand / 4.33
dagloon_bruto_normaal = bruto_week / werkdagen  # dagloon op basis van 5 werkdagen

# -----------------------------
# Constructie A
# -----------------------------
netto_A_per_week = vergoed_A_netto_per_dag * dagen_per_week
cumul_A = [0]  # start bij week 0
for i in range(weken):
    cumul_A.append(cumul_A[-1] + netto_A_per_week)

# -----------------------------
# Constructie B
# -----------------------------
cumul_B = [0]  # start bij week 0
for i in range(weken):
    # Werkdagen (ma-vr)
    bruto_werkdagen = werkdagen * dagloon_bruto_normaal * bonus_multiplier_B
    netto_werkdagen = bruto_werkdagen * (1 - belasting_normaal)

    # Zaterdag (overuren)
    bruto_zaterdag = dagloon_bruto_normaal * zaterdag_multiplier
    netto_zaterdag = bruto_zaterdag * (1 - belasting_hoog)

    # Zondag (niet gewerkt, 75%)
    bruto_zondag = dagloon_bruto_normaal * zondag_multiplier
    netto_zondag = bruto_zondag * (1 - belasting_hoog)

    # Dagvergoeding (geldt alle dagen, met normaal tarief)
    bruto_vergoed = 7 * vergoed_B_bruto_per_dag
    netto_vergoed = bruto_vergoed * (1 - belasting_normaal)

    # Totaal weekloon constructie B
    netto_week_B = netto_werkdagen + netto_zaterdag + netto_zondag + netto_vergoed
    cumul_B.append(cumul_B[-1] + netto_week_B)

# -----------------------------
# Dataframe & grafiek
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
ax.plot(df["Week"], df["Constructie A (cumulatief netto)"], label="Constructie A", linewidth=2)
ax.plot(df["Week"], df["Constructie B (cumulatief netto)"], label="Constructie B", linewidth=2)
ax.set_xlabel("Week")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking verloningsconstructies per week")
ax.legend()
ax.grid(True)
st.pyplot(fig)

verschil = df["Constructie B (cumulatief netto)"].iloc[-1] - df["Constructie A (cumulatief netto)"].iloc[-1]
if verschil > 0:
    st.success(f"✅ Constructie B levert na {weken} weken **€{verschil:,.2f}** meer op.")
else:
    st.warning(f"⚠️ Constructie A levert na {weken} weken **€{abs(verschil):,.2f}** meer op.")
