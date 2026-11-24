"""Pilotar: the levers on the left, what happens over ten years on the right."""

import numpy as np
import pandas as pd
import streamlit as st

from core import assumptions as A
from core import formatting as F
from core import scenarios as S
from ui import state as U
from ui import theme as T
from ui.charts import CONFIG, MAP_CONFIG, line_band_chart
from ui.map_view import SCENARIO_LEGEND, scenario_figure

U.init()
U.ensure_widgets()
in_tour = st.session_state.get("tour") is not None

st.title("Pilotar")
T.lead("Mexa nas alavancas e veja o que muda nos próximos dez anos face a continuar como está.")

left, right = st.columns([1, 2.15], gap="large")

# ---------------------------------------------------------------- levers
with left:
    plan = U.plan()
    T.budget_bar(S.lever_costs(plan), F.eur)
    ch = U.on_lever_change

    with st.expander("Atrair doentes", key="x_atrair", on_change="rerun"):
        st.select_slider("Marketing digital, por ano", options=list(range(0, 410, 10)), key="w_marketing",
                         format_func=lambda v: F.eur(v * 1000), on_change=ch)
        T.cost_note(f"Hoje: {F.eur(S.BASELINE.marketing)} por ano. Demora alguns meses a fazer efeito.")
        st.select_slider("Peso das convenções na procura", options=list(range(40, 81, 5)), key="w_conv",
                         format_func=lambda v: f"{v}%", on_change=ch)
        T.cost_note("Sem custo direto: mais acordos trazem mais doentes, a preços mais baixos.")
        st.select_slider("Nível de preços particulares", options=list(range(85, 121, 5)), key="w_price",
                         format_func=lambda v: "como hoje" if v == 100 else f"{v - 100:+d}%", on_change=ch)
        T.cost_note("Sem custo direto: aplica-se a quem paga do seu bolso.")

    with st.expander("Atender quem chega", key="x_atender", on_change="rerun"):
        st.toggle("Sistema de chamadas perdidas com devolução", key="w_callback", on_change=ch)
        T.cost_note(f"Cerca de {F.eur(A.value('callback_cost'))} por ano e {F.eur(A.value('callback_setup'))} "
                    "para arrancar.")
        st.toggle("Marcação online em tempo real", key="w_online", on_change=ch)
        T.cost_note(f"Cerca de {F.eur(A.value('online_cost'))} por ano e {F.eur(A.value('online_setup'))} "
                    "para arrancar.")
        st.select_slider("Equipa de receção (pessoas a tempo inteiro)", options=list(range(6, 15)),
                         key="w_front_desk", on_change=ch)
        T.cost_note(f"Cada pessoa custa cerca de {F.eur(A.value('fd_cost'))} por ano. Hoje: "
                    f"{F.num(A.value('front_desk0'))}.")

    with st.expander("Base digital", key="x_digital", on_change="rerun"):
        st.select_slider("Investimento em contas, acessos e dados", options=list(range(0, 610, 50)),
                         key="w_digital_once", format_func=lambda v: F.eur(v * 1000), on_change=ch)
        T.cost_note("Gasto ao longo de um ano; o efeito chega com meses de atraso.")
        st.select_slider("Manutenção, por ano", options=list(range(20, 160, 10)), key="w_digital_maint",
                         format_func=lambda v: F.eur(v * 1000), on_change=ch)
        T.cost_note(f"Hoje: {F.eur(A.value('maint0'))} por ano. Sem manutenção, a base digital desgasta-se.")

    with st.expander("Capacidade e grandes apostas", key="x_capacidade", on_change="rerun"):
        st.select_slider("Contratar médicos (a mais, por ano)", options=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                         key="w_hire_rate", format_func=lambda v: F.num(v, 1 if v % 1 else 0), on_change=ch)
        T.cost_note("Até encher os gabinetes. Cada médico custa cerca de 25 mil € a contratar e 20 mil € por ano "
                    "em gabinete e apoio; recebe por ato.")
        st.selectbox("Abrir nova clínica (ano da decisão)", U.YEARS_OPT, key="w_clinic_year", on_change=ch)
        T.cost_note(f"Cerca de {F.eur(A.value('clinic_capex'))} de obra e "
                    f"{F.eur(A.value('clinic_opex') + 2 * A.value('fd_cost'))} por ano de custos fixos.")
        st.selectbox("Construir hospital (ano da decisão)", U.YEARS_OPT, key="w_hospital_year", on_change=ch)
        p = U.plan()
        T.cost_note(f"Cerca de {F.eur(S.hospital_capex(p.hospital_rooms, p.hospital_beds))} de investimento e "
                    f"{F.eur(S.hospital_opex(p.hospital_rooms, p.hospital_beds))} por ano de custos fixos.")
        if st.session_state.get("w_hospital_year", "Não") != "Não":
            with st.popover("Configurar o hospital", width="stretch"):
                st.select_slider("Blocos operatórios", options=[1, 2, 3, 4], key="w_hospital_rooms", on_change=ch)
                st.select_slider("Camas", options=list(range(4, 42, 2)), key="w_hospital_beds", on_change=ch)
                st.select_slider("Parte paga com dívida", options=list(range(0, 90, 10)), key="w_hospital_debt",
                                 format_func=lambda v: f"{v}%", on_change=ch)

    with st.expander("E se o mundo mudar?"):
        for f in A.FORCES:
            opts = U.force_options(f)
            if f.key == "labour":
                fmt = (lambda v: "normal" if abs(v - 1.0) < 1e-9 else ("mais fácil" if v < 1 else
                       ("difícil" if v < 1.35 else "muito difícil")) + f" ({F.num(v, 2)})")
            elif f.key == "comp_extra":
                fmt = (lambda v: "nenhuma" if v == 0 else f"{F.pct(v)} da procura")
            else:
                fmt = (lambda v: F.pct(v, 1, signed=True) + " por ano" if v else "0% por ano")
            st.select_slider(f.label, options=opts, key=f"w_world_{f.key}", format_func=fmt,
                             on_change=U.on_world_change)
        if U.world_changed():
            st.button("Voltar ao mundo de hoje", on_click=U.reset_world, width="stretch")

    if not in_tour:
        st.button("Voltar a continuar como está", on_click=U.reset_plan, width="stretch",
                  disabled=not S.changed_levers(U.plan()))

