"""Smoke tests: every page loads, the guided tour runs end to end, a plan renders."""

from __future__ import annotations

import pytest
from streamlit.testing.v1 import AppTest

from core import scenarios as S

APP = "../app.py"
PAGES = ["ui/pages/mapa.py", "ui/pages/pilotar.py", "ui/pages/rende.py", "ui/pages/comparar.py",
         "ui/pages/como_funciona.py"]
FOOTER = "Protótipo ilustrativo preparado por André Pereira"


def _texts(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [t.value for t in at.title] + [c.value for c in at.caption]
    return "\n".join(str(p) for p in parts)


@pytest.fixture(scope="module")
def app() -> AppTest:
    return AppTest.from_file(APP, default_timeout=180).run()


def test_landing_page_loads(app):
    assert not app.exception
    text = _texts(app)
    assert "Teste decisões antes de investir." in text
    assert FOOTER in text


@pytest.mark.parametrize("page", PAGES)
def test_every_page_loads_without_exceptions(app, page):
    app.switch_page(page).run()
    assert not app.exception, [e.value for e in app.exception]
    assert FOOTER in _texts(app)


def test_guided_tour_runs_end_to_end():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.button(key="start_tour").click().run()
    assert not at.exception
    assert at.session_state["tour"] == 0
    seen = []
    for _ in range(5):
        text = _texts(at)
        assert "Visita guiada" in text
        seen.append(at.session_state["tour"])
        at.button(key="tour_next").click().run()
        assert not at.exception, [e.value for e in at.exception]
    assert seen == [0, 1, 2, 3, 4]
    assert at.session_state["tour"] is None


def test_pilotar_renders_a_plan_and_its_map():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.session_state["plan"] = S.PRESETS["Hospital depois de arrumar a casa"]
    at.session_state["x_map"] = True
    at.switch_page("ui/pages/pilotar.py").run()
    assert not at.exception, [e.value for e in at.exception]
    for chart in ("Caixa", "Espera", "Reputação", "Doentes"):
        at.session_state["w_chart"] = chart
        at.run()
        assert not at.exception, chart
