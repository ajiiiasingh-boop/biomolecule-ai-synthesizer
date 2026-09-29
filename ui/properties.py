"""Tab 3 - Original vs Modified Property Comparison (port of PropertyComparison.tsx) + Plotly/NumPy charts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .components import esc, show
from .icons import icon
from .theme import axis_style, plotly_layout

METRICS = [
    ("molecularWeight", "Molecular Weight", "MW", "scale",
     "Changes directly with mass of cleaved and substituted functional groups."),
    ("ionizationEnergy", "Ionization Energy (IA)", "IA", "zap",
     "Shift in outer valence orbital shielding, inductive effect (+I/-I), and lone-pair availability."),
    ("electronegativity", "Electronegativity", "EN", "compass",
     "Net electron pull of terminal heteroatoms influencing polar character."),
    ("dipoleMoment", "Dipole Moment (μ)", "μ", "activity",
     "Vector sum of bond dipoles across the carbon skeleton and ionic salt head."),
    ("enthalpyDeltaH", "Enthalpy of Formation (ΔH)", "ΔH", "flame",
     "Thermodynamic heat release/absorption during bond cleavage and reconstruction."),
    ("bondAngle", "Bond Angle (C-X)", "θ", "ruler",
     "Hybridization shift between sp³ (109.5° tetrahedral) and sp² (120° trigonal planar resonance)."),
    ("bondLength", "Bond Length", "d", "ruler",
     "Covalence vs. resonance stabilization (single bond ~1.43 Å vs. resonance carboxylate ~1.27 Å)."),
]


SHORT = {"molecularWeight": "Mol. Weight", "ionizationEnergy": "Ionization", "electronegativity": "Electroneg.",
         "dipoleMoment": "Dipole", "enthalpyDeltaH": "Enthalpy", "bondAngle": "Bond Angle", "bondLength": "Bond Length"}


def comparison_frame(props: dict) -> pd.DataFrame:
    """One tidy pandas table with original, modified, absolute and % change for every metric."""
    rows = []
    for mid, name, sym, _ic, _reason in METRICS:
        m = props[mid]
        delta = round(m["modified"] - m["original"], 2)
        pct = (delta / abs(m["original"]) * 100) if m["original"] else 0.0
        rows.append({"id": mid, "Parameter": name, "Symbol": sym, "Unit": m["unit"], "Original": m["original"],
                     "Modified": m["modified"], "Delta": delta, "% Change": round(pct, 1)})
    return pd.DataFrame(rows)


def render(props: dict, original_name: str, modified_name: str) -> None:
    ss = st.session_state
    df = comparison_frame(props)

    with st.container(key="card_props"):
        show(f"""
        <div class="bc-row" style="align-items:flex-start">
          <div style="flex:1;min-width:280px">
            <div class="bc-eyebrow">Advanced Physicochemical Analysis</div>
            <div class="bc-h2">Original vs. Modified Molecule Property Matrix</div>
            <div class="bc-muted">Tracking changes in Molecular Weight, Ionization Energy (IA), Electronegativity, Dipole Moment,
              Enthalpy (ΔH), and Bio-Clay Intercalation.</div>
          </div>
          <div style="display:flex;gap:1rem;font-size:.78rem;align-items:center">
            <span style="display:flex;align-items:center;gap:.35rem"><span style="width:11px;height:11px;border-radius:99px;background:#94a3b8"></span>Original Precursor</span>
            <span style="display:flex;align-items:center;gap:.35rem;font-weight:700;color:var(--accent-text)"><span style="width:11px;height:11px;border-radius:99px;background:#db2777"></span>Modified Bio-Clay Derivative</span>
          </div>
        </div><div class="bc-divider"></div>
        """)

        left, right = st.columns([5, 7], gap="medium")
        current = next(m for m in METRICS if m[0] == ss.chip_metric)
        row = df[df.id == current[0]].iloc[0]

        with left:
            with st.container(key="inner_chart"):
                show(f"""<div class="bc-row"><span class="bc-eyebrow">Visual Property Differential</span>
                     <span class="mono" style="font-size:.72rem;color:var(--slate)">Unit: {esc(row.Unit)}</span></div>
                     <div style="font-weight:800;font-size:1rem;margin-top:.2rem">{esc(current[1])}</div>""")
                fig = go.Figure(go.Bar(
                    y=[f"Original: {original_name.split(' ')[0]}", "Modified Bio-Clay Product"],
                    x=[abs(row.Original), abs(row.Modified)],
                    text=[f"{row.Original} {row.Unit}", f"{row.Modified} {row.Unit}"],
                    textposition="outside", orientation="h", marker_color=["#94a3b8", "#db2777"],
                    marker_line_width=0, width=0.55, hovertemplate="%{text}<extra></extra>"))
                fig.update_layout(**plotly_layout(height=190, margin=dict(l=10, r=30, t=10, b=10), showlegend=False))
                fig.update_xaxes(visible=False, range=[0, max(abs(row.Original), abs(row.Modified), 1) * 1.35])
                fig.update_yaxes(autorange="reversed", **axis_style())
                st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key="cmp_bar")
                show(f'<div class="bc-soft"><b style="color:var(--heading)">Chemical Reason: </b>{esc(current[4])}</div>')
                st.radio("Metric", [m[0] for m in METRICS], key="chip_metric", horizontal=True,
                         format_func=SHORT.get,
                         label_visibility="collapsed")

        with right:
            body = ""
            for mid, name, _sym, ic, _r in METRICS:
                r = df[df.id == mid].iloc[0]
                kind = "zero" if r.Delta == 0 else ("up" if r.Delta > 0 else "down")
                arrow = icon("minus" if kind == "zero" else kind, 12)
                sign = f"+{r.Delta:g}" if r.Delta > 0 else f"{r.Delta:g}"
                body += (f'<tr class="{"active" if mid == ss.chip_metric else ""}"><td><span style="display:flex;gap:.4rem;align-items:center;font-weight:600">'
                         f'{icon(ic, 14, "#db2777")}{esc(name)}</span></td><td class="orig">{r.Original:g} {esc(r.Unit)}</td>'
                         f'<td class="mod">{r.Modified:g} {esc(r.Unit)}</td><td><span class="bc-delta {kind}">{arrow}{sign}</span></td></tr>')
            body += (f'<tr><td><span style="display:flex;gap:.4rem;align-items:center;font-weight:600">{icon("droplet", 14, "#db2777")}Solubility / Hydration</span></td>'
                     f'<td style="color:var(--slate)">{esc(props["solubility"]["original"])}</td>'
                     f'<td colspan="2" style="color:var(--accent-text);font-weight:700">{esc(props["solubility"]["modified"])}</td></tr>')
            body += (f'<tr><td><span style="display:flex;gap:.4rem;align-items:center;font-weight:600">{icon("layers", 14, "#9333ea")}Bio-Clay Binding</span></td>'
                     f'<td style="color:var(--slate)">{esc(props["bioClayBinding"]["original"])}</td>'
                     f'<td colspan="2" style="color:var(--accent-text);font-weight:700">{esc(props["bioClayBinding"]["modified"])}</td></tr>')
            show(f'<table class="bc-table"><thead><tr><th>Parameter</th><th>Original</th><th>Modified Derivative</th>'
                 f'<th>Delta Shift</th></tr></thead><tbody>{body}</tbody></table>')

    # ------------------------------------------------ extra analysis card (NumPy + Plotly + Pandas)
    with st.container(key="card_props_extra"):
        show(f"""<div class="bc-eyebrow">Computational Thinking Extension · NumPy · Pandas · Plotly</div>
             <div class="bc-h2">Property Fingerprint of the Modification</div>
             <div class="bc-muted">Each property is scaled with NumPy to its own range so different units (g/mol, eV, Debye…)
             can be compared on one radar chart. The bar chart shows the percentage change of every property.</div>
             <div class="bc-divider"></div>""")
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            orig = df.Original.to_numpy(dtype=float)
            mod = df.Modified.to_numpy(dtype=float)
            both = np.abs(np.vstack([orig, mod]))
            scale = both.max(axis=0)
            scale[scale == 0] = 1.0
            o_norm, m_norm = np.abs(orig) / scale, np.abs(mod) / scale
            labels = list(df.Symbol) + [df.Symbol.iloc[0]]
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=list(o_norm) + [o_norm[0]], theta=labels, name="Original",
                                          line=dict(color="#94a3b8", width=2), fill="toself", fillcolor="rgba(148,163,184,.18)"))
            fig.add_trace(go.Scatterpolar(r=list(m_norm) + [m_norm[0]], theta=labels, name="Modified",
                                          line=dict(color="#db2777", width=2.5), fill="toself", fillcolor="rgba(219,39,119,.18)"))
            fig.update_layout(**plotly_layout(height=340, polar=dict(
                bgcolor="rgba(0,0,0,0)", radialaxis=dict(range=[0, 1.05], showticklabels=False, gridcolor="rgba(236,72,153,.2)"),
                angularaxis=dict(gridcolor="rgba(236,72,153,.2)"))))
            st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, key="radar")
        with c2:
            pct = df["% Change"].to_numpy(dtype=float)
            cap = 200.0  # very large jumps (e.g. dipole 0.2 → 5.35 D = +2575 %) are capped so small ones stay visible
            shown = np.clip(pct, -cap, cap)
            colors = np.where(pct > 0, "#10b981", np.where(pct < 0, "#f43f5e", "#94a3b8"))
            fig = go.Figure(go.Bar(x=shown, y=df.Parameter, orientation="h", marker_color=colors,
                                   text=[f"{v:+.1f}%" + (" ▸" if abs(v) > cap else "") for v in pct], textposition="outside",
                                   customdata=pct, hovertemplate="%{y}: %{customdata:.1f}%<extra></extra>"))
            fig.update_layout(**plotly_layout(height=340, showlegend=False, title=dict(text="% change after modification (bars capped at ±200 %)", font=dict(size=13))))
            fig.update_xaxes(range=[-cap * 1.7, cap * 1.7], ticksuffix="%", **axis_style())
            fig.update_yaxes(autorange="reversed", **axis_style())
            st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, key="pct_bar")
            st.caption("Radar uses magnitudes |value| ÷ max(|original|, |modified|) so every axis runs 0 → 1.")

        out = df.drop(columns=["id"]).astype(object)
        out.loc[len(out)] = ["Solubility / Hydration", "-", "-", props["solubility"]["original"], props["solubility"]["modified"], "", ""]
        out.loc[len(out)] = ["Bio-Clay Binding", "-", "-", props["bioClayBinding"]["original"], props["bioClayBinding"]["modified"], "", ""]
        st.download_button("⬇  Download comparison table (.csv)", out.to_csv(index=False).encode("utf-8"),
                           file_name=f"property_comparison_{modified_name[:30].replace(' ', '_')}.csv",
                           mime="text/csv", key="dl_csv")
