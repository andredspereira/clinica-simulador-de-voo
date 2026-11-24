"""Como funciona: the model for a technical reader. Technical vocabulary lives here only."""

import pandas as pd
import streamlit as st

from core import analysis as AN
from core import assumptions as A
from core import formatting as F
from core import model as M
from core import scenarios as S
from core import structure as ST
from ui import state as U
from ui import theme as T

U.init()
st.title("Como funciona")
T.lead("Um modelo de dinâmica de sistemas: stocks, fluxos, atrasos e limites não lineares, integrados mês a mês, "
       "corridos em centenas de futuros simulados. Tudo o que está aqui é ilustrativo e está por calibrar com dados "
       "reais.")

tabs = st.tabs(["Fronteira", "Estrutura", "Pressupostos", "Contas", "O que medir primeiro"])

# ---------------------------------------------------------------- boundary
with tabs[0]:
    c1, c2, c3 = st.columns(3, gap="medium")
    c1.markdown("""**Dentro do modelo (endógeno)**
- Notoriedade, pedidos de marcação e canais (telefone, site, seguradoras e clubes)
- Chamadas atendidas, devolução, marcação online e doentes que desistem
- Lista de espera, agenda médica, faltas e consultas de seguimento
- Médicos: recrutamento, adaptação, saídas e gabinetes
- Cansaço da equipa, satisfação e reputação
- Doentes em acompanhamento, exames e fisioterapia
- Lista cirúrgica, hospitais parceiros e bloco próprio, com procura externa
- Maturidade digital, incidentes graves e o seu custo
- Resposta da concorrência ao nosso crescimento
- Faturação, custos, EBITDA, caixa, dívida e o travão de caixa""")
    c2.markdown("""**Dado de fora (exógeno)**
- Crescimento da procura na região
- Evolução real dos preços das seguradoras
- Pressão extra dos grandes grupos hospitalares privados
- Mercado de cirurgiões
- Taxa de juro da dívida

Cada uma pode mudar em *E se o mundo mudar?*, na página Pilotar.""")
    c3.markdown("""**Deixado de fora**
- Sazonalidade e dias da semana
- Capacidade de fisioterapia e de exames (assume-se que acompanha a procura)
- Ressonância magnética (feita por um parceiro externo)
- Detalhe de cada especialidade além da ortopedia
- Escolha concreta de localização da nova clínica
- Detalhe fiscal, dividendos e amortizações contabilísticas
- Inflação: tudo em euros constantes de 2027
- Financiamento além da dívida do hospital: caixa negativa lê-se como capital a pôr pelos sócios""")

