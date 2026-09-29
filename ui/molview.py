"""Tab 4 - MolView 2D/3D Lab (port of MolViewCanvas.tsx) + NetworkX graph analysis + SciPy geometry clean-up."""

from __future__ import annotations

import time

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core import molecule_builder as mb
from core.computation import analyze_molecule, bond_geometry_table, close_contacts, optimize_geometry
from .charts import graph_figure, molecule_2d, molecule_3d
from .components import badge, esc, show, table
from .icons import icon
from .theme import plotly_layout

NONE = "— none —"
QUICK = dict(mb.QUICK_GENERATE)


# ------------------------------------------------------------------ state helpers
def _set(atoms, bonds, msg, selected="__keep__"):
    ss = st.session_state
    ss.mv_atoms, ss.mv_bonds, ss.mv_status = atoms, bonds, msg
    if selected != "__keep__":
        ss.mv_selected = selected
    if ss.mv_selected and not mb.find_atom(atoms, ss.mv_selected):
        ss.mv_selected = None
    ss.mv_energy = None


def generate(query: str):
    q = (query or "").strip()
    if not q:
        return
    gen = mb.build_molecule_from_input(q)
    ss = st.session_state
    ss.mv_info = {"name": gen["displayName"], "formula": gen["formula"], "description": gen["description"]}
    ss.mv_intercalated = False
    _set(gen["atoms"], gen["bonds"],
         f"Rendered {gen['displayName']} ({gen['formula']}) in 3D & 2D with {len(gen['atoms'])} atoms and {len(gen['bonds'])} bonds.",
         selected=None)


def _on_generate():
    generate(st.session_state.mv_input)


def _on_quick():
    ss = st.session_state
    choice = ss.get("mv_quick")
    if choice:
        ss.mv_input = QUICK[choice]
        generate(QUICK[choice])
    ss.mv_quick = None


def _on_select():
    v = st.session_state.mv_select
    st.session_state.mv_selected = None if v == NONE else v
    if v != NONE:
        a = mb.find_atom(st.session_state.mv_atoms, v)
        name = mb.ELEMENT_STYLES[a["element"]]["name"]
        st.session_state.mv_status = (f"Selected {name} ({a['element']}). Pick another atom below to create a "
                                      f"{st.session_state.chip_mv_bond} bond, or attach a new element to it!")


def _on_target_pill():
    v = st.session_state.get("mv_target_pills")
    if v:
        carbons = mb.carbons_sorted(st.session_state.mv_atoms)
        idx = next(i for i, c in enumerate(carbons) if c["id"] == v) + 1
        end = " Terminal" if idx in (1, len(carbons)) else ""
        st.session_state.mv_selected = v
        st.session_state.mv_status = f"Target site set to Carbon-{idx} ({v.upper()}{end}). Ready to Add or Remove."


def _on_element():
    el = st.session_state.chip_mv_el
    st.session_state.mv_status = f"Element set to {mb.ELEMENT_STYLES[el]['name']} ({el}). Use “+ Attach” or place it at coordinates."


def _on_bond():
    label = mb.BOND_TYPES[st.session_state.chip_mv_bond][0]
    st.session_state.mv_status = f"Bond mode set to {label}. Pick two atoms and press “Form bond”, or attach a new atom."


def _attach():
    ss = st.session_state
    atoms, bonds, new_id, msg = mb.attach_atom(ss.mv_atoms, ss.mv_bonds, ss.mv_selected, ss.chip_mv_el, ss.chip_mv_bond)
    _set(atoms, bonds, msg, selected=new_id)


def _place():
    ss = st.session_state
    atoms, bonds, new_id, msg = mb.place_atom_at(ss.mv_atoms, ss.mv_bonds, ss.mv_selected, ss.chip_mv_el,
                                                 ss.chip_mv_bond, ss.mv_place_x, ss.mv_place_y, ss.mv_place_z)
    _set(atoms, bonds, msg, selected=new_id)


