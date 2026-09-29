"""
state.py - everything the app must "remember" between clicks lives in st.session_state.

Streamlit re-runs the whole script after every click, so variables would normally be lost.
st.session_state is a dictionary that survives those re-runs (like React's useState).
"""

import copy

import streamlit as st

from core.chemistry import HYDROGEN_LABEL, SALT_LABEL
from core.molecule_builder import build_molecule_from_input
from core.rules_engine import DEFAULT_GAME_RESULT, DEFAULT_SYNTHESIS_REPORT

NAV_ITEMS = {
    "designer": ":material/science: 1. Molecule Designer",
    "synthesis": ":material/memory: 2. AI Synthesis & Feasibility",
    "properties": ":material/bar_chart: 3. Property Comparison",
    "molview": ":material/deployed_code: 4. MolView 2D/3D Lab",
    "game": ":material/sports_esports: 5. Element Slide Game",
}

# Widget keys whose value must survive while their tab is hidden.
PERSIST_KEYS = [
    "custom_molecule", "chip_action", "chip_target", "chip_cat", "group_search", "custom_group_input",
    "mv_input", "chip_mv_el", "chip_mv_bond", "chip_mv_view", "chip_metric", "chip_challenge",
    "sim_temp", "api_key_input", "mv_connect", "mv_place_x", "mv_place_y", "mv_place_z",
]


def init_state() -> None:
    ss = st.session_state
    first = "initialised" not in ss
    defaults = {
        "nav": "designer",
        "dark": False,
        "api_key_input": "",
        # ---- 1. Designer
        "custom_molecule": "CH3-CH2-CH3",
        "chip_action": "remove_h",
        "chip_target": "C3",
        "chip_cat": "all",
        "group_search": "",
        "custom_group_input": "",
        "removed_groups": [HYDROGEN_LABEL],
        "added_groups": [SALT_LABEL],
        "designer_msg": "",
        # ---- 2. Synthesis
        "report": copy.deepcopy(DEFAULT_SYNTHESIS_REPORT),
        "api_source": "preset",
        "sim_temp": None,
        # ---- 3. Properties
        "chip_metric": "ionizationEnergy",
        # ---- 4. MolView
        "mv_input": "CH3-CH2-CH3",
        "chip_mv_el": "C",
        "chip_mv_bond": "single",
        "chip_mv_view": "3D",
        "mv_selected": None,
        "mv_select": "— none —",
        "mv_connect": "— none —",
        "mv_intercalated": False,
        "mv_cam_rev": 0,
        "mv_synced_from": None,
        "mv_energy": None,
        "mv_place_x": 0,
        "mv_place_y": 0,
        "mv_place_z": 0,
        # ---- 5. Game
        "g_counts": {"C": 3, "H": 7, "-COO⁻Na⁺": 1},
        "chip_challenge": 1,
        "g_score": 120,
        "g_result": copy.deepcopy(DEFAULT_GAME_RESULT),
        "g_show": True,
        "g_source": "preset",
        "g_completed": [],
    }
    for k, v in defaults.items():
        if k not in ss:
            ss[k] = v

    if first:
        mol = build_molecule_from_input(ss.custom_molecule)
        ss.mv_atoms, ss.mv_bonds = mol["atoms"], mol["bonds"]
        ss.mv_info = {"name": mol["displayName"], "formula": mol["formula"], "description": mol["description"]}
        ss.mv_status = (f"Rendered {mol['displayName']} in 3D & 2D. Enter any molecule name or carbon chain above, "
                        "or pick atoms to modify.")
        ss.mv_synced_from = ss.custom_molecule
        ss.initialised = True

    # Re-save widget keys so Streamlit does not forget them while their tab is not shown.
    for k in PERSIST_KEYS:
        if k in ss:
            ss[k] = ss[k]

    # A "go to tab" request from the previous run (buttons cannot change the nav after it is drawn)
    if "_goto" in ss:
        ss.nav = ss.pop("_goto")


def goto(tab: str) -> None:
    """Button callback: switch tab."""
    st.session_state.nav = tab
