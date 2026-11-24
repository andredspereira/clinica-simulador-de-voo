"""Language and content rules: pt-PT, plain words for the investor, nothing private."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from core import insights as I
from core import scenarios as S
from core import structure as ST
from ui import map_view as MV

ROOT = Path(__file__).resolve().parents[1]
TEXT_FILES = [p for p in ROOT.rglob("*") if p.suffix in {".py", ".md", ".toml", ".txt", ".cfg", ".ini"}
              and ".venv" not in p.parts and ".git" not in p.parts and "__pycache__" not in p.parts]

JARGON = ["stock", "fluxo", "flow", "parâmetro", "parameter", "monte carlo", "distribuição", "distribution",
          "prior", "variância", "variance", "elasticidade", "elasticity", "regressão", "regression", "polaridade",
          "polarity"]
BRAZILIAN = ["usuário", "cadastro", "tela", "celular", "agendamento", "equipe", "registro", "contato",
             "faturamento", "gerenciar", "você", "time"]
INVESTOR_PAGES = ["ui/pages/mapa.py", "ui/pages/pilotar.py", "ui/pages/rende.py", "ui/pages/comparar.py"]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-zà-ú]+", text.lower()))


def test_no_em_or_en_dashes_anywhere():
    for path in TEXT_FILES:
        text = path.read_text(encoding="utf-8")
        assert chr(0x2014) not in text, path  # em dash
        assert chr(0x2013) not in text, path  # en dash


def _investor_texts() -> list[str]:
    texts = [n.label + " " + n.text for n in ST.NODES] + [lk.text for lk in ST.LINKS]
    texts += [lp.name + " " + lp.story for lp in ST.LOOPS] + [MV.MAP_LEGEND, MV.SCENARIO_LEGEND]
    texts += [t for pair in ST.KIND_TITLES.values() for t in pair]
    for plan in list(S.PRESETS.values()):
        b = I.bundle(plan, n_futures=80)
        for c in I.plan_cards(b):
            texts += [c.number, c.title, c.why]
    return texts


def test_investor_facing_text_is_plain_and_european_portuguese():
    for text in _investor_texts():
        words = _words(text)
        for w in JARGON:
            assert w not in text.lower() if " " in w else w not in words, (w, text)
        for w in BRAZILIAN:
            assert w not in words, (w, text)
        assert "!" not in text, text
        assert not re.search(r"\d\.\d", text), text


@pytest.mark.parametrize("page", INVESTOR_PAGES)
def test_rendered_pages_use_plain_words(page):
    at = AppTest.from_file("../app.py", default_timeout=180).run()
    at.switch_page(page).run()
    text = "\n".join(str(m.value) for m in list(at.markdown) + list(at.title) + list(at.caption))
    words = _words(re.sub(r"<[^>]+>", " ", text))
    for w in JARGON:
        assert w not in words, (page, w)
    for w in BRAZILIAN:
        assert w not in words, (page, w)
    assert not re.search(r"\d\.\d+\s?(M€|mil|%|dias)", text), page
