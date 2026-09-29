"""Tab 5 - Element Slide Game (port of ElementSlideGame.tsx)."""

from __future__ import annotations

import streamlit as st

from core.ai_engine import validate_molecule
from core.chemistry import FUNCTIONAL_FRAGMENTS_GAME, PERIODIC_ELEMENTS_GAME
from core.rules_engine import expand_to_atoms
from .components import badge, esc, show, stat_card
from .icons import icon

CHALLENGES = {
    1: dict(title="Synthesize Bio-Clay Salt",
            description="Build Sodium Butanoate (3 Carbons, 7 Hydrogens, 1 -COO⁻Na⁺) for LDH intercalation.",
            target={"C": 3, "H": 7, "-COO⁻Na⁺": 1}, reward=50, start={"C": 3, "H": 7, "-COO⁻Na⁺": 1}),
    2: dict(title="Synthesize Propanol Precursor",
            description="Assemble standard 1-Propanol (3 Carbons, 7 Hydrogens, 1 -OH group).",
            target={"C": 3, "H": 7, "-OH": 1}, reward=50, start={"C": 3, "H": 7, "-OH": 1}),
    3: dict(title="Synthesize Cationic Amine",
            description="Create Propylamine (3 Carbons, 7 Hydrogens, 1 -NH₂ group) for montmorillonite clay.",
            target={"C": 3, "H": 7, "-NH₂": 1}, reward=50, start={"C": 3, "H": 7, "-NH₂": 1}),
    4: dict(title="Free Sandbox Mode",
            description="Combine any combination of elements to test if nature and medical labs can synthesize it!",
            target={}, reward=30, start={"C": 2, "H": 5, "-OH": 1}),
}


def formula_string(counts: dict[str, int]) -> str:
    parts = []
    if counts.get("C"):
        parts.append(f"C{counts['C'] if counts['C'] > 1 else ''}")
    if counts.get("H"):
        parts.append(f"H{counts['H'] if counts['H'] > 1 else ''}")
    for k, n in counts.items():
        if k not in ("C", "H"):
            parts.append(f"{k}{f'({n})' if n > 1 else ''}")
    return "".join(parts) if parts else "Empty (Select elements below)"


# ------------------------------------------------------------------ callbacks
def _on_challenge():
    ss = st.session_state
    ss.g_counts = dict(CHALLENGES[ss.chip_challenge]["start"])
    ss.g_result, ss.g_show = None, False


def _add(sym: str):
    c = dict(st.session_state.g_counts)
    c[sym] = c.get(sym, 0) + 1
    st.session_state.g_counts = c


def _sub(sym: str):
    c = dict(st.session_state.g_counts)
    if c.get(sym, 0) <= 1:
        c.pop(sym, None)
    else:
        c[sym] -= 1
    st.session_state.g_counts = c


def _clear():
    st.session_state.g_counts = {}
    st.session_state.g_result, st.session_state.g_show = None, False