def _connect():
    ss = st.session_state
    other = None if ss.mv_connect == NONE else ss.mv_connect
    bonds, msg = mb.connect_atoms(ss.mv_bonds, ss.mv_selected, other, ss.chip_mv_bond)
    _set(ss.mv_atoms, bonds, msg, selected=other or ss.mv_selected)
    ss.mv_connect = NONE


def _delete():
    ss = st.session_state
    atoms, bonds, msg = mb.delete_atom(ss.mv_atoms, ss.mv_bonds, ss.mv_selected)
    _set(atoms, bonds, msg, selected=None)


def _add_group(group: str):
    ss = st.session_state
    atoms, bonds, msg = mb.add_functional_group(ss.mv_atoms, ss.mv_bonds, ss.mv_selected, group)
    _set(atoms, bonds, msg)


def _remove(kind: str):
    ss = st.session_state
    atoms, bonds, msg = mb.remove_group(ss.mv_atoms, ss.mv_bonds, ss.mv_selected, kind)
    _set(atoms, bonds, msg)


def _preset(kind: str):
    ss = st.session_state
    if kind == "blank":
        ss.mv_info = {"name": "Empty Canvas", "formula": "-", "description": "Cleared canvas."}
        ss.mv_intercalated = False
        _set([], [], "Canvas cleared. Enter a molecule name above or attach an element to draw!", selected=None)
        return
    q = {"salt": "CH3-CH2-CH2-COO-Na+", "amine": "CH3-CH2-CH2-NH2", "glycine": "Glycine"}[kind]
    ss.mv_input = q
    generate(q)


def _reset_view():
    st.session_state.mv_cam_rev += 1


