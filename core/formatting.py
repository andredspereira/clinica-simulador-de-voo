"""pt-PT numbers, money, dates and frequencies.

Decimal comma, thousands separated by a non-breaking space, money as
"5,2 M€" or "320 mil €". Everything is rounded aggressively: the model is
illustrative, so no number should look more precise than it is.

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

import math

NBSP = " "
MONTHS_PT = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
             "setembro", "outubro", "novembro", "dezembro")


def _group(int_text: str) -> str:
    out = []
    while len(int_text) > 3:
        out.insert(0, int_text[-3:])
        int_text = int_text[:-3]
    out.insert(0, int_text)
    return NBSP.join(out)


def num(x: float, decimals: int = 0, signed: bool = False) -> str:
    """12 345,6 style."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    sign = ""
    if x < 0:
        sign = "-"
    elif signed and x > 0:
        sign = "+"
    text = f"{abs(x):.{decimals}f}"
    if "." in text:
        whole, frac = text.split(".")
        return f"{sign}{_group(whole)},{frac}"
    return f"{sign}{_group(text)}"


def nice(x: float) -> float:
    """Round a count so it does not look more precise than the model."""
    ax = abs(x)
    if ax >= 10_000:
        step = 100
    elif ax >= 1_000:
        step = 50
    elif ax >= 100:
        step = 10
    elif ax >= 10:
        step = 1
    else:
        return round(x, 1)
    return math.copysign(round(ax / step) * step, x)


def people(x: float, signed: bool = False) -> str:
    v = nice(x)
    if abs(v) < 10 and v != int(v):
        return num(v, 1, signed)
    return num(v, 0, signed)


def eur(x: float, signed: bool = False) -> str:
    """5,2 M€ / 320 mil € / 45 mil € / 850 €."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    ax = abs(x)
    if ax >= 999_500:
        body = num(ax / 1e6, 1) + f"{NBSP}M€"
    elif ax >= 100_000:
        body = num(round(ax / 10_000) * 10, 0) + f"{NBSP}mil{NBSP}€"
    elif ax >= 9_500:
        body = num(round(ax / 1_000), 0) + f"{NBSP}mil{NBSP}€"
    elif ax >= 1_000:
        body = num(round(ax / 500) * 0.5, 1).replace(",0", "") + f"{NBSP}mil{NBSP}€"
    else:
        body = num(round(ax / 10) * 10, 0) + f"{NBSP}€"
    zero = body.startswith("0") and not any(c in body[:3] for c in "123456789")
    if zero:
        return f"0{NBSP}€"
    if x < 0:
        return "-" + body
    if signed and x > 0:
        return "+" + body
    return body


def eur_per_year(x: float, signed: bool = False) -> str:
    return eur(x, signed) + " por ano"


def pct(x: float, decimals: int = 0, signed: bool = False) -> str:
    return num(100.0 * x, decimals, signed) + "%"


def points(x: float, signed: bool = True) -> str:
    """Change in percentage points."""
    v = round(100.0 * x)
    sign = "+" if (signed and v > 0) else ""
    unit = "ponto" if abs(v) == 1 else "pontos"
    return f"{sign}{num(v, 0)} {unit}"


def days(x: float, signed: bool = False) -> str:
    v = round(x)
    unit = "dia" if abs(v) == 1 else "dias"
    return f"{num(v, 0, signed)}{NBSP}{unit}"


def stars(x: float) -> str:
    return f"{num(x, 1)} em 5"


def ratio(x: float) -> str:
    """Return per euro: 3,2 €."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/d"
    if abs(x) >= 10:
        return num(x, 0) + f"{NBSP}€"
    return num(x, 1) + f"{NBSP}€"


def month_label(t_months: float, start_year: int = 2027) -> str:
    m = int(max(0, round(t_months)))
    year = start_year + m // 12
    return f"{MONTHS_PT[m % 12]} de {year}"


def year_of(t_months: float, start_year: int = 2027) -> int:
    return start_year + int(max(0, round(t_months))) // 12


def in_futures(share: float) -> str:
    """Natural frequencies: 'em 7 de cada 10 futuros simulados'."""
    if share >= 0.995:
        return "em todos os futuros simulados"
    if share <= 0.005:
        return "em nenhum dos futuros simulados"
    k = min(9, max(1, int(round(10 * share))))
    return f"em {k} de cada 10 futuros simulados"


def tenths(share: float) -> int:
    return int(round(10 * share))