# ---------------------------------------------------------------- results
plan = U.plan()
with right:
    with st.spinner("A simular 400 futuros possíveis..."):
        v = U.plan_view(U.plan_key(plan), U.world_key())
    h = v["head"]
    is_base = v["is_base"]

    def card(label, key, fmt, good_when_up=True, note=""):
        d = h[key]
        if is_base:
            return T.metric_card(label, fmt(d["plan"]), "", "neutral", note)
        delta = d["delta"]
        small = abs(delta) < max(0.01 * abs(d["base"]), 10_000 if key in ("net_cum10", "cash_min") else 5)
        if small:
            return T.metric_card(label, fmt(d["plan"]), "igual", "neutral", note)
        sure = d["up"] >= 0.8 or d["down"] >= 0.8
        good = (delta > 0) == good_when_up
        tone = ("good" if good else "bad") if sure else "neutral"
        text = F.people(delta, signed=True) if key in ("seen_2036", "lost_2036") else F.eur(delta, signed=True)
        return T.metric_card(label, fmt(d["plan"]), text + ("" if sure else " · ainda não sabemos"), tone, note)

    month = h["cash_min"]["month"]
    if not is_base:
        st.markdown('<div class="ck-note" style="margin-bottom:0.3rem">Em baixo de cada número, a diferença face a '
                    'continuar como está.</div>', unsafe_allow_html=True)
    T.metric_row([
        card("Resultado acumulado até 2036", "net_cum10", F.eur,
             note=f"EBITDA menos investimento. Margem em 2036: {F.pct(h['margin_2036']['plan'])}"),
        card("Caixa no ponto mais baixo", "cash_min", F.eur, note=f"Em {F.month_label(month)}"),
        card("Doentes atendidos em 2036", "seen_2036", F.people, note="Novos e em acompanhamento"),
        card("Doentes perdidos em 2036", "lost_2036", F.people, good_when_up=False,
             note=f"Valem cerca de {F.eur(h['lost_value_2036']['plan'])} por ano"),
    ])

    kind = (st.segmented_control("Ver", list(U.CHARTS), key="w_chart", label_visibility="collapsed", wrap=True)
            or "Faturação")
    s = v["series"][kind]
    x = np.array(s["x"])
    b_lo, b_mid, b_hi = (np.array(a) for a in s["base"])
    p_lo, p_mid, p_hi = (np.array(a) for a in s["plan"])
    fmts = {"Faturação": F.eur, "Caixa": F.eur, "Doentes": F.people, "Espera": F.days,
            "Reputação": lambda v_: F.num(v_, 1)}
    fmt = fmts[kind]

    def title() -> str:
        if kind == "Caixa":
            mn, when = h["cash_min"]["plan"], F.year_of(h["cash_min"]["month"])
            if mn < p_mid[0] - 100_000 and p_mid[-1] > mn + 300_000:
                return f"A caixa desce antes de subir: no ponto mais baixo fica em {F.eur(mn)}, em {when}"
            if mn < p_mid[0] - 100_000:
                return f"A caixa desce até {F.eur(mn)} em {when} e não recupera até 2036"
            if is_base:
                return f"Sem mudar nada, a caixa acumula até {F.eur(p_mid[-1])} em 2036"
            gap = p_mid[-1] - b_mid[-1]
            if abs(gap) < 200_000:
                return "A caixa acompanha a de continuar como está"
            word = "acima" if gap > 0 else "abaixo"
            return f"A caixa acaba {F.eur(abs(gap))} {word} de continuar como está"
        if kind == "Reputação":
            if is_base or abs(p_mid[-1] - b_mid[-1]) < 0.05:
                return f"A reputação fica perto de {F.stars(p_mid[-1])}"
            word = "sobe" if p_mid[-1] > b_mid[-1] else "desce"
            return f"A reputação {word} para {F.stars(p_mid[-1])} em 2036"
        if kind == "Espera":
            if is_base:
                return f"Sem mudar nada, a espera passa de {F.days(p_mid[0])} para {F.days(p_mid[-1])}"
            if abs(p_mid[-1] - b_mid[-1]) < 0.6:
                return f"A espera quase não muda: cerca de {F.days(p_mid[-1])} em 2036"
            word = "sobe" if p_mid[-1] > b_mid[-1] else "desce"
            return f"A espera {word} para {F.days(p_mid[-1])} em 2036, contra {F.days(b_mid[-1])} sem o plano"
        label = {"Faturação": "A faturação", "Doentes": "O número de doentes atendidos"}[kind]
        if is_base:
            return f"Sem mudar nada, {label.lower()} fica perto de {fmt(p_mid[-1])} em 2036"
        rel = p_mid[-1] / b_mid[-1] - 1.0
        if abs(rel) < 0.02:
            return f"{label} quase não muda até 2036"
        word = "sobe" if rel > 0 else "desce"
        return f"{label} {word} {F.pct(abs(rel))} face a continuar como está"

    series = [dict(name="Continuar como está", colour=T.COLORS["mid_grey"], lo=b_lo, mid=b_mid, hi=b_hi,
                   width=2.2, dash="dot" if not is_base else "solid")]
    if not is_base:
        series.append(dict(name="Com o plano", colour=T.COLORS["petrol"], lo=p_lo, mid=p_mid, hi=p_hi))
    st.markdown(f'<div class="ck-chart-title">{T.esc(title())}</div>', unsafe_allow_html=True)
    fig = line_band_chart(x, series, "", fmt, tick_fmt=fmt, events=v["events"], height=380,
                          zero_line=(kind == "Caixa" and float(p_lo.min()) < 0))
    st.plotly_chart(fig, config=CONFIG, theme=None, key="main_chart")
    st.markdown('<div class="ck-note">A linha é o valor do meio dos futuros simulados; a sombra é o intervalo '
                'provável, onde caem 8 de cada 10.</div>', unsafe_allow_html=True)

    T.insight_row(v["cards"])

    with st.expander("Ver mais detalhe"):
        rows = [
            ("Faturação em 2036", F.eur(h["rev_2036"]["base"]), F.eur(h["rev_2036"]["plan"])),
            ("Margem EBITDA em 2036", F.pct(h["margin_2036"]["base"]), F.pct(h["margin_2036"]["plan"])),
            ("Caixa no fim de 2036", F.eur(h["cash_end"]["base"]), F.eur(h["cash_end"]["plan"])),
            ("Tempo de espera em 2036", F.days(h["wait_2036"]["base"]), F.days(h["wait_2036"]["plan"])),
            ("Reputação em 2036", F.stars(h["rep_2036"]["base"]), F.stars(h["rep_2036"]["plan"])),
            ("Ocupação da agenda em 2036", F.pct(h["util_2036"]["base"]), F.pct(h["util_2036"]["plan"])),
            ("Cansaço máximo da equipa (0 a 100%)", F.pct(h["fat_max"]["base"]), F.pct(h["fat_max"]["plan"])),
            ("Futuros com um incidente grave até 2036", f"{F.tenths(h['p_incident']['base'])} em 10",
             f"{F.tenths(h['p_incident']['plan'])} em 10"),
            ("Valor dos doentes perdidos em 2036", F.eur(h["lost_value_2036"]["base"]),
             F.eur(h["lost_value_2036"]["plan"])),
        ]
        df = pd.DataFrame(rows, columns=["", "Continuar como está", "Com o plano"])
        st.table(df, hide_index=True)
        st.markdown('<div class="ck-note">Valores do meio de 400 futuros simulados. Números ilustrativos.</div>',
                    unsafe_allow_html=True)

    exp = st.expander("Ver para onde vai o dinheiro, no mapa", key="x_map", on_change="rerun")
    with exp:
        if exp.open:
            if is_base:
                st.markdown('<div class="ck-small">Mude uma alavanca para ver o caminho do dinheiro no mapa.</div>',
                            unsafe_allow_html=True)
            else:
                sfig = scenario_figure(v["response"], set(v["changed"]))
                with st.container(key="mapwrap_plan"):
                    if T.is_phone():
                        st.caption("Deslize para o lado para ver o mapa todo.")
                    st.plotly_chart(sfig, config=MAP_CONFIG, theme=None, key="scenario_map")
                st.markdown(f'<div class="ck-legend">{SCENARIO_LEGEND}</div>', unsafe_allow_html=True)
