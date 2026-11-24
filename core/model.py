"""Stocks, flows and equations of the clinic, vectorised over simulated futures.

A column is one simulated future under one plan. Every array in the loop holds
one value per column, so a whole uncertainty run, or a batch of plans that
share the same futures, is a single pass of the time loop.

Integration is Euler with a step of 0.25 month; results are reported monthly.
Each future starts at its own equilibrium: the observable present (new
patients, wait, utilisation, team sizes) is the same in every future, while
the hidden or uncertain quantities differ. A plan with no changes therefore
stays close to today, and every change comes from a decision or from an
outside force.

Stocks (units):
  L      notoriety: people who know the clinic and would choose it (people)
  Meff   marketing spend still building notoriety (EUR/month, delayed)
  W1     waiting list for a first consultation (people)
  A      patients in an active care pathway (people)
  WS     surgical waiting list (people)
  Rep    reputation, like an online rating (0 to 5)
  Dp     doctors being recruited (FTE)
  Dn     recently hired doctors still ramping up (FTE)
  D      fully productive doctors (FTE)
  Xh, Hx planned and started expansion hires (FTE)
  FD     front desk team (FTE)
  Fat    team fatigue (0 to 1)
  Pdig   digital projects in progress (EUR)
  Dig    digital maturity (0 to 1)
  Hp     hospital licensing and construction progress (0 to 1)
  Hops   operational hospital capacity (surgeries/month)
  Xext   outside surgical demand for the hospital (surgeries/month)
  Kp, Kr new clinic works progress and ramp-up (0 to 1)
  Cp     competitive response (index, 0 = none)
  Pp     price as perceived by private patients (index, 1 = today)
  Im     memory of a serious incident, in reputation stars (stars)
  Cash   cash (EUR); Debt hospital debt (EUR)

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

from core import assumptions as A

STEP = 0.25
MONTHS = 120
START_YEAR = 2027
YEARS = MONTHS // 12
DAYS_PER_MONTH = 30.4

K_DOC = 2.5  # how the wait for new patients grows as free slots fill (close to a queue)
K_FU = 8.0  # follow-ups are booked first and are rarely squeezed
U_FU = 0.95  # follow-ups can take at most this share of the agenda
K_SURG = 3.0  # same for surgery
K_CALL = 4.0  # calls arrive in peaks, so the front desk limit is softer
N_ROOMS = 16.0  # how sharply rooms cap the doctors who can work
N_SURG = 8.0  # how sharply surgeons and operating time cap each other
THETA_SCALE = 150_000.0  # EUR: how gradually low cash cuts optional spending
FAT_QUALITY = 0.15  # satisfaction lost at full fatigue
FAT_DOC_WEIGHT = 0.75  # doctors weigh more than the front desk in team fatigue
FAT_PROD = 0.15  # productivity lost at full fatigue

# What is recorded every month. Stocks are taken at the start of each month
# (121 values); flows are summed over the month and auxiliaries averaged.
STOCKS = ("L", "W1", "A", "WS", "Rep", "D", "Dn", "Dp", "FD", "Fat", "Dig", "Hops", "Xext",
          "Kr", "Cp", "Im", "Cash", "Debt")
FLOWS = ("E", "B", "C1", "FU", "T", "S_int", "S_own", "S_par", "S_ext", "WS_in", "surg_leak",
         "lost", "lost_ph", "lost_web", "lost_ref", "lost_balk", "recovered", "missed",
         "rev", "r_cons", "r_exam", "r_phys", "r_surg", "r_hosp", "r_other", "var", "fixed",
         "lever_cost", "hosp_opex", "clinic_opex", "ebitda", "capex", "capex_hosp", "capex_clinic",
         "capex_dig", "interest", "principal", "taxes", "draw", "inc", "haz", "sessions",
         "a_in", "a_out", "mkt_spent", "dig_spent", "hires",
         "spend_attract", "spend_access", "spend_digital", "spend_capacity")
AVERAGES = ("wait", "u_doc", "u_fd", "answered", "sat", "Deff", "ins_mix", "theta",
            "surg_wait", "hosp_util", "rep_mult")
FULL = STOCKS + FLOWS + AVERAGES
LEAN = ("Cash", "A", "Rep", "ebitda", "capex", "C1", "lost", "rev", "wait", "haz", "inc", "Fat",
        "u_doc", "E", "hosp_opex", "r_hosp", "spend_attract", "spend_access", "spend_digital",
        "spend_capacity")


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def sat(x: np.ndarray, k: float, umax: float) -> np.ndarray:
    """Smooth limit: about x when x is small, levelling off at umax."""
    x = np.clip(x, 0.0, 1e6)
    return x / (1.0 + (x / umax) ** k) ** (1.0 / k)


def sat_inv(u: np.ndarray, k: float, umax: float) -> np.ndarray:
    return u / (1.0 - (u / umax) ** k) ** (1.0 / k)


def smin(a: np.ndarray, b: np.ndarray, n: float) -> np.ndarray:
    """Smooth minimum of two non-negative arrays."""
    lo = np.minimum(a, b)
    hi = np.maximum(a, b)
    ratio = np.divide(lo, hi, out=np.zeros_like(lo), where=hi > 0)
    return lo * (1.0 + ratio**n) ** (-1.0 / n)


def tri_ppf(u: np.ndarray, low: float, mode: float, high: float) -> np.ndarray:
    """Inverse of the triangular cumulative distribution."""
    span = high - low
    cut = (mode - low) / span
    left = low + np.sqrt(u * span * (mode - low))
    right = high - np.sqrt((1.0 - u) * span * (high - mode))
    return np.where(u < cut, left, right)


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

def central_params(n: int = 1) -> dict[str, np.ndarray]:
    """Central values. Two extra keys exist only for extreme-condition tests:
    wom_scale (1 = word of mouth as calibrated) and doctor_scale (1 = today's doctors)."""
    return {a.key: np.full(n, float(a.value)) for a in A.ASSUMPTIONS}


def draw_params(n: int, seed: int = 2027) -> dict[str, np.ndarray]:
    """n simulated futures: each uncertain assumption drawn by Latin hypercube."""
    rng = np.random.default_rng(seed)
    p = central_params(n)
    for a in A.uncertain():
        u = (rng.permutation(n) + rng.random(n)) / n
        p[a.key] = tri_ppf(u, a.low, a.value, a.high)
    return p


def tile(params: dict[str, np.ndarray], reps: int) -> dict[str, np.ndarray]:
    return {k: np.tile(v, reps) for k, v in params.items()}


# ---------------------------------------------------------------------------
# Calibration: constants and initial state that put every future at rest
# ---------------------------------------------------------------------------

def _structure_cost_monthly() -> float:
    """Fixed structure cost (rent, support staff, admin) that gives the target margin.

    Computed once from central values, so it is the same in every future.
    """
    p = central_params(1)
    k, s0 = calibrate(p, structure=0.0)
    rev, var, fixed = _baseline_money(p, k, s0)
    ebitda_target = float(p["margin0"][0]) * rev
    return float(rev - var - fixed - ebitda_target)


def _baseline_money(p, k, s0):
    """Monthly revenue, variable cost and explicit fixed cost at t = 0 (central run)."""
    ins = p["ins_share0"]

    def mix(pi, pp):
        return ins * pi + (1 - ins) * pp

    T0 = k["T0"]
    C1 = k["C1_0"]
    FU0 = T0 - C1
    r_cons = T0 * mix(p["p_cons_ins"], p["p_cons_priv"])
    r_exam = (p["exams_new"] * C1 + p["exams_fu"] * FU0) * mix(p["p_exam_ins"], p["p_exam_priv"])
    sessions = s0["A"] * p["physio_share"] * p["physio_sessions"] / p["pathway"]
    r_phys = sessions * mix(p["p_physio_ins"], p["p_physio_priv"])
    r_surg = k["S0"] * mix(p["p_surg_ins"], p["p_surg_priv"])
    r_other = p["other_revenue0"] / 12
    rev = r_cons + r_exam + r_phys + r_surg + r_other
    var = (p["fee_cons"] * r_cons + p["fee_exam"] * r_exam + p["fee_physio"] * r_phys
           + p["fee_surg"] * r_surg + p["fee_other"] * r_other + p["consumables"] * rev)
    fixed = (p["front_desk0"] * p["fd_cost"] / 12 + p["doctors0"] * p["doctor_support"] / 12
             + p["marketing0"] / 12 + p["clubs0"] * p["club_cost"] / 12 + p["maint0"] / 12
             + k["h0"] * p["recruit_cost"] + p["incident_rate"] / 12 * p["incident_cost"])
    return float(rev[0]), float(var[0]), float(fixed[0])


@lru_cache(maxsize=1)
def structure_cost() -> float:
    return _structure_cost_monthly()


def calibrate(p: dict[str, np.ndarray], structure: float | None = None,
              incidents: str = "expected") -> tuple[dict, dict]:
    """Derived constants (k) and the initial state (s0) for every column."""
    k: dict[str, np.ndarray] = {}
    s0: dict[str, np.ndarray] = {}
    C1 = p["new_patients0"]
    wait0 = p["wait_days0"] / DAYS_PER_MONTH
    umax = p["u_max"]
    thr = p["fatigue_threshold"]

    # Surgery: referrals, the share who go elsewhere at today's wait, and the list.
    leak0 = 1.0 - np.exp(-((p["surg_wait0"] / p["surg_patience"]) ** 1.5))
    S0 = np.maximum(p["surg_conv"] * C1 * (1.0 - leak0), 1e-9)
    WS0 = S0 * p["surg_wait0"]
    A0 = p["pathway"] * (p["follow_share"] * C1 + S0)
    FU0 = p["fu_rate"] * A0
    T0 = C1 + FU0

    # Doctors' agenda: follow-ups are booked first; new patients take the free slots.
    u0 = p["doctor_util0"]
    Kc0 = T0 / u0
    k["fu_d"] = sat_inv(FU0 / Kc0, K_FU, U_FU) * Kc0 / A0
    Kfree0 = Kc0 - FU0
    x_new0 = sat_inv(C1 / Kfree0, K_DOC, 1.0)
    W1_0 = wait0 * C1
    k["tau_min"] = W1_0 / (x_new0 * Kfree0)

    # Front desk: the missed-call share today sets the desk's call capacity.
    a0 = 1.0 - p["miss0"]
    balk0 = 1.0 - np.exp(-((p["wait_days0"] / p["patience"]) ** 1.5))
    B_raw0 = C1 / (1.0 - balk0)
    ph, web = p["ch_phone"], p["ch_web"]
    ref = 1.0 - ph - web
    keep0 = (ph * (1.0 - (1.0 - a0) * (1.0 - p["retry"])) + web * (1.0 - p["web_loss0"])
             + ref * (1.0 - p["ref_loss0"]))
    E0 = B_raw0 / keep0
    load0 = E0 * ph * p["calls_per_booking"] + T0 * p["calls_per_visit"]
    x_fd0 = ((1.0 / a0) ** K_CALL - 1.0) ** (1.0 / K_CALL)
    cap_fd0 = load0 / x_fd0
    u_fd0 = a0 * x_fd0
    over_doc0 = np.clip((u0 - thr) / (umax - thr), 0.0, 1.0)
    over_fd0 = np.clip((u_fd0 - thr) / (1.0 - thr), 0.0, 1.0)
    Fat0 = FAT_DOC_WEIGHT * over_doc0 + (1.0 - FAT_DOC_WEIGHT) * over_fd0
    prod0 = 1.0 - FAT_PROD * Fat0
    k["calls_per_fte"] = cap_fd0 / (p["front_desk0"] * p["phone_time"] * prod0)
    k["a0"] = a0

    # Doctor stocks in equilibrium with replacement hiring.
    att0 = p["attrition"] / 12 * (1.0 + (p["fatigue_attrition"] - 1.0) * Fat0)
    Dtot0 = p["doctors0"]
    h0 = att0 * Dtot0
    Dp0 = h0 * p["recruit_delay"]
    Dn0 = h0 * p["ramp_delay"] / (1.0 + p["ramp_delay"] * att0)
    D0 = Dtot0 - Dn0
    Deff0 = smin(D0 + p["ramp_productivity"] * Dn0, p["rooms0"], N_ROOMS)
    k["cap_per_fte"] = Kc0 / (Deff0 * (1.0 - p["noshow0"]) * prod0)
    k["h0"] = h0

    # Surgical capacity: partner operating time and our surgeons' time.
    xs0 = sat_inv(p["surg_util0"], K_SURG, umax)
    Kint0 = S0 / p["surg_util0"]
    Ksurg0 = 1.35 * Kint0
    k["surg_per_fte"] = Ksurg0 / (Deff0 * prod0)
    k["P_slots"] = Kint0 * (1.0 - (Kint0 / Ksurg0) ** N_SURG) ** (-1.0 / N_SURG)
    k["tau_s_min"] = WS0 / (Kint0 * xs0)

    # Satisfaction and reputation.
    wait_f0 = 1.0 / (1.0 + (p["wait_days0"] / p["wait_sat"]) ** 2)
    s_0 = 0.95 * wait_f0 * (0.7 + 0.3 * a0) * (1.0 - FAT_QUALITY * Fat0)
    if incidents == "expected":
        Im0 = p["incident_rate"] / 12 * p["incident_hit"] * p["incident_memory"]
    else:
        Im0 = np.zeros_like(C1)
    Rep0 = np.clip(1.0 + 4.0 * s_0 - Im0, 0.0, 5.0)
    k["Rep0"] = Rep0

    # Notoriety: today's enquiries imply the notoriety stock and its inflows.
    L0 = E0 / p["need_rate"]
    tauL = p["noto_halflife"] / math.log(2.0)
    satL0 = 1.0 - L0 / p["catchment"]
    Stot0 = (L0 / tauL) / satL0
    W = p["w_mkt"] + p["w_club"] + p["w_wom"] + p["w_doc"] + p["w_base"]
    k["k_mkt"] = p["w_mkt"] / W * Stot0
    k["k_club"] = p["w_club"] / W * Stot0 / p["clubs0"]
    k["k_wom"] = p["w_wom"] / W * Stot0 / (C1 * s_0) * p.get("wom_scale", 1.0)
    k["k_doc"] = p["w_doc"] / W * Stot0 / Deff0
    k["k_base"] = p["w_base"] / W * Stot0
    k["k_clinic"] = p["clinic_demand"] * Stot0
    k["k_hosp"] = p["hosp_notoriety"] * Stot0
    k["tauL"] = tauL
    k["Meff0"] = p["marketing0"] / 12

    # Digital: today's maintenance just sustains today's maturity.
    dec = p["dig_decay"] / 12
    k["dec"] = dec
    k["K_maint"] = (p["maint0"] / 12) * (1.0 - p["digital0"]) / (dec * p["digital0"])
    k["K_inv"] = p["dig_cost"] / p["dig_effect"]

    k.update(C1_0=C1, T0=T0, A0=A0, S0=S0, Dtot0=Dtot0, E0=E0)
    k["F0"] = np.full_like(C1, structure if structure is not None else structure_cost())

    s0.update(
        L=L0, Meff=p["marketing0"] / 12, W1=W1_0, A=A0, WS=WS0, Rep=Rep0,
        Dp=Dp0 * p.get("doctor_scale", 1.0), Dn=Dn0 * p.get("doctor_scale", 1.0),
        D=D0 * p.get("doctor_scale", 1.0), Xh=np.zeros_like(C1), Hx=np.zeros_like(C1),
        FD=p["front_desk0"].copy(), Fat=Fat0, Pdig=np.zeros_like(C1), Dig=p["digital0"].copy(),
        Hp=np.zeros_like(C1), Hops=np.zeros_like(C1), Xext=np.zeros_like(C1),
        Kp=np.zeros_like(C1), Kr=np.zeros_like(C1), Cp=np.zeros_like(C1), Pp=np.ones_like(C1),
        Im=Im0, Cash=p["cash0"].copy(), Debt=np.zeros_like(C1),
    )
    return k, s0


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass
class Run:
    """Monthly results. Stocks have MONTHS + 1 rows; flows and averages MONTHS rows."""
    m: dict[str, np.ndarray]
    columns: int
    extra: dict = field(default_factory=dict)

    def annual_sum(self, key: str) -> np.ndarray:
        x = self.m[key]
        return x.reshape(YEARS, 12, -1).sum(axis=1)

    def annual_mean(self, key: str) -> np.ndarray:
        x = self.m[key]
        if x.shape[0] == MONTHS + 1:
            x = x[:-1]
        return x.reshape(YEARS, 12, -1).mean(axis=1)

    def year_start(self, key: str) -> np.ndarray:
        return self.m[key][0:MONTHS:12]

    def year_end(self, key: str) -> np.ndarray:
        return self.m[key][12::12]

    def patients_seen(self) -> np.ndarray:
        """Patients seen per year: new patients plus those already in follow-up in January."""
        return self.annual_sum("C1") + self.year_start("A")

    def cols(self, start: int, stop: int) -> "Run":
        """The columns of one plan in a batch run."""
        extra = {k: (v[start:stop] if isinstance(v, np.ndarray) and v.ndim == 1 else v)
                 for k, v in self.extra.items()}
        return Run({k: v[:, start:stop] for k, v in self.m.items()}, columns=stop - start, extra=extra)


# ---------------------------------------------------------------------------
# The simulation
# ---------------------------------------------------------------------------

def simulate(p: dict[str, np.ndarray], pol: dict[str, np.ndarray], world: dict[str, np.ndarray],
             *, incidents: str = "expected", uniforms: np.ndarray | None = None,
             dt: float = STEP, months: int = MONTHS, keep: tuple[str, ...] = FULL) -> Run:
    """Integrate the model. All inputs are dicts of arrays with one value per column.

    incidents="expected" spreads the expected cost and reputation damage of
    serious incidents smoothly (single scenario run). incidents="random" draws
    them with `uniforms`, an array of shape (steps, columns) in [0, 1).
    """
    k, s = calibrate(p, incidents=incidents)
    C = p["new_patients0"].shape[0]
    sub = int(round(1.0 / dt))
    steps = months * sub
    if incidents == "random" and (uniforms is None or uniforms.shape != (steps, C)):
        raise ValueError("random incidents need uniforms of shape (steps, columns)")

    keep_set = set(keep)
    rec_stock = {key: np.empty((months + 1, C)) for key in STOCKS if key in keep_set}
    rec_flow = {key: np.empty((months, C)) for key in FLOWS + AVERAGES if key in keep_set}
    acc = {key: np.zeros(C) for key in rec_flow}

    # Unpack state.
    L, Meff, W1, Aa, WS, Rep = s["L"], s["Meff"], s["W1"], s["A"], s["WS"], s["Rep"]
    Dp, Dn, D, Xh, Hx, FD, Fat = s["Dp"], s["Dn"], s["D"], s["Xh"], s["Hx"], s["FD"], s["Fat"]
    Pdig, Dig, Hp, Hops, Xext = s["Pdig"], s["Dig"], s["Hp"], s["Hops"], s["Xext"]
    Kp, Kr, Cp, Pp, Im, Cash, Debt = s["Kp"], s["Kr"], s["Cp"], s["Pp"], s["Im"], s["Cash"], s["Debt"]
    cum_haz = np.zeros(C)
    n_inc = np.zeros(C)

    # Frequently used parameters.
    umax, thr = p["u_max"], p["fatigue_threshold"]
    Dig0 = p["digital0"]
    ins0 = p["ins_share0"]
    ph, web = p["ch_phone"], p["ch_web"]
    ref = 1.0 - ph - web
    rp = p["ramp_productivity"]
    hosp_capex_total = (p["hosp_capex_base"] + pol["hosp_or"] * p["hosp_capex_or"]
                        + pol["hosp_beds"] * p["hosp_capex_bed"]) * p["hosp_overrun"]
    hosp_opex_total = (p["hosp_opex_base"] + pol["hosp_or"] * p["hosp_opex_or"]
                       + pol["hosp_beds"] * p["hosp_opex_bed"])
    H_nom = pol["hosp_on"] * np.minimum(pol["hosp_or"] * p["or_capacity"], pol["hosp_beds"] * p["bed_capacity"])
    H_nom_safe = np.maximum(H_nom, 1e-9)
    conv_ratio0 = ins0 / (1.0 - ins0)
    labour = world["labour"]
    tau_r = p["recruit_delay"] * labour
    floor = p["credit_floor"]
    mkt0, clubs0, maint0, fd0 = p["marketing0"], p["clubs0"], p["maint0"], p["front_desk0"]

    for i in range(steps):
        t = i * dt
        yr = t / 12.0

        # Lever groups switched on at this time, and the cash brake on optional spend.
        on_a = (t >= pol["a_from"]) & (t < pol["a_to"])
        on_s = (t >= pol["s_from"]) & (t < pol["s_to"])
        on_d = (t >= pol["d_from"]) & (t < pol["d_to"])
        on_h = (t >= pol["h_from"]) & (t < pol["h_to"])
        theta = 1.0 / (1.0 + np.exp(-np.clip((Cash - floor) / THETA_SCALE, -50.0, 50.0)))
        mkt_spend = mkt0 + theta * (np.where(on_a, pol["mkt"], mkt0) - mkt0)  # EUR/year
        clubs_now = clubs0 + theta * (np.where(on_a, pol["clubs"], clubs0) - clubs0)
        conv_now = np.where(on_a, pol["conv"], ins0)
        price_now = np.where(on_a, pol["price"], 1.0)
        cb_on = pol["callback"] * on_s
        ol_on = pol["online"] * on_s
        setup_now = on_s & (t < pol["s_from"] + 1.0)
        maint_now = maint0 + theta * (np.where(on_d, pol["dig_maint"], maint0) - maint0)
        once_rate = np.where(on_d & (t < pol["d_from"] + 12.0), pol["dig_once"] / 12.0, 0.0) * theta
        hire_now = np.where(on_h, pol["hire"], 0.0) * theta

        # New clinic and hospital projects.
        c_decided = (pol["clinic_on"] > 0) & (t >= pol["clinic_t"])
        c_works = c_decided & (Kp < 1.0)
        c_open = c_decided & (Kp >= 1.0)
        c_recruit = c_decided & (Kp >= 0.6)
        h_decided = (pol["hosp_on"] > 0) & (t >= pol["hosp_t"])
        h_build = h_decided & (Hp < 1.0)
        h_open = h_decided & (Hp >= 1.0)
        h_pre = h_build & (Hp >= 1.0 - 3.0 / p["hosp_build"])
        hosp_frac = Hops / H_nom_safe

        # Outside forces.
        dem = (1.0 + world["demand_growth"]) ** yr
        ipm = (1.0 + world["ins_price_trend"]) ** yr

        # Digital maturity helps everywhere: 0 today, 1 at full maturity.
        g = (Dig - Dig0) / (1.0 - Dig0)

        # Doctors' agenda.
        rooms = p["rooms0"] + p["clinic_rooms"] * c_open
        Deff = smin(D + rp * Dn, rooms, N_ROOMS)
        prod = 1.0 - FAT_PROD * Fat
        ns = p["noshow0"] * np.maximum(1.0 - 0.6 * g, 0.3) * (1.0 - 0.15 * ol_on)
        Kc = Deff * k["cap_per_fte"] * (1.0 - ns) * prod * (1.0 + 0.10 * g)
        FUd = k["fu_d"] * Aa
        FU = np.where(Kc > 1e-9, Kc * sat(FUd / np.maximum(Kc, 1e-9), K_FU, U_FU), 0.0)
        Kfree = np.maximum(Kc - FU, 0.0)
        C1d = W1 / k["tau_min"]
        C1 = np.where(Kfree > 1e-9, Kfree * sat(C1d / np.maximum(Kfree, 1e-9), K_DOC, 1.0), 0.0)
        T = C1 + FU
        u_doc = np.divide(T, Kc, out=np.zeros(C), where=Kc > 1e-9)

        # Surgery: our surgeons, partner operating time and the hospital, if open.
        Ksurg = Deff * k["surg_per_fte"] * prod
        Kint = smin(Ksurg, k["P_slots"] + Hops, N_SURG)
        Sd = WS / k["tau_s_min"]
        S_int = np.where(Kint > 1e-9, Kint * sat(Sd / np.maximum(Kint, 1e-9), K_SURG, umax), 0.0)
        S_own = np.minimum(S_int, Hops)
        S_par = S_int - S_own
        S_ext = np.minimum(Xext, np.maximum(Hops - S_own, 0.0))
        surg_wait = WS / np.maximum(S_int, 1e-6)
        refer = p["surg_conv"] * (1.0 + p["hosp_retention"] * hosp_frac) * C1
        leak = 1.0 - np.exp(-((surg_wait / p["surg_patience"]) ** 1.5))
        WS_in = refer * (1.0 - leak)

        # Demand: notoriety turns into enquiries, shaped by reputation, competition and price.
        rep_mult = np.exp(p["rep_effect"] * (Rep - k["Rep0"]))
        comp_mult = 1.0 / (1.0 + Cp + world["comp_extra"] * yr / 10.0)
        E_base = L * p["need_rate"] * dem * rep_mult * comp_mult
        m_ins = ((conv_now / (1.0 - conv_now)) / conv_ratio0) ** p["conv_response"]
        E_ins = E_base * ins0 * m_ins
        E_priv = E_base * (1.0 - ins0) * Pp ** (-p["price_sens"])
        E = E_ins + E_priv
        mix = np.divide(E_ins, E, out=np.full(C, 0.6), where=E > 0)

        # Channels and the front desk.
        shift = p["online_shift"] * ol_on
        E_ph = E * ph * (1.0 - shift)
        E_web = E * (web + ph * shift)
        E_ref = E * ref
        load = E_ph * p["calls_per_booking"] + T * p["calls_per_visit"] * (1.0 - 0.35 * g)
        cap_calls = FD * p["phone_time"] * k["calls_per_fte"] * prod
        xf = load / np.maximum(cap_calls, 1e-9)
        answered = 1.0 / (1.0 + np.clip(xf, 0.0, 1e4) ** K_CALL) ** (1.0 / K_CALL)
        u_fd = np.clip(answered * xf, 0.0, 1.0)
        missed = E_ph * (1.0 - answered)
        gone = missed * (1.0 - p["retry"])
        cb_rate = cb_on * np.minimum(p["callback_success"] * (1.0 + 0.35 * g), 0.95)
        recovered = gone * cb_rate
        lost_ph = gone - recovered
        busy = np.sqrt((1.0 - answered) / (1.0 - k["a0"]))
        web_loss = np.where(ol_on > 0, p["web_loss_online"] * (1.0 - 0.5 * g),
                            np.minimum(p["web_loss0"] * busy, 0.9))
        lost_web = E_web * web_loss
        lost_ref = E_ref * np.minimum(p["ref_loss0"] * busy, 0.9)
        B_raw = E - lost_ph - lost_web - lost_ref
        wait_days = W1 / np.maximum(C1, 1e-6) * DAYS_PER_MONTH
        balk = 1.0 - np.exp(-((wait_days / p["patience"]) ** 1.5))
        B = B_raw * (1.0 - balk)
        lost_balk = B_raw * balk
        lost = lost_ph + lost_web + lost_ref + lost_balk

        # Satisfaction and reputation.
        wait_f = 1.0 / (1.0 + (wait_days / p["wait_sat"]) ** 2)
        sat_share = 0.95 * wait_f * (0.7 + 0.3 * answered) * (1.0 - FAT_QUALITY * Fat)
        rep_star = np.clip(1.0 + 4.0 * sat_share - Im, 0.0, 5.0)
        tau_rep = np.where(rep_star > Rep, p["rep_up"], p["rep_down"])

        # Notoriety inflows: marketing, clubs, word of mouth, doctors, new sites.
        satL = np.maximum(1.0 - L / p["catchment"], 0.0)
        in_mkt = k["k_mkt"] * (Meff / k["Meff0"]) ** p["mkt_curve"]
        inflow = (k["k_base"] + in_mkt + k["k_club"] * clubs_now + k["k_wom"] * C1 * sat_share
                  + k["k_doc"] * Deff + k["k_clinic"] * Kr + k["k_hosp"] * hosp_frac) * satL

        # Competition answers our growth and our price cuts.
        cp_star = (p["comp_response"] * np.maximum(C1 / k["C1_0"] - 1.0, 0.0)
                   + 0.5 * np.maximum(1.0 - price_now, 0.0))

        # Fatigue builds when doctors or the front desk stay above the threshold.
        over_doc = np.clip((u_doc - thr) / (umax - thr), 0.0, 1.0)
        over_fd = np.clip((u_fd - thr) / (1.0 - thr), 0.0, 1.0)
        fat_star = FAT_DOC_WEIGHT * over_doc + (1.0 - FAT_DOC_WEIGHT) * over_fd
        tau_fat = np.where(fat_star > Fat, p["fatigue_up"], p["fatigue_down"])

        # Doctors: replacement of leavers plus planned expansion, with delays.
        rep_pull = np.exp(-p["rep_doctors"] * (Rep - k["Rep0"]))  # a good name attracts and keeps doctors
        att = (p["attrition"] / 12 * (1.0 + (p["fatigue_attrition"] - 1.0) * Fat)
               * (1.0 + 0.5 * (labour - 1.0)) * rep_pull)
        quit_D, quit_Dn = D * att, Dn * att
        clinic_docs = p["clinic_doctors"] * c_recruit
        planned = k["Dtot0"] + Xh + clinic_docs
        grow_Xh = hire_now / 12.0 * (planned < rooms)
        h_exp = np.maximum(Xh + clinic_docs - Hx, 0.0)
        hires = quit_D + quit_Dn + h_exp
        arrive = Dp / (tau_r * rep_pull)
        mature = Dn / p["ramp_delay"]

        # Front desk moves towards its target with a hiring delay.
        fd_target = fd0 + theta * (np.where(on_s, pol["fd"], fd0) - fd0) + p["clinic_fd"] * c_open

        # Serious incidents: more volume and weak digital foundations raise the hazard.
        vol = (Aa + C1) / (k["A0"] + k["C1_0"])
        haz = p["incident_rate"] / 12 * vol * np.maximum(1.0 - g, 0.0) ** 2
        if incidents == "expected":
            inc = haz
        else:
            inc = (uniforms[i] < haz * dt) / dt
        inc_cost = inc * p["incident_cost"]

        # Hospital and new clinic projects.
        capex_h = h_build * hosp_capex_total / p["hosp_build"]
        draw = capex_h * pol["hosp_debt"]
        hosp_opex = (h_open + 0.5 * h_pre) * hosp_opex_total / 12.0
        principal = h_open * Debt / p["amortisation"]
        capex_c = c_works * p["clinic_capex"] / p["clinic_delay"]
        clinic_opex = (c_open + 0.4 * c_works) * p["clinic_opex"] / 12.0
        ext_target = p["ext_share"] * H_nom * rep_mult

        # Money.
        def mixp(pi, pp):
            return mix * pi * ipm + (1.0 - mix) * pp * price_now

        r_cons = T * mixp(p["p_cons_ins"], p["p_cons_priv"])
        r_exam = (p["exams_new"] * C1 + p["exams_fu"] * FU) * mixp(p["p_exam_ins"], p["p_exam_priv"])
        sessions = Aa * p["physio_share"] * p["physio_sessions"] / p["pathway"]
        r_phys = sessions * mixp(p["p_physio_ins"], p["p_physio_priv"])
        team_fee = mixp(p["p_surg_ins"], p["p_surg_priv"])
        r_surg = S_par * team_fee
        r_own = S_own * mixp(p["p_hosp_ins"], p["p_hosp_priv"])
        r_ext = S_ext * p["p_ext"] * ipm
        r_other = p["other_revenue0"] / 12 * (0.4 + 0.6 * T / k["T0"]) * (0.6 * ipm + 0.4 * price_now)
        rev = r_cons + r_exam + r_phys + r_surg + r_own + r_ext + r_other
        var = (p["fee_cons"] * r_cons + p["fee_exam"] * r_exam + p["fee_physio"] * r_phys
               + p["fee_surg"] * r_surg + p["fee_surg"] * team_fee * S_own
               + p["hosp_var"] * (r_own + r_ext) + p["fee_other"] * r_other + p["consumables"] * rev)
        lever_cost = (mkt_spend / 12.0 + clubs_now * p["club_cost"] / 12.0 + FD * p["fd_cost"] / 12.0
                      + maint_now / 12.0 + cb_on * p["callback_cost"] / 12.0 + ol_on * p["online_cost"] / 12.0
                      + setup_now * (pol["callback"] * p["callback_setup"] + pol["online"] * p["online_setup"])
                      + (D + Dn) * p["doctor_support"] / 12.0 + hires * p["recruit_cost"])
        spend_attract = mkt_spend / 12.0 + clubs_now * p["club_cost"] / 12.0
        spend_access = (FD * p["fd_cost"] / 12.0 + cb_on * p["callback_cost"] / 12.0 + ol_on * p["online_cost"] / 12.0
                        + setup_now * (pol["callback"] * p["callback_setup"] + pol["online"] * p["online_setup"]))
        spend_capacity = ((D + Dn) * p["doctor_support"] / 12.0 + hires * p["recruit_cost"]
                          + clinic_opex + capex_c + hosp_opex + capex_h)
        fixed = k["F0"] + lever_cost + clinic_opex + hosp_opex
        ebitda = rev - var - fixed - inc_cost
        capex = once_rate + capex_c + capex_h
        interest = Debt * world["interest"] / 12.0
        taxes = p["tax_share"] * np.maximum(ebitda - interest, 0.0)

        # Record (stocks at the start of each month, flows summed, auxiliaries averaged).
        if i % sub == 0:
            mi = i // sub
            for key, arr in rec_stock.items():
                arr[mi] = locals_stock(key, L, W1, Aa, WS, Rep, D, Dn, Dp, FD, Fat, Dig, Hops, Xext, Kr, Cp, Im, Cash, Debt)
        frame = {
            "E": E, "B": B, "C1": C1, "FU": FU, "T": T, "S_int": S_int, "S_own": S_own, "S_par": S_par,
            "S_ext": S_ext, "WS_in": WS_in, "surg_leak": refer * leak, "lost": lost, "lost_ph": lost_ph,
            "lost_web": lost_web, "lost_ref": lost_ref, "lost_balk": lost_balk, "recovered": recovered,
            "missed": missed, "rev": rev, "r_cons": r_cons, "r_exam": r_exam, "r_phys": r_phys,
            "r_surg": r_surg, "r_hosp": r_own + r_ext, "r_other": r_other, "var": var, "fixed": fixed,
            "lever_cost": lever_cost, "hosp_opex": hosp_opex, "clinic_opex": clinic_opex, "ebitda": ebitda,
            "capex": capex, "capex_hosp": capex_h, "capex_clinic": capex_c, "capex_dig": once_rate,
            "interest": interest, "principal": principal, "taxes": taxes, "draw": draw, "inc": inc,
            "haz": haz, "sessions": sessions, "a_in": p["follow_share"] * C1 + S_int, "a_out": Aa / p["pathway"],
            "mkt_spent": mkt_spend / 12.0, "dig_spent": once_rate + maint_now / 12.0, "hires": hires,
            "spend_attract": spend_attract, "spend_access": spend_access,
            "spend_digital": once_rate + maint_now / 12.0, "spend_capacity": spend_capacity,
        }
        avg = {
            "wait": wait_days, "u_doc": u_doc, "u_fd": u_fd, "answered": answered, "sat": sat_share,
            "Deff": Deff, "ins_mix": mix, "theta": theta, "surg_wait": surg_wait,
            "hosp_util": np.divide(S_own + S_ext, Hops, out=np.zeros(C), where=Hops > 1e-6),
            "rep_mult": rep_mult,
        }
        for key, a in acc.items():
            if key in frame:
                a += frame[key] * dt
            else:
                a += avg[key] * dt
        if (i + 1) % sub == 0:
            mi = i // sub
            for key, a in acc.items():
                rec_flow[key][mi] = a  # averages too: the dt weights sum to one month
                acc[key] = np.zeros(C)

        # Integrate (Euler).
        cum_haz += haz * dt
        n_inc += inc * dt
        L = L + dt * (inflow - L / k["tauL"])
        Meff = Meff + dt * (mkt_spend / 12.0 - Meff) / p["mkt_delay"]
        W1 = W1 + dt * (B - C1)
        Aa = Aa + dt * (p["follow_share"] * C1 + S_int - Aa / p["pathway"])
        WS = WS + dt * (WS_in - S_int)
        Rep = Rep + dt * (rep_star - Rep) / tau_rep
        Dp = Dp + dt * (hires - arrive)
        Dn = Dn + dt * (arrive - mature - quit_Dn)
        D = D + dt * (mature - quit_D)
        Xh = Xh + dt * grow_Xh
        Hx = Hx + dt * h_exp
        FD = FD + dt * (fd_target - FD) / p["fd_delay"]
        Fat = Fat + dt * (fat_star - Fat) / tau_fat
        Dig = Dig + dt * ((Pdig / p["dig_delay"]) / k["K_inv"] * (1.0 - Dig)
                          + (maint_now / 12.0) / k["K_maint"] * (1.0 - Dig) - k["dec"] * Dig)
        Pdig = Pdig + dt * (once_rate - Pdig / p["dig_delay"])
        Hp = Hp + dt * h_build / p["hosp_build"]
        Hops = Hops + dt * (h_open * H_nom - Hops) / (p["hosp_ramp"] / 3.0)
        Xext = Xext + dt * h_open * (ext_target - Xext) / (p["ext_delay"] / 2.0)
        Kp = Kp + dt * c_works / p["clinic_delay"]
        Kr = Kr + dt * c_open * (1.0 - Kr) / (p["clinic_ramp"] / 3.0)
        Cp = Cp + dt * (cp_star - Cp) / p["comp_delay"]
        Pp = Pp + dt * (price_now - Pp) / p["price_delay"]
        Im = Im + dt * (inc * p["incident_hit"] - Im / p["incident_memory"])
        Debt = Debt + dt * (draw - principal)
        Cash = Cash + dt * (ebitda - capex - interest - principal - taxes + draw)

    for key, arr in rec_stock.items():
        arr[months] = locals_stock(key, L, W1, Aa, WS, Rep, D, Dn, Dp, FD, Fat, Dig, Hops, Xext, Kr, Cp, Im, Cash, Debt)

    out = dict(rec_stock)
    out.update(rec_flow)
    extra = {"cum_haz": cum_haz, "n_inc": n_inc, "p_any_incident": 1.0 - np.exp(-cum_haz),
             "Rep0": k["Rep0"], "H_nom": H_nom, "hosp_capex_total": hosp_capex_total * pol["hosp_on"]}
    return Run(out, columns=C, extra=extra)


_STOCK_ORDER = ("L", "W1", "A", "WS", "Rep", "D", "Dn", "Dp", "FD", "Fat", "Dig", "Hops", "Xext",
                "Kr", "Cp", "Im", "Cash", "Debt")


def locals_stock(key, *values):
    return values[_STOCK_ORDER.index(key)]


def uniforms_for(n_futures: int, n_plans: int, seed: int, dt: float = STEP, months: int = MONTHS) -> np.ndarray:
    """Random numbers for incidents, shared by every plan so comparisons are paired."""
    steps = months * int(round(1.0 / dt))
    rng = np.random.default_rng(seed + 7919)
    u = rng.random((steps, n_futures))
    return np.tile(u, (1, n_plans))
