import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="Buitenlandvergoedingen", layout="centered")
st.title("💶 Vergelijking nieuwe vs oude verloningsconstructies (wekelijks)")

# -----------------------------
# Sidebar instellingen
# -----------------------------
st.sidebar.header("🔧 Instellingen")

# Input bruto uurloon
bruto_uurloon = st.sidebar.number_input("Bruto uurloon (€)", value=23.0, step=0.5)

# Periode in weken
weken = st.sidebar.slider("Periode (weken)", min_value=1, max_value=12, value=12, step=1)

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

# Slider doordeweekse overuren
overuren_per_weekdag = st.sidebar.slider(
    "Doordeweekse overuren per dag (uren)", min_value=0.0, max_value=10.0, value=0.0, step=0.5
)

# Checkbox weekendwerk
weekend_werken = st.sidebar.checkbox("Zaterdag werken", value=True)

# Extra zaterdaguren
extra_zaterdag_uren = st.sidebar.slider(
    "Extra zaterdaguren", min_value=0.0, max_value=8.0, value=0.0, step=0.5
)

# -----------------------------
# Vaste parameters
# -----------------------------
werkdagen = 5
uren_per_dag = 8
zaterdag_multiplier = 2.11
zondag_multiplier = 0.75
dagen_per_week = 7  # ma–zo

# -----------------------------
# Nieuwe constructie cumulatief
# -----------------------------
cumul_Nieuwe = [0]
for i in range(weken):
    bruto_normaal = werkdagen * uren_per_dag * bruto_uurloon
    netto_normaal = bruto_normaal * (1 - belasting_normaal)

    bruto_overuren_week = werkdagen * overuren_per_weekdag * bruto_uurloon
    netto_overuren_week = bruto_overuren_week * (1 - belasting_bijzonder)

    if weekend_werken:
        netto_zaterdag = vergoed_Nieuwe_netto_per_dag
        bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
        netto_extra_zat = bruto_extra_zat * (1 - belasting_bijzonder)
        netto_zaterdag += netto_extra_zat
    else:
        netto_zaterdag = 0

    netto_dagvergoeding = vergoed_Nieuwe_netto_per_dag * dagen_per_week
    netto_week_Nieuwe = netto_normaal + netto_overuren_week + netto_zaterdag + netto_dagvergoeding
    cumul_Nieuwe.append(cumul_Nieuwe[-1] + netto_week_Nieuwe)

# -----------------------------
# Oude constructie cumulatief
# -----------------------------
cumul_Oude = [0]
for i in range(weken):
    toeslag_werkdagen = werkdagen * uren_per_dag * bruto_uurloon * (bonus_multiplier_Oude - 1)
    bruto_werkdagen = werkdagen * uren_per_dag * bruto_uurloon
    netto_werkdagen = (bruto_werkdagen + toeslag_werkdagen) * (1 - belasting_normaal)

    bruto_overuren_week = werkdagen * overuren_per_weekdag * bruto_uurloon
    netto_overuren_week = bruto_overuren_week * (1 - belasting_bijzonder)

    if weekend_werken:
        bruto_zaterdag = uren_per_dag * bruto_uurloon * zondag_multiplier
        netto_zaterdag_basis = bruto_zaterdag * (1 - belasting_bijzonder)
        bruto_vergoed_zaterdag = vergoed_Oude_bruto_per_dag
        netto_vergoed_zaterdag = bruto_vergoed_zaterdag * (1 - belasting_normaal)
        bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
        netto_extra_zat = bruto_extra_zat * (1 - belasting_bijzonder)
        netto_zaterdag_totaal = netto_zaterdag_basis + netto_vergoed_zaterdag + netto_extra_zat
    else:
        netto_zaterdag_totaal = 0

    netto_vergoed = dagen_per_week * vergoed_Oude_bruto_per_dag * (1 - belasting_normaal)
    netto_week_Oude = netto_werkdagen + netto_overuren_week + netto_zaterdag_totaal + netto_vergoed
    cumul_Oude.append(cumul_Oude[-1] + netto_week_Oude)

# -----------------------------
# Dataframe & grafieken
# -----------------------------
weeks = list(range(0, weken + 1))
df = pd.DataFrame({
    "Week": weeks,
    "Nieuwe constructie (cumulatief netto)": cumul_Nieuwe,
    "Oude constructie (cumulatief netto)": cumul_Oude
})

st.subheader("📊 Resultaten per week")
st.dataframe(df.style.format("{:.2f}"))

# Cumulatieve grafiek
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(df["Week"], df["Nieuwe constructie (cumulatief netto)"], label="Nieuwe constructie", linewidth=2)
ax.plot(df["Week"], df["Oude constructie (cumulatief netto)"], label="Oude constructie", linewidth=2)
ax.set_xlabel("Week")
ax.set_ylabel("Cumulatief netto inkomen (€)")
ax.set_title("Vergelijking nieuwe vs oude constructies per week")
ax.legend()
ax.grid(True)
st.pyplot(fig)

# Verschilgrafiek
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

