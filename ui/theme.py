"""
theme.py - the pink "Bio-Clay" look (#fff0f5 background) written as CSS, plus a dark mode.

Colours are copied from the Tailwind classes of the old React website
(bg-[#fff0f5], pink-200 borders, pink-600 buttons, dark bg-[#110710] ...).
"""

import streamlit as st

LIGHT = {
    "bg": "#fff0f5", "card": "rgba(255,240,245,0.92)", "inner": "rgba(255,255,255,0.92)", "inner2": "rgba(253,242,248,0.75)",
    "border": "#fbcfe8", "border_soft": "rgba(251,207,232,0.7)", "text": "#1e293b", "heading": "#500724",
    "muted": "rgba(157,23,77,0.82)", "accent": "#db2777", "accent_text": "#be185d", "chip": "rgba(252,231,243,0.85)",
    "chip_text": "#831843", "slate": "#64748b", "nav_bg": "rgba(255,255,255,0.6)",
    "green_bg": "#d1fae5", "green_text": "#065f46", "amber_bg": "#fef3c7", "amber_text": "#92400e",
    "rose_bg": "#ffe4e6", "rose_text": "#9f1239", "dot": "#ec4899",
}
DARK = {
    "bg": "#110710", "card": "rgba(31,17,29,0.92)", "inner": "rgba(15,23,42,0.9)", "inner2": "rgba(30,41,59,0.6)",
    "border": "rgba(131,24,67,0.6)", "border_soft": "rgba(131,24,67,0.45)", "text": "#fce7f3", "heading": "#fce7f3",
    "muted": "rgba(249,168,212,0.82)", "accent": "#f472b6", "accent_text": "#f9a8d4", "chip": "rgba(80,7,36,0.55)",
    "chip_text": "#fbcfe8", "slate": "#94a3b8", "nav_bg": "rgba(21,10,20,0.6)",
    "green_bg": "rgba(6,78,59,0.55)", "green_text": "#6ee7b7", "amber_bg": "rgba(120,53,15,0.45)", "amber_text": "#fcd34d",
    "rose_bg": "rgba(136,19,55,0.45)", "rose_text": "#fda4af", "dot": "#be185d",
}

# Extra CSS used only in dark mode: recolours Streamlit's own widgets (text boxes, dropdowns, tabs ...)
DARK_WIDGETS = """
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stMarkdownContainer"] p, .stApp li,
[data-testid="stSidebar"] *, .stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] summary p { color: #fce7f3; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: #d8b4c8 !important; }
[data-testid="stTextInputRootElement"], .stSelectbox [role="group"], [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div,
[data-testid="stNumberInputContainer"], [data-testid="stNumberInput"] input {
  background: #1f111d !important; border-color: rgba(131,24,67,.7) !important; color: #fce7f3 !important; }
.stApp input, .stApp textarea { color: #fce7f3 !important; -webkit-text-fill-color: #fce7f3 !important; background: transparent !important; }
.stApp input::placeholder, .stApp textarea::placeholder { color: #a8879b !important; -webkit-text-fill-color: #a8879b !important; }
[data-baseweb="select"] span, [data-baseweb="select"] svg, .stSelectbox button svg, [data-testid="stNumberInput"] button { color: #fce7f3 !important; fill: #fce7f3 !important; }
[data-testid="stNumberInput"] button { background: #2a1727 !important; }
[data-testid="stSelectboxVirtualDropdown"] { background: #1f111d !important; border: 1px solid rgba(131,24,67,.7) !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"] { background: #1f111d !important; color: #fce7f3 !important; }
[data-testid="stSelectboxVirtualDropdown"] [role="option"]:hover, [data-testid="stSelectboxVirtualDropdown"] [role="option"][aria-selected="true"] { background: #500724 !important; }
[data-baseweb="popover"] ul, [data-baseweb="popover"] li, [data-baseweb="menu"] { background: #1f111d !important; color: #fce7f3 !important; }
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [aria-selected="true"] { background: #500724 !important; }
[data-baseweb="tab-list"] button p, [data-baseweb="tab"] p { color: #fbcfe8 !important; }
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"] { color: #f9a8d4 !important; }
[data-testid="stCheckbox"] label p, .stToggle label p { color: #fce7f3 !important; }
[data-testid="stHeader"] button, [data-testid="stHeader"] svg, [data-testid="stExpandSidebarButton"] svg { color: #f9a8d4 !important; }
.katex { color: #fce7f3; }
[data-testid="stAlertContainer"] { filter: saturate(.9); }
"""