# ------------------------------------------------------------------ render
def render() -> None:
    ss = st.session_state

    # Follow the Designer: if the student typed a new chain there, rebuild it here (like the React prop sync)
    if ss.custom_molecule != ss.mv_synced_from:
        ss.mv_synced_from = ss.custom_molecule
        ss.mv_input = ss.custom_molecule
        generate(ss.custom_molecule)

    atoms, bonds = ss.mv_atoms, ss.mv_bonds
    sel_atom = mb.find_atom(atoms, ss.mv_selected)

    with st.container(key="card_molview"):
        h1, h2 = st.columns([3, 2], vertical_alignment="center")
        with h1:
            show("""<div class="bc-eyebrow">MolView 3D Molecular Studio &amp; Clay Assembler</div>
                 <div class="bc-h2">Interactive 3D Atom Placement &amp; Practical Bond Builder</div>
                 <div class="bc-muted">Place Carbon (C), Nitrogen (N), Oxygen (O)… and choose bond orders (Single, Double, Triple,
                 Ionic) to construct custom bio-clay intercalators. Drag the 3D view to rotate, scroll to zoom.</div>""")
        with h2:
            st.radio("View", ["3D", "2D"], key="chip_mv_view", horizontal=True, label_visibility="collapsed",
                     format_func=lambda v: "🧊 3D Ball-and-Stick" if v == "3D" else "👁 2D Skeletal")
        show('<div class="bc-divider"></div>')

        # ---------------- generate box
        with st.container(key="inner_gen"):
            show(f"""<div class="bc-row"><span class="bc-label">{icon('sparkles', 14, '#db2777')}Generate 3D &amp; 2D Structure by Molecule Name or Carbon Chain:</span>
                 <span class="bc-badge mono"><span style="width:8px;height:8px;border-radius:99px;background:#10b981;display:inline-block"></span>
                 <b>{esc(ss.mv_info['name'])}</b> • {len(atoms)} Atoms, {len(bonds)} Bonds</span></div>""")
            g1, g2 = st.columns([4, 1.6], vertical_alignment="bottom")
            g1.text_input("Molecule", key="mv_input", label_visibility="collapsed",
                          placeholder="Enter molecule name or chain (e.g. Propane, Butane, CH3-CH2-CH3, Sodium Butanoate, Ethylamine)…")
            g2.button("⬡  Generate 3D & 2D", key="cta_generate", on_click=_on_generate, width="stretch")
            st.pills("Quick Generate", list(QUICK), key="mv_quick", on_change=_on_quick, label_visibility="collapsed")

        # ---------------- toolbar: element / bond / quick actions
        with st.container(key="inner_toolbar"):
            t1, t2, t3 = st.columns([4.3, 4, 2.2], gap="medium")
            with t1:
                show(f'<div class="bc-row"><span class="bc-label">1. Select Element to Place:</span>'
                     f'<span style="font-size:.72rem;font-weight:700;color:#db2777">Active: {ss.chip_mv_el} '
                     f'({mb.ELEMENT_STYLES[ss.chip_mv_el]["name"]})</span></div>')
                st.radio("Element", mb.PALETTE_ELEMENTS, key="chip_mv_el", horizontal=True, label_visibility="collapsed",
                         format_func=lambda e: f"{e} ({mb.ELEMENT_STYLES[e]['name'][:3]})", on_change=_on_element)
            with t2:
                show(f'<div class="bc-row"><span class="bc-label">{icon("activity", 13, "#db2777")}2. Bond Type Selector:</span>'
                     f'<span style="font-size:.72rem;font-weight:700;color:#db2777;text-transform:capitalize">{ss.chip_mv_bond} Bond</span></div>')
                st.radio("Bond", list(mb.BOND_TYPES), key="chip_mv_bond", horizontal=True, label_visibility="collapsed",
                         format_func=lambda b: mb.BOND_TYPES[b][0], on_change=_on_bond)
            with t3:
                show('<span class="bc-label">3. Quick Actions:</span>')
                st.button(f"＋ Attach {ss.chip_mv_el}", key="attach", type="primary", on_click=_attach, width="stretch")
                if sel_atom:
                    st.button(f"🗑 Delete {sel_atom['element']}", key="danger_del", on_click=_delete, width="stretch")

            # Atom picking (replaces clicking on the JS canvas)
            ids = [a["id"] for a in atoms]
            fmt = lambda i: NONE if i == NONE else f"{mb.find_atom(atoms, i)['element']} · {i} ({mb.ELEMENT_STYLES[mb.find_atom(atoms, i)['element']]['name']})"
            ss.mv_select = ss.mv_selected if ss.mv_selected in ids else NONE
            if ss.get("mv_connect") not in [NONE] + ids or ss.get("mv_connect") == ss.mv_selected:
                ss.mv_connect = NONE
            s1, s2, s3 = st.columns([2.2, 2.2, 1.3], vertical_alignment="bottom")
            s1.selectbox("Selected atom (click-to-select)", [NONE] + ids, key="mv_select", format_func=fmt, on_change=_on_select)
            s2.selectbox(f"Bond selected atom to… ({ss.chip_mv_bond})", [NONE] + [i for i in ids if i != ss.mv_selected],
                         key="mv_connect", format_func=fmt, disabled=not sel_atom)
            s3.button("🔗 Form bond", key="form_bond", on_click=_connect, width="stretch",
                      disabled=not sel_atom or ss.mv_connect == NONE)
            with st.expander("📍 Place a new atom at exact coordinates (replaces clicking empty canvas space)"):
                p1, p2, p3, p4 = st.columns([1, 1, 1, 1.4], vertical_alignment="bottom")
                p1.number_input("x", key="mv_place_x", step=10)
                p2.number_input("y (down = +)", key="mv_place_y", step=10)
                p3.number_input("z (depth)", key="mv_place_z", step=10)
                p4.button(f"Place {ss.chip_mv_el}" + (" + bond" if sel_atom else ""), key="place", on_click=_place,
                          width="stretch")

        # ---------------- functional groups
        _functional_groups_panel(atoms, sel_atom)

        # ---------------- status + presets
        show(f'<div class="bc-note info">{icon("help", 16, "#db2777")}<div>{esc(ss.mv_status)}</div></div>')
        pc = st.columns([0.7, 1.3, 1.3, 1, 0.8, 1.6], vertical_alignment="center")
        pc[0].markdown('<span class="bc-label">Presets:</span>', unsafe_allow_html=True)
        pc[1].button("Salt (-COO⁻Na⁺)", key="pre_salt", on_click=_preset, args=("salt",), width="stretch")
        pc[2].button("Nitrogen (-NH₂)", key="pre_amine", on_click=_preset, args=("amine",), width="stretch")
        pc[3].button("Glycine", key="pre_gly", on_click=_preset, args=("glycine",), width="stretch")
        pc[4].button("Clear", key="danger_clear", on_click=_preset, args=("blank",), width="stretch")

        # ---------------- canvas toolbar
        c1, c2, c3 = st.columns([1.2, 1.8, 2.4])
        c1.button("↺ Reset View", key="reset_view", on_click=_reset_view, width="stretch",
                  disabled=ss.chip_mv_view != "3D")
        clean = c2.button("🧲 Clean up geometry (SciPy)", key="optimise", width="stretch", disabled=len(atoms) < 2,
                          help="scipy.optimize.minimize relaxes bond lengths & angles to realistic values")
        inter = c3.button("🧱 Synthesize on Bio-Clay Nanosheets", key="cta_intercalate", width="stretch")
        if clean:
            new_atoms, e0, e1 = optimize_geometry(atoms, bonds)
            _set(new_atoms, bonds, f"SciPy L-BFGS-B optimiser relaxed the structure: strain energy {e0:g} → {e1:g} (model units).")
            ss.mv_energy = (e0, e1)
            st.rerun()
        if inter:
            with st.spinner("Simulating Intercalation…"):
                time.sleep(1.2)
            ss.mv_intercalated = True
            ss.mv_status = "Intercalation complete! Bio-clay gallery expanded to d001 ~ 1.42 nm."
            st.rerun()

        # ---------------- canvas
        with st.container(key="canvas_mv"):
            sel_txt = f" • <b style='color:#f9a8d4'>Selected: {sel_atom['element']} ({sel_atom['id']})</b>" if sel_atom else ""
            show(f'<div style="display:inline-flex;gap:.5rem;align-items:center;font-size:.76rem;color:#fbcfe8;'
                 f'background:rgba(15,23,42,.85);border:1px solid rgba(236,72,153,.3);padding:.3rem .7rem;border-radius:10px">'
                 f'{icon("box", 13, "#f472b6")} Atoms: {len(atoms)} • Bonds: {len(bonds)}{sel_txt}</div>')
            if not atoms:
                show('<div style="height:380px;display:flex;align-items:center;justify-content:center;color:#f9a8d4;font-size:.9rem">'
                     'Empty canvas — generate a molecule or press “＋ Attach”.</div>')
            elif ss.chip_mv_view == "3D":
                fig = molecule_3d(atoms, bonds, ss.mv_selected, ss.mv_intercalated, ss.mv_cam_rev)
                st.plotly_chart(fig, width="stretch", theme=None, key=f"mv3d_{ss.mv_cam_rev}",
                                config={"displaylogo": False, "scrollZoom": True,
                                        "modeBarButtonsToRemove": ["toImage"]})
            else:
                fig2 = molecule_2d(atoms, bonds, ss.mv_selected, ss.mv_intercalated)
                st.pyplot(fig2, width="stretch")
                plt.close(fig2)

        if ss.mv_intercalated:
            show(f"""<div class="bc-note ok" style="margin-top:.8rem">{icon('check-circle', 18, '#059669')}<div>
                 <b style="font-size:.9rem">Successful Bio-Clay Layered Nanocomposite Intercalation!</b><br>
                 The synthesized molecule intercalates efficiently between positively charged Mg-Al hydroxide nanosheets.
                 The basal spacing (d₀₀₁) expands from 0.88 nm to 1.42 nm, shielding the molecular chain and enabling
                 sustained biomedical drug release and polymer reinforcement.</div></div>""")

    _graph_card(atoms, bonds)


