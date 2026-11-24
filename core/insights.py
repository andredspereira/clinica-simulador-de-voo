"""Rule-based insight cards in pt-PT. No language model: every sentence is a
template filled with numbers from the simulations, and a rule only fires when
the numbers support it.

Each card carries one big number, a short line saying what the number is, and
one "porquê" sentence that names the loop or the delay responsible. The rule
carried over from earlier work: only claim a direction when at least 8 in 10
simulated futures agree; otherwise say plainly "ainda não sabemos" and name
what would settle it.

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from core import analysis as AN
from core import formatting as F
from core import model as M
from core import scenarios as S
from core import structure as ST


@dataclass(frozen=True)
class Card:
    number: str
    title: str
    why: str
    score: float
    loop: str | None = None
    tone: str = "info"  # info, good, warn


def _loop(loop_id: str) -> str:
    return f"ciclo '{ST.LOOP_BY_ID[loop_id].name}'"


def _med(x: np.ndarray) -> float:
    return float(np.median(x))


# ---------------------------------------------------------------------------
# A bundle of everything the plan cards need, computed once per plan.
# ---------------------------------------------------------------------------

@dataclass
class PlanBundle:
    plan: S.Plan
    base: M.Run
    run: M.Run
    base_out: dict
    out: dict
    no_hosp: M.Run | None = None
    hosp_driver: str = ""
    plan_driver: str = ""


def bundle(plan: S.Plan, world: dict | None = None, n_futures: int = AN.N_FUTURES, seed: int = AN.SEED) -> PlanBundle:
    plans = [S.BASELINE, plan]
    with_hosp = bool(plan.hospital_year)
    if with_hosp:
        plans.append(plan.with_changes(hospital_year=S.NEVER))
    runs = AN.run_plans(plans, world, n_futures, seed)
    b = PlanBundle(plan=plan, base=runs[0], run=runs[1], base_out=AN.outcomes(runs[0]), out=AN.outcomes(runs[1]))
    params = runs[0].extra["params"]
    if S.changed_levers(plan):
        b.plan_driver = _top_driver(params, b.out["net_cum10"] - b.base_out["net_cum10"])
    if with_hosp:
        b.no_hosp = runs[2]
        b.hosp_driver = _top_driver(params, b.out["net_cum10"] - AN.outcomes(runs[2])["net_cum10"])
    return b


def _top_driver(params: dict, y: np.ndarray) -> str:
    from core import assumptions as A
    best, best_rho = "", 0.0
    for a in A.uncertain():
        rho = abs(AN.spearman(params[a.key], y))
        if rho > best_rho:
            best, best_rho = a.short or a.label.lower(), rho
    return best


# ---------------------------------------------------------------------------
# Plan cards (Pilotar)
# ---------------------------------------------------------------------------

def plan_cards(b: PlanBundle, limit: int = 3) -> list[Card]:
    if not S.changed_levers(b.plan):
        return baseline_cards(b)[:limit]
    cards: list[Card] = []
    for rule in (_rule_overall, _rule_capacity, _rule_valley, _rule_hospital, _rule_callback,
                 _rule_fatigue, _rule_cash_brake, _rule_risk, _rule_delay, _rule_competition,
                 _rule_convention, _rule_price):
        card = rule(b)
        if card is not None:
            cards.append(card)
    cards.sort(key=lambda c: -c.score)
    out, seen_loops = [], set()
    for c in cards:
        if c.loop and c.loop in seen_loops:
            continue
        out.append(c)
        if c.loop:
            seen_loops.add(c.loop)
        if len(out) == limit:
            break
    return out


def baseline_cards(b: PlanBundle) -> list[Card]:
    o = b.base_out
    lost = _med(o["lost_y"][0])
    value = _med(o["lost_value_2036"]) if "lost_value_2036" in o else 0.0
    util_end = _med(o["util_y"][-1])
    wait0, wait_end = _med(o["wait_y"][0]), _med(o["wait_y"][-1])
    p_inc = float(np.mean(o["p_incident"]))
    cards = [
        Card(F.people(lost), "pessoas por ano procuram a clínica e não chegam a uma consulta",
             f"Ninguém atende a tempo, o pedido do site fica sem resposta ou a espera parece longa. Valem cerca de "
             f"{F.eur(value)} de faturação por ano.", 1.0, None, "warn"),
        Card(F.pct(util_end), "da agenda médica ocupada em 2036, sem mudar nada",
             f"A procura da região cresce e a agenda enche devagar: a espera passa de {F.days(wait0)} para "
             f"{F.days(wait_end)}. Continuar como está não é ficar igual ({_loop('B1')}).", 0.8, "B1"),
        Card(f"{F.tenths(p_inc)} em 10", "futuros simulados com pelo menos um incidente grave de dados até 2036",
             f"Mais doentes e mais dados sem base digital forte sobem o risco ({_loop('B4')}).", 0.6, "B4"),
    ]
    return cards


def _rule_overall(b: PlanBundle) -> Card | None:
    d = b.out["net_cum10"] - b.base_out["net_cum10"]
    up, down = AN.agreement(d, tol=1_000)
    med = _med(d)
    if up >= AN.AGREE:
        return Card(F.eur(med, signed=True), "de ganho acumulado até 2036, face a continuar como está",
                    f"O plano compensa {F.in_futures(up)}, já descontado o que custa.", 0.55, None, "good")
    if down >= AN.AGREE:
        return Card(F.eur(med, signed=True), "de resultado acumulado até 2036, face a continuar como está",
                    f"O plano perde dinheiro {F.in_futures(down)}: custa mais do que traz até 2036.", 0.9, None, "warn")
    driver = b.plan_driver or "a procura que o plano consegue atender"
    return Card(f"{F.tenths(up)} em 10", "futuros simulados em que este plano compensa até 2036",
                f"Ainda não sabemos se compensa: nos restantes perde dinheiro. O que mais decide é {driver}.",
                0.95, None, "info")


def _rule_capacity(b: PlanBundle) -> Card | None:
    dE = b.run.annual_sum("E").sum(0) - b.base.annual_sum("E").sum(0)
    if _med(dE) < 0.02 * _med(b.base.annual_sum("E").sum(0)):
        return None
    d_balk = b.run.annual_sum("lost_balk").sum(0) - b.base.annual_sum("lost_balk").sum(0)
    d_access = (b.run.annual_sum("lost_ph") + b.run.annual_sum("lost_web") + b.run.annual_sum("lost_ref")).sum(0) - \
               (b.base.annual_sum("lost_ph") + b.base.annual_sum("lost_web") + b.base.annual_sum("lost_ref")).sum(0)
    share = np.clip((d_balk + d_access) / np.maximum(dE, 1.0), 0.0, 1.0)
    k = F.tenths(_med(share))
    if k < 2:
        return None
    if _med(d_balk) >= _med(d_access):
        cause = "porque a lista de espera já está cheia"
    else:
        cause = "porque ninguém atende a tempo"
    return Card(f"{k} em cada 10", "doentes a mais que o plano atrai acabam perdidos",
                f"Do aumento de procura que o plano cria, {k} em cada 10 perdem-se {cause} ({_loop('B1')}).",
                0.5 + 0.06 * k, "B1", "warn")


def _rule_valley(b: PlanBundle) -> Card | None:
    cash_min = _med(b.out["cash_min"])
    base_min = _med(b.base_out["cash_min"])
    if cash_min > base_min - 200_000:
        return None
    month = _med(b.out["cash_min_month"])
    end = _med(b.out["cash_end"])
    recovers = end > cash_min + 300_000
    what = "do hospital" if b.plan.hospital_year else "deste plano"
    if recovers:
        why = (f"A caixa desce até {F.eur(cash_min)} em {F.year_of(month)} antes de recuperar: é o 'pior antes de "
               f"melhor' {what}. Os gastos chegam anos antes das receitas (atraso).")
    else:
        why = (f"A caixa desce até {F.eur(cash_min)} em {F.year_of(month)} e não recupera até 2036. Os gastos "
               f"chegam antes das receitas, e as receitas não chegam para os pagar (atraso).")
    score = 0.7 + min(abs(cash_min - base_min) / 3e6, 0.6)
    return Card(F.eur(cash_min), f"é o ponto mais baixo da caixa, em {F.year_of(month)}", why, score, None, "warn")


def _rule_hospital(b: PlanBundle) -> Card | None:
    if b.no_hosp is None:
        return None
    gain = b.out["net_cum10"] - AN.outcomes(b.no_hosp)["net_cum10"]
    share = float(np.mean(gain >= 0))
    driver = b.hosp_driver or "a procura cirúrgica externa"
    k = F.tenths(share)
    if share >= AN.AGREE:
        cum = np.cumsum(b.out["net_y"] - AN.outcomes(b.no_hosp)["net_y"], axis=0)
        years = AN.first_payback_year(cum)
        year = int(np.nanmedian(years)) if np.isfinite(years).any() else 2036
        return Card(f"{k} em 10", "futuros em que o hospital se paga até 2036",
                    f"O hospital paga-se por volta de {year} {F.in_futures(share)}; o que mais pesa é {driver}.",
                    0.85, "R4", "good")
    if share <= 1 - AN.AGREE:
        return Card(f"{10 - k} em 10", "futuros em que o hospital ainda não se pagou em 2036",
                    f"Com bloco próprio, a clínica fica com a cirurgia inteira, mas o bloco precisa de muitas cirurgias "
                    f"para pagar os custos fixos ({_loop('R4')}). O que mais decide é {driver}.", 1.0, "R4", "warn")
    return Card(f"{k} em 10", "futuros em que o hospital se paga até 2036",
                f"Ainda não sabemos se o hospital se paga até 2036: {F.in_futures(1 - share)} não se paga. "
                f"O que mais decide é {driver}.", 1.05, "R4", "info")


def _rule_callback(b: PlanBundle) -> Card | None:
    if not b.plan.callback:
        return None
    rec = b.run.annual_sum("recovered")[3:].mean(0)
    from core import assumptions as A
    cost = A.value("callback_cost")
    return Card(F.people(_med(rec)), "doentes por ano recuperados pela devolução de chamadas",
                f"Ligar o sistema de chamadas perdidas recupera cerca de {F.people(_med(rec))} doentes por ano, "
                f"por cerca de {F.eur(cost)} por ano: são pessoas que já tinham escolhido a clínica.",
                0.75, None, "good")


def _rule_fatigue(b: PlanBundle) -> Card | None:
    u = b.run.m["u_doc"]
    over = (u > 0.85).sum(0)
    over_base = (b.base.m["u_doc"] > 0.85).sum(0)
    extra = _med(over - over_base)
    fat = _med(b.out["fat_max"])
    if extra < 12 or fat < 0.25:
        return None
    d_doc = _med(b.run.m["Fat"].mean(0) - b.base.m["Fat"].mean(0))
    return Card(f"{int(round(_med(over)))} meses", "com a agenda acima de 85% até 2036",
                f"A equipa cansa-se: saem mais médicos, erra-se mais e a reputação cai. Trabalhar mais resolve hoje "
                f"e piora amanhã ({_loop('B2')}).", 0.35 + min(fat, 0.6) + 0.1 * (d_doc > 0.1), "B2", "warn")


def _rule_cash_brake(b: PlanBundle) -> Card | None:
    theta = b.run.m["theta"]
    if _med(theta.min(0)) > 0.9:
        return None
    cut = (b.run.m["spend_attract"] + b.run.m["spend_digital"])
    planned = cut / np.maximum(theta, 1e-3)
    lost_spend = _med((planned - cut).sum(0))
    month = _med(theta.argmin(0).astype(float))
    if lost_spend < 20_000:
        return None
    return Card(F.eur(lost_spend), "de marketing e base digital que o plano não consegue pagar",
                f"Em {F.year_of(month)} a caixa não chega para tudo e o investimento opcional trava: o "
                f"{_loop('R3')} a andar ao contrário.", 1.1, "R3", "warn")


def _rule_risk(b: PlanBundle) -> Card | None:
    p0, p1 = float(np.mean(b.base_out["p_incident"])), float(np.mean(b.out["p_incident"]))
    if p1 - p0 >= 0.05:
        return Card(f"{F.tenths(p1)} em 10", "futuros simulados com um incidente grave de dados até 2036",
                    f"Eram {F.tenths(p0)} em 10 sem o plano: mais volume sem base digital sobe o risco "
                    f"({_loop('B4')}).", 0.7 + (p1 - p0), "B4", "warn")
    if p0 - p1 >= 0.05:
        return Card(f"{F.tenths(p0)} para {F.tenths(p1)}", "em cada 10 futuros com um incidente grave até 2036",
                    f"A base digital baixa o risco, mesmo com mais doentes ({_loop('B4')}). É seguro, não "
                    f"faturação: paga-se no dia em que evita um incidente.", 0.55 + (p0 - p1), "B4", "good")
    return None


def _rule_delay(b: PlanBundle) -> Card | None:
    if b.plan.marketing <= S.BASELINE.marketing + 20_000:
        return None
    dL = np.median(b.run.m["L"] - b.base.m["L"], axis=1)
    target = dL[36]
    if target <= 0:
        return None
    start = int(_month_of(b.plan.attract_from))
    reach = np.argmax(dL >= 0.5 * target)
    months = max(int(reach) - start, 1)
    return Card(f"{months} meses", "até se notar metade do efeito do marketing",
                "A notoriedade acumula devagar: os primeiros meses de campanha pagam-se antes de os pedidos chegarem "
                "(atraso).", 0.45, None, "info")


def _month_of(year: int) -> float:
    return (year - S.START_YEAR) * 12.0


def _rule_competition(b: PlanBundle) -> Card | None:
    cp = _med(b.run.m["Cp"][-1] - b.base.m["Cp"][-1])
    if cp < 0.04:
        return None
    eaten = cp / (1.0 + cp)
    return Card(F.pct(eaten), "dos pedidos que a concorrência leva em 2036, por reagir ao nosso crescimento",
                f"Quando a clínica cresce ou baixa preços, os grandes grupos respondem, com atraso ({_loop('B3')}).",
                0.5 + eaten, "B3", "warn")


def _rule_convention(b: PlanBundle) -> Card | None:
    if b.plan.conv <= S.BASELINE.conv + 0.02:
        return None
    rev_per = b.run.annual_sum("r_cons")[-1] / np.maximum(b.run.annual_sum("T")[-1], 1)
    rev_per_b = b.base.annual_sum("r_cons")[-1] / np.maximum(b.base.annual_sum("T")[-1], 1)
    drop = _med(rev_per / rev_per_b - 1.0)
    d_rev = _med(b.out["rev_2036"] - b.base_out["rev_2036"])
    if d_rev < 0:
        why = (f"Mais convenções trazem mais pedidos, mas com a agenda cheia ocupam o lugar de doentes particulares: "
               f"a faturação de 2036 fica {F.eur(abs(d_rev))} abaixo ({_loop('B1')}).")
        return Card(F.pct(drop, signed=True), "no valor médio de cada consulta", why, 0.8, "B1", "warn")
    return Card(F.pct(drop, signed=True), "no valor médio de cada consulta",
                "Mais convenções trazem volume a preço mais baixo; compensa enquanto houver agenda livre.", 0.4, None)


def _rule_price(b: PlanBundle) -> Card | None:
    if abs(b.plan.price - 1.0) < 0.02:
        return None
    d_seen = _med(b.out["seen_2036"] - b.base_out["seen_2036"])
    d_rev = _med(b.out["rev_2036"] - b.base_out["rev_2036"])
    verb = "sobe" if d_rev > 0 else "desce"
    who = "menos" if d_seen < 0 else "mais"
    return Card(F.eur(d_rev, signed=True), "de faturação em 2036 com o novo nível de preços",
                f"Com preços {'mais altos' if b.plan.price > 1 else 'mais baixos'}, atendem-se {F.people(abs(d_seen))} "
                f"doentes {who} por ano e a faturação {verb}; a procura reage com meses de atraso.", 0.5, None)


# ---------------------------------------------------------------------------
# Leverage card (Onde rende cada euro): the biggest surprise
# ---------------------------------------------------------------------------

_WHY_TOP = {
    "callback": "Primeiro, deixar de perder quem já escolheu a clínica (ciclo 'Limite de capacidade').",
    "online": "Primeiro, deixar de perder quem já escolheu a clínica (ciclo 'Limite de capacidade').",
    "desk": "Primeiro, deixar de perder quem já escolheu a clínica (ciclo 'Limite de capacidade').",
    "hire": "Com a agenda cheia, o que falta é quem atenda: cada médico a mais alivia a espera e o cansaço "
            "(ciclos 'Limite de capacidade' e 'Equipa no limite').",
    "clinic": "Com a agenda cheia, uma nova unidade traz gabinetes e uma nova zona de doentes, depois de um atraso.",
    "hospital": "O bloco próprio fica com a cirurgia inteira, se se encher (ciclo 'Bloco cheio').",
    "digital": "A base digital faz as outras alavancas renderem mais e baixa o risco (ciclo 'Risco digital').",
    "mkt": "Há agenda livre: a procura extra é atendida e recomenda a clínica (ciclo 'Boca a boca').",
}


def _per_euro(ratio: float) -> str:
    if ratio < 0:
        return f"perde-se dinheiro ({F.ratio(ratio)} por cada euro)"
    return f"voltam {F.ratio(ratio)} por cada euro"


def leverage_card(costed: list[dict], free: list[dict]) -> Card | None:
    if not costed:
        return None
    top = costed[0]
    by_id = {r["id"]: r for r in costed}
    mkt = by_id.get("mkt")
    why = _WHY_TOP.get(top["id"], "")
    if mkt and top["id"] != "mkt":
        why = (f"Custa {F.eur(top['spend_per_year'])} por ano. Com mais 100 mil € de marketing, "
               f"{_per_euro(mkt['ratio'])}. " + why)
    else:
        why = f"Custa {F.eur(top['spend_per_year'])} por ano. " + why
    return Card(F.ratio(top["ratio"]), f"voltam por cada euro em {top['label'].lower()}, até 2036",
                why.strip(), 1.0, None, "good" if top["share_pay"] >= 0.8 else "info")


def leverage_sentence(r: dict) -> str:
    """One plain line next to each bar."""
    share = r["share_pay"]
    if share >= 0.5 and np.isfinite(r["pay_year"]):
        return f"paga-se até {int(round(r['pay_year']))} ({F.tenths(share)} em 10 futuros)"
    return f"não se paga até 2036 ({F.tenths(1 - share)} em 10 futuros)"


# ---------------------------------------------------------------------------
# Sequencing sentence
# ---------------------------------------------------------------------------

def sequencing_text(seq: dict) -> tuple[str, str]:
    share = seq["share_house_better"]
    casa, cres = seq["casa"], seq["crescer"]
    d_net = float(seq["diff_net10"][1])
    if share >= AN.AGREE:
        head = (f"Arrumar a casa primeiro dá mais {F.eur(abs(d_net))} até 2036 {F.in_futures(share)}.")
    elif share <= 1 - AN.AGREE:
        head = (f"Crescer primeiro dá mais {F.eur(abs(d_net))} até 2036 {F.in_futures(1 - share)}: o hospital abre "
                f"mais cedo e tem mais anos para faturar.")
    else:
        head = (f"Ainda não sabemos qual das ordens rende mais até 2036: arrumar a casa primeiro ganha "
                f"{F.in_futures(share)}.")
    tail = (f"No ponto mais baixo, a caixa fica em {F.eur(casa['cash_min'][1])} com a casa primeiro e em "
            f"{F.eur(cres['cash_min'][1])} a crescer primeiro.")
    if abs(casa["rep_min"] - cres["rep_min"]) >= 0.1:
        tail += (f" A reputação desce até {F.stars(casa['rep_min'])} contra {F.stars(cres['rep_min'])}.")
    lost_gap = float(cres["lost_total"][1] - casa["lost_total"][1])
    if abs(lost_gap) >= 200:
        more = "a crescer primeiro" if lost_gap > 0 else "com a casa primeiro"
        tail += f" Perdem-se mais {F.people(abs(lost_gap))} doentes até 2036 {more}."
    return head, tail
