"""The causal map, drawn with Plotly.

Grammar: read left to right. Levers sit in the left column, outcomes in the
right column, outside forces in a band across the top, and the mechanisms in
four middle columns ordered by where they sit between decision and result.
Within each column, nodes are ordered by the average height of their
neighbours (a few barycentre sweeps), which cuts down crossings and keeps the
layout identical on every rerun.

Node type is carried by shape (lever square, outcome diamond, outside force
triangle, mechanism circle) and by its zone, never by the sign colours. Things
that accumulate get a second, thin outline. Arrows are curved, stop at the
rim of the target, and use width for strength, opacity for certainty and
colour only for the sign. A "‖" across an arrow marks a noticeable delay.
"""

from __future__ import annotations

import math
import textwrap

import numpy as np
import plotly.graph_objects as go

from core import formatting as F
from core import structure as ST
from ui.charts import FONT, rgba
from ui.theme import COLORS

X_COL = {"lever": 0.0, 1: 3.75, 2: 6.7, 3: 9.65, 4: 12.6, "outcome": 15.9}
Y_LOW, Y_HIGH = 0.45, 9.55
Y_EXTERNAL = 11.35
X_RANGE = (-1.75, 17.75)
Y_RANGE = (-0.55, 12.55)
SYMBOL = {"lever": "square", "outcome": "diamond", "external": "triangle-up", "mechanism": "circle"}
NODE_SIZE = 22
LABEL_WRAP = {"lever": 26, "outcome": 18, "mechanism": 15, "external": 14}
SWEEPS = 6
PX_X, PX_Y = 58.0, 52.0  # rough pixels per data unit at laptop width, used only for angles

KIND_STYLE = {
    "lever": {"fill": COLORS["white"], "line": COLORS["teal_muted"], "zone": rgba(COLORS["pale"], 0.45)},
    "mechanism": {"fill": COLORS["white"], "line": COLORS["mid_grey"], "zone": rgba(COLORS["softer"], 1.0)},
    "outcome": {"fill": COLORS["white"], "line": COLORS["dark_grey"], "zone": rgba(COLORS["pale"], 0.28)},
    "external": {"fill": COLORS["softer"], "line": COLORS["mid_grey"], "zone": rgba(COLORS["soft"], 0.9)},
}

SIGN_COLOUR = {1: COLORS["petrol"], -1: COLORS["orange"], 0: COLORS["mid_grey"]}
SIGN_WORD = {1: "Mais de um, mais do outro.", -1: "Mais de um, menos do outro.", 0: "Depende."}

# Whether a rise in each node is good news for the clinic (+1), bad news (-1) or neither (0).
GOOD_WHEN_UP = {"noto": 1, "comp": -1, "invest": 0, "price_avg": 0, "enq": 1, "access": 1, "digital_mat": 1,
                "wait": -1, "doctors": 1, "util": 0, "fatigue": -1, "sat": 1, "rep": 1, "follow": 1, "surg": 0,
                "hosp": 1, "seen": 1, "lost": -1, "revenue": 1, "ebitda": 1, "cash": 1, "risk": -1}


def _wrap(text: str, width: int = 15) -> str:
    return "<br>".join(textwrap.wrap(text, width=width)) or text


def _hover_wrap(text: str, width: int = 52) -> str:
    return "<br>".join(textwrap.wrap(text, width=width))


def _spread(n: int, low: float, high: float) -> list[float]:
    if n == 1:
        return [(low + high) / 2]
    step = (high - low) / (n - 1)
    return [high - i * step for i in range(n)]


