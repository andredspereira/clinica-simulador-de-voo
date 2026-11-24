"""Comparar cenários: the presets side by side, and whether the order of decisions matters."""

import numpy as np
import pandas as pd
import streamlit as st

from core import formatting as F
from core import scenarios as S
from ui import state as U
from ui import theme as T
from ui.charts import CONFIG, small_panel

U.init()
st.title("Comparar cenários")
T.lead("Cinco maneiras de usar os próximos dez anos, e o seu plano. Veja a caixa, o EBITDA e a espera lado a lado.")

with st.spinner("A simular os cenários..."):
    cv = U.compare_view(U.plan_key(), U.world_key())
names = cv["names"]
palette = [T.COLORS["mid_grey"], T.COLORS["orange"], T.COLORS["teal"], T.COLORS["light_blue"], T.COLORS["petrol"],
           T.COLORS["text"]]
colour = {n: palette[i % len(palette)] for i, n in enumerate(names)}

default = [n for n in ("Continuar como está", "Crescer com marketing", "Hospital já",
                       "Hospital depois de arrumar a casa", "O seu plano") if n in names]
if "w_compare" not in st.session_state:
    st.session_state["w_compare"] = default
chosen = st.pills("Cenários", names, selection_mode="multi", key="w_compare", label_visibility="collapsed") or default

years = np.array(cv["years"], dtype=float)
scen = []
for n in chosen:
    d = cv["data"][n]
    scen.append({"name": n, "colour": colour[n], "width": 2.6 if n == "O seu plano" else 2.0,
                 "dash": "dot" if n == "Continuar como está" else "solid",
                 "cash": tuple(np.array(a) for a in d["cash"]), "ebitda": tuple(np.array(a) for a in d["ebitda"]),
                 "wait": tuple(np.array(a) for a in d["wait"])})

best = max(chosen, key=lambda n: cv["data"][n]["gain"])
low = min(chosen, key=lambda n: cv["data"][n]["cash_min"])
if low != best:
    st.markdown(f'#### "{best}" ganha mais até 2036; "{low}" é o que mais aperta a caixa')
else:
    st.markdown(f'#### "{best}" ganha mais até 2036, mas é também o que mais aperta a caixa')
cols = st.columns(3, gap="small")
for col, (key, ttl, fmt) in zip(cols, [("cash", "Caixa no fim de cada ano", F.eur), ("ebitda", "EBITDA por ano", F.eur),
                                       ("wait", "Espera por uma primeira consulta", F.days)]):
    with col:
        st.plotly_chart(small_panel(years, scen, key, ttl, fmt), config=CONFIG, theme=None, key=f"cmp_{key}")
legend = " ".join(f'<span style="color:{colour[n]};font-weight:600">■</span> {T.esc(n)}&nbsp;&nbsp;' for n in chosen)
st.markdown(f'<div class="ck-small">{legend}</div>', unsafe_allow_html=True)

rows = []
for n in chosen:
    d = cv["data"][n]
    rows.append({"Cenário": n, "Ganho até 2036 face a hoje": F.eur(d["gain"], signed=True),
                 "Caixa no ponto mais baixo": F.eur(d["cash_min"]), "Espera em 2036": F.days(d["wait_2036"])})
st.table(pd.DataFrame(rows), hide_index=True)
with st.expander("Ver o que tem cada cenário"):
    for n in names:
        if n in S.PRESET_NOTES:
            st.markdown(f"**{n}.** {S.PRESET_NOTES[n]}")
        else:
            st.markdown(f"**{n}.** O plano que está em Pilotar.")

st.markdown("### A ordem das decisões conta?")
with st.spinner("A comparar as duas ordens..."):
    seq = U.sequencing_view(U.world_key())
st.markdown(f'<div class="ck-insight info"><div class="ck-insight-title">{T.esc(seq["head"])}</div>'
            f'<div class="ck-insight-why">{T.esc(seq["tail"])}</div></div>', unsafe_allow_html=True)
c, g = seq["casa"], seq["crescer"]
order = pd.DataFrame([
    {"Ordem": "Casa primeiro: receção, chamadas e base digital em 2027; marketing e hospital em 2029",
     "Ganho até 2036": F.eur(c["net10"][1], signed=True), "Caixa mais baixa": F.eur(c["cash_min"][1]),
     "Espera média": F.days(c["wait_avg"][1]), "Futuros com incidente": f"{F.tenths(c['p_incident'])} em 10"},
    {"Ordem": "Crescer primeiro: marketing e hospital em 2027; receção, chamadas e base digital em 2029",
     "Ganho até 2036": F.eur(g["net10"][1], signed=True), "Caixa mais baixa": F.eur(g["cash_min"][1]),
     "Espera média": F.days(g["wait_avg"][1]), "Futuros com incidente": f"{F.tenths(g['p_incident'])} em 10"},
])
st.table(order, hide_index=True)
st.markdown('<div class="ck-note">Mesmas alavancas e o mesmo investimento total; cada grupo dura sete anos. '
            'Valores do meio de 200 futuros simulados.</div>', unsafe_allow_html=True)
