"""Tab 1 - Molecule Designer (port of MoleculeDesigner.tsx)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.ai_engine import synthesize
from core.chemistry import (
    FUNCTIONAL_GROUPS_CATALOG, HYDROGEN_LABEL, NONE_LABEL, SALT_LABEL, blueprint_headline,
    count_carbons_in_chain, display_formula, parse_functional_group_input, parse_target_position,
    property_contributions,
)
from .components import badge, esc, label, show, stat_card, table
from .icons import icon
from .state import goto

QUICK_FILL = {
    "Ethane (2C)": "CH3-CH3",
    "Propane (3C)": "CH3-CH2-CH3",
    "Butane (4C)": "CH3-CH2-CH2-CH3",
    "Pentane (5C)": "CH3-CH2-CH2-CH2-CH3",
    "Hexane (6C)": "CH3-CH2-CH2-CH2-CH2-CH3",
}
ACTIONS = {"remove_h": "1. Remove Hydrogen  (-H Removal)",
           "remove_functional_group": "2. Remove Functional Group  (Group Substitution)"}
CATEGORIES = {"all": "All Groups", "salt": "Salts ⚡", "halogen": "Halogens 🧪"}


# ------------------------------------------------------------------ callbacks
def _on_quick_fill():
    choice = st.session_state.get("quick_fill")
    if choice:
        st.session_state.custom_molecule = QUICK_FILL[choice]
    st.session_state.quick_fill = None


def _on_action_change():
    ss = st.session_state
    if ss.chip_action == "remove_h":
        ss.removed_groups = [HYDROGEN_LABEL]
    elif not ss.removed_groups or HYDROGEN_LABEL in ss.removed_groups:
        ss.removed_groups = [SALT_LABEL]


def _normalise(new: list[str], old: list[str]) -> list[str]:
    """'None (No Action)' is exclusive: picking it clears the rest, picking anything else clears it."""
    new = list(new or [])
    if NONE_LABEL in new and NONE_LABEL not in old:
        return [NONE_LABEL]
    cleaned = [g for g in new if g != NONE_LABEL]
    return cleaned or [NONE_LABEL]


def _on_pills(kind: str):
    ss = st.session_state
    canon = "removed_groups" if kind == "rm" else "added_groups"
    ss[canon] = _normalise(ss[f"{kind}_pills"], ss[canon])


def _toggle(canon: str, label_: str):
    ss = st.session_state
    current = [g for g in ss[canon] if g != NONE_LABEL]
    if label_ == NONE_LABEL:
        ss[canon] = [NONE_LABEL]
        return
    current = [g for g in current if g != label_] if label_ in current else current + [label_]
    ss[canon] = current or [NONE_LABEL]


def _on_custom_group(is_add: bool):
    ss = st.session_state
    text = (ss.custom_group_input or "").strip()
    if not text:
        return
    match = parse_functional_group_input(text)
    if match:
        _toggle("added_groups" if is_add else "removed_groups", match.label)
        ss.designer_msg = f"{'Added' if is_add else 'Removed'} toggle: {match.label}"
        ss.custom_group_input = ""
    else:
        ss.designer_msg = f"Could not recognise “{text}”. Try -COO-Na+, -Cl, -NH2, amine, nitro …"


def _on_target_change():
    pass  # the radio value itself is the source of truth


# ------------------------------------------------------------------ render
def render(parsed: dict, props: dict, api_key: str | None, ai_ready: bool) -> None:
    ss = st.session_state
    total_c = max(1, count_carbons_in_chain(ss.custom_molecule) or parsed["carbons"] or 3)

    # keep the target carbon inside the chain (C5 makes no sense for a 3-carbon chain)
    options_c = [f"C{i}" for i in range(1, total_c + 1)]
    if ss.chip_target not in options_c:
        idx = parse_target_position(ss.chip_target or "", total_c)["carbon_index"]
        ss.chip_target = f"C{min(idx, total_c)}"
    pos = parse_target_position(ss.chip_target, total_c)

    left, right = st.columns([5, 7], gap="medium")

    # ============================ LEFT: configuration panel
    with left:
        with st.container(key="card_designer_cfg"):
            show(f"""<div class="bc-row"><div class="bc-h3">{icon('sliders', 16, '#db2777')}Molecular Designer</div>
                 {badge(f'{total_c} Carbons')}</div><div class="bc-divider"></div>
                 <div class="bc-muted">Enter your custom carbon chain below. Select the modification type, specify the target
                 carbon atom, and choose which groups to remove and add.</div>""")

            label("1. Base Molecule / Carbon Chain", badge(f"{total_c} Carbons in Chain", "mono"))
            st.text_input("Base molecule", key="custom_molecule", label_visibility="collapsed",
                          placeholder="Enter carbon chain (e.g. CH3-CH2-CH3, CH3-(CH2)2-CH3, butanol)…")
            st.pills("Quick fill", list(QUICK_FILL), key="quick_fill", on_change=_on_quick_fill,
                     label_visibility="collapsed")

            label("2. Modification Action Type", "Select Action")
            st.radio("Action", list(ACTIONS), key="chip_action", format_func=ACTIONS.get, horizontal=True,
                     on_change=_on_action_change, label_visibility="collapsed")

            label("3. Target Carbon Atom", f"Chain has C1 to C{total_c}")
            with st.container(key="inner_target"):
                show('<div class="bc-muted" style="text-align:center;font-size:.72rem;font-weight:600;'
                     'text-transform:uppercase;letter-spacing:.05em">Backbone atoms in chain (click to choose target carbon)</div>')
                st.radio("Target carbon", options_c, key="chip_target", horizontal=True,
                         label_visibility="collapsed", on_change=_on_target_change)
                show(f'<div style="text-align:center;font-size:.78rem;padding-top:.2rem">Target Selected: '
                     f'<b style="color:#db2777">Carbon-{pos["carbon_index"]} (C{pos["carbon_index"]})</b> • '
                     f'<span class="bc-muted">{esc(pos["terminal_type"])}</span></div>')

            show('<div class="bc-divider"></div>')
            label("Group Selection", f'{icon("dna", 12, "#ec4899")} Bio-Clay Intercalators')
            st.radio("Category", list(CATEGORIES), key="chip_cat", format_func=CATEGORIES.get, horizontal=True,
                     label_visibility="collapsed")
            st.text_input("Search groups", key="group_search", label_visibility="collapsed",
                          placeholder="🔍  Search groups (e.g. Salt, COO-Na+, Cl, Br, Amine)…")

            st.text_input("Custom group", key="custom_group_input", label_visibility="collapsed",
                          placeholder="Type custom formula (-COO-Na+, -Cl, -NH2)…")
            c2, c3 = st.columns(2)
            c2.button("+ Remove typed group", key="rm_custom", on_click=_on_custom_group, args=(False,), width="stretch")
            c3.button("+ Add typed group", key="add_custom", on_click=_on_custom_group, args=(True,), type="primary",
                      width="stretch")
            if ss.designer_msg:
                st.caption(ss.designer_msg)

            catalog = _filtered_catalog(ss.chip_cat, ss.group_search)
            fmt = _group_formatter()

            rm_opts = _merge(catalog, ss.removed_groups)
            ss.rm_pills = ss.removed_groups
            n_rm = "None" if NONE_LABEL in ss.removed_groups else f"{len(ss.removed_groups)} selected"
            label("Select to Remove (which one to remove)", n_rm, color="#e11d48")
            with st.container(height=165, key="scroll_rm"):
                st.pills("Remove", rm_opts, selection_mode="multi", key="rm_pills", format_func=fmt,
                         on_change=_on_pills, args=("rm",), label_visibility="collapsed")

            add_opts = _merge(catalog, ss.added_groups)
            ss.add_pills = ss.added_groups
            n_add = "None" if NONE_LABEL in ss.added_groups else f"{len(ss.added_groups)} selected"
            label("Select to Add (which one to add)", n_add)
            with st.container(height=185, key="scroll_add"):
                st.pills("Add", add_opts, selection_mode="multi", key="add_pills", format_func=fmt,
                         on_change=_on_pills, args=("add",), label_visibility="collapsed")

            engine = "Gemini" if ai_ready else "Offline Rules Engine"
            if st.button(f"✨  Synthesize & Analyze with {engine}", key="cta_synth", width="stretch"):
                with st.spinner("Consulting Gemini AI Lab…" if ai_ready else "Running the rules engine…"):
                    source, report = synthesize(ss.custom_molecule, ss.chip_action, ss.chip_target,
                                                ss.removed_groups, ss.added_groups, props, api_key)
                ss.report, ss.api_source = report, source
                ss.sim_temp = None  # re-centre the kinetics slider on the new protocol
                ss._goto = "synthesis"
                st.rerun()

    # ============================ RIGHT: blueprint + live parameters
    with right:
        with st.container(key="card_designer_live"):
            show(f"""
            <div class="bc-row" style="align-items:flex-start">
              <div><div class="bc-eyebrow">Molecular Blueprint &amp; Real-Time Reaction Matrix</div>
                   <div class="bc-h2">{esc(blueprint_headline(ss.added_groups))}</div></div>
              {badge('Feasible in Lab', '', 'check-circle')}
            </div><div class="bc-divider"></div>
            <div class="bc-visual">
              <span class="bc-badge mono">Target: Carbon-{pos['carbon_index']} (C{pos['carbon_index']}) •
                {'Remove Hydrogen (-H)' if ss.chip_action == 'remove_h' else 'Remove Functional Group'}</span>
              <div class="bc-formula">{esc(display_formula(parsed['formula'], ss.added_groups, ss.chip_action, pos['carbon_index']))}</div>
              <div style="display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center;align-items:center">
                <span class="bc-pill rm">{icon('x', 12)}Removed: {esc(', '.join(ss.removed_groups))}</span>
                <span style="color:#f472b6;font-weight:700">→</span>
                <span class="bc-pill add">{icon('check', 12)}Added: {esc(', '.join(ss.added_groups))}</span>
              </div>
            </div>
            <div class="bc-row" style="margin:1.1rem 0 .6rem 0">
              <span class="bc-label">{icon('activity', 13, '#db2777')}Real-Time Physicochemical Parameters</span>
              <span class="bc-muted" style="font-size:.72rem">Updates dynamically</span>
            </div>
            <div class="bc-grid c3">
              {stat_card('scale', 'Molecular Weight', props['molecularWeight']['modified'], 'g/mol', f"Base: {props['molecularWeight']['original']} g/mol")}
              {stat_card('zap', 'Ionization Energy (IA)', props['ionizationEnergy']['modified'], 'eV', f"Base: {props['ionizationEnergy']['original']} eV", pink=True)}
              {stat_card('compass', 'Electronegativity', props['electronegativity']['modified'], 'Pauling', f"Base: {props['electronegativity']['original']} Pauling")}
              {stat_card('activity', 'Dipole Moment (μ)', props['dipoleMoment']['modified'], 'Debye (D)', f"Base: {props['dipoleMoment']['original']} D")}
              {stat_card('flame', 'Enthalpy Shift (ΔH)', props['enthalpyDeltaH']['modified'], 'kJ/mol', f"Base: {props['enthalpyDeltaH']['original']} kJ/mol", pink=True)}
              <div class="bc-stat"><div class="k">{icon('layers', 14)}<span>Bio-Clay Binding</span></div>
                <div style="font-size:.8rem;font-weight:700;color:var(--accent-text);margin-top:.3rem;line-height:1.35">
                  {esc(props['bioClayBinding']['modified'].split('(')[0])}</div>
                <div class="s">LDH / Clay Interlayer</div></div>
            </div>
            """)

            with st.expander("🧮 How were these numbers calculated? (the Python logic)"):
                rows = property_contributions(ss.removed_groups, ss.added_groups)
                st.markdown(
                    f"**Base molecule recognised:** `{parsed['preset'].name}` → MW {parsed['preset'].base_mw}, "
                    f"IE {parsed['preset'].base_ie} eV, EN {parsed['preset'].base_en}, μ {parsed['preset'].base_dipole} D, "
                    f"ΔH {parsed['preset'].base_delta_h} kJ/mol")
                if rows:
                    table(pd.DataFrame(rows))
                    st.caption("final value = base value + Σ(contributions) → then clipped to realistic ranges "
                               "(IE 7–15 eV, EN 1.8–3.8). Removed groups are weighted less than added ones "
                               "(EN ×0.2, μ ×0.7, ΔH ×0.8) — exactly the same rule as the original website.")
                else:
                    st.caption("No groups selected — values equal the base molecule.")

            show('<div class="bc-divider"></div>')
            b1, b2 = st.columns([1, 1.05], vertical_alignment="center")
            b1.markdown('<span style="font-size:.82rem;font-weight:600;color:var(--chip-text)">'
                        'Ready to generate lab protocol and temperature conditions?</span>', unsafe_allow_html=True)
            b2.button("View Deep AI Synthesis Protocol  →", key="dark_goto_synth", on_click=goto, args=("synthesis",),
                      width="stretch")


# ------------------------------------------------------------------ helpers
def _filtered_catalog(category: str, query: str) -> list[str]:
    out = []
    q = (query or "").strip().lower()
    for g in FUNCTIONAL_GROUPS_CATALOG:
        if category == "salt" and not (g.is_salt or g.category == "salt"):
            continue
        if category == "halogen" and g.category != "halogen":
            continue
        if q and q not in g.label.lower() and q not in g.formula.lower() and q not in g.name.lower():
            continue
        out.append(g.label)
    return out


def _merge(options: list[str], selected: list[str]) -> list[str]:
    """Options shown = filtered catalogue + anything already selected (so a filter never 'loses' a choice)."""
    order = [g.label for g in FUNCTIONAL_GROUPS_CATALOG]
    wanted = set(options) | set(selected)
    return [l for l in order if l in wanted]


def _group_formatter():
    by_label = {g.label: g for g in FUNCTIONAL_GROUPS_CATALOG}

    def fmt(lbl: str) -> str:
        g = by_label.get(lbl)
        if g is None:
            return lbl
        if g.is_salt:
            return f"⚡ {lbl}"
        if g.category == "halogen":
            return f"🧪 {lbl}"
        return lbl
    return fmt