verschil_totaal = df["Verschil (Oude - Nieuwe)"].iloc[-1]
if verschil_totaal > 0:
    st.success(f"✅ Oude constructie levert na {weken} weken **€{verschil_totaal:,.2f}** meer op.")
else:
    st.warning(f"⚠️ Nieuwe constructie levert na {weken} weken **€{abs(verschil_totaal):,.2f}** meer op.")

# -----------------------------
# Staafdiagram week 1 met labels
# -----------------------------
st.subheader("📊 Inkomenscomponenten per constructie (week 1)")

# Componentberekening Nieuwe
bruto_normaal = werkdagen * uren_per_dag * bruto_uurloon
netto_normaal = bruto_normaal * (1 - belasting_normaal)
bruto_overuren_week = werkdagen * overuren_per_weekdag * bruto_uurloon
netto_overuren_week = bruto_overuren_week * (1 - belasting_bijzonder)
if weekend_werken:
    netto_zaterdag = vergoed_Nieuwe_netto_per_dag
    bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
    netto_extra_zat = bruto_extra_zat * (1 - belasting_bijzonder)
    netto_zaterdag += netto_extra_zat
else:
    netto_zaterdag = 0
netto_dagvergoeding = vergoed_Nieuwe_netto_per_dag * dagen_per_week
componenten_Nieuwe = [netto_normaal, netto_overuren_week, netto_zaterdag, netto_dagvergoeding]
labels_Nieuwe = ["Normaal loon", "Overuren", "Zaterdag extra", "Dagvergoeding"]

# Componentberekening Oude
toeslag_werkdagen = werkdagen * uren_per_dag * bruto_uurloon * (bonus_multiplier_Oude - 1)
bruto_werkdagen = werkdagen * uren_per_dag * bruto_uurloon
netto_werkdagen = (bruto_werkdagen + toeslag_werkdagen) * (1 - belasting_normaal)
netto_overuren_week_Oude = bruto_overuren_week * (1 - belasting_bijzonder)
if weekend_werken:
    bruto_zaterdag = uren_per_dag * bruto_uurloon * zondag_multiplier
    netto_zaterdag_basis = bruto_zaterdag * (1 - belasting_bijzonder)
    bruto_vergoed_zaterdag = vergoed_Oude_bruto_per_dag
    netto_vergoed_zaterdag = bruto_vergoed_zaterdag * (1 - belasting_normaal)
    bruto_extra_zat = extra_zaterdag_uren * bruto_uurloon * zaterdag_multiplier
    netto_extra_zat = bruto_extra_zat * (1 - belasting_bijzonder)
    netto_zaterdag_totaal = netto_zaterdag_basis + netto_vergoed_zaterdag + netto_extra_zat
else:
    netto_zaterdag_totaal = 0
netto_vergoed = dagen_per_week * vergoed_Oude_bruto_per_dag * (1 - belasting_normaal)
componenten_Oude = [netto_werkdagen, netto_overuren_week_Oude, netto_zaterdag_totaal, netto_vergoed]
labels_Oude = ["Normaal loon + toeslag", "Overuren", "Zaterdag + toeslag", "Dagvergoeding"]

# Staafdiagram
x = np.arange(2)
kleuren = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
fig3, ax3 = plt.subplots(figsize=(8,5))

# Nieuwe
bottom = 0
for comp, label, color in zip(componenten_Nieuwe, labels_Nieuwe, kleuren):
    bar = ax3.bar(x[0], comp, bottom=bottom, label=label, color=color)
    ax3.text(x[0], bottom + comp/2, f"{comp:.0f}", ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    bottom += comp

# Oude
bottom = 0
for comp, label, color in zip(componenten_Oude, labels_Oude, kleuren):
    bar = ax3.bar(x[1], comp, bottom=bottom, label=label, color=color)
    ax3.text(x[1], bottom + comp/2, f"{comp:.0f}", ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    bottom += comp

ax3.set_xticks(x)
ax3.set_xticklabels(["Nieuwe constructie", "Oude constructie"])
ax3.set_ylabel("Netto inkomen week 1 (€)")
ax3.set_title("Inkomenscomponenten week 1 per constructie")
ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
ax3.grid(True, axis='y', linestyle='--', alpha=0.7)
st.pyplot(fig3)

# -----------------------------
# Tabel met bedragen
# -----------------------------
st.subheader("💰 Specificatie bedragen (week 1)")

df_week1 = pd.DataFrame({
    "Component": labels_Nieuwe,
    "Nieuwe constructie (€)": [round(v, 2) for v in componenten_Nieuwe],
    "Oude constructie (€)": [round(v, 2) for v in componenten_Oude]
})

df_week1["Verschil (Oude - Nieuwe) (€)"] = (
    df_week1["Oude constructie (€)"] - df_week1["Nieuwe constructie (€)"]
)

# ✅ Format alleen numerieke kolommen – voorkomt ValueError
st.dataframe(df_week1.style.format({
    "Nieuwe constructie (€)": "{:.2f}",
    "Oude constructie (€)": "{:.2f}",
    "Verschil (Oude - Nieuwe) (€)": "{:.2f}"
}))