def _functional_groups_panel(atoms, sel_atom):
    ss = st.session_state
    with st.container(key="inner_groups"):
        carbons = mb.carbons_sorted(atoms)
        target = mb.target_carbon(atoms, ss.mv_selected)
        g1, g2 = st.columns([2, 3], vertical_alignment="center")
        g1.markdown('<span class="bc-label"><span style="width:9px;height:9px;border-radius:99px;background:#ec4899;display:inline-block"></span>'
                    '4. Add &amp; Remove Functional Groups (Class 11 &amp; 12 Syllabus)</span>', unsafe_allow_html=True)
        with g2:
            if carbons:
                labels = {c["id"]: f"C{i + 1}" + (" •end" if i in (0, len(carbons) - 1) else "") for i, c in enumerate(carbons)}
                ss.mv_target_pills = target["id"] if target else None
                st.pills("Target Carbon in Chain", list(labels), key="mv_target_pills", format_func=labels.get,
                         on_change=_on_target_pill, label_visibility="collapsed")
            else:
                show('<span style="color:#e11d48;font-size:.8rem;font-weight:600">No carbons found</span>')

        a_col, r_col = st.columns([7, 5], gap="medium")
        with a_col:
            show('<div class="bc-row"><span class="bc-label" style="color:var(--chip-text)">'
                 '<span style="width:7px;height:7px;border-radius:99px;background:#10b981;display:inline-block"></span>'
                 '+ What can we ADD to the given chain?</span><span class="mono" style="font-size:.68rem;color:#db2777">Class 11 &amp; 12 Core Groups</span></div>')
            cols = st.columns(2)
            for i, (gid, lbl, desc) in enumerate(mb.ADD_GROUPS):
                cols[i % 2].button(f"＋ {lbl}", key=f"addg_{gid}", help=desc, on_click=_add_group, args=(gid,), width="stretch")
        with r_col:
            show('<div class="bc-row"><span class="bc-label" style="color:#e11d48">'
                 '<span style="width:7px;height:7px;border-radius:99px;background:#f43f5e;display:inline-block"></span>'
                 '− What can we REMOVE from the given chain?</span></div>')
            info = mb.chain_analysis(atoms)
            removals = [("h", "− Remove Hydrogen (-H)"), ("terminal_c", "− Remove Terminal Carbon (-CH₃)")]
            if info["hasSalt"]:
                removals.append(("salt", "− Remove Salt (-COO⁻Na⁺)"))
            if info["hasAmine"]:
                removals.append(("amine", "− Remove Amine (-NH₂)"))
            if info["hasChloride"]:
                removals.append(("chloride", "− Remove Chloride (-Cl)"))
            if info["hasBromide"]:
                removals.append(("bromide", "− Remove Bromide (-Br)"))
            removals.append(("functional_group", "− Remove Functional Group"))
            for kind, lbl in removals:
                st.button(lbl, key=f"rm_{kind}", on_click=_remove, args=(kind,), width="stretch")
            if sel_atom:
                st.button(f"🗑 − Extract Selected Atom ({sel_atom['element']})", key="danger_extract", on_click=_delete,
                          width="stretch")


