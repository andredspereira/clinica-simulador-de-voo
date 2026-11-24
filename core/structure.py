"""The causal map of the clinic: what pushes what, and the feedback loops.

Nodes come in four kinds: levers (what the clinic controls), outside forces
(what it does not control), mechanisms (how the clinic works inside) and
outcomes (what matters). Some nodes accumulate over time; they carry
stock=True and the map draws them with a double outline.

Each arrow has a sign (+ when more of the cause gives more of the effect,
- when it gives less, 0 when it depends), a strength and a certainty between
0 and 1, and a flag for a noticeable delay. The text is the plain pt-PT
sentence shown when hovering.

The structure mirrors core/model.py: every arrow corresponds to a term in
the equations. No streamlit imports anywhere under core/.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    kind: str  # lever, external, mechanism, outcome
    text: str
    stock: bool = False
    stage: int = 0  # column for mechanisms, 1 (left) to 4 (right)


@dataclass(frozen=True)
class Link:
    source: str
    target: str
    sign: int  # +1, -1, or 0 for "depende"
    strength: float
    certainty: float
    delay: bool
    text: str


@dataclass(frozen=True)
class Loop:
    id: str
    name: str
    kind: str  # "reforça" or "trava"
    story: str
    path: tuple[str, ...]  # node ids, the first repeated implicitly at the end


N = Node
NODES: list[Node] = [
    # Levers: what the clinic controls.
    N("mkt", "Marketing digital", "lever", "Campanhas online para dar a conhecer a clínica."),
    N("clubs", "Parcerias com clubes", "lever", "Apoio médico a clubes e federações, em troca de visibilidade."),
    N("conv", "Convenções", "lever", "Acordos com seguradoras e subsistemas: mais doentes, a preços mais baixos."),
    N("price", "Preços particulares", "lever", "O nível de preços para quem paga do seu bolso."),
    N("callback", "Devolução de chamadas", "lever",
      "Um sistema que regista as chamadas não atendidas e liga de volta."),
    N("online", "Marcação online", "lever", "Marcar a consulta no site, a qualquer hora, em tempo real."),
    N("desk", "Equipa de receção", "lever", "As pessoas que atendem o telefone e recebem os doentes."),
    N("digital", "Base digital", "lever", "Contas, acessos e dados integrados, e a sua manutenção."),
    N("hire", "Contratar médicos", "lever", "Mais médicos, até encher os gabinetes disponíveis."),
    N("clinic", "Nova clínica", "lever", "Uma nova unidade: nova zona de doentes e mais gabinetes."),
    N("hospital", "Hospital", "lever", "Um hospital próprio com bloco operatório e internamento."),
    # Outside forces: what the clinic does not control.
    N("f_demand", "Procura na região", "external", "População a envelhecer e mais gente a fazer desporto."),
    N("f_ins", "Pressão das seguradoras", "external", "As seguradoras empurram os preços das tabelas para baixo."),
    N("f_comp", "Grandes grupos privados", "external", "Grupos hospitalares grandes a abrir unidades e a mexer nos preços."),
    N("f_labour", "Mercado de cirurgiões", "external", "Quão fácil é contratar e segurar cirurgiões."),
    N("f_rate", "Juros", "external", "O custo do dinheiro emprestado."),
    # Mechanisms: how the clinic works inside.
    N("noto", "Notoriedade", "mechanism",
      "Pessoas da região que conhecem a clínica e a escolheriam. Acumula com marketing e recomendações e esquece-se com o tempo.",
      stock=True, stage=1),
    N("comp", "Resposta da concorrência", "mechanism",
      "Quanto os concorrentes reagem ao nosso crescimento. Acumula devagar.", stock=True, stage=1),
    N("invest", "Dinheiro para investir", "mechanism",
      "O plano só se faz se houver caixa: quando a caixa aperta, o investimento opcional trava.", stage=1),
    N("price_avg", "Preço médio", "mechanism", "O que a clínica recebe, em média, por cada ato.", stage=1),
    N("enq", "Pedidos de marcação", "mechanism", "Pessoas que ligam, escrevem ou chegam via seguradora ou clube.", stage=2),
    N("access", "Pedidos atendidos", "mechanism",
      "A parte dos pedidos que recebe resposta a tempo: chamadas atendidas e pedidos do site tratados.", stage=2),
    N("digital_mat", "Maturidade digital", "mechanism",
      "Contas, acessos e dados fiáveis. Acumula com investimento e desgasta-se sem manutenção.", stock=True, stage=2),
    N("wait", "Lista e tempo de espera", "mechanism",
      "Doentes marcados que ainda não foram vistos. Quanto mais cheia, mais dias de espera.", stock=True, stage=3),
    N("doctors", "Médicos", "mechanism",
      "Médicos a trabalhar, incluindo os recém-chegados que ainda estão a encher a agenda.", stock=True, stage=3),
    N("util", "Ocupação da agenda", "mechanism", "Que parte da agenda dos médicos está preenchida.", stage=3),
    N("fatigue", "Cansaço da equipa", "mechanism",
      "Acumula quando a ocupação fica muito tempo acima de 85% e só passa devagar.", stock=True, stage=3),
    N("sat", "Satisfação", "mechanism", "Quantos doentes saem bem tratados: espera curta, telefone atendido, equipa descansada.",
      stage=4),
    N("rep", "Reputação", "mechanism", "Como uma avaliação online, de 0 a 5. Sobe devagar e cai depressa.", stock=True, stage=4),
    N("follow", "Doentes em acompanhamento", "mechanism", "Doentes em seguimento, exames ou fisioterapia.", stock=True, stage=4),
    N("surg", "Lista cirúrgica", "mechanism", "Doentes propostos para cirurgia à espera de data.", stock=True, stage=4),
    N("hosp", "Bloco próprio", "mechanism",
      "Capacidade do hospital próprio, quando abre: enche-se com doentes nossos e de cirurgiões de fora.", stock=True, stage=4),
    # Outcomes: what matters.
    N("seen", "Doentes atendidos", "outcome", "Doentes vistos por ano: novos e em acompanhamento."),
    N("lost", "Doentes perdidos", "outcome", "Pessoas que procuraram a clínica e nunca chegaram a uma consulta."),
    N("revenue", "Faturação", "outcome", "Consultas, exames, fisioterapia, cirurgia e outras especialidades."),
    N("ebitda", "EBITDA", "outcome", "O que sobra da faturação depois dos custos de funcionamento."),
    N("cash", "Caixa", "outcome", "O dinheiro em banco. Acumula o EBITDA e paga investimentos e dívida.", stock=True),
    N("risk", "Risco de incidente grave", "outcome", "Probabilidade de uma fuga ou bloqueio de dados de saúde."),
]

L = Link
LINKS: list[Link] = [
    # Levers.
    L("mkt", "noto", +1, 0.6, 0.6, True, "O marketing dá a conhecer a clínica, com alguns meses de atraso."),
    L("clubs", "noto", +1, 0.4, 0.6, True, "Cada clube parceiro traz atletas e famílias que passam a conhecer a clínica."),
    L("conv", "enq", +1, 0.6, 0.6, False, "Mais convenções abrem a porta aos doentes de mais seguradoras."),
    L("conv", "price_avg", -1, 0.6, 0.8, False, "Mas cada consulta por convenção paga cerca de metade."),
    L("price", "price_avg", +1, 0.6, 0.9, False, "Preços particulares mais altos sobem o preço médio."),
    L("price", "enq", -1, 0.4, 0.5, True, "E afastam alguns doentes particulares, com atraso."),
    L("price", "comp", -1, 0.3, 0.4, True, "Baixar preços provoca a concorrência a baixar também."),
    L("callback", "access", +1, 0.5, 0.7, False, "Ligar de volta recupera quem não foi atendido."),
    L("online", "access", +1, 0.6, 0.7, False, "Quem marca online não fica à espera de resposta e liberta o telefone."),
    L("desk", "access", +1, 0.6, 0.7, False, "Mais gente na receção, menos chamadas sem resposta."),
    L("digital", "digital_mat", +1, 0.6, 0.6, True, "O investimento leva meses a fazer efeito e precisa de manutenção."),
    L("hire", "doctors", +1, 0.6, 0.7, True, "Um médico demora meses a chegar e mais meses a encher a agenda."),
    L("clinic", "noto", +1, 0.5, 0.5, True, "Uma nova unidade traz uma nova zona de doentes, depois de abrir."),
    L("clinic", "doctors", +1, 0.5, 0.7, True, "E gabinetes para mais médicos."),
    L("clinic", "ebitda", -1, 0.4, 0.8, False, "Renda e equipa custam desde o primeiro dia."),
    L("clinic", "cash", -1, 0.4, 0.9, False, "A obra paga-se antes de a clínica faturar."),
    L("hospital", "hosp", +1, 0.8, 0.7, True, "Licenciar e construir demora anos; depois ainda é preciso arrancar."),
    L("hospital", "ebitda", -1, 0.7, 0.8, False, "O hospital tem custos fixos altos, cheio ou vazio."),
    L("hospital", "cash", -1, 0.8, 0.9, False, "A obra e o equipamento pagam-se antes de o hospital abrir."),
    # Outside forces.
    L("f_demand", "enq", +1, 0.3, 0.6, False, "Mais gente na região com queixas de ortopedia."),
    L("f_ins", "price_avg", -1, 0.4, 0.7, False, "As tabelas das seguradoras descem em termos reais."),
    L("f_comp", "comp", +1, 0.5, 0.5, False, "Os grandes grupos disputam os mesmos doentes."),
    L("f_labour", "doctors", -1, 0.4, 0.5, True, "Com o mercado difícil, contratar demora mais e saem mais médicos."),
    L("f_rate", "cash", -1, 0.3, 0.8, False, "Com dívida, juros mais altos tiram caixa."),
    # Demand and access.
    L("noto", "enq", +1, 0.8, 0.8, False, "Quem conhece a clínica pede marcação quando precisa."),
    L("comp", "enq", -1, 0.4, 0.5, False, "A concorrência leva parte dos doentes."),
    L("rep", "enq", +1, 0.6, 0.6, False, "Uma boa avaliação faz escolher a clínica."),
    L("enq", "access", -1, 0.4, 0.7, False, "Muitos pedidos ao mesmo tempo entopem o telefone."),
    L("access", "wait", +1, 0.5, 0.8, False, "Pedido atendido é doente marcado."),
    L("enq", "wait", +1, 0.7, 0.8, False, "Mais pedidos enchem a lista de espera."),
    L("access", "lost", -1, 0.6, 0.7, False, "Cada pedido sem resposta é um doente que pode ir a outro lado."),
    L("wait", "lost", +1, 0.6, 0.6, False, "Com espera longa, mais gente desiste."),
    L("digital_mat", "access", +1, 0.4, 0.5, True, "Dados integrados fazem a devolução e a marcação online funcionar melhor."),
    L("invest", "noto", +1, 0.4, 0.6, False, "Sem caixa, o marketing do plano trava."),
    L("invest", "digital_mat", +1, 0.3, 0.6, False, "Sem caixa, o investimento digital trava."),
    L("invest", "doctors", +1, 0.3, 0.6, False, "Sem caixa, as contratações travam."),
    # Capacity and experience.
    L("wait", "seen", +1, 0.6, 0.8, False, "Doentes marcados tornam-se consultas."),
    L("doctors", "seen", +1, 0.8, 0.9, False, "Mais médicos, mais consultas por mês."),
    L("doctors", "wait", -1, 0.7, 0.8, False, "Com mais médicos, a lista esvazia mais depressa."),
    L("digital_mat", "seen", +1, 0.3, 0.5, True, "Menos faltas e agendas mais bem usadas."),
    L("seen", "util", +1, 0.6, 0.8, False, "Mais consultas, agenda mais cheia."),
    L("doctors", "util", -1, 0.6, 0.8, False, "Mais médicos para as mesmas consultas, agenda com mais folga."),
    L("follow", "util", +1, 0.4, 0.7, False, "Os seguimentos também ocupam a agenda."),
    L("util", "fatigue", +1, 0.6, 0.6, True, "Semanas acima de 85% de ocupação acumulam cansaço."),
    L("fatigue", "doctors", -1, 0.5, 0.5, True, "Equipas cansadas perdem médicos, e substituí-los demora."),
    L("fatigue", "sat", -1, 0.4, 0.5, False, "Cansaço traz erros e pior atendimento."),
    L("wait", "sat", -1, 0.6, 0.7, False, "Quanto mais longa a espera, menos satisfeitos os doentes."),
    L("access", "sat", +1, 0.3, 0.6, False, "Telefone atendido é parte de um bom serviço."),
    L("sat", "rep", +1, 0.6, 0.7, True, "Boas experiências levantam a reputação devagar."),
    L("rep", "doctors", +1, 0.3, 0.4, True, "Bons médicos preferem casas com bom nome, e ficam."),
    L("seen", "noto", +1, 0.5, 0.6, False, "Doentes satisfeitos recomendam a clínica."),
    L("seen", "comp", +1, 0.3, 0.5, True, "Quando crescemos, a concorrência reage."),
    L("seen", "follow", +1, 0.6, 0.8, False, "Parte dos novos doentes fica em seguimento, exames ou fisioterapia."),
    L("seen", "surg", +1, 0.5, 0.6, False, "Uma parte dos novos doentes precisa de cirurgia."),
    L("surg", "hosp", +1, 0.6, 0.6, False, "A lista cirúrgica enche o bloco próprio."),
    L("rep", "hosp", +1, 0.3, 0.4, True, "Um bom nome atrai cirurgiões de fora para o bloco."),
    L("hosp", "noto", +1, 0.2, 0.4, True, "Um hospital dá visibilidade à marca."),
    L("seen", "risk", +1, 0.4, 0.6, False, "Mais doentes, mais dados para proteger."),
    L("digital_mat", "risk", -1, 0.6, 0.6, False, "Acessos e dados bem geridos baixam o risco."),
    L("risk", "rep", -1, 0.5, 0.5, False, "Um incidente grave tira reputação em semanas."),
    # Money.
    L("seen", "revenue", +1, 0.8, 0.9, False, "Cada consulta fatura, e puxa exames e outras especialidades."),
    L("follow", "revenue", +1, 0.5, 0.8, False, "Seguimentos, exames e fisioterapia faturam."),
    L("price_avg", "revenue", +1, 0.6, 0.9, False, "Preço médio mais alto, mais faturação por ato."),
    L("hosp", "revenue", +1, 0.7, 0.6, False, "Com bloco próprio, a clínica fatura a cirurgia inteira."),
    L("revenue", "ebitda", +1, 0.8, 0.9, False, "Mais faturação, mais margem, se os custos não crescerem ao mesmo ritmo."),
    L("risk", "ebitda", -1, 0.3, 0.5, False, "Um incidente custa dinheiro."),
    L("ebitda", "cash", +1, 0.8, 0.9, False, "O EBITDA acumula em caixa, depois de impostos."),
    L("cash", "invest", +1, 0.6, 0.6, False, "Com caixa, o plano anda."),
]

LOOPS: list[Loop] = [
    Loop("R1", "Boca a boca", "reforça",
         "Mais doentes bem tratados trazem mais recomendações, e as recomendações trazem mais doentes.",
         ("noto", "enq", "wait", "seen")),
    Loop("R2", "Reputação", "reforça",
         "Espera curta e bom tratamento dão boa reputação; a boa reputação atrai e segura médicos, e a espera encurta.",
         ("rep", "doctors", "wait", "sat")),
    Loop("R3", "Reinvestir", "reforça",
         "A margem vira caixa, a caixa paga o plano, e o plano traz crescimento e mais margem.",
         ("ebitda", "cash", "invest", "noto", "enq", "wait", "seen", "revenue")),
    Loop("R4", "Bloco cheio", "reforça",
         "Com hospital próprio, mais cirurgias dão mais margem e mais dinheiro para crescer, o que enche mais o bloco.",
         ("surg", "hosp", "revenue", "ebitda", "cash", "invest", "doctors", "seen")),
    Loop("B1", "Limite de capacidade", "trava",
         "Mais procura do que agenda alonga a espera; os doentes desistem, a reputação cai e a procura desce.",
         ("enq", "wait", "sat", "rep")),
    Loop("B2", "Equipa no limite", "trava",
         "Com a agenda sempre cheia, a equipa cansa-se, saem médicos e atende-se menos gente. Trabalhar mais resolve hoje e piora amanhã.",
         ("seen", "util", "fatigue", "doctors")),
    Loop("B3", "Concorrência", "trava",
         "Quando a clínica cresce ou baixa preços, os concorrentes reagem e levam parte do crescimento.",
         ("enq", "wait", "seen", "comp")),
    Loop("B4", "Risco digital", "trava",
         "Mais doentes e mais dados, sem base digital, sobem o risco de um incidente que derruba a reputação.",
         ("seen", "risk", "rep", "enq", "wait")),
]

NODE_BY_ID = {n.id: n for n in NODES}
LOOP_BY_ID = {lp.id: lp for lp in LOOPS}

KIND_TITLES = {
    "lever": ("ALAVANCAS", "o que controlamos"),
    "external": ("FORÇAS DE FORA", "o que não controlamos"),
    "mechanism": ("COMO A CLÍNICA FUNCIONA", "o que acontece por dentro"),
    "outcome": ("RESULTADOS", "o que nos importa"),
}


def loop_links(loop: Loop) -> list[tuple[str, str]]:
    path = list(loop.path)
    return [(path[i], path[(i + 1) % len(path)]) for i in range(len(path))]


def link_between(source: str, target: str) -> Link | None:
    for lk in LINKS:
        if lk.source == source and lk.target == target:
            return lk
    return None


def loop_sign(loop: Loop) -> int:
    sign = 1
    for s, t in loop_links(loop):
        lk = link_between(s, t)
        if lk is None or lk.sign == 0:
            return 0
        sign *= lk.sign
    return sign


def reachable_from(sources: set[str]) -> set[str]:
    """Every node a change in `sources` can travel to along the arrows."""
    out = set(sources)
    frontier = list(sources)
    while frontier:
        node = frontier.pop()
        for lk in LINKS:
            if lk.source == node and lk.target not in out:
                out.add(lk.target)
                frontier.append(lk.target)
    return out


# Which levers in a Plan correspond to which lever nodes.
PLAN_FIELDS_TO_NODES = {
    "marketing": "mkt", "clubs": "clubs", "conv": "conv", "price": "price",
    "callback": "callback", "online": "online", "front_desk": "desk",
    "digital_once": "digital", "digital_maint": "digital", "hire_rate": "hire",
    "clinic_year": "clinic", "hospital_year": "hospital", "hospital_rooms": "hospital",
    "hospital_beds": "hospital", "hospital_debt": "hospital",
    "attract_from": "mkt", "attract_to": "mkt", "access_from": "desk", "access_to": "desk",
    "digital_from": "digital", "digital_to": "digital", "hire_from": "hire", "hire_to": "hire",
}
