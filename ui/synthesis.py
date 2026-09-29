"""Tab 2 - AI Synthesis Protocol & Feasibility (port of AiSynthesisProtocol.tsx) + SciPy kinetics model."""

from __future__ import annotations

import json

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.ai_engine import synthesize
from core.computation import activation_energy_for, parse_hours, parse_temperature_c, simulate_kinetics
from .components import badge, esc, note, progress, section_header, show
from .icons import icon
from .theme import axis_style, plotly_layout


def _source_label(src: str) -> str:
    if src.startswith("gemini"):
        model = src.split("(")[1].rstrip(")") if "(" in src else "Active"
        return f"Live Gemini AI ({model})"
    if src == "preset":
        return "Preset Example Report"
    return "Deterministic Rules Engine"


def _report_text(r: dict) -> str:
    pc = r["physicochemicalChanges"]
    lines = [
        f"BIO-CLAY SYNTHESIS PROTOCOL — {r['moleculeName']}",
        f"Formula: {r['chemicalFormula']}   |   Lab feasible: {'YES' if r['isFeasibleInLab'] else 'CHALLENGING'}   |   Confidence: {r['confidenceScore']}%",
        "", f"Technique : {r['synthesisTechnique']}", f"Temperature: {r['temperatureCondition']}",
        f"Pressure  : {r['pressureCondition']}", f"pH        : {r['pHRange']}", f"Duration  : {r['reactionTime']}",
        f"Reagents  : {r['catalystAndReagents']}", "", "STEP-BY-STEP PROTOCOL",
    ]
    lines += [f"  {i}. {s}" for i, s in enumerate(r["stepByStepProtocol"], 1)]
    lines += ["", "PROPERTY CHANGES"]
    for k in ("molecularWeight", "ionizationEnergy", "electronegativity", "dipoleMoment", "enthalpyDeltaH", "bondAngle", "bondLength"):
        m = pc[k]
        lines.append(f"  {k:<18} {m['original']} → {m['modified']} {m['unit']}")
    lines += [f"  solubility         {pc['solubility']}", "", "BIO-CLAY INTERACTION"]
    lines += [f"  {k}: {v}" for k, v in r["bioClayInteraction"].items()]
    lines += ["", f"SAFETY: {r['safetyPrecautions']}"]
    return "\n".join(lines)