def layout() -> dict[str, tuple[float, float]]:
    """Deterministic positions: fixed columns, barycentre ordering inside each column."""
    columns: list[list[str]] = [[n.id for n in ST.NODES if n.kind == "lever"]]
    for stage in (1, 2, 3, 4):
        columns.append([n.id for n in ST.NODES if n.kind == "mechanism" and n.stage == stage])
    columns.append([n.id for n in ST.NODES if n.kind == "outcome"])
    neigh: dict[str, set[str]] = {n.id: set() for n in ST.NODES}
    for lk in ST.LINKS:
        neigh[lk.source].add(lk.target)
        neigh[lk.target].add(lk.source)

    def heights() -> dict[str, float]:
        out = {}
        for col in columns:
            for nid, y in zip(col, _spread(len(col), 0.0, 1.0)):
                out[nid] = y
        return out

    order = list(range(len(columns)))
    for sweep in range(SWEEPS):
        for ci in (order if sweep % 2 == 0 else order[::-1]):
            h = heights()
            col = columns[ci]
            keyed = []
            for pos, nid in enumerate(col):
                ys = [h[m] for m in neigh[nid] if m in h and m not in col]
                keyed.append((sum(ys) / len(ys) if ys else h[nid], -pos, nid))
            keyed.sort(key=lambda t: (-t[0], t[1]))
            columns[ci] = [nid for _, _, nid in keyed]

    pos: dict[str, tuple[float, float]] = {}
    keys = ["lever", 1, 2, 3, 4, "outcome"]
    for key, col in zip(keys, columns):
        low, high = (Y_LOW, Y_HIGH) if key in ("lever", "outcome") else (Y_LOW + 0.35, Y_HIGH - 0.75)
        for nid, y in zip(col, _spread(len(col), low, high)):
            pos[nid] = (X_COL[key], y)
    externals = [n.id for n in ST.NODES if n.kind == "external"]

    def target_x(eid: str) -> float:
        xs = [pos[lk.target][0] for lk in ST.LINKS if lk.source == eid and lk.target in pos]
        return sum(xs) / len(xs) if xs else 8.0

    externals.sort(key=target_x)
    for nid, x in zip(externals, _spread(len(externals), X_COL[4], X_COL[1])[::-1]):
        pos[nid] = (x, Y_EXTERNAL)
    return pos


def _curve(p0, p1, r0: float = 0.42, r1: float = 0.55) -> tuple[np.ndarray, np.ndarray]:
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy) or 1.0
    bow = min(0.12 * length, 1.0)
    cx = (x0 + x1) / 2 - dy / length * bow
    cy = (y0 + y1) / 2 + dx / length * bow
    t = np.linspace(0.0, 1.0, 90)
    xs = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
    ys = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
    keep = (np.hypot(xs - x0, ys - y0) >= r0) & (np.hypot(xs - x1, ys - y1) >= r1)
    if keep.sum() < 4:
        keep[:] = True
    xs, ys = xs[keep], ys[keep]
    idx = np.unique(np.linspace(0, len(xs) - 1, 28).astype(int))
    return xs[idx], ys[idx]


def _delay_mark(xs: np.ndarray, ys: np.ndarray) -> dict:
    i = len(xs) // 2
    tx, ty = xs[i + 1] - xs[i - 1], ys[i + 1] - ys[i - 1]
    angle = math.degrees(math.atan2(-ty * PX_Y, tx * PX_X))
    return dict(x=xs[i], y=ys[i], text="‖", showarrow=False, textangle=angle,
                font=dict(size=15, color=COLORS["dark_grey"], family=FONT))


def _rounded(x0, y0, x1, y1, r=0.45) -> str:
    return (f"M {x0 + r},{y0} L {x1 - r},{y0} Q {x1},{y0} {x1},{y0 + r} L {x1},{y1 - r} Q {x1},{y1} {x1 - r},{y1} "
            f"L {x0 + r},{y1} Q {x0},{y1} {x0},{y1 - r} L {x0},{y0 + r} Q {x0},{y0} {x0 + r},{y0} Z")


def _zones(pos) -> tuple[list[dict], list[dict]]:
    shapes, notes = [], []
    groups: dict[str, list[tuple[float, float]]] = {}
    for n in ST.NODES:
        groups.setdefault(n.kind, []).append(pos[n.id])
    for kind, pts in groups.items():
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1 = min(xs) - 1.3, max(xs) + 1.3
        y0, y1 = min(ys) - 0.95, max(ys) + 0.55
        shapes.append(dict(type="path", path=_rounded(x0, y0, x1, y1), fillcolor=KIND_STYLE[kind]["zone"],
                           line=dict(width=0), layer="below"))
        title, plain = ST.KIND_TITLES[kind]
        notes.append(dict(x=(x0 + x1) / 2, y=y1, yshift=11, showarrow=False,
                          text=f"<b>{title}</b>  <span style='font-size:10px'>{plain}</span>",
                          font=dict(size=10.5, color=COLORS["dark_grey"], family=FONT)))
    return shapes, notes


def _node_hover(node: ST.Node) -> str:
    kind_word = {"lever": "Alavanca: o que controlamos", "outcome": "Resultado: o que nos importa",
                 "external": "Força de fora: não controlamos", "mechanism": "Como a clínica funciona"}[node.kind]
    extra = "<br><i>Acumula ao longo do tempo.</i>" if node.stock else ""
    return f"<b>{node.label}</b><br>{kind_word}<br>{_hover_wrap(node.text)}{extra}"


