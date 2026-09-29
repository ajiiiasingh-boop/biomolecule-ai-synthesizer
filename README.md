# ⚛️ Bio-Clay AI Synthesizer — Python Edition

The same Bio-Clay website (pink `#fff0f5` theme, 5 tabs, same chemistry), rebuilt **100 % in Python**
for the Computational Thinking course. There is no HTML, CSS or JavaScript code to write: Streamlit turns
Python into the web page.

| Tab | What it does | Python libraries |
|---|---|---|
| 1. Molecule Designer | Type a carbon chain, pick the target carbon, remove / add functional groups, live property matrix | Streamlit, `re`, dataclasses |
| 2. AI Synthesis & Feasibility | Lab protocol, temperature, pH, safety + **kinetics simulator** | SciPy `solve_ivp`, Plotly, optional Gemini |
| 3. Property Comparison | Original vs modified table, bar chart, radar fingerprint, CSV download | Pandas, NumPy, Plotly |
| 4. MolView 2D/3D Lab | 3D ball-and-stick (drag to rotate, auto-spin), 2D skeletal, bond builder, bio-clay intercalation, **graph analysis** | Plotly, Matplotlib, NetworkX, SciPy `minimize` |
| 5. Element Slide Game | Build molecules from elements/fragments, valency check, XP score, challenges | Python dictionaries + rules engine |

---

## 🍎 How to run it on your Mac (step by step)

**1. Install Python (one time only)**
Download **Python 3.12** from <https://www.python.org/downloads/macos/> and run the installer.
(The Python that comes with macOS is too old for the latest libraries.)

**2. Unzip the project**
Double-click `bio_clay_python.zip` in your Downloads folder. You get a folder called `bio_clay_python`.

**3. Open Terminal in that folder**
Open the **Terminal** app, type `cd ` (with a space), drag the `bio_clay_python` folder into the Terminal window, press **Enter**.

**4. Create a private Python environment (one time only)**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
```
You should now see `(.venv)` at the start of the line.

**5. Install the libraries (one time only)**
```bash
pip install -r requirements.txt
```

**6. Start the app**
```bash
streamlit run app.py
```
Your browser opens at <http://localhost:8501> with the pink app. Stop it with **Control + C** in Terminal.

**Next time** you only need step 3, then:
```bash
source .venv/bin/activate
streamlit run app.py
```

### Optional: live Gemini AI
The app works fully **offline** with its built-in rules engine. For live Gemini answers, open the sidebar
(the `>>` arrow at the top-left) and paste your key from <https://aistudio.google.com/apikey>,
or rename `.env.example` to `.env` and put the key inside.

### Run the tests
```bash
python -m unittest discover tests -v
```

---

## 📁 Project structure

```
bio_clay_python/
├── app.py                  ← main file: page setup, header, 5 navigation tabs
├── requirements.txt
├── .streamlit/config.toml  ← the pink theme colours
├── core/                   ← pure Python "brain" (no web code)
│   ├── chemistry.py        ← molecules, 26 functional groups, parsers, property calculator
│   ├── rules_engine.py     ← offline synthesis protocol + game evaluator
│   ├── ai_engine.py        ← optional Gemini connection with automatic fallback
│   ├── molecule_builder.py ← atoms/bonds builder + add/remove group logic
│   └── computation.py      ← NetworkX graph analysis, SciPy optimisation & kinetics
├── ui/                     ← everything you see on screen
│   ├── theme.py            ← pink light theme + dark mode (CSS)
│   ├── designer.py · synthesis.py · properties.py · molview.py · game.py   ← the 5 tabs
│   ├── charts.py           ← 3D (Plotly) / 2D (Matplotlib) molecule drawings
│   └── components.py, icons.py, state.py
└── tests/test_core.py      ← 15 unit tests
```

### Old website file → new Python file

| React / TypeScript file | Python file |
|---|---|
| `src/data/chemistry.ts` | `core/chemistry.py` |
| `server.ts` (Express + Gemini routes) | `core/ai_engine.py` + `core/rules_engine.py` |
| `src/App.tsx`, `Navbar.tsx` | `app.py`, `ui/state.py`, `ui/components.py` |
| `MoleculeDesigner.tsx` | `ui/designer.py` |
| `AiSynthesisProtocol.tsx` | `ui/synthesis.py` |
| `PropertyComparison.tsx` | `ui/properties.py` |
| `MolViewCanvas.tsx` | `ui/molview.py` + `core/molecule_builder.py` + `ui/charts.py` |
| `ElementSlideGame.tsx` | `ui/game.py` |
| Tailwind CSS classes | `ui/theme.py` + `.streamlit/config.toml` |

---

## 🧠 Computational-thinking ideas you can explain in the viva

* **Decomposition** – the app is split into `core/` (logic) and `ui/` (display); each tab is its own module.
* **Pattern recognition** – regular expressions read formulas such as `CH3-(CH2)4-CH3`, `C5H12` or `butanol`.
* **Abstraction** – `calculate_realtime_properties()` hides all the maths behind one function call.
* **Algorithms** – graph diameter finds the longest carbon chain; degree of unsaturation
  `DoU = 1 + ½ Σ nᵢ(vᵢ − 2)` detects radicals and impossible molecules.
* **Simulation** – an ODE model + Arrhenius equation (`scipy.integrate.solve_ivp`) predicts reaction and clay-gallery filling over time.
* **Optimisation** – `scipy.optimize.minimize` relaxes a messy 3D structure to realistic bond lengths and angles.
* **Data handling** – Pandas tables and CSV/JSON/TXT downloads.
* **State** – `st.session_state` remembers choices between clicks (like React's `useState`).
* **Testing** – `tests/test_core.py` checks the chemistry automatically.

## ✨ Small fixes compared with the JS version
* Typing `-Cl` now finds the Halide group (the JS version matched the ammonium salt first).
* The formula preview puts the group on the carbon you chose, e.g. `CH₃-CH(NH₂)-CH₃` for C2.
* The offline protocol names the product from your chain length and position (e.g. *Butan-2-amine*, *Sodium 2-methylpropanoate*) and its molecular weight is the exact formula mass.
* The “Sodium Butanoate” quick-chip in MolView now really builds 4 carbons.
* The game expands fragments into atoms (so `-COO⁻Na⁺` counts as C + 2 O + Na), recognises the three challenge molecules and awards the challenge XP, and the missing `-OH` fragment is in the tray.

> The kinetics simulator is an **educational model** for computational thinking, not measured lab data.