# ------------------------------------------------------------------ render
def render(api_key: str | None, ai_ready: bool) -> None:
    ss = st.session_state
    ch = CHALLENGES[ss.chip_challenge]
    counts = ss.g_counts

    with st.container(key="card_game"):
        h1, h2 = st.columns([5, 1.3], vertical_alignment="center")
        with h1:
            show(f"""<div class="bc-eyebrow" style="display:flex;gap:.4rem;align-items:center">{icon('gamepad', 15)}Interactive Molecule Assembly Game</div>
                 <div class="bc-h2">Element Slide &amp; Lab Synthesizability Challenge</div>
                 <div class="bc-muted">Choose elements and functional groups from the tray, join them into a molecule, and determine
                 if it can be synthesized in a medical laboratory!</div>""")
        with h2:
            show(f"""<div style="display:flex;align-items:center;gap:.55rem;padding:.55rem .8rem;border-radius:14px;
                 border:1px solid #fcd34d;background:linear-gradient(90deg,rgba(245,158,11,.15),rgba(236,72,153,.15))">
                 {icon('award', 18, '#d97706')}<div><div style="font-size:.62rem;font-weight:800;text-transform:uppercase;color:var(--amber-text)">Lab Score</div>
                 <div style="font-weight:800;color:var(--amber-text);font-size:1rem">{ss.g_score} XP</div></div></div>""")
        show('<div class="bc-divider"></div>')

        st.radio("Challenge", list(CHALLENGES), key="chip_challenge", horizontal=True, label_visibility="collapsed",
                 format_func=lambda i: CHALLENGES[i]["title"], on_change=_on_challenge)
        done = "  ✅ completed" if ss.chip_challenge in ss.g_completed else ""
        show(f"""<div class="bc-note info" style="justify-content:space-between;margin:.3rem 0 .9rem 0">
             <div style="display:flex;gap:.5rem">{icon('sparkles', 16, '#db2777')}<span><b>{esc(ch['title'])}: </b>{esc(ch['description'])}{done}</span></div>
             <b style="white-space:nowrap">+{ch['reward']} XP</b></div>""")

        # ---------------- assembly dock
        with st.container(key="inner_dock"):
            d1, d2 = st.columns([5, 1], vertical_alignment="center")
            d1.markdown('<span class="bc-label">Assembly Dock • Selected Elements</span>', unsafe_allow_html=True)
            d2.button("🗑 Clear All", key="danger_clear_all", on_click=_clear, width="stretch")
            if not counts:
                show('<div class="bc-dock bc-muted" style="font-style:italic">No elements chosen yet. Click any element or '
                     'fragment below to add it to your molecule!</div>')
            else:
                items = list(counts.items())
                per_row = 4
                for start in range(0, len(items), per_row):
                    cols = st.columns(per_row)
                    for offset, (col, (sym, n)) in enumerate(zip(cols, items[start:start + per_row])):
                        idx = start + offset
                        with col:
                            with st.container(key=f"inner_chip_{idx}"):
                                show(f'<div class="bc-row"><span class="mono" style="color:#db2777;font-weight:800;font-size:1rem">{esc(sym)}</span>'
                                     f'<span class="bc-badge mono">×{n}</span></div>')
                                b1, b2 = st.columns(2)
                                b1.button("＋", key=f"plus_{idx}", on_click=_add, args=(sym,), width="stretch",
                                          help="Add one more")
                                b2.button("－", key=f"rm_minus_{idx}", on_click=_sub, args=(sym,), width="stretch",
                                          help="Remove one")

            f1, f2 = st.columns([3, 2], vertical_alignment="center")
            atoms = expand_to_atoms(counts)
            hill = "".join(f"{k}{v if v > 1 else ''}" for k, v in atoms.items())
            f1.markdown(f'<span class="bc-muted">Assembled Formula:</span> <span class="mono" style="font-size:1.25rem;'
                        f'font-weight:800;color:var(--accent-text)">{esc(formula_string(counts))}</span>'
                        f'<br><span class="bc-muted" style="font-size:.72rem">atoms after expanding fragments: {esc(hill or "–")}</span>',
                        unsafe_allow_html=True)
            go_btn = f2.button("✨  Step 1: Bond & Synthesize Molecule", key="cta_bond", width="stretch", disabled=not counts)

        if go_btn:
            with st.spinner("Analyzing Chemical Validity…"):
                source, result = validate_molecule(counts, formula_string(counts), api_key)
            ss.g_result, ss.g_show, ss.g_source = result, True, source
            if result["isValid"] and result["isSynthesizable"]:
                ss.g_score += 25
                target = ch["target"]
                if target and expand_to_atoms(target) == expand_to_atoms(counts) and ss.chip_challenge not in ss.g_completed:
                    ss.g_score += ch["reward"]
                    ss.g_completed = ss.g_completed + [ss.chip_challenge]
                    st.balloons()
            st.rerun()

        # ---------------- trays
        show('<div class="bc-label" style="margin:1rem 0 .4rem 0">Periodic Table Elements Tray</div>')
        cols = st.columns(6)
        for i, el in enumerate(PERIODIC_ELEMENTS_GAME):
            n = counts.get(el.symbol, 0)
            label = f"{el.atomic_number} · {el.symbol}{f'  (×{n})' if n else ''}\n{el.name}\nVal: {el.valence}"
            cols[i % 6].button(label, key=f"el_{el.symbol}", on_click=_add, args=(el.symbol,), width="stretch",
                               help=f"{el.name}: mass {el.atomic_mass}, EN {el.electronegativity}, IE {el.ionization_energy} eV")

        show('<div class="bc-label" style="margin:1rem 0 .4rem 0">Bio-Clay Functional Groups &amp; Salt Fragments</div>')
        cols = st.columns(6)
        for i, fr in enumerate(FUNCTIONAL_FRAGMENTS_GAME):
            n = counts.get(fr.symbol, 0)
            cols[i % 6].button(f"{fr.symbol}{f'  (×{n})' if n else ''}\n{fr.name}", key=f"frag_{i}", on_click=_add,
                               args=(fr.symbol,), width="stretch")

        # ---------------- step 2 result
        if ss.g_show and ss.g_result:
            _result_card(ss.g_result, ss.g_source)