def _edge_hover(lk: ST.Link) -> str:
    s, t = ST.NODE_BY_ID[lk.source], ST.NODE_BY_ID[lk.target]
    delay = "<br>Com atraso." if lk.delay else ""
    return f"<b>{s.label} → {t.label}</b><br>{_hover_wrap(lk.text)}<br><i>{SIGN_WORD[lk.sign]}</i>{delay}"


def _finish(fig: go.Figure, shapes, notes, height: int) -> go.Figure:
    fig.update_layout(
        height=height, shapes=shapes, annotations=notes, showlegend=False, hovermode="closest", hoverdistance=14,
        dragmode=False, paper_bgcolor=COLORS["white"], plot_bgcolor=COLORS["white"],
        margin=dict(l=4, r=4, t=6, b=4), font=dict(family=FONT, color=COLORS["text"]),
        xaxis=dict(visible=False, range=list(X_RANGE), fixedrange=True),
        yaxis=dict(visible=False, range=list(Y_RANGE), fixedrange=True),
        hoverlabel=dict(bgcolor=COLORS["white"], bordercolor=COLORS["line"], align="left",
                        font=dict(family=FONT, size=12, color=COLORS["text"])),
    )
    return fig


def _add_nodes(fig, pos, styles: dict[str, dict]):
    """styles: node id -> {size, fill, line, width, opacity, text_colour, hover}."""
    for node in ST.NODES:
        st_ = styles[node.id]
        x, y = pos[node.id]
        if node.stock:
            fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", hoverinfo="skip",
                                     marker=dict(symbol=SYMBOL[node.kind], size=st_["size"] + 9,
                                                 color="rgba(0,0,0,0)",
                                                 line=dict(color=rgba(st_["line"], 0.55 * st_["opacity"]), width=1.3))))
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[_wrap(node.label, LABEL_WRAP[node.kind])],
            textposition="bottom center",
            textfont=dict(size=10.5, color=st_["text_colour"], family=FONT),
            marker=dict(symbol=SYMBOL[node.kind], size=st_["size"], color=st_["fill"], opacity=1.0,
                        line=dict(color=rgba(st_["line"], st_["opacity"]), width=st_["width"])),
            hoverinfo="text", hovertext=st_["hover"]))


def map_figure(loop_id: str | None = None, height: int = 760) -> go.Figure:
    pos = layout()
    shapes, notes = _zones(pos)
    fig = go.Figure()
    in_loop_links = set(ST.loop_links(ST.LOOP_BY_ID[loop_id])) if loop_id else set()
    in_loop_nodes = set(ST.LOOP_BY_ID[loop_id].path) if loop_id else set()
    for lk in ST.LINKS:
        xs, ys = _curve(pos[lk.source], pos[lk.target])
        colour = SIGN_COLOUR[lk.sign]
        opacity = 0.30 + 0.65 * lk.certainty
        width = 1.0 + 2.6 * lk.strength
        if loop_id:
            if (lk.source, lk.target) in in_loop_links:
                opacity, width = 1.0, width + 1.2
            else:
                opacity *= 0.10
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", hoverinfo="text", hovertext=_edge_hover(lk),
            line=dict(color=rgba(colour, opacity), width=width, shape="spline", smoothing=0.5),
            marker=dict(symbol="arrow", size=[0] * (len(xs) - 1) + [10 + 2 * lk.strength], angleref="previous",
                        color=rgba(colour, opacity))))
        if lk.delay and (not loop_id or (lk.source, lk.target) in in_loop_links):
            notes.append(_delay_mark(xs, ys))
    styles = {}
    for node in ST.NODES:
        ks = KIND_STYLE[node.kind]
        dim = bool(loop_id) and node.id not in in_loop_nodes
        styles[node.id] = dict(size=NODE_SIZE, fill=ks["fill"], line=ks["line"], width=2.2,
                               opacity=0.18 if dim else 1.0,
                               text_colour=COLORS["mid_grey"] if dim else COLORS["text"], hover=_node_hover(node))
        if loop_id and not dim:
            styles[node.id].update(line=COLORS["petrol"], width=3.0)
    _add_nodes(fig, pos, styles)
    return _finish(fig, shapes, notes, height)


