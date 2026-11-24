"""Plotly charts with one clean light template.

No chart junk: light gridlines, lines labelled directly at their ends instead
of legends, uncertainty bands as soft fills of the line colour, events as
dotted vertical lines with short labels, pt-PT number formats. The mode bar
shows only the download button.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from core import formatting as F
from ui.theme import COLORS

FONT = "Poppins, sans-serif"
CONFIG = {"displaylogo": False, "modeBarButtons": [["toImage"]], "responsive": True,
          "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "simulador-clinica"}}
MAP_CONFIG = {**CONFIG, "scrollZoom": False}


def rgba(hex_colour: str, alpha: float) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.3f})"


def base_layout(fig: go.Figure, height: int, title: str = "", right: int = 110) -> go.Figure:
    fig.update_layout(
        height=height,
        title=dict(text=title, x=0.0, xanchor="left", y=0.98, yanchor="top",
                   font=dict(family=FONT, size=16, color=COLORS["text"])),
        font=dict(family=FONT, size=12, color=COLORS["dark_grey"]),
        paper_bgcolor=COLORS["white"], plot_bgcolor=COLORS["white"],
        margin=dict(l=8, r=right, t=52 if title else 16, b=36),
        separators=", ",
        showlegend=False,
        hovermode="x unified",
        hoverlabel=dict(bgcolor=COLORS["white"], bordercolor=COLORS["line"], font=dict(family=FONT, size=12,
                                                                                         color=COLORS["text"])),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["line"], ticks="outside", tickcolor=COLORS["line"],
                     tickfont=dict(color=COLORS["dark_grey"]), zeroline=False, fixedrange=True, automargin=True,
                     tickformat="d", dtick=2)
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["soft"], zeroline=False, linecolor=COLORS["line"],
                     tickfont=dict(color=COLORS["dark_grey"]), fixedrange=True, automargin=True)
    return fig


def _band_traces(fig, x, lo, mid, hi, colour, name, hover_fmt, row=None, col=None, show_band=True, dash="solid",
                 width=2.6):
    kw = dict(row=row, col=col) if row else {}
    if show_band:
        fig.add_trace(go.Scatter(x=x, y=hi, mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False), **kw)
        fig.add_trace(go.Scatter(x=x, y=lo, mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor=rgba(colour, 0.14), hoverinfo="skip", showlegend=False), **kw)
    text = [hover_fmt(v) for v in mid]
    fig.add_trace(go.Scatter(x=x, y=mid, mode="lines", name=name, line=dict(color=colour, width=width, dash=dash),
                             customdata=text, hovertemplate=f"{name}: %{{customdata}}<extra></extra>",
                             showlegend=False), **kw)


def line_band_chart(x, series: list[dict], title: str, hover_fmt, tick_fmt=None, events=None, height: int = 400,
                    y_title: str = "", zero_line: bool = False) -> go.Figure:
    """series: [{name, colour, lo, mid, hi, dash}] drawn in order, labelled at their right end."""
    fig = go.Figure()
    for s in series:
        _band_traces(fig, x, s["lo"], s["mid"], s["hi"], s["colour"], s["name"], hover_fmt,
                     show_band=s.get("band", True), dash=s.get("dash", "solid"), width=s.get("width", 2.6))
    base_layout(fig, height, title, right=16)
    # Direct labels just above the end of each line, inside the plot, nudged apart when they collide.
    ends = [(float(s["mid"][-1]), s) for s in series]
    ends.sort(key=lambda t: t[0])
    span = max(float(np.nanmax([np.nanmax(s["hi"]) for s in series]) - np.nanmin([np.nanmin(s["lo"]) for s in series])),
               1e-9)
    placed = []
    for y, s in ends:
        yy = y
        for p in placed:
            if abs(yy - p) < 0.07 * span:
                yy = p + 0.07 * span
        placed.append(yy)
        fig.add_annotation(x=x[-1], y=yy, xref="x", yref="y", text=f"<b>{s['name']}</b>", showarrow=False,
                           xanchor="right", yanchor="bottom", yshift=4, font=dict(color=s["colour"], size=12,
                                                                                    family=FONT),
                           bgcolor="rgba(255,255,255,0.7)")
    for ev_x, label in events or []:
        fig.add_vline(x=ev_x, line=dict(color=COLORS["mid_grey"], width=1, dash="dot"))
        fig.add_annotation(x=ev_x, y=1.0, yref="paper", text=label, showarrow=False, xanchor="left", yanchor="top",
                           xshift=4, font=dict(size=11, color=COLORS["dark_grey"], family=FONT),
                           bgcolor="rgba(255,255,255,0.85)")
    if zero_line:
        fig.add_hline(y=0, line=dict(color=COLORS["mid_grey"], width=1))
    if tick_fmt is not None:
        lo = min(float(np.nanmin(s["lo"])) for s in series)
        hi = max(float(np.nanmax(s["hi"])) for s in series)
        ticks = _nice_ticks(lo, hi)
        fig.update_yaxes(tickvals=ticks, ticktext=[tick_fmt(t) for t in ticks])
    if y_title:
        fig.update_yaxes(title=dict(text=y_title, font=dict(size=12, color=COLORS["dark_grey"])))
    return fig


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return [lo]
    raw = (hi - lo) / n
    mag = 10 ** np.floor(np.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=raw)
    start = np.floor(lo / step) * step
    ticks = list(np.arange(start, hi + step * 1.01, step))
    return [float(t) for t in ticks]


def small_panel(x, scenarios: list[dict], key: str, title: str, fmt, height: int = 300) -> go.Figure:
    """One small chart of a set of small multiples; scenarios carry a colour and {key: (lo, mid, hi)}."""
    fig = go.Figure()
    for sc in scenarios:
        lo, mid, hi = sc[key]
        _band_traces(fig, x, lo, mid, hi, sc["colour"], sc["name"], fmt, show_band=sc.get("band", False),
                     width=sc.get("width", 2.0), dash=sc.get("dash", "solid"))
    lows = min(float(np.nanmin(sc[key][1])) for sc in scenarios)
    highs = max(float(np.nanmax(sc[key][1])) for sc in scenarios)
    ticks = _nice_ticks(lows, highs, 4)
    base_layout(fig, height, "", right=12)
    fig.update_yaxes(tickvals=ticks, ticktext=[fmt(t) for t in ticks])
    fig.update_layout(margin=dict(l=8, r=12, t=34, b=30), hovermode="x unified",
                      title=dict(text=title, x=0.0, xanchor="left", y=0.97, yanchor="top",
                                 font=dict(family=FONT, size=13, color=COLORS["text"])))
    return fig


def leverage_bars(rows: list[dict], sentence) -> go.Figure:
    """Ranked horizontal bars of return per euro, with the likely range and a payback label."""
    rows = rows[::-1]  # best at the top
    labels = [f"<b>{r['label']}</b> · {F.ratio(r['ratio'])}<br><span style='font-size:10px;color:{COLORS['dark_grey']}'>"
              f"{sentence(r)}</span>" for r in rows]
    mids = [r["ratio"] for r in rows]
    lo = [max(r["ratio"] - r["ratio_lo"], 0) for r in rows]
    hi = [max(r["ratio_hi"] - r["ratio"], 0) for r in rows]
    colours = [COLORS["petrol"] if (r["share_pay"] >= 0.8) else COLORS["orange"] if r["share_pay"] <= 0.2
               else COLORS["mid_grey"] for r in rows]
    hover = [f"<b>{r['label']}</b> ({r['increment']})<br>Por cada euro voltam {F.ratio(r['ratio'])} até 2036"
             f"<br>Intervalo provável: {F.ratio(r['ratio_lo'])} a {F.ratio(r['ratio_hi'])}"
             f"<br>Custo: {F.eur(r['spend_per_year'])} por ano em média<br>Ganho líquido até 2036: "
             f"{F.eur(r['net10'], True)}<br>{sentence(r)}" for r in rows]
    fig = go.Figure(go.Bar(
        y=labels, x=mids, orientation="h", marker=dict(color=colours, line=dict(width=0)),
        error_x=dict(type="data", symmetric=False, array=hi, arrayminus=lo, color=COLORS["dark_grey"], thickness=1.2,
                     width=4),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>",
        cliponaxis=False,
    ))
    xmax = max(max(r["ratio_hi"] for r in rows) * 1.08, 1.5)
    xmin = min(min(r["ratio_lo"] for r in rows) * 1.08, 0.0)
    fig.add_vline(x=1.0, line=dict(color=COLORS["text"], width=1, dash="dot"))
    fig.add_annotation(x=1.0, y=1.0, yref="paper", text="paga o que custa", showarrow=False, xanchor="left",
                       yanchor="bottom", xshift=4, font=dict(size=11, color=COLORS["dark_grey"], family=FONT))
    base_layout(fig, max(360, 54 * len(rows) + 90), "", right=16)
    fig.update_layout(hovermode="closest", bargap=0.32, margin=dict(l=8, r=16, t=30, b=30))
    ticks = [t for t in _nice_ticks(xmin, xmax, 3) if xmin - 1e-9 <= t <= xmax + 1e-9]
    fig.update_xaxes(range=[xmin - 0.05 * (xmax - xmin), xmax], showgrid=True, gridcolor=COLORS["soft"],
                     tickvals=ticks, ticktext=[F.ratio(v) for v in ticks], zeroline=True,
                     zerolinecolor=COLORS["line"])
    fig.update_yaxes(showgrid=False)
    return fig


def payback_strip(rows: list[dict]) -> go.Figure:
    """When each lever pays back: median year and the likely range among the futures where it does."""
    rows = rows[::-1]
    fig = go.Figure()
    for r in rows:
        if np.isfinite(r["pay_year"]) and r["share_pay"] >= 0.5:
            lo, hi = r["pay_year_lo"], r["pay_year_hi"]
            fig.add_trace(go.Scatter(x=[lo, hi], y=[r["label"]] * 2, mode="lines",
                                     line=dict(color=rgba(COLORS["petrol"], 0.35), width=6), hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=[r["pay_year"]], y=[r["label"]], mode="markers",
                                     marker=dict(color=COLORS["petrol"], size=11),
                                     hovertemplate=f"{r['label']}: paga-se por volta de {int(round(r['pay_year']))}"
                                                   "<extra></extra>"))
        else:
            fig.add_trace(go.Scatter(x=[2036.6], y=[r["label"]], mode="markers+text",
                                     marker=dict(color=COLORS["orange"], size=9, symbol="x"),
                                     text=["não se paga até 2036"], textposition="middle right",
                                     textfont=dict(size=11, color=COLORS["orange"], family=FONT),
                                     hovertemplate=f"{r['label']}: não se paga até 2036 na maioria dos futuros"
                                                   "<extra></extra>"))
    base_layout(fig, max(260, 34 * len(rows) + 60), "", right=12)
    fig.update_layout(hovermode="closest", margin=dict(l=8, r=12, t=12, b=8))
    fig.update_xaxes(range=[2026.5, 2039.2], tickvals=list(range(2027, 2037)), showgrid=True, gridcolor=COLORS["soft"])
    fig.update_yaxes(showgrid=False)
    return fig
