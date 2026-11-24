"""The guided tour: five steps, each sets the levers so nothing can go wrong.

Each step has one sentence on what to do and one on what to notice. The second
sentence is generated from the actual results of the step's plan.
"""

from __future__ import annotations

import streamlit as st

from core import formatting as F
from core import scenarios as S
from ui import state as U
from ui.theme import esc

B = S.BASELINE
_MKT = B.with_changes(marketing=B.marketing + 200_000)
_FIX = B.with_changes(callback=True, online=True)
_HOSP = _FIX.with_changes(hospital_year=2028)

STEPS = [
    dict(page="mapa", plan=B, loop="R1", chart=None, open=None,
         do="Isto é a clínica vista como um sistema: à esquerda o que controlamos, à direita o que nos importa."),
    dict(page="pilotar", plan=_MKT, chart="Espera", open="x_atrair",
         do="Pusemos mais 200 mil € por ano em marketing digital. Veja a espera e os doentes perdidos."),
    dict(page="pilotar", plan=_FIX, chart="Doentes", open="x_atender",
         do="Agora, em vez do marketing, ligámos as chamadas perdidas e a marcação online. Compare."),
    dict(page="pilotar", plan=_HOSP, chart="Caixa", open="x_capacidade",
         do="Por cima disso, decidimos construir um hospital em 2028. Veja o vale da caixa."),
    dict(page="rende", plan=_HOSP, chart=None, open=None,
         do="Por fim, onde rende cada euro: cada barra é uma alavanca a mais sobre este plano."),
]


def _view(p: S.Plan) -> dict:
    return U.plan_view(U.plan_key(p), U.world_key())


def notice(i: int) -> str:
    """What to notice, written from the simulated results of this step."""
    if i == 0:
        v = _view(B)
        lost = v["cards"][0]["number"] if v["cards"] else "muitas"
        return (f"Siga o ciclo do boca a boca a azul. Hoje, no modelo, cerca de {lost} pessoas por ano procuram a "
                f"clínica e não chegam a uma consulta.")
    if i == 1:
        h = _view(_MKT)["head"]
        w0, w1 = h["wait_2036"]["base"], h["wait_2036"]["plan"]
        d_lost = h["lost_2036"]["delta"]
        d_net = h["net_cum10"]["delta"]
        verb = "melhora" if d_net > 0 else "piora"
        return (f"Em 2036 a espera passa de {F.days(w0)} para {F.days(w1)}, perdem-se mais {F.people(d_lost)} doentes "
                f"por ano e o resultado acumulado até 2036 {verb} {F.eur(abs(d_net))}.")
    if i == 2:
        h2, h3 = _view(_MKT)["head"], _view(_FIX)["head"]
        cost = S.lever_costs(_FIX)["atender"]["per_year"]
        d3, d2 = h3["seen_2036"]["delta"], h2["seen_2036"]["delta"]
        more3 = f"mais {F.people(d3)}" if d3 >= 0 else f"menos {F.people(-d3)}"
        more2 = f"{F.people(d2)} a mais" if d2 >= 0 else f"{F.people(-d2)} a menos"
        return (f"Por cerca de {F.eur(cost)} por ano, atendem-se {more3} doentes em 2036 e o resultado acumulado muda "
                f"{F.eur(h3['net_cum10']['delta'], signed=True)}. Os 200 mil € por ano de marketing davam {more2}, "
                f"com {F.eur(h2['net_cum10']['delta'], signed=True)}.")
    if i == 3:
        v = _view(_HOSP)
        h = v["head"]["cash_min"]
        year = F.year_of(h["month"])
        hosp = next((c for c in v["cards"] if c.get("loop") == "R4"), None)
        tail = f" {hosp['number']} {hosp['title']}." if hosp else ""
        return f"A caixa desce até {F.eur(h['plan'])} em {year} antes de recuperar.{tail}"
    lv = U.leverage_view(U.plan_key(_HOSP), U.world_key())
    if not lv["costed"]:
        return ""
    top = lv["costed"][0]
    return (f"Com este plano, o euro que mais rende está em {top['label'].lower()}: voltam {F.ratio(top['ratio'])} "
            f"por cada euro até 2036.")


def start() -> None:
    go_to(0)


def go_to(i: int | None) -> None:
    """Apply a step's settings (call before the lever widgets render)."""
    if i is None or i >= len(STEPS):
        st.session_state["tour"] = None
        return
    step = STEPS[i]
    st.session_state["tour"] = i
    U.reset_world()
    U.push_plan_to_widgets(step["plan"])
    if step.get("chart"):
        st.session_state["w_chart"] = step["chart"]
    if step.get("open"):
        for key in U.EXPANDERS:
            st.session_state[key] = key == step["open"]
    if "loop" in step:
        st.session_state["w_loop"] = step["loop"]


def panel(current_page: str) -> None:
    """The tour box at the top of the page, while the tour is on."""
    i = st.session_state.get("tour")
    if i is None:
        return
    step = STEPS[i]
    if step["page"] != current_page:
        return
    with st.spinner("A preparar este passo..."):
        see = notice(i)
    st.markdown(f'<div class="ck-tour"><div class="ck-tour-step">Visita guiada · passo {i + 1} de {len(STEPS)}</div>'
                f'<div class="ck-tour-do">{esc(step["do"])}</div><div class="ck-tour-see">{esc(see)}</div></div>',
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1.2], gap="small")
    if c1.button("Anterior", disabled=i == 0, key="tour_prev", width="stretch"):
        go_to(i - 1)
        st.switch_page(U.PAGE_FILES[STEPS[i - 1]["page"]])
    last = i == len(STEPS) - 1
    if c2.button("Terminar" if last else "Seguinte", type="primary", key="tour_next", width="stretch"):
        if last:
            st.session_state["tour"] = None
            st.rerun()
        go_to(i + 1)
        st.switch_page(U.PAGE_FILES[STEPS[i + 1]["page"]])
    if c3.button("Fechar visita", key="tour_close", width="stretch"):
        st.session_state["tour"] = None
        st.rerun()