def scenario_figure(response: dict[str, dict], changed: set[str], height: int = 760) -> go.Figure:
    """The map with a plan applied.

    The levers the plan changes are highlighted. Every other node grows or
    shrinks with its response, petrol blue for up and orange for down, faint
    grey when the futures disagree, and anything the plan never reaches fades.
    """
    pos = layout()
    shapes, notes = _zones(pos)
    reach = ST.reachable_from(changed)
    moved = {nid for nid, r in response.items() if nid in reach and abs(r["rel"]) >= 0.005}
    scale = max([min(abs(response[n]["rel"]), 1.0) for n in moved] or [1.0])
    fig = go.Figure()

    def node_style(nid: str):
        r = response.get(nid)
        if nid in changed:
            return COLORS["petrol"], 1.0, NODE_SIZE + 6, "lever"
        if r is None or nid not in moved:
            return COLORS["mid_grey"], 0.18, NODE_SIZE * 0.8, "faded"
        share = max(-1.0, min(1.0, r["rel"] / scale))
        size = NODE_SIZE * (1.0 + 0.55 * share)
        agree = max(r["up"], r["down"])
        if agree < 0.8:
            return COLORS["mid_grey"], 0.5, size, "unsure"
        colour = COLORS["petrol"] if r["rel"] > 0 else COLORS["orange"]
        return colour, 0.55 + 0.45 * (agree - 0.8) / 0.2, size, "clear"

    for lk in ST.LINKS:
        xs, ys = _curve(pos[lk.source], pos[lk.target])
        active = (lk.source in moved or lk.source in changed) and lk.target in moved
        if active:
            colour, op, _, _ = node_style(lk.target)
            op *= 0.8
            width = 2.2
        else:
            colour, op, width = COLORS["mid_grey"], 0.08, 1.0
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines+markers", hoverinfo="text" if active else "skip",
            hovertext=_edge_hover(lk), line=dict(color=rgba(colour, op), width=width, shape="spline", smoothing=0.5),
            marker=dict(symbol="arrow", size=[0] * (len(xs) - 1) + [10 if active else 6], angleref="previous",
                        color=rgba(colour, op))))
    styles = {}
    for node in ST.NODES:
        colour, op, size, state = node_style(node.id)
        r = response.get(node.id)
        if state == "lever":
            hover = f"<b>{node.label}</b><br>É isto que o plano muda."
        elif state == "faded" or r is None:
            hover = f"<b>{node.label}</b><br>O plano não chega aqui, ou quase não mexe."
        else:
            verb = "sobe" if r["rel"] > 0 else "desce"
            agree = r["up"] if r["rel"] > 0 else r["down"]
            good = GOOD_WHEN_UP.get(node.id, 0) * (1 if r["rel"] > 0 else -1)
            verdict = {1: "É bom para a clínica.", -1: "É mau para a clínica.", 0: ""}[good]
            unsure = "" if state == "clear" else "<br><i>Ainda não sabemos: os futuros não concordam.</i>"
            hover = (f"<b>{node.label}</b><br>{verb} {F.pct(abs(r['rel']))} face a continuar como está"
                     f"<br>Intervalo provável: {F.pct(r['lo'], signed=True)} a {F.pct(r['hi'], signed=True)}"
                     f"<br>{F.in_futures(agree).capitalize()} {verb}.{unsure}<br>{verdict}")
        styles[node.id] = dict(size=size, fill=rgba(colour, 0.16 if state != "faded" else 0.05), line=colour,
                               width=3.2 if state == "lever" else 2.2, opacity=op,
                               text_colour=COLORS["text"] if state != "faded" else COLORS["mid_grey"], hover=hover)
    _add_nodes(fig, pos, styles)
    return _finish(fig, shapes, notes, height)


MAP_LEGEND = (
    "<b>Como ler.</b> Da esquerda para a direita: as <b>alavancas</b> que controlamos, o que acontece por dentro da "
    "clínica, e os <b>resultados</b> que nos importam. Em cima, as forças de fora que não controlamos. "
    "Uma seta azul-petróleo quer dizer <b>mais de um, mais do outro</b>; uma seta laranja quer dizer "
    "<b>mais de um, menos do outro</b>. Quanto mais grossa, mais forte; quanto mais clara, menos certa. "
    "O sinal ‖ numa seta marca um <b>atraso</b>. Os nós com dois contornos <b>acumulam</b> ao longo do tempo, "
    "como a reputação ou a caixa. Passe o rato por cima de qualquer nó ou seta."
)

SCENARIO_LEGEND = (
    "<b>Como ler.</b> As alavancas que o plano muda têm contorno grosso. Os outros nós crescem quando o plano os "
    "faz subir e encolhem quando os faz descer: <b>azul-petróleo sobe, laranja desce</b>. Cinzento claro quer dizer "
    "que os futuros simulados não concordam. O que o plano não alcança fica esbatido. Passe o rato por cima para ver "
    "quanto muda e se isso é bom ou mau."
)
