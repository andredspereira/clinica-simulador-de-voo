"""O mapa: the clinic as a system, one loop at a time."""

import streamlit as st

from core import structure as ST
from ui import state as U
from ui.charts import MAP_CONFIG
from ui.map_view import MAP_LEGEND, map_figure
from ui.theme import badge, esc, is_phone

U.init()
st.title("O mapa da clínica")
st.markdown('<div class="ck-lead">O que puxa o quê. Os ciclos explicam as surpresas: uns fazem crescer, '
            'outros travam. Escolha um ciclo para o ver sozinho.</div>', unsafe_allow_html=True)

if "w_loop" not in st.session_state:
    st.session_state["w_loop"] = ""
options = [""] + [lp.id for lp in ST.LOOPS]
names = {"": "Nenhum: ver o mapa inteiro"} | {lp.id: f"{lp.name} ({lp.kind})" for lp in ST.LOOPS}
loop_id = st.selectbox("Mostrar um ciclo", options, format_func=lambda k: names[k], key="w_loop")

if loop_id:
    lp = ST.LOOP_BY_ID[loop_id]
    st.markdown(f'<div class="ck-loop"><span class="ck-loop-name">{esc(lp.name)}</span>{badge(lp.kind)}'
                f'<div class="ck-loop-story">{esc(lp.story)}</div></div>', unsafe_allow_html=True)

fig = map_figure(loop_id or None)
with st.container(key="mapwrap"):
    if is_phone():
        st.caption("Deslize para o lado para ver o mapa todo.")
    st.plotly_chart(fig, config=MAP_CONFIG, theme=None, key="causal_map")
st.markdown(f'<div class="ck-legend">{MAP_LEGEND}</div>', unsafe_allow_html=True)

with st.expander("Ver mais detalhe: os oito ciclos"):
    for lp in ST.LOOPS:
        st.markdown(f'<div class="ck-loop"><span class="ck-loop-name">{esc(lp.name)}</span>{badge(lp.kind)}'
                    f'<div class="ck-loop-story">{esc(lp.story)}</div></div>', unsafe_allow_html=True)