def _result_card(r: dict, source: str):
    valid = badge("Valid Molecule", "green", "check-circle") if r["isValid"] else badge("Invalid Valence", "rose", "alert")
    synth = badge("Synthesizable in Lab", "") if r["isSynthesizable"] else badge("Not Lab Feasible", "amber")
    src = "Live Gemini AI" if source.startswith("gemini") else ("Preset example" if source == "preset" else "Offline rules engine")
    hill = f" · Hill: {esc(r['hillFormula'])}" if r.get("hillFormula") else ""
    show(f"""
    <div style="margin-top:1.2rem;padding:1.3rem;border-radius:18px;border:2px solid rgba(236,72,153,.4);background:var(--inner);
         box-shadow:0 10px 30px rgba(236,72,153,.12)">
      <div class="bc-row" style="align-items:flex-start">
        <div><div class="bc-eyebrow">Step 2: Laboratory Feasibility &amp; Chemical Properties · {src}</div>
          <div style="font-size:1.25rem;font-weight:800;margin:.2rem 0">{esc(r['moleculeName'])}</div>
          <span class="mono" style="font-size:.78rem;color:var(--accent-text)">Formula: {esc(r['formula'])}{hill}</span></div>
        <div style="display:flex;gap:.4rem;flex-wrap:wrap">{valid}{synth}</div>
      </div>
      <div class="bc-divider"></div>
      <div class="bc-soft" style="margin-bottom:.8rem"><b style="color:var(--heading)">Scientific Assessment: </b>{esc(r['explanation'])}
        <div style="margin-top:.35rem;font-size:.74rem;color:var(--slate)">Valency status: {esc(r['valencyStatus'])}</div></div>
      <div class="bc-grid c4">
        {stat_card('scale', 'Molecular Weight', r['molecularWeight'], 'g/mol')}
        {stat_card('zap', 'Ionization Energy (IA)', r['ionizationEnergy'], 'eV', pink=True)}
        {stat_card('compass', 'Electronegativity', r['electronegativity'], 'Pauling')}
        {stat_card('activity', 'Dipole Moment (μ)', r['dipoleMoment'], 'Debye')}
      </div>
      <div class="bc-grid c2" style="margin-top:.8rem">
        <div class="bc-soft"><div class="bc-label" style="color:var(--accent-text);text-transform:none;letter-spacing:0">{icon('layers', 14)}Bio-Clay Suitability</div>
          <div style="margin-top:.3rem">{esc(r['bioClaySuitability'])}</div></div>
        <div class="bc-soft"><div class="bc-label" style="color:#9333ea;text-transform:none;letter-spacing:0">{icon('sparkles', 14)}Lab Synthesis Technique</div>
          <div style="margin-top:.3rem">{esc(r['synthesisTechnique'])}</div></div>
      </div>
    </div>""")