# ---------------------------------------------------------------- structure
with tabs[1]:
    st.markdown("#### Stocks e fluxos")
    stocks = [
        ("Notoriedade", "pessoas", "marketing (com atraso), parcerias, boca a boca, rede dos médicos, novas unidades",
         "esquecimento (meia-vida de 6 a 18 meses)"),
        ("Lista de espera para primeira consulta", "pessoas", "pedidos marcados (depois de perdas no acesso e de quem "
         "não aceita a espera)", "primeiras consultas, limitadas pela agenda livre"),
        ("Doentes em acompanhamento", "pessoas", "novos doentes que ficam em seguimento e operados", "altas"),
        ("Lista de espera cirúrgica", "pessoas", "propostas de cirurgia, menos quem vai operar-se a outro lado",
         "cirurgias, limitadas por cirurgiões e por tempo de bloco"),
        ("Reputação", "0 a 5", "sobe devagar para o nível que a satisfação justifica", "cai depressa; incidentes"),
        ("Médicos em recrutamento, em adaptação e plenos", "ETI", "contratações (substituição e expansão)",
         "chegada, adaptação e saídas (que sobem com o cansaço)"),
        ("Equipa de receção", "ETI", "contratação até ao alvo do plano", "ajuste ao alvo (1 a 3 meses)"),
        ("Cansaço da equipa", "0 a 1", "ocupação acima de 85%", "recuperação lenta"),
        ("Maturidade digital e projetos em curso", "0 a 1 e €", "investimento (3 a 9 meses de atraso) e manutenção",
         "desgaste de 25% por ano"),
        ("Obra do hospital, capacidade operacional e procura externa", "0 a 1, cirurgias/mês",
         "licenciamento e obra (24 a 48 meses), arranque (12 a 24)", "nada: são investimentos que ficam"),
        ("Obra e arranque da nova clínica", "0 a 1", "obra (9 a 18 meses), arranque (12 a 24)", ""),
        ("Resposta da concorrência", "índice", "o nosso crescimento e descidas de preço", "ajuste em 18 meses"),
        ("Preço percebido", "índice", "o preço do plano, com 6 meses de atraso", ""),
        ("Memória de incidente", "estrelas", "incidentes graves", "esquecimento em 18 meses"),
        ("Caixa e dívida", "€", "EBITDA e empréstimo do hospital", "investimento, juros, amortização, impostos"),
    ]
    st.dataframe(pd.DataFrame(stocks, columns=["Stock", "Unidade", "Entra", "Sai"]), hide_index=True,
                 width="stretch")
    st.markdown("#### Ciclos de realimentação")
    loops = [(lp.id, lp.name, "positivo (reforça)" if lp.kind == "reforça" else "negativo (trava)",
              " → ".join(ST.NODE_BY_ID[n].label for n in lp.path + (lp.path[0],)), lp.story) for lp in ST.LOOPS]
    st.dataframe(pd.DataFrame(loops, columns=["", "Nome", "Polaridade", "Caminho", "Em palavras"]), hide_index=True,
                 width="stretch")
    st.markdown("#### Método")
    st.markdown(f"""
- **Integração.** Euler com passo de {F.num(M.STEP, 2)} mês, de janeiro de 2027 a dezembro de 2036, reportado
  mês a mês. Um teste confirma que reduzir o passo a metade muda os resultados principais menos de 1%.
- **Equilíbrio inicial.** Cada futuro começa em repouso: o presente observável (novos doentes, espera, ocupação,
  equipas, faturação) é igual em todos, e o que não se observa (chamadas perdidas, conversão para cirurgia,
  eficácia do marketing) varia. Assim cada mudança vem de uma decisão ou de uma força de fora.
- **Limites não lineares.** A agenda dá prioridade aos seguimentos e os novos doentes usam os tempos livres, com uma
  curva de saturação suave: perto do limite, a espera sobe como numa fila. O telefone segue uma curva semelhante.
- **Incerteza.** {AN.N_FUTURES} futuros por amostragem por hipercubo latino, com distribuições triangulares
  (moda no valor central), semente fixa. Os incidentes são sorteados mês a mês (Bernoulli) nos futuros simulados;
  na corrida central entra o custo esperado. Todas as comparações usam os mesmos futuros e os mesmos sorteios
  (números aleatórios comuns), por isso as diferenças vêm do plano.
- **Regra de decisão.** Só se afirma uma direção quando pelo menos 8 em cada 10 futuros concordam; caso
  contrário, a app diz "ainda não sabemos" e aponta o pressuposto que mais pesa.
- **Onde rende cada euro.** Para cada alavanca, um incremento padrão sobre o plano atual (100 mil €, ou ligar),
  em {AN.N_LEVERAGE} futuros. Retorno por euro = 1 + ganho líquido até 2036 / custo da alavanca até 2036.
""")
    st.markdown('<div class="ck-small">Inspirado na dinâmica de sistemas (John Sterman, <i>Business Dynamics</i>, '
                '2000). Números ilustrativos.</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- assumptions
with tabs[2]:
    st.markdown('<div class="ck-small">Todos os valores são hipóteses plausíveis para um grupo independente de '
                'ortopedia desta dimensão em Portugal: <b>a calibrar com dados reais</b>. Os que têm intervalo '
                'variam entre futuros simulados (distribuição triangular).</div>', unsafe_allow_html=True)

    def show(a: A.Assumption, v: float) -> str:
        if a.kind == "eur":
            return F.eur(v)
        if a.kind == "pct":
            return F.pct(v, 1 if abs(v) < 0.1 and v != 0 else 0)
        if a.kind in ("months",):
            return f"{F.num(v, 1 if v % 1 else 0)} meses"
        if a.kind == "days":
            return F.days(v)
        if a.kind == "int":
            return F.num(v, 0)
        if a.kind == "x":
            return f"{F.num(v, 2)} vezes"
        return F.num(v, 2 if abs(v) < 10 and v % 1 else 0)

    rows = []
    for a in A.ASSUMPTIONS:
        rows.append({"Grupo": A.GROUPS[a.group], "Pressuposto": a.label, "Unidade": a.unit,
                     "Valor central": show(a, a.value),
                     "Intervalo": f"{show(a, a.low)} a {show(a, a.high)}" if a.uncertain else "fixo",
                     "Porquê": a.why})
    groups = ["Todos"] + list(A.GROUPS.values())
    g = st.selectbox("Grupo", groups, key="w_assumption_group")
    df = pd.DataFrame(rows)
    if g != "Todos":
        df = df[df["Grupo"] == g]
    st.dataframe(df, hide_index=True, width="stretch", height=480)
    st.markdown("#### Forças de fora (valores de partida)")
    st.dataframe(pd.DataFrame([{"Força": f.label, "Valor de partida": F.pct(f.value, 1) if f.kind == "pct"
                                else F.num(f.value, 2), "Porquê": f.why} for f in A.FORCES]),
                 hide_index=True, width="stretch")

# ---------------------------------------------------------------- money


@st.cache_data(show_spinner=False)
def baseline_pnl() -> dict[str, float]:
    r = AN.run_plans([S.BASELINE])[0]
    y = {k: float(r.annual_sum(k)[0, 0]) for k in ("rev", "r_cons", "r_exam", "r_phys", "r_surg", "r_other",
                                                    "var", "fixed", "lever_cost", "ebitda")}
    return y


with tabs[3]:
    st.markdown("""
| Linha | Como se calcula |
|---|---|
| Consultas | (primeiras consultas + seguimentos) × preço médio; o preço médio mistura convenções e particulares |
| Exames na clínica | 0,9 por novo doente e 0,3 por seguimento × preço médio |
| Fisioterapia | doentes em acompanhamento × parte que faz fisioterapia × sessões por percurso × preço médio |
| Cirurgia | em hospitais parceiros, os honorários da equipa; no bloco próprio, o episódio inteiro, e a receita de bloco dos cirurgiões de fora |
| Outras especialidades | valor de partida, que acompanha 60% da variação da atividade de ortopedia |
| Custos variáveis | parte paga por ato a médicos, técnicos e fisioterapeutas; implantes e consumíveis no hospital; 4% de consumíveis e faturação |
| Custos fixos | estrutura (calibrada para a margem de partida), receção, apoio por médico, marketing, parcerias, sistemas, devolução de chamadas, marcação online, contratações, nova clínica e hospital |
| EBITDA | faturação menos custos variáveis, custos fixos e custo de incidentes |
| Caixa | EBITDA menos investimento, juros, amortização da dívida e 25% do EBITDA positivo (impostos e reinvestimento corrente), mais o empréstimo recebido |
| Travão de caixa | abaixo de -1 M€ de caixa, o investimento opcional do plano (marketing, base digital, receção, contratações) é cortado aos poucos |
""")
    y = baseline_pnl()
    st.markdown("#### Continuar como está, primeiro ano (corrida central)")
    pnl = [("Faturação", y["rev"]), ("  Consultas", y["r_cons"]), ("  Exames", y["r_exam"]),
           ("  Fisioterapia", y["r_phys"]), ("  Cirurgia", y["r_surg"]), ("  Outras especialidades", y["r_other"]),
           ("Custos variáveis", -y["var"]), ("Custos fixos", -y["fixed"]), ("EBITDA", y["ebitda"])]
    st.table(pd.DataFrame([{"Linha": a, "Valor": F.eur(b), "Peso": F.pct(b / y["rev"])} for a, b in pnl]),
             hide_index=True)

# ---------------------------------------------------------------- what to measure first
with tabs[4]:
    st.markdown("#### Se medíssemos isto primeiro, a decisão ficava mais clara")
    st.markdown('<div class="ck-small">Para cada decisão, mede-se quanto cada pressuposto incerto explica da '
                'incerteza no resultado: correlação de ordem (Spearman) entre o valor sorteado e o resultado, em '
                f'{AN.N_FUTURES} futuros. O peso é a parte de ρ² no total.</div>', unsafe_allow_html=True)
    options = ["Hospital depois de arrumar a casa"] + [n for n in list(S.PRESETS)[1:]
                                                       if n != "Hospital depois de arrumar a casa"]
    if S.changed_levers(U.plan()):
        options = ["O seu plano"] + options
    c1, c2 = st.columns(2, gap="medium")
    decision = c1.selectbox("Decisão", options, key="w_measure_plan")
    outcome = c2.selectbox("Resultado", list(AN.OUTCOME_CHOICES), format_func=lambda k: AN.OUTCOME_CHOICES[k],
                           key="w_measure_outcome")
    chosen_plan = U.plan() if decision == "O seu plano" else S.PRESETS[decision]
    with st.spinner("A medir o que mais pesa..."):
        ranking = U.measure_view(U.plan_key(chosen_plan), U.world_key(), outcome)
    st.dataframe(pd.DataFrame([{"Pressuposto": r["label"], "Peso na incerteza": F.pct(r["share"]),
                                "ρ": F.num(r["rho"], 2, signed=True), "Como medir": r["measure"]}
                               for r in ranking]), hide_index=True, width="stretch")