def _graph_card(atoms, bonds):
    ss = st.session_state
    with st.container(key="card_graph"):
        show("""<div class="bc-eyebrow">Computational Thinking Extension · NetworkX · NumPy · SciPy</div>
             <div class="bc-h2">Your Molecule as a Graph</div>
             <div class="bc-muted">Atoms are <b>nodes</b>, bonds are <b>edges</b>. Graph algorithms check valency, find the longest
             carbon chain (how IUPAC names are chosen), count rings and measure every bond length.</div>
             <div class="bc-divider"></div>""")
        if not atoms:
            st.info("Draw or generate a molecule to analyse it.")
            return
        an = analyze_molecule(atoms, bonds)
        ok = badge("All valencies satisfied", "green", "check-circle") if an["all_valences_ok"] else badge("Open / over-filled valence", "amber", "alert")
        dou = an["dou"]
        dou_txt = f"{dou:g}" + (" (radical)" if dou != int(dou) else "")
        show(f"""<div class="bc-grid c4">
             <div class="bc-stat"><div class="k">{icon('flask', 14)}Hill formula</div><div class="v mono">{esc(an['hill'])}</div><div class="s">computed from the atoms</div></div>
             <div class="bc-stat"><div class="k">{icon('scale', 14)}Exact mass</div><div class="v">{an['mw']}<small>g/mol</small></div><div class="s">Σ atoms × atomic mass</div></div>
             <div class="bc-stat"><div class="k">{icon('ruler', 14)}Longest carbon chain</div><div class="v pink">{an['longest_chain']}<small>C</small></div><div class="s">graph diameter of carbons</div></div>
             <div class="bc-stat"><div class="k">{icon('layers', 14)}Rings + π bonds</div><div class="v">{dou_txt}</div><div class="s">degree of unsaturation</div></div>
             </div>
             <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin:.7rem 0">{ok}{badge(f"{an['components']} connected fragment(s)", 'mono')}
             {badge(f"{an['rings']} ring(s) in graph", 'mono')}{badge(f"{an['n_atoms']} nodes · {an['n_bonds']} edges", 'mono')}</div>""")
        if ss.mv_energy:
            st.caption(f"Last SciPy geometry optimisation: strain energy {ss.mv_energy[0]:g} → {ss.mv_energy[1]:g}")

        t1, t2, t3, t4 = st.tabs(["✅ Valence check", "📏 Bond geometry", "🕸 Graph view", "🔢 Adjacency matrix"])
        with t1:
            table(an["valence_table"], max_height=420)
        with t2:
            geo = bond_geometry_table(atoms, bonds)
            table(geo, max_height=420)
            clashes = close_contacts(atoms, bonds)
            if clashes:
                st.warning("Atoms overlapping (not bonded but < 0.9 Å apart): " +
                           ", ".join(f"{a}–{b} ({d} Å)" for a, b, d in clashes) + " → try “Clean up geometry”.")
            st.caption("Model length uses the drawing scale 55 units = 1.54 Å (a C–C bond). Ideal length = sum of covalent radii "
                       "(shorter for double/triple bonds).")
        with t3:
            fig = graph_figure(an["graph"], atoms, bool(ss.get("dark")))
            st.pyplot(fig, width="stretch")
            plt.close(fig)
        with t4:
            order = [a["id"] for a in atoms]
            A = np.zeros((len(order), len(order)))
            idx = {k: i for i, k in enumerate(order)}
            for b in bonds:
                if b["sourceId"] in idx and b["targetId"] in idx:
                    i, j = idx[b["sourceId"]], idx[b["targetId"]]
                    A[i, j] = A[j, i] = b.get("order", 1)
            lbl = [f"{mb.find_atom(atoms, k)['element']}·{k}" for k in order]
            fig = go.Figure(go.Heatmap(z=A, x=lbl, y=lbl, colorscale=[[0, "rgba(252,231,243,0.15)"], [0.34, "#f9a8d4"], [0.67, "#db2777"], [1, "#831843"]],
                                       zmin=0, zmax=3, colorbar=dict(title="bond order"),
                                       hovertemplate="%{y} – %{x}: order %{z}<extra></extra>"))
            fig.update_layout(**plotly_layout(height=460, margin=dict(l=10, r=10, t=10, b=10)))
            fig.update_yaxes(autorange="reversed", tickfont=dict(size=9), automargin=True)
            fig.update_xaxes(tickfont=dict(size=9), automargin=True)
            st.plotly_chart(fig, width="stretch", theme=None, config={"displaylogo": False}, key="adj")
            st.caption(f"Adjacency matrix A (NumPy). Number of bonds = ½·ΣAᵢⱼ>0 = {int((A > 0).sum() / 2)}; "
                       f"bond-order sum = {A.sum() / 2:g}. The matrix is symmetric because a bond A–B is also B–A.")
