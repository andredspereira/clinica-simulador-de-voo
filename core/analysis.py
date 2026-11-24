"""What the app computes from the simulations.

1. Runs of plans across simulated futures (paired: every plan sees the same
   futures and the same random incidents, so differences come from the plan).
2. Onde rende cada euro: the standard increment for each lever, measured as
   return per euro, payback year and in how many futures it pays.
3. Para onde vai o dinheiro: how much each node of the causal map moves.
4. O número que mais vale a pena medir: which uncertain assumptions drive
   the uncertainty in an outcome (rank correlation across futures).
5. Ordem das decisões: the same investments in two orders.

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core import assumptions as A
from core import model as M
from core import scenarios as S
from core import structure as ST

SEED = 2027
N_FUTURES = 400  # an uncertainty run
N_LEVERAGE = 200  # futures per plan in the batched leverage analysis
AGREE = 0.8  # the rule: claim a direction only when 8 in 10 futures agree


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

def run_plans(plans: list[S.Plan], world: dict[str, float] | None = None, n_futures: int = 0,
              seed: int = SEED, keep: tuple[str, ...] = M.FULL, dt: float = M.STEP) -> list[M.Run]:
    """Simulate several plans on the same futures. n_futures=0 is the single central run."""
    world = world or A.default_world()
    if n_futures == 0:
        params, nf, incidents, uniforms = M.central_params(1), 1, "expected", None
    else:
        params, nf, incidents = M.draw_params(n_futures, seed), n_futures, "random"
        uniforms = M.uniforms_for(nf, len(plans), seed, dt=dt)
    batch = M.simulate(M.tile(params, len(plans)), S.policy_arrays(plans, nf),
                       S.world_arrays(world, nf * len(plans)), incidents=incidents,
                       uniforms=uniforms, keep=keep, dt=dt)
    runs = [batch.cols(j * nf, (j + 1) * nf) for j in range(len(plans))]
    for r in runs:
        r.extra["params"] = params
    return runs


def band(x: np.ndarray, axis: int = -1) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """10th, 50th and 90th percentiles: the median and the 'intervalo provável'."""
    lo, mid, hi = np.percentile(x, [10, 50, 90], axis=axis)
    return lo, mid, hi


def agreement(delta: np.ndarray, tol: float = 0.0) -> tuple[float, float]:
    """Share of futures where the change is up, and where it is down."""
    up = float(np.mean(delta > tol))
    down = float(np.mean(delta < -tol))
    return up, down


# ---------------------------------------------------------------------------
# Outcomes of one run (one value per future, or per year and future)
# ---------------------------------------------------------------------------

def outcomes(run: M.Run) -> dict[str, np.ndarray]:
    eb = run.annual_sum("ebitda")
    cx = run.annual_sum("capex")
    rev = run.annual_sum("rev")
    cash = run.m["Cash"]
    seen = run.patients_seen()
    lost = run.annual_sum("lost")
    c1 = run.annual_sum("C1")
    ortho_rev = rev - run.annual_sum("r_other") if "r_other" in run.m else rev
    value_per_new = np.divide(ortho_rev, c1, out=np.zeros_like(ortho_rev), where=c1 > 0)
    return {
        "rev_y": rev,
        "rev_2036": rev[-1],
        "ebitda_y": eb,
        "ebitda_cum10": eb.sum(0),
        "ebitda_cum5": eb[:5].sum(0),
        "margin_2036": np.divide(eb[-1], rev[-1], out=np.zeros_like(rev[-1]), where=rev[-1] > 0),
        "net_y": eb - cx,
        "net_cum10": (eb - cx).sum(0),
        "net_cum5": (eb - cx)[:5].sum(0),
        "cash_m": cash,
        "cash_min": cash.min(0),
        "cash_min_month": cash.argmin(0).astype(float),
        "cash_end": cash[-1],
        "seen_y": seen,
        "seen_2036": seen[-1],
        "wait_y": run.annual_mean("wait"),
        "wait_2036": run.annual_mean("wait")[-1],
        "lost_y": lost,
        "lost_2036": lost[-1],
        "lost_value_2036": lost[-1] * value_per_new[-1],
        "rep_y": run.year_end("Rep"),
        "rep_2036": run.m["Rep"][-1],
        "fat_max": run.m["Fat"].max(0),
        "util_y": run.annual_mean("u_doc"),
        "p_incident": run.extra["p_any_incident"],
    }


def first_payback_year(cum: np.ndarray) -> np.ndarray:
    """cum: (years, futures) cumulative gain at each year end.

    Returns the first calendar year from which the cumulative gain stays at
    or above zero until the horizon, or nan when it never does.
    """
    ok = cum >= 0
    stays = np.flip(np.logical_and.accumulate(np.flip(ok, axis=0), axis=0), axis=0)
    first = np.argmax(stays, axis=0)
    return np.where(stays.any(axis=0), M.START_YEAR + first, np.nan).astype(float)


# ---------------------------------------------------------------------------
# Onde rende cada euro
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Increment:
    id: str
    label: str
    group: str  # which spend flow carries its cost
    costed: bool


INCREMENTS: list[Increment] = [
    Increment("mkt", "Marketing digital", "spend_attract", True),
    Increment("callback", "Devolução de chamadas", "spend_access", True),
    Increment("online", "Marcação online", "spend_access", True),
    Increment("desk", "Equipa de receção", "spend_access", True),
    Increment("digital", "Base digital", "spend_digital", True),
    Increment("hire", "Contratar médicos", "spend_capacity", True),
    Increment("clinic", "Nova clínica", "spend_capacity", True),
    Increment("hospital", "Hospital", "spend_capacity", True),
    Increment("price", "Preços particulares", "", False),
    Increment("conv", "Convenções", "", False),
]
INC_BY_ID = {i.id: i for i in INCREMENTS}


def increment_variant(inc_id: str, plan: S.Plan) -> tuple[S.Plan, bool, str]:
    """The plan with one standard increment. Returns (variant, reversed, description).

    When a lever is already switched on in the plan, the variant switches it
    off and the result is read in reverse: what the lever is worth in the plan.
    """
    if inc_id == "mkt":
        return plan.with_changes(marketing=plan.marketing + 100_000), False, "mais 100 mil € por ano"
    if inc_id == "callback":
        if plan.callback:
            return plan.with_changes(callback=False), True, "já está no plano"
        return plan.with_changes(callback=True), False, "ligar o sistema"
    if inc_id == "online":
        if plan.online:
            return plan.with_changes(online=False), True, "já está no plano"
        return plan.with_changes(online=True), False, "ligar a marcação online"
    if inc_id == "desk":
        return plan.with_changes(front_desk=plan.front_desk + 2), False, "mais 2 pessoas (cerca de 40 mil € por ano)"
    if inc_id == "digital":
        return (plan.with_changes(digital_once=plan.digital_once + 100_000, digital_maint=plan.digital_maint + 20_000),
                False, "mais 100 mil € de investimento e 20 mil € por ano")
    if inc_id == "hire":
        return plan.with_changes(hire_rate=plan.hire_rate + 1.0), False, "mais 1 médico por ano, até encher os gabinetes"
    if inc_id == "clinic":
        if plan.clinic_year:
            return plan.with_changes(clinic_year=S.NEVER), True, "já está no plano"
        return plan.with_changes(clinic_year=2028), False, "abrir uma clínica decidida em 2028"
    if inc_id == "hospital":
        if plan.hospital_year:
            return plan.with_changes(hospital_year=S.NEVER), True, "já está no plano"
        return plan.with_changes(hospital_year=2028), False, "hospital decidido em 2028, 2 blocos e 12 camas"
    if inc_id == "price":
        return plan.with_changes(price=round(plan.price + 0.05, 2)), False, "mais 5% nos preços particulares"
    if inc_id == "conv":
        return plan.with_changes(conv=round(min(plan.conv + 0.05, 0.85), 2)), False, "mais 5 pontos de convenções"
    raise KeyError(inc_id)


def leverage(plan: S.Plan, world: dict[str, float] | None = None, n_futures: int = N_LEVERAGE,
             seed: int = SEED) -> list[dict]:
    """Return per euro, payback and agreement for each lever's standard increment."""
    variants, rev_flags, descr = [], [], []
    for inc in INCREMENTS:
        v, rev, d = increment_variant(inc.id, plan)
        variants.append(v)
        rev_flags.append(rev)
        descr.append(d)
    runs = run_plans([plan] + variants, world, n_futures, seed, keep=M.LEAN)
    base = runs[0]
    b_net = base.annual_sum("ebitda") - base.annual_sum("capex")
    b_cash_min = base.m["Cash"].min(0)
    b_seen = (base.annual_sum("C1") + base.year_start("A"))[-1]
    b_wait = base.annual_mean("wait")[-1]
    b_lost = base.annual_sum("lost")[-1]
    out = []
    for inc, run, rev, d in zip(INCREMENTS, runs[1:], rev_flags, descr):
        sign = -1.0 if rev else 1.0
        net_y = sign * ((run.annual_sum("ebitda") - run.annual_sum("capex")) - b_net)
        cum = np.cumsum(net_y, axis=0)
        net10, net5 = cum[-1], cum[4]
        if inc.costed:
            spend = sign * (run.annual_sum(inc.group).sum(0) - base.annual_sum(inc.group).sum(0))
        else:
            spend = np.zeros_like(net10)
        has_cost = inc.costed and float(np.median(spend)) > 1_000
        ratio = np.where(spend > 1_000, 1.0 + net10 / np.maximum(spend, 1_000), np.nan) if has_cost else np.full_like(net10, np.nan)
        pay_year = first_payback_year(cum)
        share_pay = float(np.mean(net10 >= 0))
        paying = pay_year[~np.isnan(pay_year)]
        seen = sign * ((run.annual_sum("C1") + run.year_start("A"))[-1] - b_seen)
        out.append({
            "id": inc.id, "label": inc.label, "increment": d, "reversed": rev, "costed": has_cost,
            "spend": float(np.median(spend)),
            "spend_per_year": float(np.median(spend)) / M.YEARS,
            "ratio": float(np.nanmedian(ratio)) if has_cost else float("nan"),
            "ratio_lo": float(np.nanpercentile(ratio, 10)) if has_cost else float("nan"),
            "ratio_hi": float(np.nanpercentile(ratio, 90)) if has_cost else float("nan"),
            "net10": float(np.median(net10)), "net10_lo": float(np.percentile(net10, 10)),
            "net10_hi": float(np.percentile(net10, 90)),
            "net5": float(np.median(net5)),
            "share_pay": share_pay,
            "pay_year": float(np.median(paying)) if paying.size else float("nan"),
            "pay_year_lo": float(np.percentile(paying, 10)) if paying.size else float("nan"),
            "pay_year_hi": float(np.percentile(paying, 90)) if paying.size else float("nan"),
            "cash_min": float(np.median(sign * (run.m["Cash"].min(0) - b_cash_min))),
            "seen": float(np.median(seen)),
            "wait": float(np.median(sign * (run.annual_mean("wait")[-1] - b_wait))),
            "lost": float(np.median(sign * (run.annual_sum("lost")[-1] - b_lost))),
            "util": float(np.median(base.annual_mean("u_doc")[-1])),
        })
    return out


