"""Correctness of the simulation core (Sterman, Business Dynamics, ch. 3 tests)."""

from __future__ import annotations

import time

import numpy as np
import pytest

from core import analysis as AN
from core import assumptions as A
from core import model as M
from core import scenarios as S
from core import structure as ST

BASE = S.BASELINE
BUSY = S.PRESETS["Hospital depois de arrumar a casa"]


def _run(plans, params, n, world=None, incidents="expected", dt=M.STEP, seed=11):
    world = world or A.default_world()
    pol = S.policy_arrays(plans, n)
    w = S.world_arrays(world, n * len(plans))
    U = M.uniforms_for(n, len(plans), seed, dt=dt) if incidents == "random" else None
    return M.simulate(M.tile(params, len(plans)), pol, w, incidents=incidents, uniforms=U, dt=dt)


# ---------------------------------------------------------------- units and documentation

def test_every_assumption_is_documented():
    for a in A.ASSUMPTIONS:
        assert a.unit and a.label and a.why, a.key
        if a.uncertain:
            assert a.low <= a.value <= a.high, a.key
            assert a.measure, f"{a.key} needs a 'what to measure' sentence"
    for f in A.FORCES:
        assert f.unit and f.label and f.why and f.low <= f.value <= f.high


# ---------------------------------------------------------------- bounds

@pytest.mark.parametrize("plan", [BASE, BUSY, S.PRESETS["Crescer com marketing"], S.PRESETS["Hospital já"],
                                  BASE.with_changes(marketing=400_000.0, conv=0.8, price=0.85)])
def test_stocks_stay_within_physical_bounds(plan):
    r = _run([plan], M.draw_params(120, 3), 120, incidents="random")
    for key in ("L", "W1", "A", "WS", "D", "Dn", "Dp", "FD", "Hops", "Xext", "Debt", "Kr"):
        assert r.m[key].min() >= -1e-9, key
    assert 0.0 <= r.m["Rep"].min() and r.m["Rep"].max() <= 5.0
    assert 0.0 <= r.m["Dig"].min() and r.m["Dig"].max() <= 1.0
    assert 0.0 <= r.m["Fat"].min() and r.m["Fat"].max() <= 1.0
    assert np.isfinite(r.m["Cash"]).all()


# ---------------------------------------------------------------- conservation

def test_patient_stocks_conserve_people():
    r = _run([BUSY], M.draw_params(50, 5), 50, incidents="random")
    for stock, inflow, outflow in (("W1", "B", "C1"), ("A", "a_in", "a_out"), ("WS", "WS_in", "S_int")):
        change = np.diff(r.m[stock], axis=0)
        np.testing.assert_allclose(change, r.m[inflow] - r.m[outflow], rtol=1e-9, atol=1e-7, err_msg=stock)


def test_every_enquiry_is_either_booked_or_lost():
    r = _run([BUSY], M.draw_params(50, 6), 50, incidents="random")
    np.testing.assert_allclose(r.m["E"], r.m["B"] + r.m["lost"], rtol=1e-10)
    np.testing.assert_allclose(r.m["lost"], r.m["lost_ph"] + r.m["lost_web"] + r.m["lost_ref"] + r.m["lost_balk"],
                               rtol=1e-10)


# ---------------------------------------------------------------- calibration

def test_baseline_calibration_targets():
    r = AN.run_plans([BASE])[0]
    rev = r.annual_sum("rev")[:, 0]
    eb = r.annual_sum("ebitda")[:, 0]
    assert abs(rev[0] - 5.0e6) <= 0.05 * 5.0e6
    assert 0.08 <= eb[0] / rev[0] <= 0.15
    seen = r.patients_seen()[0, 0]
    assert 9_000 <= seen <= 11_000
    mix = {k: r.annual_sum(k)[0, 0] / rev[0] for k in ("r_cons", "r_exam", "r_phys", "r_surg", "r_other")}
    assert abs(sum(mix.values()) - 1.0) < 1e-9
    assert all(0.05 <= v <= 0.35 for v in mix.values()), mix
    # Roughly stable: no explosive growth or collapse without a decision.
    assert np.max(np.abs(rev / rev[0] - 1.0)) < 0.10
    wait = r.annual_mean("wait")[:, 0]
    assert np.max(np.abs(wait / wait[0] - 1.0)) < 0.25
    assert abs(wait[0] - A.value("wait_days0")) < 0.5


def test_every_future_starts_at_rest():
    p = M.draw_params(200, 8)
    world = {**A.default_world(), "demand_growth": 0.0, "ins_price_trend": 0.0}
    r = _run([BASE], p, 200, world=world)
    for key in ("L", "W1", "A", "WS", "Rep", "D", "FD", "Dig"):
        drift = np.abs(r.m[key][12] / r.m[key][0] - 1.0)
        assert drift.max() < 1e-6, key
    np.testing.assert_allclose(r.m["C1"][0], A.value("new_patients0"), rtol=1e-6)


# ---------------------------------------------------------------- zero change

def test_plan_without_changes_reproduces_baseline_exactly():
    same = S.Plan()
    runs = AN.run_plans([BASE, same], n_futures=100)
    for key in ("Cash", "rev", "ebitda", "C1", "wait", "Rep"):
        assert np.array_equal(runs[0].m[key], runs[1].m[key]), key


# ---------------------------------------------------------------- extreme conditions

