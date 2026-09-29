"""
ai_engine.py
============
Optional Google Gemini connection (port of the Express routes in the old `server.ts`).

* If a GEMINI_API_KEY is available -> ask Gemini for a JSON answer.
* If not (or Gemini is busy)       -> fall back to the offline rules engine.

So the app ALWAYS works, even with no internet during a viva.
"""

from __future__ import annotations

import json
import os
import re
import time

from .rules_engine import (
    evaluate_assembled_molecule, generate_deterministic_chemistry_analysis,
    normalize_game_validation, normalize_synthesis_report,
)

try:  # python-dotenv is optional: it lets you keep the key in a local .env file
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

try:  # google-genai is optional too
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except Exception:  # pragma: no cover
    genai = None
    genai_types = None
    GENAI_AVAILABLE = False

# Same model priority list as the website (first one that answers wins).
MODEL_PRIORITIES = ["gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]

_client_cache: dict[str, object] = {}


def resolve_api_key(user_key: str | None = None) -> str | None:
    """Look for the key in: the sidebar box -> environment / .env file."""
    for key in (user_key, os.environ.get("GEMINI_API_KEY")):
        if key and key.strip() and key.strip() != "MY_GEMINI_API_KEY":
            return key.strip()
    return None


def get_client(api_key: str | None):
    if not (GENAI_AVAILABLE and api_key):
        return None
    if api_key not in _client_cache:
        _client_cache[api_key] = genai.Client(api_key=api_key)
    return _client_cache[api_key]


def _clean_json(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.I)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def execute_gemini_with_fallback(client, prompt: str):
    """Try each model twice; return (model_name, parsed_json) or None."""
    for model in MODEL_PRIORITIES:
        for attempt in range(2):
            try:
                config = genai_types.GenerateContentConfig(response_mime_type="application/json")
                resp = client.models.generate_content(model=model, contents=prompt, config=config)
                cleaned = _clean_json(getattr(resp, "text", "") or "")
                if cleaned:
                    return model, json.loads(cleaned)
            except Exception as err:  # busy / quota / bad JSON -> retry once, then next model
                msg = str(err)
                transient = any(s in msg for s in ("503", "429", "UNAVAILABLE", "high demand", "exhausted"))
                if transient and attempt == 0:
                    time.sleep(0.5)
                    continue
                break
    return None


# --------------------------------------------------------------------------------------
# Prompts (copied from the website so Gemini answers in exactly the same JSON shape)
# --------------------------------------------------------------------------------------
def _synthesis_prompt(base, action, position, removed, added, env) -> str:
    return f"""You are an expert computational chemist and medical engineering professor specializing in bio-clay (Layered Double Hydroxides / Smectite / Montmorillonite) polymer nanocomposites and organic synthesis.
Analyze this molecular modification:
- Base Molecule / Carbon Chain: {base or "Propane Chain (CH3-CH2-CH3)"}
- Modification Action: {action or "Remove Hydrogen (-H)"}
- Target Position: {position or "Carbon-3 (Terminal)"}
- Removed Group(s) / Atom(s): {json.dumps(removed or ["Hydrogen (-H)"], ensure_ascii=False)}
- Added / Substituted Group(s): {json.dumps(added or ["Organic Salt (-COO- Na+)"], ensure_ascii=False)}
- Reaction Medium: {env or "Aqueous / Hydrothermal"}

Respond in STRICT JSON format with no markdown wrappers or backticks around the json object, matching this structure:
{{
  "moleculeName": "Name of newly synthesized compound",
  "chemicalFormula": "Condensed formula e.g. CH3-CH2-CH2-COO-Na+",
  "iupacName": "IUPAC name",
  "isFeasibleInLab": true,
  "confidenceScore": 95,
  "synthesisTechnique": "Hydrothermal / Sol-Gel / Room Temperature Precipitation / Low-Temperature Reflux",
  "temperatureCondition": "e.g. 60°C - 80°C (Moderate) or Room Temp (25°C)",
  "pressureCondition": "e.g. 1.0 atm or Autogenous hydrothermal pressure",
  "catalystAndReagents": "Specific catalysts, base/acid, e.g. NaOH, Pd/C, aqueous buffer",
  "reactionTime": "e.g. 2-4 hours under continuous stirring",
  "pHRange": "e.g. 8.5 - 10.0 (Alkaline for LDH precipitation)",
  "stepByStepProtocol": ["Step 1...", "Step 2...", "Step 3...", "Step 4..."],
  "physicochemicalChanges": {{
    "molecularWeight": {{ "original": 60.1, "modified": 110.08, "unit": "g/mol", "description": "Shift in molecular mass" }},
    "ionizationEnergy": {{ "original": 10.2, "modified": 9.12, "unit": "eV", "description": "Change in valence ionization potential" }},
    "electronegativity": {{ "original": 2.55, "modified": 2.82, "unit": "Pauling", "description": "Local dipole attraction" }},
    "dipoleMoment": {{ "original": 1.68, "modified": 5.4, "unit": "Debye (D)", "description": "Polarity elevation" }},
    "enthalpyDeltaH": {{ "original": -303.2, "modified": -185.4, "unit": "kJ/mol", "description": "Enthalpy of formation" }},
    "solubility": "e.g. High Ionic Solubility in physiological buffers",
    "bondAngle": {{ "original": 109.5, "modified": 120.0, "unit": "degrees (°)" }},
    "bondLength": {{ "original": 1.43, "modified": 1.27, "unit": "Å" }}
  }},
  "bioClayInteraction": {{
    "intercalationFeasibility": "High / Intercalates easily into LDH interlayer galleries",
    "bindingMechanism": "Electrostatic anionic attraction with positively charged bio-clay sheets",
    "biomedicalApplications": "Controlled drug release, cellular delivery, tissue engineering scaffold"
  }},
  "safetyPrecautions": "Exothermic risk, PPE requirements, ventilation"
}}"""


def _game_prompt(elements: list[str], formula: str) -> str:
    return f"""You are a chemistry evaluator assessing a user-assembled molecule in an educational game:
Selected elements / groups: {json.dumps(elements, ensure_ascii=False)}
Assembled formula: {formula}

Determine:
1. Is this a valid, stable chemical molecule (respecting valency, octet rule)?
2. Can it be synthesized in a medical engineering or chemistry lab?
3. What is its name, properties (Molecular Weight, Ionization Energy, Electronegativity, Dipole Moment), and compatibility with Bio-Clay?

Respond strictly in JSON with this structure:
{{
  "isValid": true,
  "isSynthesizable": true,
  "confidence": 92,
  "moleculeName": "Name",
  "formula": "Clean formula",
  "valencyStatus": "All valencies satisfied / Radical / Violates octet",
  "molecularWeight": 89.09,
  "ionizationEnergy": 9.8,
  "electronegativity": 2.7,
  "dipoleMoment": 2.3,
  "solubility": "Water soluble",
  "bioClaySuitability": "Excellent for intercalation",
  "synthesisTechnique": "Hydrothermal synthesis or Sol-gel",
  "explanation": "Scientific explanation of why this molecule is valid or why it cannot be formed in nature/lab."
}}"""


# --------------------------------------------------------------------------------------
# Public API used by the UI
# --------------------------------------------------------------------------------------
def synthesize(base, action, position, removed, added, props=None, api_key=None,
               env="Aqueous Bio-Clay Buffer") -> tuple[str, dict]:
    """Return (source_label, report). source_label is 'gemini (model)' or 'rules_engine'."""
    fallback = generate_deterministic_chemistry_analysis(base, action, position, removed, added, props)
    client = get_client(resolve_api_key(api_key))
    if client is not None:
        result = execute_gemini_with_fallback(client, _synthesis_prompt(base, action, position, removed, added, env))
        if result:
            model, data = result
            return f"gemini ({model})", normalize_synthesis_report(data, fallback)
    return "rules_engine", fallback


def validate_molecule(selected_counts: dict[str, int], formula: str, api_key=None) -> tuple[str, dict]:
    fallback = evaluate_assembled_molecule(selected_counts, formula)
    client = get_client(resolve_api_key(api_key))
    if client is not None:
        elements = [sym for sym, n in selected_counts.items() for _ in range(int(n))]
        result = execute_gemini_with_fallback(client, _game_prompt(elements, formula))
        if result:
            model, data = result
            return f"gemini ({model})", normalize_game_validation(data, fallback)
    return "rules_engine", fallback
