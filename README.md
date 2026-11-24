# Simulador de voo da clínica

Um simulador de gestão (*management flight simulator*, no sentido de John Sterman, *Business Dynamics*, 2000) de um
grupo privado de clínicas de ortopedia e medicina desportiva. Serve para experimentar decisões, ver o que acontece
ao longo de dez anos e perceber atrasos, ciclos de realimentação e efeitos secundários antes de gastar dinheiro a
sério.

**Os números são ilustrativos.** São hipóteses plausíveis para um grupo independente com cerca de 5 M€ de faturação
por ano em Portugal, não dados reais de nenhuma clínica. Todos estão por calibrar com dados reais.

## O que tem

| Página | Para quê |
|---|---|
| Entrada | Visita guiada de dois minutos, ou exploração livre |
| O mapa | O mapa causal da clínica e os oito ciclos que fazem crescer ou travar |
| Pilotar | As alavancas, quatro números, um gráfico com o intervalo provável e até três leituras automáticas |
| Onde rende cada euro | Um pouco mais de cada alavanca sobre o plano atual: retorno por euro, quando se paga e em quantos futuros |
| Comparar cenários | Cinco cenários e o seu plano lado a lado, e se a ordem das decisões conta |
| Como funciona | Fronteira do modelo, estrutura, pressupostos, contas e o que vale a pena medir primeiro |

## Como correr

Precisa de Python 3.12 ou mais recente (testado com 3.14).

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt
```

```bash
.venv/bin/streamlit run app.py
```

Para correr os testes:

```bash
.venv/bin/python -m pytest -q
```

## Como atualizar

- **Pressupostos.** Todos os números estão num só sítio, `core/assumptions.py`: unidade, descrição, valor central,
  intervalo e justificação. Para calibrar com dados reais, mude o valor central e estreite o intervalo.
- **Ponto de partida.** O grupo "A clínica hoje" em `core/assumptions.py` define o presente (novos doentes, espera,
  ocupação, equipas, margem). Cada futuro simulado começa em repouso a partir daí.
- **Cenários.** Os cenários de comparação estão em `core/scenarios.py`.
- **Mapa.** Nós, setas e ciclos estão em `core/structure.py`; cada seta corresponde a um termo das equações em
  `core/model.py`.
- **Leituras automáticas.** As frases são regras em `core/insights.py`. Só disparam quando os números as sustentam, e
  só afirmam uma direção quando pelo menos 8 em cada 10 futuros simulados concordam.
- Depois de qualquer mudança, corra os testes. Eles verificam limites físicos, conservação de doentes, calibração,
  condições extremas, o passo de integração, a reprodutibilidade, a velocidade e o texto.

## Estrutura

```
app.py                 navegação, tema e visita guiada
core/                  modelo e análise (sem Streamlit)
  assumptions.py       todos os pressupostos, com unidade, intervalo e justificação
  model.py             stocks, fluxos e equações, vetorizados sobre futuros simulados
  scenarios.py         plano de partida, cenários e custos das alavancas
  analysis.py          onde rende cada euro, ordem das decisões, o que medir primeiro
  insights.py          frases geradas por regras
  structure.py         mapa causal e ciclos
  formatting.py        números, datas e frequências em português europeu
ui/                    tema, gráficos, mapa, estado e páginas
tests/                 testes (pytest)
```

## Publicar

A app corre no Streamlit Community Cloud a partir deste repositório: ramo `main`, ficheiro principal `app.py`.
Não usa base de dados, APIs externas nem modelos de linguagem.

---

Protótipo ilustrativo preparado por André Pereira. Inspirado na dinâmica de sistemas (John Sterman, *Business
Dynamics*, 2000).