def test_zero_marketing_and_referrals_fall_to_a_floor():
    p = M.central_params(1)
    p["wom_scale"] = np.zeros(1)
    plan = BASE.with_changes(marketing=0.0, clubs=0)
    r = _run([plan], p, 1)
    E = r.m["E"][:, 0]
    assert E.min() >= 0.0 and r.m["L"].min() >= 0.0
    assert E[-1] < 0.8 * E[0]
    # It levels off rather than falling forever: the last year moves far less than the first.
    first_drop = E[0] - E[11]
    last_drop = E[-12] - E[-1]
    assert last_drop < 0.25 * first_drop
    assert E[-1] > 0.0


def test_huge_marketing_with_fixed_capacity_saturates():
    p = M.central_params(1)
    p["credit_floor"] = np.full(1, -1e15)  # keep the cash brake from cutting the marketing
    runs = _run([BASE, BASE.with_changes(marketing=5_000_000.0)], M.tile(p, 1), 1)
    base, big = runs.cols(0, 1), runs.cols(1, 2)
    assert big.annual_mean("wait")[-1, 0] > 1.5 * base.annual_mean("wait")[-1, 0]
    assert big.annual_sum("lost")[-1, 0] > 3.0 * base.annual_sum("lost")[-1, 0]
    rev_gain = big.annual_sum("rev")[-1, 0] / base.annual_sum("rev")[-1, 0]
    assert rev_gain < 1.25  # 80 times the marketing budget, a fraction more revenue


def test_zero_doctors_means_zero_consultations():
    p = M.central_params(1)
    p["doctor_scale"] = np.zeros(1)
    r = _run([BASE], p, 1)
    assert np.allclose(r.m["C1"][1:], 0.0, atol=1e-9)
    assert np.allclose(r.m["FU"][1:], 0.0, atol=1e-9)
    assert np.allclose(r.m["T"][1:], 0.0, atol=1e-9)


def test_hospital_without_surgical_flow_loses_money_every_year():
    p = M.central_params(1)
    p["surg_conv"] = np.zeros(1)
    p["ext_share"] = np.zeros(1)
    plan = BASE.with_changes(hospital_year=2027)
    r = _run([BASE, plan], M.tile(p, 1), 1)
    base, hosp = r.cols(0, 1), r.cols(1, 2)
    gap = hosp.annual_sum("ebitda")[:, 0] - base.annual_sum("ebitda")[:, 0]
    opened = hosp.annual_sum("hosp_opex")[:, 0] > 0
    assert opened.sum() >= 5
    assert (gap[opened] < 0).all()
    cash_gap = hosp.m["Cash"][12:, 0] - base.m["Cash"][12:, 0]
    assert (cash_gap < 0).all()


def test_unlimited_front_desk_loses_no_calls():
    p = M.central_params(1)
    p["credit_floor"] = np.full(1, -1e15)
    r = _run([BASE.with_changes(front_desk=1e6)], p, 1)
    lost_access = r.m["lost_ph"] + r.m["lost_web"] + r.m["lost_ref"]
    assert lost_access[24:].max() < 1e-3 * r.m["E"][24:].min()


# ---------------------------------------------------------------- structural property

def test_marginal_return_of_marketing_falls_as_the_agenda_fills():
    gains = []
    for util in (0.60, 0.72, 0.84, 0.92):
        p = M.central_params(1)
        p["doctor_util0"] = np.full(1, util)
        r = _run([BASE, BASE.with_changes(marketing=110_000.0)], M.tile(p, 1), 1)
        extra_patients = r.cols(1, 2).annual_sum("C1").sum() - r.cols(0, 1).annual_sum("C1").sum()
        gains.append(extra_patients / 500.0)  # per thousand euros over ten years
    assert all(a > b for a, b in zip(gains, gains[1:])), gains
    assert gains[0] > 0


# ---------------------------------------------------------------- numerics

def test_halving_the_time_step_changes_key_outputs_by_under_one_percent():
    outs = []
    for dt in (M.STEP, M.STEP / 2):
        r = AN.run_plans([BUSY], dt=dt)[0]
        o = AN.outcomes(r)
        outs.append({k: float(o[k][0]) for k in ("rev_2036", "ebitda_cum10", "seen_2036", "wait_2036", "cash_end",
                                                  "lost_2036", "rep_2036")})
    for key in outs[0]:
        a, b = outs[0][key], outs[1][key]
        assert abs(a - b) <= 0.01 * abs(b), (key, a, b)


def test_same_seed_same_results_and_different_seed_different_results():
    a = AN.run_plans([BUSY], n_futures=60, seed=5)[0]
    b = AN.run_plans([BUSY], n_futures=60, seed=5)[0]
    c = AN.run_plans([BUSY], n_futures=60, seed=6)[0]
    assert np.array_equal(a.m["Cash"], b.m["Cash"])
    assert not np.array_equal(a.m["Cash"], c.m["Cash"])


def test_speed():
    AN.run_plans([BASE])  # warm up
    t = time.perf_counter()
    AN.run_plans([BUSY])
    single = time.perf_counter() - t
    t = time.perf_counter()
    AN.run_plans([BUSY], n_futures=AN.N_FUTURES)
    many = time.perf_counter() - t
    assert single < 0.3, single
    assert many < 3.0, many


# ---------------------------------------------------------------- map structure

def test_map_links_and_loops_are_consistent():
    ids = {n.id for n in ST.NODES}
    for lk in ST.LINKS:
        assert lk.source in ids and lk.target in ids, lk
        assert lk.sign in (-1, 0, 1)
        assert 0 <= lk.strength <= 1 and 0 <= lk.certainty <= 1
    for loop in ST.LOOPS:
        for s, t in ST.loop_links(loop):
            assert ST.link_between(s, t) is not None, (loop.id, s, t)
        expected = 1 if loop.kind == "reforça" else -1
        assert ST.loop_sign(loop) == expected, loop.id
