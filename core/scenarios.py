"""Plans (what the clinic decides), the baseline and the preset scenarios.

A Plan holds the lever settings. The baseline plan, "Continuar como está",
reproduces today's values from core/assumptions.py. Presets and the
sequencing analysis can also move the year each group of levers starts and
stops, which the Pilotar page does not expose.

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace

import numpy as np

from core import assumptions as A

START_YEAR = 2027
END_YEAR = 2036
NEVER = 0  # clinic_year / hospital_year value meaning "not in the plan"
OPEN_END = END_YEAR + 1  # a group that runs until the end of the horizon


@dataclass(frozen=True)
class Plan:
    # Atrair doentes
    marketing: float = A.value("marketing0")  # EUR per year
    clubs: int = int(A.value("clubs0"))
    conv: float = A.value("ins_share0")  # share of demand through insurers and subsystems
    price: float = 1.0  # index of private prices, 1 = today
    # Atender quem chega
    callback: bool = False
    online: bool = False
    front_desk: float = A.value("front_desk0")  # FTE
    # Base digital
    digital_once: float = 0.0  # EUR, spent over the first year
    digital_maint: float = A.value("maint0")  # EUR per year
    # Capacidade e grandes apostas
    hire_rate: float = 0.0  # extra doctors per year, until the rooms are full
    clinic_year: int = NEVER
    hospital_year: int = NEVER
    hospital_rooms: int = 2  # operating rooms
    hospital_beds: int = 12
    hospital_debt: float = 0.60  # share of the hospital investment paid with debt
    # Timing of each group (years, end exclusive). Presets and sequencing only.
    attract_from: int = START_YEAR
    attract_to: int = OPEN_END
    access_from: int = START_YEAR
    access_to: int = OPEN_END
    digital_from: int = START_YEAR
    digital_to: int = OPEN_END
    hire_from: int = START_YEAR
    hire_to: int = OPEN_END

    def as_key(self) -> tuple:
        """A hashable, cache-friendly description of the plan."""
        return tuple((f.name, getattr(self, f.name)) for f in fields(self))

    def with_changes(self, **changes) -> "Plan":
        return replace(self, **changes)


BASELINE = Plan()


def plan_from_key(key: tuple) -> Plan:
    return Plan(**dict(key))


def changed_levers(plan: Plan, base: Plan = BASELINE) -> list[str]:
    """Names of the lever fields that differ from the base plan."""
    out = []
    for f in fields(plan):
        if getattr(plan, f.name) != getattr(base, f.name):
            out.append(f.name)
    return out


def _month(year: int) -> float:
    return float((year - START_YEAR) * 12)


def policy_arrays(plans: list[Plan], n_futures: int) -> dict[str, np.ndarray]:
    """Lever settings as arrays, one entry per column (plan-major, then future)."""
    rows = []
    for plan in plans:
        rows.append({
            "mkt": plan.marketing,
            "clubs": float(plan.clubs),
            "conv": plan.conv,
            "price": plan.price,
            "callback": 1.0 if plan.callback else 0.0,
            "online": 1.0 if plan.online else 0.0,
            "fd": plan.front_desk,
            "dig_once": plan.digital_once,
            "dig_maint": plan.digital_maint,
            "hire": plan.hire_rate,
            "a_from": _month(plan.attract_from), "a_to": _month(plan.attract_to),
            "s_from": _month(plan.access_from), "s_to": _month(plan.access_to),
            "d_from": _month(plan.digital_from), "d_to": _month(plan.digital_to),
            "h_from": _month(plan.hire_from), "h_to": _month(plan.hire_to),
            "clinic_on": 1.0 if plan.clinic_year else 0.0,
            "clinic_t": _month(plan.clinic_year) if plan.clinic_year else 1e9,
            "hosp_on": 1.0 if plan.hospital_year else 0.0,
            "hosp_t": _month(plan.hospital_year) if plan.hospital_year else 1e9,
            "hosp_or": float(plan.hospital_rooms),
            "hosp_beds": float(plan.hospital_beds),
            "hosp_debt": plan.hospital_debt,
        })
    out = {}
    for key in rows[0]:
        out[key] = np.repeat(np.array([r[key] for r in rows], dtype=float), n_futures)
    return out


def world_arrays(world: dict[str, float], n_columns: int) -> dict[str, np.ndarray]:
    return {k: np.full(n_columns, float(v)) for k, v in world.items()}


# ---------------------------------------------------------------------------
# Costs shown next to each lever and in the budget bar. These are planning
# figures at central values; the simulation computes the real spend.
# ---------------------------------------------------------------------------

def hospital_capex(rooms: int, beds: int) -> float:
    return (A.value("hosp_capex_base") + rooms * A.value("hosp_capex_or")
            + beds * A.value("hosp_capex_bed")) * A.value("hosp_overrun")


def hospital_opex(rooms: int, beds: int) -> float:
    return A.value("hosp_opex_base") + rooms * A.value("hosp_opex_or") + beds * A.value("hosp_opex_bed")


def lever_costs(plan: Plan, base: Plan = BASELINE) -> dict[str, dict[str, float]]:
    """Planned extra spend versus the base plan, by lever group.

    Returns {group: {"per_year": EUR/year, "once": EUR}}.
    """
    fd_cost = A.value("fd_cost")
    attract = (plan.marketing - base.marketing) + (plan.clubs - base.clubs) * A.value("club_cost")
    access = ((plan.callback - base.callback) * A.value("callback_cost")
              + (plan.online - base.online) * A.value("online_cost")
              + (plan.front_desk - base.front_desk) * fd_cost)
    access_once = ((plan.callback and not base.callback) * A.value("callback_setup")
                   + (plan.online and not base.online) * A.value("online_setup"))
    digital = plan.digital_maint - base.digital_maint
    digital_once = plan.digital_once - base.digital_once
    room_left = max(A.value("rooms0") - A.value("doctors0"), 0.0)
    extra_doctors = min(plan.hire_rate * 3.0, room_left)  # what the rooms allow over a few years
    capacity = extra_doctors * A.value("doctor_support") + plan.hire_rate * A.value("recruit_cost") * (extra_doctors > 0)
    capacity_once = 0.0
    if plan.clinic_year:
        capacity += A.value("clinic_opex") + A.value("clinic_fd") * fd_cost + A.value("clinic_doctors") * A.value("doctor_support")
        capacity_once += A.value("clinic_capex")
    if plan.hospital_year:
        capacity += hospital_opex(plan.hospital_rooms, plan.hospital_beds)
        capacity_once += hospital_capex(plan.hospital_rooms, plan.hospital_beds)
    return {
        "atrair": {"per_year": attract, "once": 0.0},
        "atender": {"per_year": access, "once": float(access_once)},
        "digital": {"per_year": digital, "once": digital_once},
        "capacidade": {"per_year": capacity, "once": capacity_once},
    }


# ---------------------------------------------------------------------------
# Preset scenarios for "Comparar cenários".
# ---------------------------------------------------------------------------

_HOUSE = dict(callback=True, online=True, front_desk=A.value("front_desk0") + 2,
              digital_once=250_000.0, digital_maint=100_000.0, hire_rate=0.5)

PRESETS: dict[str, Plan] = {
    "Continuar como está": BASELINE,
    "Crescer com marketing": BASELINE.with_changes(marketing=260_000.0, clubs=12),
    "Arrumar a casa primeiro": BASELINE.with_changes(**_HOUSE, marketing=160_000.0, attract_from=2029),
    "Hospital já": BASELINE.with_changes(marketing=160_000.0, hospital_year=2027),
    "Hospital depois de arrumar a casa": BASELINE.with_changes(
        **_HOUSE, marketing=160_000.0, attract_from=2029, hospital_year=2029),
}

PRESET_NOTES: dict[str, str] = {
    "Continuar como está": "Tudo como hoje.",
    "Crescer com marketing": "Mais 200 mil € por ano em marketing e o dobro das parcerias com clubes.",
    "Arrumar a casa primeiro": "Chamadas perdidas, marcação online, mais receção, base digital e médicos; mais marketing só a partir de 2029.",
    "Hospital já": "Hospital decidido em 2027 e mais 100 mil € por ano em marketing.",
    "Hospital depois de arrumar a casa": "Primeiro arrumar a casa; hospital decidido em 2029.",
}


def sequencing_pair() -> tuple[Plan, Plan]:
    """The same investments in two orders, each recurring group running seven years.

    "Casa primeiro": front desk, calls and digital from 2027 to 2033; marketing
    from 2029 to 2035; hospital decided in 2029.
    "Crescer primeiro": marketing from 2027 to 2033 and the hospital in 2027;
    front desk, calls and digital from 2029 to 2035.
    """
    common = dict(callback=True, online=True, front_desk=A.value("front_desk0") + 2,
                  digital_once=250_000.0, digital_maint=100_000.0, marketing=160_000.0)
    house_first = BASELINE.with_changes(
        **common, access_from=2027, access_to=2034, digital_from=2027, digital_to=2034,
        attract_from=2029, attract_to=2036, hospital_year=2029)
    grow_first = BASELINE.with_changes(
        **common, attract_from=2027, attract_to=2034, hospital_year=2027,
        access_from=2029, access_to=2036, digital_from=2029, digital_to=2036)
    return house_first, grow_first


def plan_summary(plan: Plan) -> dict:
    return asdict(plan)