def render(props: dict, api_key: str | None, ai_ready: bool) -> None:
    ss = st.session_state
    r = ss.report

    with st.container(key="card_synth"):
        head_l, head_r = st.columns([5, 2], vertical_alignment="center")
        with head_l:
            show(f"""<div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
                 <span class="bc-eyebrow">Gemini Intelligent Engine</span>{badge(_source_label(ss.api_source), 'mono')}</div>
                 <div class="bc-h2">Synthesis Protocol, Feasibility &amp; Lab Techniques</div>
                 <div class="bc-muted">Evaluating laboratory synthesizability, high vs. low temperature techniques, and bio-clay intercalation.</div>""")
        with head_r:
            again = st.button("↻  Re-Analyze with " + ("Gemini API" if ai_ready else "Rules Engine"),
                              key="reanalyze", type="primary", width="stretch")
        show('<div class="bc-divider"></div>')

        if again:
            with st.spinner("Consulting Gemini for thermodynamic calculations, lab conditions, and bio-clay adhesion…"
                            if ai_ready else "Recalculating with the offline rules engine…"):
                source, report = synthesize(ss.custom_molecule, ss.chip_action, ss.chip_target,
                                            ss.removed_groups, ss.added_groups, props, api_key)
            ss.report, ss.api_source, ss.sim_temp = report, source, None
            st.rerun()

        if ai_ready and ss.api_source == "rules_engine":
            st.caption("⚠️ Gemini did not answer (wrong key, no internet or model busy) — this report comes from the "
                       "offline rules engine instead.")

        left, right = st.columns([4, 8], gap="medium")

        # ---------------------------------------------------------------- left column
        with left:
            feas = badge("Lab Feasible", "green", "check-circle") if r["isFeasibleInLab"] else badge("Challenging", "amber", "alert")
            show(f"""
            <div class="bc-inner" style="margin-bottom:.9rem">
              <div class="bc-row"><span class="bc-eyebrow">Product Identification</span>{feas}</div>
              <div style="font-weight:800;font-size:1.05rem;margin:.55rem 0 .45rem 0;color:var(--text)">{esc(r['moleculeName'])}</div>
              <div class="bc-soft mono" style="font-weight:600;color:var(--accent-text)">Formula: {esc(r['chemicalFormula'])}</div>
              <div class="bc-divider"></div>
              <div class="bc-row" style="font-size:.8rem"><span class="bc-muted">Confidence Score</span>
                <b style="color:#db2777">{esc(r['confidenceScore'])}%</b></div>
              <div style="margin-top:.4rem">{progress(r['confidenceScore'])}</div>
            </div>
            <div class="bc-inner" style="margin-bottom:.9rem">
              <div class="bc-label">{icon('shield', 14, '#9333ea')}Primary Synthesis Technique</div>
              <div style="margin:.6rem 0;padding:.7rem;border-radius:12px;border:1px solid #f9a8d4;font-weight:700;font-size:.9rem;
                   color:var(--heading);background:linear-gradient(90deg,rgba(236,72,153,.1),rgba(168,85,247,.1))">{esc(r['synthesisTechnique'])}</div>
              <div class="bc-muted" style="color:var(--slate)">Suitable for 1st-year medical engineering wet laboratory protocols,
                prioritizing high-yield organic-clay hybrid formation.</div>
            </div>
            <div class="bc-inner">
              <div class="bc-label">{icon('layers', 14, '#db2777')}Bio-Clay Nanocomposite Interaction</div>
              <div style="font-size:.8rem;line-height:1.5;margin-top:.5rem">
                <b>Intercalation Feasibility:</b><div style="color:var(--slate);margin-bottom:.45rem">{esc(r['bioClayInteraction']['intercalationFeasibility'])}</div>
                <b>Binding Mechanism:</b><div style="color:var(--slate);margin-bottom:.45rem">{esc(r['bioClayInteraction']['bindingMechanism'])}</div>
                <b>Biomedical Application:</b><div style="color:var(--slate)">{esc(r['bioClayInteraction']['biomedicalApplications'])}</div>
              </div>
            </div>
            """)

        # ---------------------------------------------------------------- right column
        with right:
            cond = lambda ic, k, v: (f'<div class="bc-soft" style="background:var(--inner2)"><div class="bc-label" '
                                     f'style="color:var(--accent-text);text-transform:none;letter-spacing:0">{icon(ic, 14)}{k}</div>'
                                     f'<div style="font-weight:700;font-size:.86rem;margin-top:.3rem">{esc(v)}</div></div>')
            show(f"""
            <div class="bc-inner" style="margin-bottom:.9rem">
              <div class="bc-label" style="margin-bottom:.7rem">{icon('beaker', 14, '#db2777')}Experimental Parameters &amp; Reaction Conditions</div>
              <div class="bc-grid c4">
                {cond('thermometer', 'Temperature', r['temperatureCondition'])}
                {cond('gauge', 'Pressure', r['pressureCondition'])}
                {cond('droplet', 'pH &amp; Buffer', 'pH: ' + r['pHRange'])}
                {cond('clock', 'Duration', r['reactionTime'])}
              </div>
              <div class="bc-soft" style="margin-top:.7rem"><b style="color:var(--chip-text)">Catalyst &amp; Key Reagents: </b>{esc(r['catalystAndReagents'])}</div>
            </div>
            """)
            steps = "".join(f'<div class="bc-step"><span class="n">{i}</span><span>{esc(s)}</span></div>'
                            for i, s in enumerate(r["stepByStepProtocol"], 1))
            safety = (f'<div class="bc-note warn" style="margin-top:.6rem">{icon("alert", 16, "#d97706")}<div>'
                      f'<b>Laboratory Safety Note: </b>{esc(r["safetyPrecautions"])}</div></div>') if r.get("safetyPrecautions") else ""
            show(f"""
            <div class="bc-inner">
              <div class="bc-label" style="margin-bottom:.7rem">{icon('file', 14, '#9333ea')}Step-by-Step Medical Engineering Lab Protocol</div>
              {steps}{safety}
            </div>
            """)

            d1, d2 = st.columns(2)
            d1.download_button("⬇  Download protocol (.txt)", _report_text(r), file_name="bioclay_protocol.txt",
                               mime="text/plain", width="stretch", key="dl_txt")
            d2.download_button("⬇  Download full report (.json)", json.dumps(r, indent=2, ensure_ascii=False),
                               file_name="bioclay_report.json", mime="application/json", width="stretch", key="dl_json")

    _kinetics_card(r)


