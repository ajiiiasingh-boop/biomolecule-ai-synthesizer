"""
components.py - small reusable HTML building blocks (header, badges, stat cards ...).

Streamlit draws the widgets (buttons, inputs). Anything that is only *displayed*
is written as a little HTML string here so it can look exactly like the old website.
"""

from __future__ import annotations

import html as _html

import streamlit as st

from .icons import icon


def esc(text) -> str:
    """Escape user text before putting it inside HTML (so '<' in a formula can't break the page)."""
    return _html.escape(str(text), quote=True)


def show(html_str: str) -> None:
    """Render an HTML snippet. Lines are stripped so Markdown never mistakes them for code blocks."""
    st.markdown(" ".join(line.strip() for line in html_str.splitlines() if line.strip()), unsafe_allow_html=True)


def badge(text: str, kind: str = "", ic: str | None = None) -> str:
    return f'<span class="bc-badge {kind}">{icon(ic, 12) if ic else ""}{esc(text)}</span>'


def section_header(eyebrow: str, title: str, subtitle: str = "", right_html: str = "", ic: str | None = None) -> None:
    show(f"""
    <div class="bc-row" style="align-items:flex-start;margin-bottom:.35rem">
      <div style="flex:1;min-width:260px">
        <div class="bc-eyebrow" style="display:flex;align-items:center;gap:.4rem">{icon(ic, 14) if ic else ""}{esc(eyebrow)}</div>
        <div class="bc-h2">{esc(title)}</div>
        {f'<div class="bc-muted">{esc(subtitle)}</div>' if subtitle else ''}
      </div>
      <div>{right_html}</div>
    </div>
    <div class="bc-divider"></div>
    """)


def label(text: str, right: str = "", ic: str | None = None, color: str | None = None) -> None:
    style = f' style="color:{color}"' if color else ""
    show(f'<div class="bc-row" style="margin:.35rem 0 .25rem 0"><span class="bc-label"{style}>'
         f'{icon(ic, 13) if ic else ""}{esc(text)}</span><span class="bc-muted" style="font-size:.72rem">{right}</span></div>')


def stat_card(ic: str, key: str, value, unit: str = "", sub: str = "", pink: bool = False) -> str:
    return (f'<div class="bc-stat"><div class="k">{icon(ic, 14)}<span>{esc(key)}</span></div>'
            f'<div class="v {"pink" if pink else ""}">{esc(value)}<small>{esc(unit)}</small></div>'
            f'{f"<div class=s>{esc(sub)}</div>" if sub else ""}</div>')


def progress(pct: float) -> str:
    pct = max(0.0, min(100.0, float(pct)))
    return f'<div class="bc-progress"><div style="width:{pct:.0f}%"></div></div>'


def note(text_html: str, kind: str = "info", ic: str = "help") -> None:
    show(f'<div class="bc-note {kind}">{icon(ic, 16)}<div>{text_html}</div></div>')


def app_header(ai_connected: bool, busy: bool = False) -> None:
    status = ("Gemini AI Connected", "") if ai_connected else ("Offline Rules Engine", "")
    show(f"""
    <div style="display:flex;align-items:center;gap:.8rem;padding:.2rem 0">
      <div style="width:44px;height:44px;border-radius:14px;background:linear-gradient(45deg,#db2777,#f43f5e,#9333ea);
                  display:flex;align-items:center;justify-content:center;color:#fff;box-shadow:0 6px 14px rgba(236,72,153,.28)">
        {icon("atom", 22, "#fff")}
      </div>
      <div>
        <div style="display:flex;align-items:center;gap:.5rem;flex-wrap:wrap">
          <span style="font-weight:800;font-size:1.25rem;letter-spacing:-.01em;background:linear-gradient(90deg,#be185d,#e11d48,#7e22ce);
                -webkit-background-clip:text;background-clip:text;color:transparent">Bio-Clay AI Synthesizer</span>
          <span class="bc-badge mono" style="font-size:.62rem;letter-spacing:.06em;text-transform:uppercase">v2.4 Pro · Python Edition</span>
        </div>
        <div class="bc-muted" style="font-size:.74rem;font-weight:500">Medical Engineering Molecular Design &amp; Feasibility Lab</div>
      </div>
    </div>
    """)


def status_badge(ai_connected: bool) -> None:
    if ai_connected:
        show(f'<div style="display:flex;justify-content:flex-end;padding-top:.55rem">{badge("Gemini AI Connected", "", "sparkles")}</div>')
    else:
        show(f'<div style="display:flex;justify-content:flex-end;padding-top:.55rem">{badge("Offline Rules Engine (add key in sidebar for Gemini)", "", "cpu")}</div>')


def footer() -> None:
    show('<div class="bc-footer">Bio-Clay Molecular Synthesis Platform • Rebuilt 100% in Python '
         '(Streamlit · NumPy · Pandas · SciPy · Plotly · NetworkX · Matplotlib) • Optional Gemini AI</div>')


def table(df, max_height: int | None = None) -> None:
    """Show a pandas DataFrame as a pink HTML table (looks right in light AND dark mode)."""
    html_table = df.to_html(index=False, escape=True, border=0, classes="bc-table")
    wrap = f'<div style="max-height:{max_height}px;overflow:auto;border-radius:12px">' if max_height else "<div>"
    show(wrap + html_table + "</div>")
