"""Colours, the small amount of CSS the app needs, and reusable blocks.

Light theme, white background, rounded cards with a thin light-grey border.
Poppins is set in .streamlit/config.toml; Tenor Sans, used only for the large
headline numbers, is loaded here because Streamlit's font option takes one
family per stylesheet.

Colour rule: petrol blue and teal for things that go up or help, the
orange-red accent only for losses and warnings, greys for "not sure".
"""

from __future__ import annotations

import html

import streamlit as st

COLORS = {
    "petrol": "#065268",
    "teal_muted": "#60919E",
    "light_blue": "#4CA3BE",
    "cyan": "#009DC3",
    "teal": "#17BCBE",
    "pale": "#CCEBF3",
    "text": "#333333",
    "dark_grey": "#5E6162",
    "mid_grey": "#A9ABAC",
    "line": "#E3E3E3",
    "soft": "#F0F0F0",
    "softer": "#F6F6F6",
    "white": "#FFFFFF",
    "orange": "#F16037",
}

FOOTER = ("Protótipo ilustrativo preparado por André Pereira. Os números são hipóteses plausíveis, "
          "não dados reais da clínica.")

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tenor+Sans&display=swap');
.block-container {{ padding-top: 4.2rem; padding-bottom: 2rem; max-width: 1280px; }}
h1 {{ color: {COLORS['petrol']}; letter-spacing: -0.01em; }}
h2, h3 {{ color: {COLORS['text']}; letter-spacing: -0.01em; }}
.ck-wordmark {{ font-weight: 600; color: {COLORS['petrol']}; font-size: 1.05rem; letter-spacing: 0.01em; }}
.ck-wordmark span {{ color: {COLORS['teal_muted']}; font-weight: 400; }}
.ck-lead {{ color: {COLORS['dark_grey']}; font-size: 1.02rem; line-height: 1.55; margin: -0.3rem 0 1.1rem 0; max-width: 52rem; }}
.ck-card {{ background: {COLORS['white']}; border: 1px solid {COLORS['line']}; border-radius: 14px;
           padding: 0.95rem 1.1rem; height: 100%; }}
.ck-metric-label {{ color: {COLORS['dark_grey']}; font-size: 0.82rem; font-weight: 500; line-height: 1.3; }}
.ck-metric-value {{ font-family: 'Tenor Sans', 'Poppins', sans-serif; color: {COLORS['petrol']};
                   font-size: 2.05rem; line-height: 1.15; margin: 0.25rem 0 0.2rem 0; white-space: nowrap; }}
.ck-metric-delta {{ font-size: 0.84rem; font-weight: 500; line-height: 1.35; }}
.ck-good {{ color: {COLORS['petrol']}; }}
.ck-bad {{ color: {COLORS['orange']}; }}
.ck-neutral {{ color: {COLORS['dark_grey']}; }}
.ck-note {{ color: {COLORS['mid_grey']}; font-size: 0.76rem; margin-top: 0.15rem; line-height: 1.35; }}
.ck-insight {{ background: {COLORS['white']}; border: 1px solid {COLORS['line']}; border-left: 4px solid {COLORS['petrol']};
              border-radius: 14px; padding: 0.9rem 1.1rem; height: 100%; }}
.ck-insight.warn {{ border-left-color: {COLORS['orange']}; }}
.ck-insight.info {{ border-left-color: {COLORS['mid_grey']}; }}
.ck-insight-number {{ font-family: 'Tenor Sans', 'Poppins', sans-serif; font-size: 1.65rem; color: {COLORS['petrol']};
                     line-height: 1.15; }}
.ck-insight.warn .ck-insight-number {{ color: {COLORS['orange']}; }}
.ck-insight-title {{ font-weight: 500; color: {COLORS['text']}; font-size: 0.92rem; margin: 0.2rem 0 0.35rem 0;
                    line-height: 1.35; }}
.ck-insight-why {{ color: {COLORS['dark_grey']}; font-size: 0.86rem; line-height: 1.45; }}
.ck-badge {{ display: inline-block; padding: 0.12rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 500;
            border: 1px solid {COLORS['line']}; }}
