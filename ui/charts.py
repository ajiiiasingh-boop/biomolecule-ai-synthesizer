"""
charts.py - drawing the molecule.

* 3D ball-and-stick  -> Plotly (drag to rotate, scroll to zoom, ▶ button to auto-spin)
* 2D skeletal        -> Matplotlib (textbook-style drawing, double bonds as two lines)
* Molecular graph    -> NetworkX + Matplotlib
"""

from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")  # draw off-screen (no window needed)
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from matplotlib.patches import Circle  # noqa: E402

from core.molecule_builder import ELEMENT_STYLES  # noqa: E402

BOND_COLORS = {"single": "#94a3b8", "double": "#cbd5e1", "triple": "#e2e8f0", "ionic": "#fbbf24"}


def _style(el: str) -> dict:
    return ELEMENT_STYLES.get(el, ELEMENT_STYLES["C"])


def _to_plot(a: dict) -> np.ndarray:
    """Screen coordinates (y points down) -> 3D plot coordinates (Z points up)."""
    return np.array([a["x"], a.get("z", 0), -a["y"]], dtype=float)


def _perp(v: np.ndarray) -> np.ndarray:
    ref = np.array([0.0, 0.0, 1.0]) if abs(v[2]) < 0.9 * np.linalg.norm(v) else np.array([0.0, 1.0, 0.0])
    p = np.cross(v, ref)
    n = np.linalg.norm(p)
    return p / n if n else np.array([0.0, 1.0, 0.0])


