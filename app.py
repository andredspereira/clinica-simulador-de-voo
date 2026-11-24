"""Simulador de voo da clínica: a management flight simulator built on system dynamics.

Run with:  streamlit run app.py
"""

import streamlit as st

from ui import state as U
from ui import theme as T
from ui import tour

st.set_page_config(page_title="Simulador de voo da clínica", page_icon=":material/flight_takeoff:",
                   layout="wide", initial_sidebar_state="collapsed")
T.apply_theme()
U.init()

PAGES = {
    "entrada": st.Page(U.PAGE_FILES["entrada"], title="Entrada", icon=":material/home:", default=True),
    "mapa": st.Page(U.PAGE_FILES["mapa"], title="O mapa", url_path="mapa", icon=":material/hub:"),
    "pilotar": st.Page(U.PAGE_FILES["pilotar"], title="Pilotar", url_path="pilotar", icon=":material/tune:"),
    "rende": st.Page(U.PAGE_FILES["rende"], title="Onde rende cada euro", url_path="onde-rende",
                     icon=":material/euro:"),
    "comparar": st.Page(U.PAGE_FILES["comparar"], title="Comparar cenários", url_path="comparar",
                        icon=":material/compare_arrows:"),
    "como": st.Page(U.PAGE_FILES["como"], title="Como funciona", url_path="como-funciona",
                    icon=":material/menu_book:"),
}
page = st.navigation(list(PAGES.values()), position="top")
current = next(k for k, v in PAGES.items() if v.url_path == page.url_path)

T.wordmark()
tour.panel(current)
page.run()
T.footer()
