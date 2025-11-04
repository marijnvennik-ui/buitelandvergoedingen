# Checkbox weekendwerk
weekend_werken = st.sidebar.checkbox("Zaterdag werken", value=True)

# -----------------------------
# Nieuwe constructie
# -----------------------------
cumul_Nieuwe = [0]
for i in range(weken):
    # 1. Normale doordeweekse uren
    bruto_normaal = werkdagen * uren_per_dag * bruto_uurloon
    netto_normaal = bruto_normaal * (1 - belasting_normaal)

    # 2. Overuren doordeweek
    bruto_overuren_week = werkdagen * overuren_per_weekdag * bruto_uurloon
    netto_overuren_week = bruto_overuren_week * (1 - belasting_bijzonder)

    # 3. Zaterdag overuren alleen meenemen als checkbox aan staat
    if weekend_werken:
        netto_zaterdag = vergoed_Nieuwe_netto_per_dag  # alleen netto vergoeding
    else:
        netto_zaterdag = 0

    # 4. Dagvergoeding 7 dagen per week - netto
    netto_dagvergoeding = vergoed_Nieuwe_netto_per_dag * dagen_per_week

    # Totaal netto week
    netto_week_Nieuwe = netto_normaal + netto_overuren_week + netto_zaterdag + netto_dagvergoeding
    cumul_Nieuwe.append(cumul_Nieuwe[-1] + netto_week_Nieuwe)

# -----------------------------
# Oude constructie
# -----------------------------
cumul_Oude = [0]
for i in range(weken):
    # Werkdagen (ma–vr) normaal + 30% toeslag
    bruto_werkdagen = werkdagen * uren_per_dag * bruto_uurloon
    toeslag_werkdagen = werkdagen * uren_per_dag * bruto_uurloon * (bonus_multiplier_Oude - 1)
    netto_werkdagen = (bruto_werkdagen + toeslag_werkdagen) * (1 - belasting_normaal)

    # Overuren doordeweek
    bruto_overuren_week = werkdagen * overuren_per_weekdag * bruto_uurloon
    netto_overuren_week = bruto_overuren_week * (1 - belasting_bijzonder)

    # Zaterdag alleen meenemen als checkbox aan staat
    if weekend_werken:
        bruto_zaterdag = uren_per_dag * bruto_uurloon * zondag_multiplier  # 75% normale dag
        netto_zaterdag = bruto_zaterdag * (1 - belasting_bijzonder)
        bruto_vergoed_zaterdag = vergoed_Oude_bruto_per_dag
        netto_vergoed_zaterdag = bruto_vergoed_zaterdag * (1 - belasting_normaal)
        netto_zaterdag_totaal = netto_zaterdag + netto_vergoed_zaterdag
    else:
        netto_zaterdag_totaal = 0

    # Extra dagvergoeding (overige dagen)
    bruto_vergoed = dagen_per_week * vergoed_Oude_bruto_per_dag
    netto_vergoed = bruto_vergoed * (1 - belasting_normaal)

    # Netto week totaal
    netto_week_Oude = netto_werkdagen + netto_overuren_week + netto_zaterdag_totaal + netto_vergoed
    cumul_Oude.append(cumul_Oude[-1] + netto_week_Oude)