# ======================================================================================
# 3D (Plotly)
# ======================================================================================
def molecule_3d(atoms: list[dict], bonds: list[dict], selected: str | None, intercalated: bool,
                revision: int = 0, height: int = 480) -> go.Figure:
    pos = {a["id"]: _to_plot(a) for a in atoms}
    fig = go.Figure()

    # -- bio-clay LDH sheets
    if intercalated:
        for zc, text in ((125, "Bio-Clay LDH Positive Hydroxide Nanosheet [Mg₂Al(OH)₆]⁺"),
                         (-125, "Basal Gallery Spacing d₀₀₁: ~1.42 nm")):
            xs, ys = [-220, 220, 220, -220], [-70, -70, 70, 70]
            for dz in (-10, 10):
                fig.add_trace(go.Mesh3d(x=xs, y=ys, z=[zc + dz] * 4, i=[0, 0], j=[1, 2], k=[2, 3],
                                        color="#ec4899", opacity=0.28, hoverinfo="skip", showscale=False))
            fig.add_trace(go.Scatter3d(x=[-210], y=[0], z=[zc + 22], mode="text", text=[text],
                                       textfont=dict(color="#f9a8d4", size=11), hoverinfo="skip", showlegend=False))

    # -- bonds, grouped by type so each type is one trace
    segs: dict[str, list] = {"single": [], "double": [], "triple": [], "ionic": []}
    for b in bonds:
        if b["sourceId"] not in pos or b["targetId"] not in pos:
            continue
        p1, p2 = pos[b["sourceId"]], pos[b["targetId"]]
        kind = "ionic" if b.get("type") == "ionic" else {3: "triple", 2: "double"}.get(b.get("order", 1), "single")
        n = _perp(p2 - p1) * 3.5
        offsets = {"single": [0], "ionic": [0], "double": [-1, 1], "triple": [-1.6, 0, 1.6]}[kind]
        for o in offsets:
            segs[kind] += [p1 + n * o, p2 + n * o, None]
    widths = {"single": 10, "double": 6, "triple": 5, "ionic": 6}
    for kind, pts in segs.items():
        if not pts:
            continue
        xs = [p[0] if p is not None else None for p in pts]
        ys = [p[1] if p is not None else None for p in pts]
        zs = [p[2] if p is not None else None for p in pts]
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", hoverinfo="skip", showlegend=False,
                                   line=dict(color=BOND_COLORS[kind], width=widths[kind],
                                             dash="dash" if kind == "ionic" else "solid")))

    # -- selection glow
    if selected in pos:
        p = pos[selected]
        fig.add_trace(go.Scatter3d(x=[p[0]], y=[p[1]], z=[p[2]], mode="markers", hoverinfo="skip", showlegend=False,
                                   marker=dict(size=_style(next(a["element"] for a in atoms if a["id"] == selected))["radius"] * 3.0 + 18,
                                               color="rgba(236,72,153,0.35)", line=dict(color="#ec4899", width=3))))

    # -- atoms
    if atoms:
        P = np.array([pos[a["id"]] for a in atoms])
        fig.add_trace(go.Scatter3d(
            x=P[:, 0], y=P[:, 1], z=P[:, 2], mode="markers+text", showlegend=False, textposition="middle center",
            text=[a["element"] for a in atoms],
            textfont=dict(color=[_style(a["element"])["text"] for a in atoms], size=13, family="Inter, sans-serif"),
            marker=dict(size=[_style(a["element"])["radius"] * 3.0 for a in atoms],
                        color=[_style(a["element"])["hex"] for a in atoms], opacity=1.0,
                        line=dict(color="rgba(0,0,0,0.55)", width=1)),
            customdata=[[a["id"], _style(a["element"])["name"]] for a in atoms],
            hovertemplate="<b>%{customdata[1]}</b> (%{text})<br>id: %{customdata[0]}<extra></extra>",
        ))

    # -- camera + auto-spin animation frames
    eye_r, eye_z, theta0 = 1.35, 0.45, math.radians(-65)
    eye = dict(x=eye_r * math.cos(theta0), y=eye_r * math.sin(theta0), z=eye_z)
    axis = dict(visible=False, showbackground=False, showgrid=False, zeroline=False)
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)", showlegend=False,
        uirevision=f"cam{revision}",
        scene=dict(xaxis=axis, yaxis=axis, zaxis=axis, bgcolor="rgba(0,0,0,0)", aspectmode="data",
                   camera=dict(eye=eye, up=dict(x=0, y=0, z=1)), dragmode="orbit"),
        updatemenus=[dict(type="buttons", showactive=False, x=0.99, y=0.02, xanchor="right", yanchor="bottom",
                          bgcolor="rgba(131,24,67,0.75)", bordercolor="#ec4899", font=dict(color="#fce7f3", size=11),
                          direction="left", pad=dict(r=4, t=4),
                          buttons=[dict(label="⟳ Auto-Spin", method="animate",
                                        args=[None, dict(frame=dict(duration=45, redraw=True), transition=dict(duration=0),
                                                         fromcurrent=True, mode="immediate")]),
                                   dict(label="⏸ Stop", method="animate",
                                        args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")])])],
    )
    frames = []
    for k in range(72):
        t = theta0 + 2 * math.pi * k / 72
        frames.append(go.Frame(layout=dict(scene_camera=dict(eye=dict(x=eye_r * math.cos(t), y=eye_r * math.sin(t), z=eye_z)))))
    fig.frames = frames
    return fig


# ======================================================================================
# 2D (Matplotlib)
# ======================================================================================
def molecule_2d(atoms: list[dict], bonds: list[dict], selected: str | None, intercalated: bool):
    fig, ax = plt.subplots(figsize=(10, 5.4), dpi=110)
    fig.patch.set_alpha(0)
    ax.set_facecolor("#0b1020")

    if atoms:
        xs = [a["x"] for a in atoms]
        ys = [a["y"] for a in atoms]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        half_w = max((max(xs) - min(xs)) / 2 + 70, 230)
        half_h = max((max(ys) - min(ys)) / 2 + 60, half_w * 0.54)
        half_w = max(half_w, half_h / 0.54)
    else:
        cx = cy = 0
        half_w, half_h = 260, 140
    if intercalated:
        half_h = max(half_h, 160)
    ax.set_xlim(cx - half_w, cx + half_w)
    ax.set_ylim(cy + half_h, cy - half_h)  # y grows downwards, like the website canvas
    ax.set_aspect("equal")
    ax.axis("off")

    # dotted pink background grid
    gx = np.arange(cx - half_w, cx + half_w, 24)
    gy = np.arange(cy - half_h, cy + half_h, 24)
    GX, GY = np.meshgrid(gx, gy)
    ax.scatter(GX.ravel(), GY.ravel(), s=2, color="#ec4899", alpha=0.18, zorder=0)

    if intercalated:
        for yc, txt in ((cy - half_h + 22, "Bio-Clay LDH Nanosheet [Mg₂Al(OH)₆]⁺"), (cy + half_h - 22, "Basal Gallery Spacing d₀₀₁ ≈ 1.42 nm")):
            ax.add_patch(matplotlib.patches.FancyBboxPatch((cx - half_w + 20, yc - 12), 2 * half_w - 40, 24,
                                                           boxstyle="round,pad=2,rounding_size=8", fc=(0.93, 0.28, 0.6, 0.22),
                                                           ec="#db2777", lw=1.5, zorder=1))
            ax.text(cx - half_w + 34, yc, txt, color="#f9a8d4", fontsize=9, fontweight="bold", va="center", zorder=2)

    pos = {a["id"]: np.array([a["x"], a["y"]], dtype=float) for a in atoms}
    for b in bonds:
        if b["sourceId"] not in pos or b["targetId"] not in pos:
            continue
        p1, p2 = pos[b["sourceId"]], pos[b["targetId"]]
        v = p2 - p1
        L = np.linalg.norm(v)
        if L == 0:
            continue
        nrm = np.array([-v[1], v[0]]) / L * 4.5
        if b.get("type") == "ionic":
            ax.plot(*zip(p1, p2), color="#fbbf24", lw=2.5, ls=(0, (3, 3)), zorder=2, solid_capstyle="round")
            continue
        order = b.get("order", 1)
        offs = [0] if order == 1 else ([-1, 1] if order == 2 else [-1.6, 0, 1.6])
        for o in offs:
            q1, q2 = p1 + nrm * o, p2 + nrm * o
            ax.plot([q1[0], q2[0]], [q1[1], q2[1]], color="#ec4899", lw=3 if order == 1 else 2.2, zorder=2,
                    solid_capstyle="round")

    for a in atoms:
        s = _style(a["element"])
        r = 16 if a["element"] != "H" else 12
        if a["id"] == selected:
            ax.add_patch(Circle((a["x"], a["y"]), r + 7, fc=(0.93, 0.28, 0.6, 0.35), ec="#f472b6", lw=2.5, zorder=3))
        ax.add_patch(Circle((a["x"], a["y"]), r, fc=s["hex"], ec=(0, 0, 0, 0.5), lw=1.2, zorder=4))
        ax.text(a["x"], a["y"], a["element"], color=s["text"], ha="center", va="center", fontsize=9,
                fontweight="bold", zorder=5)
    fig.tight_layout(pad=0.2)
    return fig


# ======================================================================================
# Molecular graph (NetworkX + Matplotlib)
# ======================================================================================
def graph_figure(g: nx.Graph, atoms: list[dict], dark: bool):
    fig, ax = plt.subplots(figsize=(7.5, 3.6), dpi=110)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    ax.axis("off")
    if len(g) == 0:
        return fig
    layout = nx.kamada_kawai_layout(g) if len(g) > 2 else nx.spring_layout(g, seed=3)
    el = nx.get_node_attributes(g, "element")
    colors = [_style(el[n])["hex"] for n in g.nodes]
    sizes = [520 if el[n] != "H" else 260 for n in g.nodes]
    widths = [1.5 + 1.2 * (d.get("order", 1) - 1) for _, _, d in g.edges(data=True)]
    styles = ["dashed" if d.get("type") == "ionic" else "solid" for _, _, d in g.edges(data=True)]
    nx.draw_networkx_edges(g, layout, ax=ax, width=widths, style=styles, edge_color="#ec4899", alpha=0.8)
    nx.draw_networkx_nodes(g, layout, ax=ax, node_color=colors, node_size=sizes, edgecolors="#831843", linewidths=1)
    nx.draw_networkx_labels(g, layout, labels=el, ax=ax, font_size=8, font_weight="bold",
                            font_color="#0f172a" if not dark else "#fdf2f8")
    fig.tight_layout(pad=0.2)
    return fig
