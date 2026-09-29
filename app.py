"""
Bio-Clay AI Synthesizer — Python Edition
========================================
Run with:   streamlit run app.py

This is the main file. It only:
  1. sets up the page + pink theme,
  2. draws the header and the 5 navigation tabs,
  3. calls the right "tab" module from the ui/ folder.

All chemistry lives in core/ (pure Python, no web code), all drawing lives in ui/.
"""

import streamlit as st

st.set_page_config(
    page_title="Bio-Clay AI Synthesizer",
    page_icon="⚛️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from core.ai_engine import GENAI_AVAILABLE, resolve_api_key  # noqa: E402
from core.chemistry import calculate_realtime_properties, parse_molecule_input  # noqa: E402
from ui import designer, game, molview, properties, synthesis  # noqa: E402
from ui.components import app_header, footer, status_badge  # noqa: E402
from ui.state import NAV_ITEMS, init_state  # noqa: E402
from ui.theme import inject_css  # noqa: E402

# ------------------------------------------------------------------ 1. state + theme
init_state()
ss = st.session_state
inject_css()

# ------------------------------------------------------------------ 2. sidebar (optional Gemini key)
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.text_input("Gemini API key (optional)", key="api_key_input", type="password",
                  help="Leave empty to use the offline rules engine. You can also put GEMINI_API_KEY in a .env file.")
    if not GENAI_AVAILABLE:
        st.caption("`google-genai` is not installed → offline rules engine only.")
    st.markdown("---")
    st.markdown("**Libraries used**  \nStreamlit · NumPy · Pandas · SciPy · Plotly · Matplotlib · NetworkX · google-genai · python-dotenv")
    st.caption("Tip: everything works without internet — Gemini is only an optional upgrade.")

api_key = resolve_api_key(ss.api_key_input)
ai_ready = bool(api_key and GENAI_AVAILABLE)

# ------------------------------------------------------------------ 3. header + navigation
h_left, h_mid, h_right = st.columns([6, 3.4, 1.3], vertical_alignment="center")
with h_left:
    app_header(ai_ready)
with h_mid:
    status_badge(ai_ready)
with h_right:
    st.toggle("🌙", key="dark", help="Switch between the pink light theme and dark theme")

st.radio("Navigation", list(NAV_ITEMS), key="nav", format_func=NAV_ITEMS.get, horizontal=True,
         label_visibility="collapsed")

# ------------------------------------------------------------------ 4. shared calculations (like React's useMemo)
parsed = parse_molecule_input(ss.custom_molecule)
current_base = parsed["preset"]
props = calculate_realtime_properties(current_base, ss.removed_groups, ss.added_groups)

# ------------------------------------------------------------------ 5. show the selected tab
if ss.nav == "designer":
    designer.render(parsed, props, api_key, ai_ready)
elif ss.nav == "synthesis":
    synthesis.render(props, api_key, ai_ready)
elif ss.nav == "properties":
    properties.render(props, current_base.name, ss.report["moleculeName"])
elif ss.nav == "molview":
    molview.render()
elif ss.nav == "game":
    game.render(api_key, ai_ready)

footer()
