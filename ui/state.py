"""Session state, lever widgets and cached computations.

The plan lives in st.session_state["plan"]. Lever widgets have keys of the
form "w_<field>" and are initialised from the plan before they render, so a
plan set by the guided tour or by a reset shows up in the widgets. Cached
functions take hashable keys (plan and world as tuples) and return small
summaries, never the raw simulation arrays, to keep memory low.
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core import analysis as AN
from core import assumptions as A
from core import formatting as F
from core import insights as I
from core import scenarios as S

PAGE_FILES = {
    "entrada": "ui/pages/entrada.py",
    "mapa": "ui/pages/mapa.py",
    "pilotar": "ui/pages/pilotar.py",
    "rende": "ui/pages/rende.py",
    "comparar": "ui/pages/comparar.py",
    "como": "ui/pages/como_funciona.py",
}

YEARS_OPT = ["Não"] + [str(y) for y in range(2027, 2034)]

# field -> (widget key, plan value -> widget value, widget value -> plan value)
LEVERS = {
    "marketing": ("w_marketing", lambda v: int(round(v / 1000)), lambda w: float(w) * 1000),
    "conv": ("w_conv", lambda v: int(round(v * 100)), lambda w: w / 100.0),
    "price": ("w_price", lambda v: int(round(v * 100)), lambda w: w / 100.0),
    "callback": ("w_callback", bool, bool),
    "online": ("w_online", bool, bool),
    "front_desk": ("w_front_desk", lambda v: int(round(v)), float),
    "digital_once": ("w_digital_once", lambda v: int(round(v / 1000)), lambda w: float(w) * 1000),
    "digital_maint": ("w_digital_maint", lambda v: int(round(v / 1000)), lambda w: float(w) * 1000),
    "hire_rate": ("w_hire_rate", float, float),
    "clinic_year": ("w_clinic_year", lambda v: "Não" if not v else str(v), lambda w: 0 if w == "Não" else int(w)),
    "hospital_year": ("w_hospital_year", lambda v: "Não" if not v else str(v), lambda w: 0 if w == "Não" else int(w)),
    "hospital_rooms": ("w_hospital_rooms", int, int),
    "hospital_beds": ("w_hospital_beds", int, int),
    "hospital_debt": ("w_hospital_debt", lambda v: int(round(v * 100)), lambda w: w / 100.0),
}

EXPANDERS = ("x_atrair", "x_atender", "x_digital", "x_capacidade")
CHARTS = ("Faturação", "Caixa", "Doentes", "Espera", "Reputação")


def init() -> None:
    ss = st.session_state
    if "plan" not in ss:
        ss["plan"] = S.BASELINE
    if "world" not in ss:
        ss["world"] = A.default_world()
    if "tour" not in ss:
        ss["tour"] = None
    if "w_chart" not in ss:
        ss["w_chart"] = "Faturação"
    for i, key in enumerate(EXPANDERS):
        if key not in ss:
            ss[key] = i == 0


def plan() -> S.Plan:
    return st.session_state["plan"]


def world() -> dict[str, float]:
    return st.session_state["world"]


def plan_key(p: S.Plan | None = None) -> tuple:
    return (p or plan()).as_key()


def world_key(w: dict | None = None) -> tuple:
    return tuple(sorted((w or world()).items()))


def ensure_widgets() -> None:
    """Give every lever widget its value from the plan, if it has none yet."""
    p = plan()
    for field, (key, to_w, _) in LEVERS.items():
        if key not in st.session_state:
            st.session_state[key] = to_w(getattr(p, field))
    for f in A.FORCES:
        key = f"w_world_{f.key}"
        if key not in st.session_state:
            st.session_state[key] = _snap(world()[f.key], f)


def _snap(v: float, f: A.Force) -> float:
    opts = force_options(f)
    return min(opts, key=lambda o: abs(o - v))


def force_options(f: A.Force) -> list[float]:
    n = int(round((f.high - f.low) / f.step))
    return [round(f.low + i * f.step, 4) for i in range(n + 1)]


def push_plan_to_widgets(p: S.Plan) -> None:
    """Set the plan and overwrite every lever widget (only before the widgets render)."""
    st.session_state["plan"] = p
    for field, (key, to_w, _) in LEVERS.items():
        st.session_state[key] = to_w(getattr(p, field))


def on_lever_change() -> None:
    p = plan()
    changes = {}
    for field, (key, _, from_w) in LEVERS.items():
        if key in st.session_state:
            changes[field] = from_w(st.session_state[key])
    st.session_state["plan"] = p.with_changes(**changes)


def on_world_change() -> None:
    w = dict(world())
    for f in A.FORCES:
        key = f"w_world_{f.key}"
        if key in st.session_state:
            w[f.key] = float(st.session_state[key])
    st.session_state["world"] = w


def reset_plan() -> None:
    push_plan_to_widgets(S.BASELINE)


def reset_world() -> None:
    st.session_state["world"] = A.default_world()
    for f in A.FORCES:
        st.session_state[f"w_world_{f.key}"] = _snap(f.value, f)


def world_changed() -> bool:
    return world_key() != world_key(A.default_world())


# ---------------------------------------------------------------------------
# Cached view models
# ---------------------------------------------------------------------------

def _plan_from(key: tuple) -> S.Plan:
    return S.plan_from_key(key)


def _event_month(run, key: str, threshold: float) -> float | None:
    x = run.m[key]
    hit = x > threshold
    if not hit.any():
        return None
    first = np.where(hit.any(axis=0), hit.argmax(axis=0), np.nan)
    if np.mean(np.isfinite(first)) < 0.5:
        return None
    return float(np.nanmedian(first))


@st.cache_data(max_entries=24, show_spinner=False)
def plan_view(pk: tuple, wk: tuple) -> dict:
    p = _plan_from(pk)
    b = I.bundle(p, dict(wk))
    base, run, ob, op = b.base, b.run, b.base_out, b.out
    years = np.arange(S.START_YEAR, S.END_YEAR + 1)
    months_stock = S.START_YEAR + np.arange(run.m["Cash"].shape[0]) / 12.0
    months_flow = S.START_YEAR + (np.arange(run.m["wait"].shape[0]) + 0.5) / 12.0

    def bands(arr_b, arr_p):
        return {"base": [x.tolist() for x in AN.band(arr_b)], "plan": [x.tolist() for x in AN.band(arr_p)]}

    series = {
        "Faturação": {"x": years.tolist(), **bands(ob["rev_y"], op["rev_y"])},
        "Caixa": {"x": months_stock.tolist(), **bands(base.m["Cash"], run.m["Cash"])},
        "Doentes": {"x": years.tolist(), **bands(ob["seen_y"], op["seen_y"])},
        "Espera": {"x": months_flow.tolist(), **bands(base.m["wait"], run.m["wait"])},
        "Reputação": {"x": months_stock.tolist(), **bands(base.m["Rep"], run.m["Rep"])},
    }
    events = []
    h = _event_month(run, "Hops", 0.5) if p.hospital_year else None
    if h is not None:
        events.append((S.START_YEAR + h / 12.0, "Hospital abre"))
    c = _event_month(run, "Kr", 0.001) if p.clinic_year else None
    if c is not None:
        events.append((S.START_YEAR + c / 12.0, "Nova clínica abre"))

    def delta(key):
        d = op[key] - ob[key]
        up, down = AN.agreement(d, tol=1e-6 * max(1.0, float(np.median(np.abs(ob[key])))))
        return {"plan": float(np.median(op[key])), "base": float(np.median(ob[key])), "delta": float(np.median(d)),
                "up": up, "down": down}

    head = {k: delta(k) for k in ("ebitda_cum10", "net_cum10", "cash_min", "seen_2036", "lost_2036", "rev_2036",
                                  "wait_2036", "rep_2036", "margin_2036", "cash_end", "fat_max", "lost_value_2036")}
    head["cash_min"]["month"] = float(np.median(op["cash_min_month"]))
    head["p_incident"] = {"plan": float(np.mean(op["p_incident"])), "base": float(np.mean(ob["p_incident"]))}
    head["util_2036"] = {"plan": float(np.median(op["util_y"][-1])), "base": float(np.median(ob["util_y"][-1]))}
    cards = [c.__dict__ for c in I.plan_cards(b)]
    response = AN.map_response(base, run)
    return {"series": series, "events": events, "head": head, "cards": cards, "response": response,
            "changed": sorted(AN.plan_nodes(p)), "is_base": not S.changed_levers(p)}


@st.cache_data(max_entries=16, show_spinner=False)
def leverage_view(pk: tuple, wk: tuple) -> dict:
    rows = AN.leverage(_plan_from(pk), dict(wk))
    costed, free = AN.ranked(rows)
    card = I.leverage_card(costed, free)
    for r in costed + free:
        r["sentence"] = I.leverage_sentence(r)
    return {"costed": costed, "free": free, "card": card.__dict__ if card else None}


@st.cache_data(max_entries=8, show_spinner=False)
def compare_view(pk: tuple, wk: tuple) -> dict:
    current = _plan_from(pk)
    names = list(S.PRESETS)
    plans = [S.PRESETS[n] for n in names]
    if all(current != pl for pl in plans):
        names.append("O seu plano")
        plans.append(current)
    runs = AN.run_plans(plans, dict(wk), AN.N_LEVERAGE)
    out = {"names": names, "years": list(range(S.START_YEAR, S.END_YEAR + 1)), "data": {}}
    for name, r in zip(names, runs):
        o = AN.outcomes(r)
        out["data"][name] = {
            "cash": [x.tolist() for x in AN.band(r.year_end("Cash"))],
            "ebitda": [x.tolist() for x in AN.band(o["ebitda_y"])],
            "wait": [x.tolist() for x in AN.band(o["wait_y"])],
            "net10": float(np.median(o["net_cum10"])),
            "cash_min": float(np.median(o["cash_min"])),
            "wait_2036": float(np.median(o["wait_2036"])),
        }
    base_net = out["data"]["Continuar como está"]["net10"]
    for name in names:
        out["data"][name]["gain"] = out["data"][name]["net10"] - base_net
    return out


@st.cache_data(max_entries=4, show_spinner=False)
def sequencing_view(wk: tuple) -> dict:
    seq = AN.sequencing(dict(wk))
    head, tail = I.sequencing_text(seq)
    keep = {k: seq[k] for k in ("share_house_better",)}
    for side in ("casa", "crescer"):
        keep[side] = {k: (list(map(float, v)) if isinstance(v, tuple) else v) for k, v in seq[side].items()}
    keep["head"], keep["tail"] = head, tail
    return keep


@st.cache_data(max_entries=16, show_spinner=False)
def measure_view(pk: tuple, wk: tuple, outcome: str) -> list[dict]:
    return AN.measure_first(_plan_from(pk), dict(wk), outcome)[:8]


def fmt_head(key: str, value: float) -> str:
    if key in ("ebitda_cum10", "net_cum10", "cash_min", "rev_2036", "cash_end", "lost_value_2036"):
        return F.eur(value)
    if key in ("seen_2036", "lost_2036"):
        return F.people(value)
    if key == "wait_2036":
        return F.days(value)
    if key == "rep_2036":
        return F.stars(value)
    if key in ("margin_2036", "fat_max"):
        return F.pct(value)
    return F.num(value, 1)
