"""Every number the model uses, in one place.

Each assumption carries five things: a unit, a plain pt-PT description, the
central value used in the single scenario run, a plausible range (used to draw
the simulated futures) and a one-line justification. Values are illustrative:
they are meant to be plausible for an independent orthopaedic and sports
medicine group of about 5 M EUR of yearly revenue in Portugal, not to
reproduce anyone's accounts. Every value is "a calibrar com dados reais".

An assumption with a range is drawn from a triangular distribution with its
mode at the central value. An assumption without a range is held fixed.

Money is in constant 2027 euros (real terms). Time is in months unless the
unit says otherwise.

No streamlit imports anywhere under core/.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumption:
    key: str
    group: str
    label: str
    unit: str
    value: float
    low: float | None = None
    high: float | None = None
    why: str = ""
    measure: str = ""
    kind: str = "dec"  # how to display it: eur, pct, int, dec, months, days, stars, x
    short: str = ""  # a short name to use inside a sentence (uncertain assumptions)

    @property
    def uncertain(self) -> bool:
        return self.low is not None and self.high is not None and self.high > self.low


GROUPS = {
    "presente": "A clínica hoje (ponto de partida)",
    "procura": "Procura e notoriedade",
    "acesso": "Atender quem chega",
    "capacidade": "Médicos e percurso do doente",
    "experiencia": "Satisfação e reputação",
    "digital": "Base digital e risco",
    "dinheiro": "Preços e custos",
    "clinica": "Nova clínica",
    "hospital": "Hospital",
}


_A = Assumption

ASSUMPTIONS: list[Assumption] = [
    # ------------------------------------------------------------------ today
    _A("new_patients0", "presente", "Novos doentes por mês (primeiras consultas)", "doentes/mês", 625,
       why="Cerca de 7 500 primeiras consultas por ano; com os doentes em acompanhamento dá perto de 10 000 doentes por ano.",
       kind="int"),
    _A("wait_days0", "presente", "Espera atual por uma primeira consulta", "dias", 12,
       why="Uma a duas semanas é plausível em ortopedia privada numa grande cidade.", kind="days"),
    _A("doctor_util0", "presente", "Ocupação atual da agenda médica", "fração", 0.80,
       why="Agenda bem preenchida, ainda com alguma folga antes dos 85%.", kind="pct"),
    _A("doctors0", "presente", "Médicos de ortopedia", "ETI", 9.0,
       why="Muitos médicos a tempo parcial, que somam cerca de nove a tempo inteiro.", kind="dec"),
    _A("rooms0", "presente", "Gabinetes disponíveis, em médicos a tempo inteiro", "ETI", 10.5,
       why="Espaço para crescer cerca de 15% sem novas instalações.", kind="dec"),
    _A("front_desk0", "presente", "Equipa de receção", "ETI", 8.0,
       why="Receção para um grupo com mais de uma unidade.", kind="dec"),
    _A("phone_time", "presente", "Parte do tempo da receção passada ao telefone", "fração", 0.35,
       why="O resto vai para o atendimento presencial, faturação e seguradoras.", kind="pct"),
    _A("ch_phone", "presente", "Pedidos de marcação que chegam por telefone", "fração", 0.55,
       why="O telefone continua a ser o canal principal das clínicas privadas.", kind="pct"),
    _A("ch_web", "presente", "Pedidos que chegam pelo formulário do site", "fração", 0.20,
       why="Pedidos por formulário, respondidos depois pela receção.", kind="pct"),
    _A("ins_share0", "presente", "Peso das convenções na procura atual", "fração", 0.60,
       why="Seguradoras e subsistemas pesam muito na ortopedia privada em Portugal.", kind="pct"),
    _A("surg_wait0", "presente", "Espera atual por cirurgia", "meses", 1.5,
       why="Cirurgia programada em hospitais parceiros, com algumas semanas de espera.", kind="months"),
    _A("surg_util0", "presente", "Ocupação atual dos tempos de bloco contratados", "fração", 0.80,
       why="Tempos de bloco nos parceiros quase sempre usados.", kind="pct"),
    _A("digital0", "presente", "Maturidade digital no ponto de partida", "0 a 1", 0.25,
       why="Ponto de partida ilustrativo: base digital modesta, comum em grupos desta dimensão.", kind="dec"),
    _A("cash0", "presente", "Caixa no início de 2027", "€", 800_000,
       why="Uma reserva de cerca de dois meses de custos fixos.", kind="eur"),
    _A("marketing0", "presente", "Marketing digital hoje", "€/ano", 60_000,
       why="Cerca de 1% da faturação, típico de clínicas que vivem muito do boca a boca.", kind="eur"),
    _A("clubs0", "presente", "Parcerias com clubes e federações hoje", "número", 6,
       why="Alguns clubes locais com apoio médico-desportivo.", kind="int"),
    _A("maint0", "presente", "Manutenção anual de sistemas hoje", "€/ano", 40_000,
       why="Licenças e suporte básicos; chega para manter a maturidade atual.", kind="eur"),
    _A("margin0", "presente", "Margem EBITDA no primeiro ano (alvo da calibração)", "fração", 0.11,
       why="Meio do intervalo de 8% a 15% para um grupo independente desta dimensão.", kind="pct"),

    # ------------------------------------------------------------------ demand
    _A("need_rate", "procura", "Pessoas que conhecem a clínica e procuram ortopedia em cada mês", "fração/mês", 0.006,
       why="Cerca de 7% por ano têm uma queixa que leva a uma consulta de especialidade.", kind="pct"),
    _A("catchment", "procura", "População da área de influência", "pessoas", 1_200_000,
       why="Área metropolitana servida por mais de uma unidade; limita quanto a notoriedade pode crescer.", kind="int"),
    _A("noto_halflife", "procura", "Meia-vida da notoriedade (quanto tempo dura a memória da clínica)", "meses", 12, 6, 18,
       why="Sem novos estímulos, metade das pessoas esquece ou escolhe outro em 6 a 18 meses.",
       measure="Perguntar 'como nos conheceu?' e há quanto tempo, em cada marcação, ao longo do ano.", short="quanto tempo dura a notoriedade", kind="months"),
    _A("mkt_delay", "procura", "Atraso entre o marketing e a notoriedade", "meses", 4, 2, 6,
       why="Campanhas digitais levam alguns meses a criar memória e intenção.",
       measure="Registar a origem de cada marcação e cruzar com as datas das campanhas.", short="o atraso do marketing", kind="months"),
    _A("mkt_curve", "procura", "Quanto rende cada euro extra de marketing (1 = sempre igual)", "expoente", 0.75, 0.6, 0.9,
       why="Cada euro adicional alcança pessoas menos interessadas: o retorno desce aos poucos.",
       measure="Variar o orçamento por trimestre e medir pedidos por euro.", short="quanto rende cada euro extra de marketing", kind="dec"),
    _A("w_mkt", "procura", "Peso do marketing na notoriedade de hoje", "peso", 0.15, 0.08, 0.22,
       why="Uma parte pequena; a maioria vem de recomendações e convenções.",
       measure="Registar 'como nos conheceu?' em cada marcação.", short="o peso atual do marketing", kind="pct"),
    _A("w_club", "procura", "Peso das parcerias com clubes na notoriedade", "peso", 0.08, 0.04, 0.12,
       why="Atletas e famílias dos clubes parceiros.",
       measure="Registar 'como nos conheceu?' em cada marcação.", short="o peso das parcerias com clubes", kind="pct"),
    _A("w_wom", "procura", "Peso do boca a boca na notoriedade", "peso", 0.35, 0.25, 0.45,
       why="Em ortopedia, muitos doentes chegam por recomendação de quem já foi tratado.",
       measure="Registar 'como nos conheceu?' em cada marcação.", short="o peso do boca a boca", kind="pct"),
    _A("w_doc", "procura", "Peso da rede pessoal dos médicos", "peso", 0.12, 0.06, 0.18,
       why="Médicos conhecidos trazem doentes e referenciações de colegas.",
       measure="Registar o médico pedido na marcação e se o doente o seguiu de outro lado.", short="o peso da rede dos médicos", kind="pct"),
    _A("w_base", "procura", "Peso de outras origens (listas das seguradoras, pesquisa, médicos de família)", "peso", 0.30, 0.20, 0.40,
       why="Base estável que não depende das alavancas do plano.",
       measure="Registar 'como nos conheceu?' em cada marcação.", short="o peso das outras origens de doentes", kind="pct"),
    _A("price_sens", "procura", "Quanto a procura particular reage ao preço", "fator", 1.0, 0.6, 1.5,
       why="Subir 10% os preços particulares faz perder cerca de 10% desses pedidos, com atraso.",
       measure="Testar uma subida pequena numa especialidade e medir as marcações particulares.", short="a reação dos doentes ao preço", kind="dec"),
    _A("price_delay", "procura", "Atraso até a procura reagir a um novo preço", "meses", 6,
       why="As pessoas comparam preços quando precisam, não no dia da mudança.", kind="months"),
    _A("conv_response", "procura", "Quanto a procura cresce com mais convenções", "fator", 0.8, 0.5, 1.0,
       why="Cada novo acordo abre a porta a doentes dessa seguradora, mas não a todos.",
       measure="Registar marcações por seguradora antes e depois de cada novo acordo.", short="a procura que cada convenção traz", kind="dec"),
    _A("patience", "procura", "Tolerância à espera por uma primeira consulta", "dias", 70, 45, 100,
       why="Com 12 dias de espera perde-se cerca de 1 em 15; com 30 dias, cerca de 1 em 4.",
       measure="Registar quem recusa a data proposta e quem desmarca para ir a outro lado.", short="quanto tempo os doentes aceitam esperar", kind="days"),
    _A("comp_response", "procura", "Força da reação da concorrência ao nosso crescimento", "fator", 0.25, 0.10, 0.40,
       why="Os grandes grupos reagem com preços e aberturas quando perdem doentes.",
       measure="Acompanhar preços, campanhas e aberturas dos grandes grupos na área.", short="a reação da concorrência", kind="dec"),
    _A("comp_delay", "procura", "Tempo até a concorrência reagir", "meses", 18,
       why="Abrir serviços ou rever preços leva mais de um ano.", kind="months"),

    # ------------------------------------------------------------------ access
    _A("miss0", "acesso", "Chamadas não atendidas hoje", "fração", 0.15, 0.08, 0.25,
       why="Comum em clínicas com picos de chamadas; varia muito de clínica para clínica.",
       measure="Registar todas as chamadas, atendidas e não atendidas, por hora do dia.", short="a parte das chamadas que hoje fica sem resposta", kind="pct"),
    _A("retry", "acesso", "Quem volta a ligar depois de não ser atendido", "fração", 0.50, 0.35, 0.65,
       why="Metade insiste; a outra metade liga para outra clínica.",
       measure="Cruzar os números que ligam mais de uma vez no mesmo dia.", short="quantos voltam a ligar", kind="pct"),
    _A("callback_success", "acesso", "Chamadas perdidas que a devolução recupera", "fração", 0.65, 0.45, 0.80,
       why="Ligar de volta em poucos minutos recupera a maioria; com dados integrados, ainda mais.",
       measure="Fazer um piloto de um mês a devolver todas as chamadas perdidas.", short="quantas chamadas a devolução recupera", kind="pct"),
    _A("calls_per_booking", "acesso", "Chamadas por cada nova marcação", "chamadas", 1.3,
       why="Algumas marcações precisam de mais de uma chamada.", kind="dec"),
    _A("calls_per_visit", "acesso", "Chamadas de doentes já seguidos, por consulta", "chamadas", 0.5,
       why="Remarcações, resultados e dúvidas.", kind="dec"),
    _A("web_loss0", "acesso", "Pedidos pelo formulário do site que se perdem hoje", "fração", 0.25, 0.15, 0.35,
       why="Um pedido respondido horas depois muitas vezes já marcou noutro lado.",
       measure="Registar a hora de cada pedido e a hora da resposta.", short="quantos pedidos do site se perdem hoje", kind="pct"),
    _A("online_shift", "acesso", "Telefonemas que passam para a marcação online", "fração", 0.30, 0.15, 0.45,
       why="Quem pode marcar sozinho a qualquer hora deixa de ligar.",
       measure="Medir no primeiro trimestre depois de lançar a marcação online.", short="quantos passam a marcar online", kind="pct"),
    _A("web_loss_online", "acesso", "Pedidos online que se perdem com marcação em tempo real", "fração", 0.04,
       why="Só se perde quem não encontra uma hora que lhe convenha.", kind="pct"),
    _A("ref_loss0", "acesso", "Pedidos via seguradoras e clubes que se perdem hoje", "fração", 0.05,
       why="Canal com contacto direto; perde-se pouco.", kind="pct"),
    _A("fd_delay", "acesso", "Tempo para contratar alguém para a receção", "meses", 2, 1, 3,
       why="Recrutamento simples, mas com formação.",
       measure="Registar o tempo entre abrir uma vaga na receção e a pessoa começar.", short="o tempo para contratar receção", kind="months"),
    _A("fd_cost", "acesso", "Custo anual de uma pessoa na receção", "€/ano", 20_000,
       why="Salário, encargos e formação.", kind="eur"),
    _A("callback_cost", "acesso", "Sistema de chamadas perdidas com devolução", "€/ano", 12_000,
       why="Central telefónica com registo de chamadas e lista de devolução.", kind="eur"),
    _A("callback_setup", "acesso", "Arranque do sistema de chamadas perdidas", "€", 5_000,
       why="Configuração e formação.", kind="eur"),
    _A("online_cost", "acesso", "Marcação online em tempo real", "€/ano", 18_000,
       why="Licença e integração com a agenda.", kind="eur"),
    _A("online_setup", "acesso", "Arranque da marcação online", "€", 15_000,
       why="Integração com a agenda e com o site.", kind="eur"),

    # ------------------------------------------------------------------ capacity
    _A("recruit_delay", "capacidade", "Tempo até um médico contratado chegar", "meses", 6, 3, 9,
       why="Pré-aviso no sítio anterior e mercado de cirurgiões apertado.",
       measure="Registar o tempo entre abrir uma vaga e o médico começar.", short="o tempo para contratar médicos", kind="months"),
    _A("ramp_delay", "capacidade", "Tempo até um médico novo ter a agenda cheia", "meses", 9, 6, 12,
       why="Um médico novo precisa de tempo para criar a sua lista de doentes.",
       measure="Acompanhar a agenda de cada médico novo mês a mês.", short="o tempo até um médico novo encher a agenda", kind="months"),
    _A("ramp_productivity", "capacidade", "Produtividade de um médico ainda em adaptação", "fração", 0.5,
       why="Em média, metade da agenda de um médico estabelecido.", kind="pct"),
    _A("attrition", "capacidade", "Médicos que saem por ano, sem cansaço", "fração/ano", 0.08, 0.05, 0.12,
       why="Mobilidade normal entre grupos privados.",
       measure="Registar saídas de médicos e os motivos.", short="a saída de médicos", kind="pct"),
    _A("fatigue_attrition", "capacidade", "Quanto o cansaço máximo multiplica as saídas", "vezes", 2.0, 1.0, 3.0,
       why="Equipas esgotadas perdem gente mais depressa.",
       measure="Inquérito curto à equipa duas vezes por ano.", short="quanto o cansaço faz sair médicos", kind="x"),
    _A("fatigue_threshold", "capacidade", "Ocupação a partir da qual a equipa acumula cansaço", "fração", 0.85,
       why="Acima de 85% de ocupação, o dia deixa de ter folga.", kind="pct"),
    _A("fatigue_up", "capacidade", "Tempo para o cansaço se instalar", "meses", 6,
       why="Semanas puxadas acumulam-se ao longo de meses.", kind="months"),
    _A("fatigue_down", "capacidade", "Tempo para o cansaço passar", "meses", 9,
       why="Recuperar demora mais do que cansar.", kind="months"),
    _A("u_max", "capacidade", "Ocupação máxima possível de uma agenda", "fração", 1.0,
       why="Uma agenda não passa de 100%; perto disso, a espera dispara.", kind="pct"),
    _A("noshow0", "capacidade", "Faltas às consultas hoje", "fração", 0.09, 0.06, 0.12,
       why="Em ortopedia privada, entre 6% e 12% de faltas.",
       measure="Registar faltas por dia, por médico e por canal de marcação.", short="as faltas às consultas", kind="pct"),
    _A("follow_share", "capacidade", "Novos doentes que ficam em acompanhamento", "fração", 0.55,
       why="Muitos precisam de seguimento, exames ou fisioterapia.", kind="pct"),
    _A("pathway", "capacidade", "Duração média do acompanhamento", "meses", 6,
       why="Do diagnóstico à alta, incluindo fisioterapia.", kind="months"),
    _A("fu_rate", "capacidade", "Consultas de seguimento por doente em acompanhamento", "consultas/mês", 0.42,
       why="Cerca de 2,5 consultas de seguimento por percurso.", kind="dec"),
    _A("physio_share", "capacidade", "Doentes em acompanhamento que fazem fisioterapia", "fração", 0.55,
       why="Ortopedia e medicina desportiva vivem muito da reabilitação.", kind="pct"),
    _A("physio_sessions", "capacidade", "Sessões de fisioterapia por doente que faz fisioterapia", "sessões", 16,
       why="Dois meses de reabilitação a duas sessões por semana.", kind="int"),
    _A("exams_new", "capacidade", "Exames feitos na clínica por novo doente", "exames", 0.9,
       why="Raio X e ecografia na primeira consulta; a ressonância é feita fora.", kind="dec"),
    _A("exams_fu", "capacidade", "Exames feitos na clínica por consulta de seguimento", "exames", 0.3,
       why="Controlo radiológico em parte dos seguimentos.", kind="dec"),
    _A("surg_conv", "capacidade", "Taxa de conversão para cirurgia", "fração dos novos doentes", 0.09, 0.06, 0.12,
       why="Entre 6% e 12% dos novos doentes de ortopedia acabam operados.",
       measure="Registar, por médico, quantos novos doentes são propostos para cirurgia e quantos operam connosco.",
       short="a taxa de conversão para cirurgia", kind="pct"),
    _A("surg_patience", "capacidade", "Tolerância à espera por cirurgia", "meses", 6,
       why="Com espera longa, o doente opera-se pela sua seguradora noutro sítio.", kind="months"),
    _A("doctor_support", "capacidade", "Custo fixo por médico (gabinete, assistente, equipamento)", "€/ano por ETI", 20_000,
       why="Os médicos recebem por ato; o custo fixo é o espaço e o apoio.", kind="eur"),
    _A("recruit_cost", "capacidade", "Custo de cada contratação de médico", "€ por ETI", 25_000,
       why="Recrutamento, integração e garantia de rendimento no arranque.", kind="eur"),

    # ------------------------------------------------------------------ experience
    _A("rep_up", "experiencia", "Tempo para a reputação subir", "meses", 8, 6, 12,
       why="Boas experiências acumulam-se devagar: 12 a 24 meses até se notarem por inteiro.",
       measure="Acompanhar as avaliações online mês a mês.", short="o tempo para a reputação subir", kind="months"),
    _A("rep_down", "experiencia", "Tempo para a reputação cair depois de um choque", "meses", 1.2, 0.7, 2.0,
       why="Más experiências espalham-se em semanas.",
       measure="Acompanhar as avaliações online mês a mês.", short="o tempo para a reputação cair", kind="months"),
    _A("rep_effect", "experiencia", "Efeito de cada estrela de reputação na procura", "fração por estrela", 0.35, 0.20, 0.50,
       why="Meia estrela a menos custa perto de 1 em 6 pedidos.",
       measure="Cruzar avaliações online com marcações novas mês a mês.", short="o peso da reputação na escolha", kind="pct"),
    _A("rep_doctors", "experiencia", "Quanto a reputação ajuda a atrair e a segurar médicos", "fator", 0.4,
       why="Bons médicos preferem casas com bom nome; meia estrela muda cerca de 20% nas saídas e no tempo de contratação.",
       kind="dec"),
    _A("wait_sat", "experiencia", "Espera a partir da qual a satisfação cai a pique", "dias", 45,
       why="Até duas semanas incomoda pouco; acima de um mês e meio, muito.", kind="days"),

    # ------------------------------------------------------------------ digital
    _A("dig_delay", "digital", "Atraso até o investimento digital fazer efeito", "meses", 6, 3, 9,
       why="Contas, acessos e dados integrados levam meses a implementar e a adotar.",
       measure="Plano de projeto com marcos mensais.", short="o atraso da base digital", kind="months"),
    _A("dig_cost", "digital", "Investimento que fecharia toda a distância até à maturidade máxima", "€", 800_000,
       why="Escala de um projeto de identidade, acessos e dados para um grupo pequeno.", kind="eur"),
    _A("dig_effect", "digital", "Eficácia do investimento digital", "vezes", 1.0, 0.7, 1.3,
       why="Projetos digitais variam muito na execução.",
       measure="Começar por um piloto numa unidade e medir antes de alargar.", short="a eficácia do investimento digital", kind="x"),
    _A("dig_decay", "digital", "Desgaste anual da maturidade digital sem manutenção", "fração/ano", 0.25,
       why="Acessos, integrações e painéis degradam-se sem cuidado contínuo.", kind="pct"),
    _A("incident_rate", "digital", "Probabilidade anual de um incidente grave de dados hoje", "fração/ano", 0.04, 0.02, 0.07,
       why="Saúde é um setor muito visado; a probabilidade desce com acessos e dados bem geridos.",
       measure="Auditoria de segurança e inventário de quem acede a quê.", short="o risco de incidente de hoje", kind="pct"),
    _A("incident_cost", "digital", "Custo direto de um incidente grave", "€", 200_000, 80_000, 400_000,
       why="Recuperação, paragem, coimas e apoio jurídico.",
       measure="Simulacro de incidente com a equipa e o fornecedor de sistemas.", short="o custo de um incidente", kind="eur"),
    _A("incident_hit", "digital", "Estrelas de reputação que um incidente tira", "estrelas", 0.6, 0.3, 1.0,
       why="Uma fuga de dados de saúde é notícia e fica na memória.",
       measure="Difícil de medir antes; olhar para casos públicos semelhantes.", short="o dano de um incidente na reputação", kind="stars"),
    _A("incident_memory", "digital", "Tempo até a memória de um incidente passar", "meses", 18,
       why="A memória dura mais do que o problema.", kind="months"),

    # ------------------------------------------------------------------ money
    _A("p_cons_priv", "dinheiro", "Consulta particular", "€", 95,
       why="Primeira consulta de ortopedia privada.", kind="eur"),
    _A("p_cons_ins", "dinheiro", "Consulta por convenção (seguradora e copagamento)", "€", 47,
       why="As seguradoras pagam cerca de metade do preço particular.", kind="eur"),
    _A("p_exam_priv", "dinheiro", "Exame particular feito na clínica", "€", 60,
       why="Raio X ou ecografia.", kind="eur"),
    _A("p_exam_ins", "dinheiro", "Exame por convenção", "€", 30, why="Tabelas das seguradoras.", kind="eur"),
    _A("p_physio_priv", "dinheiro", "Sessão de fisioterapia particular", "€", 30, why="Preço de mercado.", kind="eur"),
    _A("p_physio_ins", "dinheiro", "Sessão de fisioterapia por convenção", "€", 16, why="Tabelas das seguradoras.", kind="eur"),
    _A("p_surg_priv", "dinheiro", "Honorários da equipa cirúrgica por cirurgia particular (hospital parceiro)", "€", 2_100,
       why="O hospital parceiro fatura o resto; a clínica fica com os honorários.", kind="eur"),
    _A("p_surg_ins", "dinheiro", "Honorários da equipa por cirurgia por convenção (hospital parceiro)", "€", 1_250,
       why="Tabelas das seguradoras.", kind="eur"),
    _A("other_revenue0", "dinheiro", "Outras especialidades (medicina dentária, cardiologia, nutrição e outras)", "€/ano", 1_450_000,
       why="Cerca de 29% da faturação; acompanha em parte a atividade de ortopedia.", kind="eur"),
    _A("fee_cons", "dinheiro", "Parte da consulta paga ao médico", "fração", 0.45,
       why="Médicos pagos por ato.", kind="pct"),
    _A("fee_exam", "dinheiro", "Parte do exame paga a técnicos e relatórios", "fração", 0.20, why="Custo por exame.", kind="pct"),
    _A("fee_physio", "dinheiro", "Parte da sessão paga ao fisioterapeuta", "fração", 0.35, why="Pagamento por sessão.", kind="pct"),
    _A("fee_surg", "dinheiro", "Parte dos honorários cirúrgicos paga à equipa", "fração", 0.70,
       why="A clínica fica com cerca de 30% pela coordenação.", kind="pct"),
    _A("fee_other", "dinheiro", "Parte das outras especialidades paga aos profissionais", "fração", 0.50,
       why="Pagamento por ato.", kind="pct"),
    _A("consumables", "dinheiro", "Consumíveis e custos de faturação", "fração da faturação", 0.04,
       why="Material clínico e comissões.", kind="pct"),
    _A("club_cost", "dinheiro", "Custo anual de cada parceria com um clube", "€/ano", 8_000,
       why="Apoio médico em jogos, rastreios e visibilidade.", kind="eur"),
    _A("tax_share", "dinheiro", "Impostos e reinvestimento corrente, em parte do EBITDA positivo", "fração", 0.25,
       why="Imposto sobre lucros e substituição de equipamento, de forma simples.", kind="pct"),
    _A("credit_floor", "dinheiro", "Caixa mínima tolerada antes de cortar investimento do plano", "€", -1_000_000,
       why="Uma linha de crédito de curto prazo; abaixo disto a clínica trava o investimento opcional.", kind="eur"),

    # ------------------------------------------------------------------ new clinic
    _A("clinic_delay", "clinica", "Tempo até abrir uma nova clínica", "meses", 12, 9, 18,
       why="Encontrar espaço, licenciar e fazer obras.",
       measure="Levantamento de espaços disponíveis e prazos de licenciamento.", short="o tempo para abrir a nova clínica", kind="months"),
    _A("clinic_ramp", "clinica", "Tempo até a nova clínica estar cheia", "meses", 18, 12, 24,
       why="A notoriedade local e as agendas dos médicos crescem devagar.",
       measure="Comparar com a curva de arranque das unidades anteriores.", short="o arranque da nova clínica", kind="months"),
    _A("clinic_capex", "clinica", "Investimento na nova clínica", "€", 800_000, 600_000, 1_200_000,
       why="Obras, raio X, ecografia e mobiliário clínico.",
       measure="Orçamentos de obra e de equipamento.", short="o custo da nova clínica", kind="eur"),
    _A("clinic_opex", "clinica", "Custos fixos anuais da nova clínica (sem receção nem médicos)", "€/ano", 260_000,
       why="Renda, enfermagem e apoio administrativo, limpeza e energia.", kind="eur"),
    _A("clinic_rooms", "clinica", "Gabinetes da nova clínica, em médicos a tempo inteiro", "ETI", 4.0,
       why="Uma unidade de média dimensão.", kind="dec"),
    _A("clinic_doctors", "clinica", "Médicos contratados para a nova clínica", "ETI", 3.5,
       why="Contratados durante as obras.", kind="dec"),
    _A("clinic_fd", "clinica", "Receção da nova clínica", "ETI", 2.0, why="Dois turnos.", kind="dec"),
    _A("clinic_demand", "clinica", "Nova procura que a clínica traz quando está madura", "fração da atual", 0.30, 0.15, 0.45,
       why="Nova área de influência; depende muito da localização.",
       measure="Estudo de localização: população, concorrência e acessos.", short="a procura que a nova clínica traz", kind="pct"),

    # ------------------------------------------------------------------ hospital
    _A("hosp_build", "hospital", "Licenciamento e obra do hospital", "meses", 36, 24, 48,
       why="Licenciamento hospitalar e obra num edifício arrendado.",
       measure="Conversa prévia com a entidade licenciadora e com empreiteiros.", short="o tempo de licenciamento e obra", kind="months"),
    _A("hosp_ramp", "hospital", "Tempo até o hospital funcionar a pleno", "meses", 18, 12, 24,
       why="Equipas, circuitos e acordos com seguradoras levam tempo.",
       measure="Comparar com o arranque de hospitais privados pequenos abertos nos últimos anos.", short="o arranque do hospital", kind="months"),
    _A("hosp_capex_base", "hospital", "Investimento base no hospital (edifício arrendado)", "€", 1_000_000,
       why="Adaptação do edifício, esterilização, farmácia e sistemas.", kind="eur"),
    _A("hosp_capex_or", "hospital", "Investimento por bloco operatório", "€", 1_400_000,
       why="Obra limpa, equipamento de anestesia, mesa e intensificador de imagem.", kind="eur"),
    _A("hosp_capex_bed", "hospital", "Investimento por cama", "€", 50_000,
       why="Quarto, cama e monitorização.", kind="eur"),
    _A("hosp_overrun", "hospital", "Derrapagem do investimento", "vezes", 1.05, 0.9, 1.5,
       why="Obras de saúde derrapam muitas vezes; raramente saem mais baratas.",
       measure="Orçamento detalhado e comparação com obras semelhantes.", short="a derrapagem da obra", kind="x"),
    _A("hosp_opex_base", "hospital", "Custos fixos anuais base do hospital", "€/ano", 700_000,
       why="Renda, direção, farmácia, manutenção e limpeza.", kind="eur"),
    _A("hosp_opex_or", "hospital", "Custos fixos anuais por bloco operatório", "€/ano", 600_000,
       why="Enfermagem de bloco, auxiliares e esterilização.", kind="eur"),
    _A("hosp_opex_bed", "hospital", "Custos fixos anuais por cama", "€/ano", 30_000,
       why="Enfermagem de internamento, 24 horas por dia.", kind="eur"),
    _A("or_capacity", "hospital", "Cirurgias por bloco operatório por mês", "cirurgias/mês", 90,
       why="Cerca de quatro a cinco cirurgias por dia útil.", kind="int"),
    _A("bed_capacity", "hospital", "Cirurgias por cama por mês", "cirurgias/mês", 20.4,
       why="Metade das cirurgias precisa de internamento de cerca de 2,5 dias, com 85% de ocupação.", kind="dec"),
    _A("p_hosp_priv", "hospital", "Episódio cirúrgico particular no hospital próprio", "€", 7_500,
       why="Bloco, internamento, material e honorários.", kind="eur"),
    _A("p_hosp_ins", "hospital", "Episódio cirúrgico por convenção no hospital próprio", "€", 4_800,
       why="Tabelas das seguradoras.", kind="eur"),
    _A("hosp_var", "hospital", "Implantes, consumíveis e outros custos variáveis do episódio", "fração", 0.33,
       why="Próteses e material de osteossíntese pesam muito.", kind="pct"),
    _A("p_ext", "hospital", "Receita por cirurgia de cirurgiões externos (bloco e internamento)", "€", 3_800,
       why="O cirurgião externo fatura os seus honorários; o hospital fatura o resto.", kind="eur"),
    _A("ext_share", "hospital", "Procura cirúrgica externa, em parte da capacidade do hospital", "fração", 0.40, 0.15, 0.70,
       why="Cirurgiões sem bloco próprio e seguradoras podem encher parte do hospital, ou não.",
       measure="Sondar cirurgiões independentes e seguradoras sobre o uso de um bloco próprio.", short="a procura cirúrgica externa", kind="pct"),
    _A("ext_delay", "hospital", "Tempo até a procura externa chegar", "meses", 24, 12, 36,
       why="Cirurgiões externos só mudam quando o hospital provou que funciona.",
       measure="Cartas de intenção de cirurgiões antes de decidir.", short="o tempo até chegarem cirurgiões de fora", kind="months"),
    _A("hosp_retention", "hospital", "Mais doentes operados connosco quando há hospital próprio", "fração", 0.15, 0.0, 0.30,
       why="Com bloco próprio, menos doentes vão operar-se a outro lado.",
       measure="Registar quantos doentes propostos para cirurgia operam noutro sítio, e porquê.", short="quantos doentes passam a operar-se connosco", kind="pct"),
    _A("hosp_notoriety", "hospital", "Procura extra que o hospital traz às clínicas", "fração da atual", 0.05, 0.0, 0.12,
       why="Um hospital dá visibilidade à marca.",
       measure="Perguntar 'como nos conheceu?' e acompanhar a procura das clínicas depois da abertura.", short="a visibilidade que o hospital dá", kind="pct"),
    _A("amortisation", "hospital", "Prazo de pagamento da dívida do hospital", "meses", 180,
       why="Empréstimo a 15 anos, a começar quando o hospital abre.", kind="months"),
]


BY_KEY: dict[str, Assumption] = {a.key: a for a in ASSUMPTIONS}
assert len(BY_KEY) == len(ASSUMPTIONS), "duplicate assumption keys"


def value(key: str) -> float:
    return BY_KEY[key].value


def uncertain() -> list[Assumption]:
    return [a for a in ASSUMPTIONS if a.uncertain]


# ---------------------------------------------------------------------------
# Outside forces: not controlled by the clinic. Defaults describe the
# "Continuar como está" world; each can be changed in "E se o mundo mudar?".
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Force:
    key: str
    label: str
    unit: str
    value: float
    low: float
    high: float
    step: float
    why: str
    kind: str = "pct"


FORCES: list[Force] = [
    Force("demand_growth", "Crescimento da procura na região", "por ano", 0.01, -0.02, 0.04, 0.005,
          "População a envelhecer e mais gente a fazer desporto."),
    Force("ins_price_trend", "Evolução dos preços pagos pelas seguradoras", "por ano, em termos reais", -0.01, -0.04, 0.01, 0.005,
          "As seguradoras pressionam os preços das tabelas."),
    Force("comp_extra", "Pressão extra dos grandes grupos hospitalares privados até 2036", "procura perdida", 0.0, 0.0, 0.20, 0.05,
          "Grandes grupos a abrir unidades e a baixar preços na área."),
    Force("labour", "Mercado de cirurgiões (1 = normal, mais alto = mais difícil)", "índice", 1.0, 0.7, 1.6, 0.1,
          "Quanto mais difícil, mais demora a contratar e mais médicos saem.", kind="x"),
    Force("interest", "Taxa de juro da dívida", "por ano", 0.045, 0.02, 0.08, 0.005,
          "Custo do empréstimo para o hospital."),
]

FORCE_BY_KEY: dict[str, Force] = {f.key: f for f in FORCES}


def default_world() -> dict[str, float]:
    return {f.key: f.value for f in FORCES}