def ranked(levers: list[dict]) -> tuple[list[dict], list[dict]]:
    """Costed levers sorted by return per euro, and the levers without a direct cost."""
    costed = sorted([r for r in levers if r["costed"]], key=lambda r: -r["ratio"])
    free = sorted([r for r in levers if not r["costed"]], key=lambda r: -r["net10"])
    return costed, free


# ---------------------------------------------------------------------------
# O número que mais vale a pena medir
# ---------------------------------------------------------------------------

def _ranks(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    # average ties
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    return sums[inv] / counts[inv]


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = _ranks(x), _ranks(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return 0.0
    return float(np.mean((rx - rx.mean()) * (ry - ry.mean())) / (sx * sy))


OUTCOME_CHOICES = {
    "net_cum10": "Ganho acumulado até 2036 (EBITDA menos investimento)",
    "cash_min": "Caixa no ponto mais baixo",
    "wait_2036": "Tempo de espera em 2036",
}


def measure_first(plan: S.Plan, world: dict[str, float] | None = None, outcome: str = "net_cum10",
                  n_futures: int = N_FUTURES, seed: int = SEED) -> list[dict]:
    """Uncertain assumptions ranked by how much they drive the outcome of this plan.

    When the plan differs from the baseline, the outcome is the plan's change
    versus continuing as today, future by future; otherwise it is the level.
    """
    differs = bool(S.changed_levers(plan))
    runs = run_plans([S.BASELINE, plan], world, n_futures, seed)
    o_plan = outcomes(runs[1])[outcome]
    y = o_plan - outcomes(runs[0])[outcome] if differs else o_plan
    params = runs[0].extra["params"]
    rows = []
    for a in A.uncertain():
        rho = spearman(params[a.key], y)
        rows.append({"key": a.key, "label": a.label, "rho": rho, "measure": a.measure,
                     "group": A.GROUPS[a.group]})
    rows.sort(key=lambda r: -abs(r["rho"]))
    total = sum(r["rho"] ** 2 for r in rows) or 1.0
    for r in rows:
        r["share"] = r["rho"] ** 2 / total
    return rows


# ---------------------------------------------------------------------------
# Para onde vai o dinheiro: how much each map node moves
# ---------------------------------------------------------------------------

def _last3(x: np.ndarray) -> np.ndarray:
    return x[-3:].mean(0)


def _node_values(run: M.Run) -> dict[str, np.ndarray]:
    m = run.m
    E = run.annual_sum("E")
    lost_access = run.annual_sum("lost_ph") + run.annual_sum("lost_web") + run.annual_sum("lost_ref")
    T = run.annual_sum("T")
    r_cons = run.annual_sum("r_cons")
    seen = run.patients_seen()
    return {
        "noto": _last3(run.annual_mean("L")),
        "comp": _last3(run.annual_mean("Cp")),
        "invest": _last3(run.annual_sum("spend_attract") + run.annual_sum("spend_digital")
                         + run.annual_sum("spend_access")),
        "price_avg": _last3(np.divide(r_cons, T, out=np.zeros_like(T), where=T > 0)),
        "enq": _last3(E),
        "access": _last3(np.divide(E - lost_access, E, out=np.zeros_like(E), where=E > 0)),
        "digital_mat": _last3(run.annual_mean("Dig")),
        "wait": _last3(run.annual_mean("wait")),
        "doctors": _last3(run.annual_mean("Deff")),
        "util": _last3(run.annual_mean("u_doc")),
        "fatigue": _last3(run.annual_mean("Fat")),
        "sat": _last3(run.annual_mean("sat")),
        "rep": _last3(run.annual_mean("Rep")),
        "follow": _last3(run.annual_mean("A")),
        "surg": _last3(run.annual_sum("S_int")),
        "hosp": _last3(run.annual_sum("S_own") + run.annual_sum("S_ext")),
        "seen": _last3(seen),
        "lost": _last3(run.annual_sum("lost")),
        "revenue": _last3(run.annual_sum("rev")),
        "ebitda": run.annual_sum("ebitda").sum(0),
        "cash": m["Cash"][-1],
        "risk": run.extra["p_any_incident"],
    }


# Scale below which a change counts as relative to this floor (for nodes near zero).
_FLOORS = {"comp": 0.05, "fatigue": 0.1, "hosp": 50.0, "cash": 1_000_000.0, "ebitda": 1_000_000.0,
           "risk": 0.1, "invest": 100_000.0}


def map_response(base: M.Run, plan_run: M.Run) -> dict[str, dict]:
    """Relative change of each node, per future, summarised by median and agreement."""
    vb, vp = _node_values(base), _node_values(plan_run)
    out = {}
    for node_id in vb:
        b, p = vb[node_id], vp[node_id]
        floor = _FLOORS.get(node_id, 0.0)
        denom = np.maximum(np.abs(b), floor) if floor else np.where(np.abs(b) > 1e-12, np.abs(b), 1.0)
        rel = (p - b) / denom
        up, down = agreement(rel, tol=1e-4)
        out[node_id] = {
            "rel": float(np.median(rel)), "lo": float(np.percentile(rel, 10)),
            "hi": float(np.percentile(rel, 90)), "up": up, "down": down,
            "base": float(np.median(b)), "plan": float(np.median(p)),
        }
    return out


def plan_nodes(plan: S.Plan, base: S.Plan = S.BASELINE) -> set[str]:
    return {ST.PLAN_FIELDS_TO_NODES[f] for f in S.changed_levers(plan, base) if f in ST.PLAN_FIELDS_TO_NODES}


# ---------------------------------------------------------------------------
# Ordem das decisões
# ---------------------------------------------------------------------------

def sequencing(world: dict[str, float] | None = None, n_futures: int = N_LEVERAGE, seed: int = SEED) -> dict:
    house_first, grow_first = S.sequencing_pair()
    runs = run_plans([S.BASELINE, house_first, grow_first], world, n_futures, seed)
    o = [outcomes(r) for r in runs]
    spend = [sum(r.annual_sum(g).sum(0) for g in ("spend_attract", "spend_access", "spend_digital")) for r in runs]
    res = {"plans": {"casa": house_first, "crescer": grow_first}}
    for key, idx in (("casa", 1), ("crescer", 2)):
        res[key] = {
            "net10": band(o[idx]["net_cum10"] - o[0]["net_cum10"]),
            "cash_min": band(o[idx]["cash_min"]),
            "cash_min_month": float(np.median(o[idx]["cash_min_month"])),
            "wait_avg": band(o[idx]["wait_y"].mean(0)),
            "lost_total": band(o[idx]["lost_y"].sum(0)),
            "p_incident": float(np.mean(o[idx]["p_incident"])),
            "spend": float(np.median(spend[idx] - spend[0])),
            "rep_min": float(np.median(runs[idx].m["Rep"].min(0))),
        }
    diff = o[1]["net_cum10"] - o[2]["net_cum10"]
    res["share_house_better"] = float(np.mean(diff > 0))
    res["diff_net10"] = band(diff)
    res["diff_cash_min"] = band(o[1]["cash_min"] - o[2]["cash_min"])
    return res
