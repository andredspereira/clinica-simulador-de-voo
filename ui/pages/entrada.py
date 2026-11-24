"""Entrada: the name, one promise, and two ways in."""

import streamlit as st

from ui import state as U
from ui import tour

U.init()

st.markdown('<div class="ck-hero"><h1>Simulador de voo da clínica</h1>'
            '<p>Teste decisões antes de investir.</p></div>', unsafe_allow_html=True)
st.markdown('<div class="ck-quote">O Cockpit mostra o presente. O simulador testa o futuro.</div>',
            unsafe_allow_html=True)

c1, c2, _ = st.columns([1.35, 1, 1.4], gap="small")
if c1.button("Começar visita guiada (2 minutos)", type="primary", width="stretch", key="start_tour"):
    tour.start()
    st.switch_page(U.PAGE_FILES["mapa"])
if c2.button("Explorar à vontade", width="stretch", key="explore"):
    st.session_state["tour"] = None
    st.switch_page(U.PAGE_FILES["pilotar"])

st.markdown(
    '<div class="ck-grid ck-grid-3" style="margin-top:2rem">'
    '<div class="ck-card"><div class="ck-insight-title">Experimente</div><div class="ck-insight-why">'
    'Mexa em marketing, receção, base digital, médicos, uma nova clínica ou um hospital, e veja dez anos '
    'passarem em segundos.</div></div>'
    '<div class="ck-card"><div class="ck-insight-title">Veja para onde vai o dinheiro</div><div class="ck-insight-why">'
    'Onde cada euro rende, onde se perde pelo caminho, e quando chega o efeito.</div></div>'
    '<div class="ck-card"><div class="ck-insight-title">Saiba quão seguro é</div><div class="ck-insight-why">'
    'Cada plano corre em centenas de futuros possíveis. Só se afirma uma direção quando 8 em cada 10 '
    'concordam.</div></div></div>', unsafe_allow_html=True)