def palette() -> dict:
    return DARK if st.session_state.get("dark") else LIGHT


def inject_css() -> None:
    p = palette()
    dark = bool(st.session_state.get("dark"))
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');
:root {{
  --bg:{p['bg']}; --card:{p['card']}; --inner:{p['inner']}; --inner2:{p['inner2']}; --border:{p['border']};
  --border-soft:{p['border_soft']}; --text:{p['text']}; --heading:{p['heading']}; --muted:{p['muted']};
  --accent:{p['accent']}; --accent-text:{p['accent_text']}; --chip:{p['chip']}; --chip-text:{p['chip_text']};
  --slate:{p['slate']}; --green-bg:{p['green_bg']}; --green-text:{p['green_text']}; --amber-bg:{p['amber_bg']};
  --amber-text:{p['amber_text']}; --rose-bg:{p['rose_bg']}; --rose-text:{p['rose_text']}; --dot:{p['dot']};
  --grad: linear-gradient(90deg,#db2777 0%,#f43f5e 50%,#9333ea 100%);
}}
html, body, .stApp, [data-testid="stAppViewContainer"] {{ background: var(--bg) !important; color: var(--text);
  font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif; }}
[data-testid="stHeader"] {{ background: transparent !important; }}
.block-container, [data-testid="stMainBlockContainer"] {{ max-width: 1280px; padding-top: 3.2rem !important; padding-bottom: 1rem; }}
p, li, label, span, div {{ font-family: inherit; }}
code, .mono {{ font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace !important; }}

/* ---------- cards: any container created with key="card_..." ---------- */
[class*="st-key-card_"] {{ background: var(--card) !important; border: 1px solid var(--border) !important;
  border-radius: 18px !important; padding: 1.25rem 1.35rem !important; box-shadow: 0 1px 2px rgba(190,24,93,.06); backdrop-filter: blur(8px); }}
[class*="st-key-inner_"] {{ background: var(--inner) !important; border: 1px solid var(--border) !important;
  border-radius: 16px !important; padding: 1rem 1.1rem !important; }}
[class*="st-key-canvas_"] {{ background: linear-gradient(180deg,#020617 0%,#0f172a 60%,rgba(80,7,36,.55) 100%) !important;
  border: 1px solid rgba(249,168,212,.35) !important; border-radius: 18px !important; padding: .6rem !important; }}

/* ---------- top navigation (key="nav") and every chip-style radio (key="chip_...") ---------- */
.st-key-nav {{ background: {p['nav_bg']}; border-top: 1px solid var(--border-soft); border-bottom: 1px solid var(--border-soft);
  padding: .5rem .25rem; margin: .1rem 0 .6rem 0; border-radius: 14px; }}
.st-key-nav [data-testid="stRadioGroup"], [class*="st-key-chip_"] [data-testid="stRadioGroup"] {{ gap: .4rem !important; flex-wrap: wrap; }}
.st-key-nav label[data-testid="stRadioOption"], [class*="st-key-chip_"] label[data-testid="stRadioOption"] {{
  background: var(--chip); color: var(--chip-text); padding: .45rem .8rem; border-radius: 12px; margin: 0 !important;
  transition: all .15s; border: 1px solid var(--border-soft); cursor: pointer; }}
[class*="st-key-chip_"] label[data-testid="stRadioOption"] {{ padding: .3rem .65rem; border-radius: 10px; }}
.st-key-nav label[data-testid="stRadioOption"]:hover, [class*="st-key-chip_"] label[data-testid="stRadioOption"]:hover {{ border-color: #f472b6; }}
.st-key-nav label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]),
[class*="st-key-chip_"] label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {{ display: none !important; }}
.st-key-nav label[data-testid="stRadioOption"][data-selected="true"],
[class*="st-key-chip_"] label[data-testid="stRadioOption"][data-selected="true"] {{ background: #db2777; border-color: #db2777;
  box-shadow: 0 4px 12px rgba(219,39,119,.22); }}
.st-key-nav label[data-testid="stRadioOption"][data-selected="true"] *,
[class*="st-key-chip_"] label[data-testid="stRadioOption"][data-selected="true"] * {{ color: #fff !important; }}
.st-key-nav label[data-testid="stRadioOption"] p {{ font-size: .86rem; font-weight: 600; }}
[class*="st-key-chip_"] label[data-testid="stRadioOption"] p {{ font-size: .8rem; font-weight: 600; }}
.st-key-nav label[data-testid="stRadioOption"][data-selected="true"] {{ transform: scale(1.02); }}

/* ---------- buttons ---------- */
.st-key-chip_target [data-testid="stRadioGroup"] {{ justify-content: center; }}
.st-key-chip_target label[data-testid="stRadioOption"] {{ min-width: 42px; justify-content: center; font-family: 'JetBrains Mono', monospace; }}
.stButton button, .stDownloadButton button {{ border-radius: 12px !important; font-weight: 600 !important; }}
.stButton button[kind="secondary"], .stDownloadButton button {{ background: var(--chip) !important; color: var(--chip-text) !important;
  border: 1px solid var(--border) !important; }}
.stButton button[kind="secondary"]:hover {{ border-color: #db2777 !important; color: #db2777 !important; }}
[class*="st-key-cta_"] .stButton button[kind] {{ background: var(--grad) !important; color: #fff !important; border: none !important;
  box-shadow: 0 6px 16px rgba(219,39,119,.22); padding-top: .65rem !important; padding-bottom: .65rem !important; }}
[class*="st-key-cta_"] .stButton button[kind]:hover {{ filter: brightness(1.06); color: #fff !important; }}
[class*="st-key-cta_"] .stButton button[kind] p {{ color: #fff !important; font-weight: 700; }}
[class*="st-key-dark_"] .stButton button[kind] {{ background: #831843 !important; color: #fff !important; border: none !important; }}
[class*="st-key-rm_"] .stButton button[kind], [class*="st-key-danger_"] .stButton button[kind] {{ background: var(--rose-bg) !important; color: var(--rose-text) !important; border: 1px solid rgba(244,63,94,.35) !important; }}
[class*="st-key-rm_"] .stButton button[kind]:hover, [class*="st-key-danger_"] .stButton button[kind]:hover {{ background: #e11d48 !important; color: #fff !important; }}
[class*="st-key-el_"] .stButton button[kind] {{ min-height: 74px; white-space: pre-line; line-height: 1.25; background: var(--inner) !important; }}
[class*="st-key-el_"] .stButton button[kind] p {{ white-space: pre-line; }}
[class*="st-key-frag_"] .stButton button[kind] {{ min-height: 56px; white-space: pre-line; background: var(--inner2) !important; }}
[class*="st-key-frag_"] .stButton button[kind] p {{ white-space: pre-line; font-family: 'JetBrains Mono', monospace; }}

/* ---------- pills (multi-select chips) ---------- */
button[data-variant="pills"] {{ background: var(--inner) !important; border: 1px solid var(--border) !important; color: var(--text) !important; }}
button[data-variant="pills"] p {{ font-size: .78rem !important; }}
button[data-variant="pills"]:hover {{ border-color: #db2777 !important; }}
button[data-variant="pills"][aria-pressed="true"] {{ background: #db2777 !important; border-color: #db2777 !important; }}
button[data-variant="pills"][aria-pressed="true"] * {{ color: #fff !important; }}
.st-key-rm_pills button[data-variant="pills"][aria-pressed="true"] {{ background: #f43f5e !important; border-color: #f43f5e !important; }}
[class*="st-key-scroll_"] {{ background: var(--inner2); border: 1px solid var(--border) !important; border-radius: 12px; }}

/* ---------- small text helpers used by the HTML snippets ---------- */
.bc-eyebrow {{ font-size: .72rem; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: var(--accent); }}
.bc-h2 {{ font-size: 1.28rem; font-weight: 800; color: var(--heading); margin: .15rem 0 .1rem 0; line-height: 1.3; }}
.bc-h3 {{ font-size: .95rem; font-weight: 700; color: var(--heading); display:flex; align-items:center; gap:.45rem; }}
.bc-muted {{ font-size: .8rem; color: var(--muted); line-height: 1.55; }}
.bc-label {{ font-size: .72rem; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; color: var(--chip-text); display:flex; align-items:center; gap:.4rem; }}
.bc-row {{ display:flex; align-items:center; justify-content:space-between; gap:.6rem; flex-wrap: wrap; }}
.bc-badge {{ display:inline-flex; align-items:center; gap:.3rem; font-size:.72rem; font-weight:700; padding:.18rem .6rem; border-radius:999px;
  background: var(--chip); color: var(--chip-text); border: 1px solid var(--border); white-space: nowrap; }}
.bc-badge.mono {{ border-radius: 8px; }}
.bc-badge.green {{ background: var(--green-bg); color: var(--green-text); border-color: transparent; }}
.bc-badge.amber {{ background: var(--amber-bg); color: var(--amber-text); border-color: transparent; }}
.bc-badge.rose {{ background: var(--rose-bg); color: var(--rose-text); border-color: transparent; }}
.bc-divider {{ height:1px; background: var(--border-soft); margin: .8rem 0; }}
.bc-inner {{ background: var(--inner); border: 1px solid var(--border); border-radius: 14px; padding: .85rem 1rem; }}
.bc-soft {{ background: var(--inner2); border: 1px solid var(--border-soft); border-radius: 12px; padding: .7rem .85rem; font-size: .8rem; color: var(--text); }}
.bc-stat {{ background: var(--inner); border: 1px solid var(--border); border-radius: 14px; padding: .8rem .9rem; height: 100%; transition: border-color .15s; }}
.bc-stat:hover {{ border-color: #f472b6; }}
.bc-stat .k {{ display:flex; align-items:center; gap:.35rem; font-size:.76rem; font-weight:600; color: var(--accent-text); }}
.bc-stat .v {{ font-size: 1.15rem; font-weight: 800; color: var(--text); margin-top: .25rem; }}
.bc-stat .v.pink {{ color: var(--accent-text); }}
.bc-stat .v small {{ font-size: .72rem; font-weight: 500; color: var(--slate); margin-left: .25rem; }}
.bc-stat .s {{ font-size: .68rem; color: var(--slate); margin-top: .15rem; }}
.bc-grid {{ display:grid; gap:.8rem; }}
.bc-grid.c2 {{ grid-template-columns: repeat(2, minmax(0,1fr)); }}
.bc-grid.c3 {{ grid-template-columns: repeat(3, minmax(0,1fr)); }}
.bc-grid.c4 {{ grid-template-columns: repeat(4, minmax(0,1fr)); }}
@media (max-width: 900px) {{ .bc-grid.c3, .bc-grid.c4 {{ grid-template-columns: repeat(2, minmax(0,1fr)); }} }}
.bc-visual {{ position:relative; overflow:hidden; background: var(--inner); border:1px solid var(--border); border-radius:18px;
  padding: 1.6rem 1.2rem; text-align:center; }}
.bc-visual:before {{ content:""; position:absolute; inset:0; opacity:.12; background-image: radial-gradient(var(--dot) 1.5px, transparent 1.5px); background-size:16px 16px; }}
.bc-visual > * {{ position: relative; }}
.bc-formula {{ font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--accent-text); font-size: 1.35rem; letter-spacing: .03em;
  margin: .7rem 0; word-break: break-word; }}
.bc-pill {{ display:inline-flex; align-items:center; gap:.3rem; padding:.28rem .65rem; border-radius:8px; font-size:.76rem; }}
.bc-pill.rm {{ background: var(--rose-bg); color: var(--rose-text); border: 1px solid rgba(244,63,94,.3); }}
.bc-pill.add {{ background: var(--chip); color: var(--accent-text); border: 1px solid var(--border); }}
.bc-step {{ display:flex; gap:.7rem; align-items:flex-start; padding:.6rem .75rem; border-radius:12px; background: var(--inner2);
  border:1px solid var(--border-soft); font-size:.82rem; line-height:1.55; color: var(--text); margin-bottom:.5rem; }}
.bc-step .n {{ width:22px; height:22px; border-radius:999px; background:#db2777; color:#fff; font-weight:700; font-size:.72rem;
  display:flex; align-items:center; justify-content:center; flex-shrink:0; margin-top:1px; }}
.bc-note {{ display:flex; gap:.5rem; align-items:flex-start; padding:.7rem .85rem; border-radius:12px; font-size:.8rem; line-height:1.5; }}
.bc-note.warn {{ background: var(--amber-bg); color: var(--amber-text); border: 1px solid rgba(245,158,11,.35); }}
.bc-note.ok {{ background: var(--green-bg); color: var(--green-text); border: 1px solid rgba(16,185,129,.35); }}
.bc-note.info {{ background: var(--chip); color: var(--chip-text); border: 1px solid var(--border); }}
.bc-table {{ width:100%; border-collapse: separate; border-spacing:0; font-size:.8rem; color: var(--text); }}
.bc-table th {{ background: var(--chip); color: var(--heading); text-transform: uppercase; letter-spacing:.04em; font-size:.7rem;
  text-align:left; padding:.65rem .7rem; }}
.bc-table th:first-child {{ border-radius: 12px 0 0 12px; }} .bc-table th:last-child {{ border-radius: 0 12px 12px 0; }}
.bc-table td {{ padding:.62rem .7rem; border-bottom:1px solid var(--border-soft); vertical-align: top; }}
.bc-table tr.active td {{ background: var(--chip); font-weight: 700; }}
.bc-table td.orig {{ color: var(--slate); font-family:'JetBrains Mono',monospace; }}
.bc-table td.mod {{ color: var(--accent-text); font-weight:700; font-family:'JetBrains Mono',monospace; }}
.bc-delta {{ display:inline-flex; align-items:center; gap:.2rem; padding:.12rem .45rem; border-radius:6px; font-size:.72rem; font-weight:700; }}
.bc-delta.up {{ background: var(--green-bg); color: var(--green-text); }}
.bc-delta.down {{ background: var(--rose-bg); color: var(--rose-text); }}
.bc-delta.zero {{ background: var(--inner2); color: var(--slate); }}
.bc-chain {{ display:flex; flex-wrap:wrap; justify-content:center; align-items:center; gap:.3rem; padding:.3rem 0; }}
.bc-chain .c {{ width:36px; height:36px; border-radius:11px; display:flex; align-items:center; justify-content:center; font-family:'JetBrains Mono',monospace;
  font-size:.74rem; font-weight:700; background: var(--inner2); border:1px solid var(--border); color: var(--text); }}
.bc-chain .c.on {{ background:#db2777; color:#fff; box-shadow: 0 0 0 3px rgba(244,114,182,.45); transform: scale(1.08); }}
.bc-chain .b {{ color:#f472b6; font-weight:700; font-family:'JetBrains Mono',monospace; font-size:.75rem; }}
.bc-footer {{ text-align:center; font-size:.74rem; color: var(--muted); padding: 1rem 0 .4rem 0; border-top: 1px solid var(--border-soft); margin-top: 1.4rem; }}
.bc-dock {{ min-height: 60px; padding:.7rem; border-radius:14px; border:1.5px dashed #f9a8d4; background: var(--inner2); }}
.bc-progress {{ height: 8px; border-radius: 999px; background: var(--chip); overflow: hidden; }}
.bc-progress > div {{ height:100%; background: var(--grad); border-radius: 999px; }}

/* widget labels a bit smaller and pink like the original */
[data-testid="stWidgetLabel"] p {{ font-size: .74rem !important; font-weight: 700 !important; letter-spacing: .05em; text-transform: uppercase; color: var(--chip-text) !important; }}
.st-key-nav [data-testid="stWidgetLabel"] {{ display:none; }}
[data-testid="stExpander"] details {{ border-radius: 14px !important; border-color: var(--border) !important; background: var(--inner); }}
[data-testid="stMetricValue"] {{ color: var(--accent-text); }}
[data-testid="stSidebar"] {{ background: {"#1a0f19" if dark else "#ffe4ef"} !important; }}
{DARK_WIDGETS if dark else ""}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def plotly_layout(**extra) -> dict:
    """Common Plotly styling so every chart matches the pink theme."""
    p = palette()
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color=p["text"], size=12),
        margin=dict(l=10, r=10, t=36, b=10),
        colorway=["#94a3b8", "#db2777", "#9333ea", "#f43f5e", "#f59e0b", "#0ea5e9"],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(font=dict(family="Inter, sans-serif")),
    )
    base.update(extra)
    return base


def axis_style() -> dict:
    p = palette()
    return dict(gridcolor="rgba(236,72,153,0.15)", zerolinecolor="rgba(236,72,153,0.3)", linecolor=p["border"],
                automargin=True, tickfont=dict(color=p["slate"]), title_font=dict(color=p["text"]))