.ck-badge.reforca {{ color: {COLORS['petrol']}; background: {COLORS['pale']}; border-color: {COLORS['pale']}; }}
.ck-badge.trava {{ color: {COLORS['orange']}; background: #FDE7E0; border-color: #FDE7E0; }}
.ck-budget {{ margin: 0.2rem 0 0.9rem 0; }}
.ck-budget-bar {{ display: flex; height: 12px; border-radius: 999px; overflow: hidden; background: {COLORS['soft']}; }}
.ck-budget-bar div {{ height: 100%; }}
.ck-budget-legend {{ display: flex; flex-wrap: wrap; gap: 0.2rem 0.9rem; margin-top: 0.4rem; font-size: 0.76rem;
                    color: {COLORS['dark_grey']}; }}
.ck-budget-legend i {{ display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 0.3rem; }}
.ck-budget-total {{ font-size: 0.9rem; color: {COLORS['text']}; margin-bottom: 0.35rem; }}
.ck-budget-total b {{ font-weight: 600; color: {COLORS['petrol']}; }}
.ck-cost {{ color: {COLORS['dark_grey']}; font-size: 0.78rem; margin: -0.55rem 0 0.6rem 0; line-height: 1.35; }}
.ck-tour {{ background: {COLORS['softer']}; border: 1px solid {COLORS['line']}; border-radius: 14px; padding: 0.9rem 1.1rem;
           margin-bottom: 0.6rem; }}
.ck-tour-step {{ color: {COLORS['teal_muted']}; font-size: 0.78rem; font-weight: 600; letter-spacing: 0.04em;
                text-transform: uppercase; }}
.ck-tour-do {{ color: {COLORS['text']}; font-size: 1.0rem; font-weight: 500; margin: 0.2rem 0 0.3rem 0; }}
.ck-tour-see {{ color: {COLORS['dark_grey']}; font-size: 0.92rem; line-height: 1.5; }}
.ck-hero {{ padding: 2.2rem 0 1rem 0; }}
.ck-hero h1 {{ font-size: 2.6rem; margin-bottom: 0.4rem; }}
.ck-hero p {{ font-size: 1.2rem; color: {COLORS['dark_grey']}; }}
.ck-quote {{ font-family: 'Tenor Sans', 'Poppins', sans-serif; font-size: 1.35rem; color: {COLORS['teal_muted']};
            margin: 1.2rem 0 1.6rem 0; }}
.ck-footer {{ border-top: 1px solid {COLORS['line']}; margin-top: 2.4rem; padding-top: 0.9rem; color: {COLORS['mid_grey']};
             font-size: 0.8rem; text-align: center; }}
.ck-legend {{ color: {COLORS['dark_grey']}; font-size: 0.86rem; line-height: 1.55; }}
.ck-legend b {{ color: {COLORS['text']}; font-weight: 500; }}
.ck-small {{ color: {COLORS['dark_grey']}; font-size: 0.84rem; line-height: 1.5; }}
.ck-chart-title {{ font-size: 1.08rem; font-weight: 500; color: {COLORS['text']}; line-height: 1.4;
                  margin: 0.4rem 0 0.1rem 0; }}
.st-key-mapwrap, .st-key-mapwrap_plan {{ overflow-x: auto; }}
@media (max-width: 900px) {{
  .st-key-mapwrap .stElementContainer, .st-key-mapwrap_plan .stElementContainer {{ min-width: 1000px; }}
}}
.ck-grid {{ display: grid; gap: 0.75rem; margin: 0.2rem 0 0.9rem 0; }}
.ck-grid-4 {{ grid-template-columns: repeat(4, minmax(0, 1fr)); }}
.ck-grid-3 {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
.ck-grid-2 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
@media (max-width: 900px) {{ .ck-grid-4 {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                             .ck-grid-3 {{ grid-template-columns: 1fr; }} }}
.ck-loop {{ border: 1px solid {COLORS['line']}; border-radius: 14px; padding: 0.75rem 1rem; margin: 0.2rem 0 0.6rem 0; }}
.ck-loop-name {{ font-weight: 600; color: {COLORS['text']}; margin-right: 0.5rem; }}
.ck-loop-story {{ color: {COLORS['dark_grey']}; font-size: 0.92rem; margin-top: 0.3rem; line-height: 1.5; }}
.ck-row {{ display: flex; justify-content: space-between; gap: 1rem; padding: 0.55rem 0; border-bottom: 1px solid {COLORS['soft']};
          font-size: 0.9rem; }}
.ck-row span:last-child {{ color: {COLORS['dark_grey']}; text-align: right; }}
@media (max-width: 640px) {{
  .block-container {{ padding-left: 1rem; padding-right: 1rem; padding-top: 3.6rem; }}
  .ck-hero h1 {{ font-size: 2rem; }}
  .ck-hero p {{ font-size: 1.05rem; }}
  .ck-metric-value {{ font-size: 1.7rem; }}
  .ck-insight-number {{ font-size: 1.45rem; }}
}}
</style>
"""


def is_phone() -> bool:
    """A phone browser, from the request's user agent (used to give the map room to scroll)."""
    try:
        agent = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return "Mobi" in agent or "Android" in agent or "iPhone" in agent


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def wordmark() -> None:
    st.markdown('<div class="ck-wordmark">Clínica <span>· simulador de voo</span></div>', unsafe_allow_html=True)


def lead(text: str) -> None:
    st.markdown(f'<div class="ck-lead">{esc(text)}</div>', unsafe_allow_html=True)


def footer() -> None:
    st.markdown(f'<div class="ck-footer">{esc(FOOTER)}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = "", tone: str = "neutral", note: str = "") -> str:
    parts = [f'<div class="ck-card"><div class="ck-metric-label">{esc(label)}</div>',
             f'<div class="ck-metric-value">{esc(value)}</div>']
    if delta:
        parts.append(f'<div class="ck-metric-delta ck-{tone}">{esc(delta)}</div>')
    if note:
        parts.append(f'<div class="ck-note">{esc(note)}</div>')
    parts.append("</div>")
    return "".join(parts)


def metric_row(cards: list[str]) -> None:
    """Up to four headline numbers: four across on a laptop, two by two on a phone."""
    st.markdown(f'<div class="ck-grid ck-grid-4">{"".join(cards)}</div>', unsafe_allow_html=True)


def insight_html(card) -> str:
    c = card if isinstance(card, dict) else card.__dict__
    return (f'<div class="ck-insight {esc(c["tone"])}"><div class="ck-insight-number">{esc(c["number"])}</div>'
            f'<div class="ck-insight-title">{esc(c["title"])}</div>'
            f'<div class="ck-insight-why">{esc(c["why"])}</div></div>')


def insight_row(cards: list) -> None:
    """Up to three insight cards side by side, stacked on a phone."""
    if not cards:
        return
    body = "".join(insight_html(c) for c in cards)
    st.markdown(f'<div class="ck-grid ck-grid-3">{body}</div>', unsafe_allow_html=True)


def badge(kind: str) -> str:
    cls = "reforca" if kind == "reforça" else "trava"
    return f'<span class="ck-badge {cls}">{esc(kind)}</span>'


GROUP_COLORS = {"atrair": COLORS["petrol"], "atender": COLORS["teal"], "digital": COLORS["light_blue"],
                "capacidade": COLORS["teal_muted"]}
GROUP_NAMES = {"atrair": "Atrair doentes", "atender": "Atender quem chega", "digital": "Base digital",
               "capacidade": "Capacidade e grandes apostas"}


def budget_bar(costs: dict, fmt_eur) -> None:
    per_year = {g: max(v["per_year"], 0.0) for g, v in costs.items()}
    once = sum(max(v["once"], 0.0) for v in costs.values())
    saved = sum(min(v["per_year"], 0.0) for v in costs.values())
    total = sum(per_year.values())
    scale = max(total, 400_000.0)
    segs = "".join(f'<div style="width:{100 * v / scale:.1f}%;background:{GROUP_COLORS[g]}"></div>'
                   for g, v in per_year.items() if v > 0)
    legend = "".join(f'<span><i style="background:{GROUP_COLORS[g]}"></i>{esc(GROUP_NAMES[g])}</span>'
                     for g, v in per_year.items() if v > 0)
    head = f"Investimento anual planeado: <b>{esc(fmt_eur(total))}</b> por ano a mais"
    if once > 0:
        head += f", e <b>{esc(fmt_eur(once))}</b> de investimento único"
    if saved < -1_000:
        head += f"; poupa {esc(fmt_eur(-saved))} por ano"
    if total <= 0 and once <= 0 and saved >= -1_000:
        head = "Investimento anual planeado: <b>nenhum a mais</b>, tudo como hoje"
    st.markdown(f'<div class="ck-budget"><div class="ck-budget-total">{head}</div>'
                f'<div class="ck-budget-bar">{segs}</div><div class="ck-budget-legend">{legend}</div></div>',
                unsafe_allow_html=True)


def cost_note(text: str) -> None:
    st.markdown(f'<div class="ck-cost">{esc(text)}</div>', unsafe_allow_html=True)