def _kinetics_card(r: dict) -> None:
    """SciPy ODE model: how fast does the reaction + clay intercalation happen at a chosen temperature?"""
    ss = st.session_state
    t_ref = parse_temperature_c(r["temperatureCondition"])
    hours = parse_hours(r["reactionTime"])
    if ss.sim_temp is None:
        ss.sim_temp = int(min(220, max(0, round(t_ref))))

    with st.container(key="card_kinetics"):
        section_header("Computational Thinking Extension · SciPy solve_ivp",
                       "Reaction & Intercalation Kinetics Simulator",
                       "A small differential-equation model built from this protocol. Move the temperature slider to see how "
                       "the Arrhenius equation speeds up or slows down the synthesis and the bio-clay gallery expansion.",
                       badge(f"Eₐ ≈ {activation_energy_for(r['synthesisTechnique']):.0f} kJ/mol", "mono"), ic="activity")
        c1, c2 = st.columns([2, 5], gap="medium")
        with c1:
            st.slider("Simulation temperature (°C)", min_value=0, max_value=220, key="sim_temp", step=1)
            sim = simulate_kinetics(t_ref, hours, r["synthesisTechnique"], float(ss.sim_temp))
            t95 = f"{sim['t95_conversion']:.2f} h" if sim["t95_conversion"] is not None else "not reached"
            t90 = f"{sim['t90_intercalated']:.2f} h" if sim["t90_intercalated"] is not None else "not reached"
            show(f"""
            <div class="bc-grid c2" style="margin-top:.4rem">
              <div class="bc-stat"><div class="k">{icon('thermometer', 14)}Protocol temp.</div><div class="v">{t_ref:.0f}<small>°C</small></div></div>
              <div class="bc-stat"><div class="k">{icon('zap', 14)}Rate × vs protocol</div><div class="v pink">{sim['rate_factor']:.2f}<small>×</small></div></div>
              <div class="bc-stat"><div class="k">{icon('clock', 14)}95 % conversion</div><div class="v">{t95}</div></div>
              <div class="bc-stat"><div class="k">{icon('layers', 14)}90 % intercalated</div><div class="v">{t90}</div></div>
            </div>
            <div class="bc-soft" style="margin-top:.7rem">Final basal spacing d₀₀₁ ≈ <b>{sim['final_d001']:.2f} nm</b>
              (starts at 0.88 nm, fully expanded ≈ 1.42 nm).</div>
            """)
        with c2:
            df = sim["df"]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=df.time_h, y=df.Precursor, name="Precursor left", line=dict(color="#94a3b8", width=2.5)))
            fig.add_trace(go.Scatter(x=df.time_h, y=df["Product (free)"], name="Product (free in solution)",
                                     line=dict(color="#9333ea", width=2.5, dash="dot")))
            fig.add_trace(go.Scatter(x=df.time_h, y=df.Intercalated, name="Clay galleries filled",
                                     line=dict(color="#db2777", width=3), fill="tozeroy", fillcolor="rgba(219,39,119,0.08)"))
            fig.add_trace(go.Scatter(x=df.time_h, y=df.d001_nm, name="d₀₀₁ spacing (nm)",
                                     line=dict(color="#f59e0b", width=2)), secondary_y=True)
            fig.add_vline(x=hours, line_dash="dash", line_color="#f472b6",
                          annotation_text=f"protocol time {hours:g} h", annotation_font_color="#db2777")
            fig.update_layout(**plotly_layout(height=340, hovermode="x unified", margin=dict(l=10, r=10, t=50, b=10)))
            fig.update_xaxes(title="time (hours)", **axis_style())
            fig.update_yaxes(title="fraction (0 – 1)", range=[0, 1.05], secondary_y=False, **axis_style())
            fig.update_yaxes(title="d₀₀₁ (nm)", range=[0.8, 1.5], secondary_y=True, showgrid=False, automargin=True,
                             tickfont=dict(color="#f59e0b"), title_font=dict(color="#f59e0b"))
            st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, key="kin_chart")
        with st.expander("📐 The maths behind this simulation"):
            st.latex(r"\frac{dP}{dt}=-k_1P,\qquad \frac{dS}{dt}=k_1P-k_2S(1-I),\qquad \frac{dI}{dt}=k_2S(1-I)")
            st.latex(r"k(T)=k_{ref}\,\exp\!\left[-\frac{E_a}{R}\left(\frac{1}{T}-\frac{1}{T_{ref}}\right)\right],\qquad "
                     r"d_{001}=0.88+0.54\,I\ \text{nm}")
            st.markdown(
                f"- **P** = precursor, **S** = product in solution, **I** = fraction of clay galleries filled.\n"
                f"- k₁ is *calibrated* so the protocol reaches 95 % conversion after **{hours:g} h at {t_ref:.0f} °C** "
                f"(k₁ = ln 20 / t = {sim['k1'] / sim['rate_factor']:.3f} h⁻¹ at the protocol temperature).\n"
                f"- `scipy.integrate.solve_ivp` (LSODA method) solves the three equations numerically.\n"
                "- This is an **educational model** to show computational thinking — not measured lab data.")
