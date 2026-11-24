"""Onde rende cada euro: one more step on each lever, on top of the current plan."""

import numpy as np
import pandas as pd
import streamlit as st

from core import formatting as F
from core import scenarios as S
from ui import state as U
from ui import theme as T
from ui.charts import CONFIG, leverage_bars, payback_strip

U.init()
st.title("Onde rende cada euro")
plan = U.plan()
base_words = "a continuar como está" if not S.changed_levers(plan) else "ao plano que está em Pilotar"
T.lead(f"Cada barra junta um pouco mais de uma alavanca {base_words} e mede o que volta até 2036, em 200 "
       "futuros simulados. Acima de 1 €, paga o que custa.")

with st.spinner("A testar cada alavanca em 200 futuros..."):
    lv = U.leverage_view(U.plan_key(plan), U.world_key())
costed, free = lv["costed"], lv["free"]

if costed:
    best, worst = costed[0], costed[-1]
    if worst["ratio"] < 1:
        head = f"{best['label']} rende mais por euro; {worst['label'].lower()} não paga o que custa"
    else:
        head = f"{best['label']} rende mais por euro; todas pagam o que custam"
    st.markdown(f'<div class="ck-chart-title">{T.esc(head)}</div>', unsafe_allow_html=True)
    st.plotly_chart(leverage_bars(costed, lambda r: r["sentence"]), config=CONFIG, theme=None, key="lev_bars")
    st.markdown('<div class="ck-note">Barras azul-petróleo: pagam-se em 8 de cada 10 futuros ou mais. Laranja: não se '
                'pagam em 8 de cada 10. Cinzento: ainda não sabemos. O traço mostra o intervalo provável.</div>',
                unsafe_allow_html=True)

if lv["card"]:
    T.insight_row([lv["card"]])

with st.expander("Ver quando se paga cada alavanca"):
    st.plotly_chart(payback_strip(costed), config=CONFIG, theme=None, key="payback")
    st.markdown('<div class="ck-note">O ponto é o ano do meio em que o ganho acumulado passa a cobrir o custo; o '
                'traço vai do mais cedo ao mais tarde, nos futuros em que se paga.</div>', unsafe_allow_html=True)

with st.expander("Ver mais detalhe: o que muda com cada alavanca"):
    rows = []
    for r in costed + free:
        rows.append({
            "Alavanca": r["label"],
            "O que se junta": r["increment"],
            "Custo médio por ano": F.eur(r["spend_per_year"]) if r["costed"] else "sem custo direto",
            "Ganho líquido até 2036": F.eur(r["net10"], signed=True),
            "Ganho até 2031": F.eur(r["net5"], signed=True),
            "Caixa mais baixa": F.eur(r["cash_min"], signed=True),
            "Doentes em 2036": F.people(r["seen"], signed=True),
            "Espera em 2036": F.days(r["wait"], signed=True),
        })
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    if free:
        st.markdown('<div class="ck-small"><b>Sem custo direto.</b> ' + " ".join(
            f"{T.esc(r['label'])} ({T.esc(r['increment'])}): {T.esc(F.eur(r['net10'], signed=True))} até 2036, "
            f"{T.esc(F.in_futures(r['share_pay']))} compensa." for r in free) + "</div>", unsafe_allow_html=True)
    st.markdown('<div class="ck-note">Quando uma alavanca já está no plano, a barra mostra quanto vale tê-la. '
                'Ganho líquido: EBITDA a mais, depois do custo da alavanca e do investimento.</div>',
                unsafe_allow_html=True)
