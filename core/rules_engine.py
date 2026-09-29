"""
rules_engine.py
===============
The offline "brain" of the app. Port of the two helper functions from the old `server.ts`:

* generate_deterministic_chemistry_analysis()  -> synthesis protocol when Gemini is not available
* evaluate_assembled_molecule()                -> checks molecules built in the Element Slide Game

It works with no internet and no API key, so the project always runs in the lab / viva.
"""

from __future__ import annotations

import copy
import re
from collections import Counter

from .chemistry import (
    ATOMIC_MASS, NONE_LABEL, count_carbons_in_chain, js_round, parse_target_position, substitute_on_carbon,
)

# ======================================================================================
# Default report shown before the first analysis (same text as the React App.tsx)
# ======================================================================================
DEFAULT_SYNTHESIS_REPORT: dict = {
    "moleculeName": "Sodium Butanoate (Bio-Clay Intercalating Salt Precursor)",
    "chemicalFormula": "CH₃-CH₂-CH₂-COO⁻Na⁺",
    "iupacName": "Sodium Butanoate",
    "isFeasibleInLab": True,
    "confidenceScore": 95,
    "synthesisTechnique": "Room-Temperature Saponification & Neutralization",
    "temperatureCondition": "25°C - 35°C (Controlled Room Temperature)",
    "pressureCondition": "1.0 atm (Standard Atmospheric)",
    "catalystAndReagents": "0.1M NaOH Aqueous Buffer Solution, Magnetic Stirring",
    "reactionTime": "1.5 - 2 Hours",
    "pHRange": "8.5 - 9.5 (Alkaline buffer for LDH precipitation)",
    "stepByStepProtocol": [
        "Prepare a 0.2M precursor solution of the 3-carbon chain in deionized water.",
        "Add 0.1M aqueous NaOH dropwise to reach target alkaline pH ~ 9.0.",
        "Stir vigorously under nitrogen atmosphere at 25°C for 90 minutes to ensure complete salt ionization.",
        "Introduce Layered Double Hydroxide (Mg-Al-LDH) slurry to initiate spontaneous anion exchange into the clay interlayer galleries.",
        "Centrifuge at 4000 rpm, wash three times with ethanol/water, and freeze-dry the bio-clay nanocomposite.",
    ],
    "physicochemicalChanges": {
        "molecularWeight": {"original": 60.1, "modified": 110.08, "unit": "g/mol"},
        "ionizationEnergy": {"original": 10.2, "modified": 9.12, "unit": "eV"},
        "electronegativity": {"original": 2.55, "modified": 2.85, "unit": "Pauling"},
        "dipoleMoment": {"original": 1.68, "modified": 6.2, "unit": "Debye (D)"},
        "enthalpyDeltaH": {"original": -303.2, "modified": -185.4, "unit": "kJ/mol"},
        "solubility": "Very High Ionic Aqueous Solubility",
        "bondAngle": {"original": 109.5, "modified": 120.0, "unit": "degrees (°)"},
        "bondLength": {"original": 1.43, "modified": 1.27, "unit": "Å"},
    },
    "bioClayInteraction": {
        "intercalationFeasibility": "High: Strong electrostatic attraction between anionic carboxylate head and cationic LDH sheets.",
        "bindingMechanism": "Ion-exchange intercalation expanding d001 gallery spacing from 0.88 nm to 1.42 nm.",
        "biomedicalApplications": "Controlled transdermal drug delivery, antibacterial wound dressing matrix, and biopolymer scaffold reinforcement.",
    },
    "safetyPrecautions": "Standard PPE, avoid eye contact with basic NaOH solution, perform in well-ventilated laboratory.",
}

DEFAULT_GAME_RESULT: dict = {
    "isValid": True,
    "isSynthesizable": True,
    "confidence": 94,
    "moleculeName": "Sodium Butanoate (Bio-Clay Intercalating Salt)",
    "formula": "C₃H₇COO⁻Na⁺",
    "hillFormula": "C4H7NaO2",
    "valencyStatus": "All covalent & ionic valencies satisfied",
    "molecularWeight": 110.09,
    "ionizationEnergy": 9.12,
    "electronegativity": 2.85,
    "dipoleMoment": 6.2,
    "solubility": "Highly Water Soluble (Polar Ionic)",
    "bioClaySuitability": "Excellent: Intercalates into Layered Double Hydroxide (LDH) galleries with 1.42 nm d-spacing",
    "synthesisTechnique": "Room-Temperature Saponification & Neutralization",
    "explanation": "The carboxylate head (-COO⁻) interacts strongly via electrostatic attraction with the positive charge of LDH clay nanosheets, making it an ideal carrier.",
}


# ======================================================================================
# Helpers
# ======================================================================================
_PREFIX = ["Meth", "Eth", "Prop", "But", "Pent", "Hex", "Hept", "Oct", "Non", "Dec", "Undec", "Dodec"]


def iupac_prefix(n: int) -> str:
    return _PREFIX[n - 1] if 1 <= n <= len(_PREFIX) else f"C{n}-"


def alkyl_chain(n: int) -> str:
    """alkyl_chain(3) -> 'CH3-CH2-CH2'  (the chain that carries the new group)."""
    return "CH3" if n <= 1 else "CH3-" + "-".join(["CH2"] * (n - 1))


def molar_mass(counts: dict[str, int]) -> float:
    """Molecular weight = sum(number of atoms x atomic mass).  Classic loop + dictionary example."""
    return js_round(sum(ATOMIC_MASS.get(sym, 0.0) * n for sym, n in counts.items()), 2)


def hill_formula(counts: dict[str, int]) -> str:
    """Hill system: C first, then H, then everything else alphabetically (e.g. C4H7NaO2)."""
    counts = {k: v for k, v in counts.items() if v > 0}
    if not counts:
        return "-"
    order = []
    if "C" in counts:
        order += ["C"] + (["H"] if "H" in counts else [])
        order += sorted(k for k in counts if k not in ("C", "H"))
    else:
        order = sorted(counts)
    return "".join(f"{el}{counts[el] if counts[el] > 1 else ''}" for el in order)


def _nice_formula(s: str) -> str:
    """CH3 -> CH₃ (only digits that follow a letter or a bracket are subscripts)."""
    return re.sub(r"(?<=[A-Za-z)])(\d+)", lambda m: m.group(1).translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")), s)


# ======================================================================================
# 1. Synthesis protocol rules engine
# ======================================================================================
def generate_deterministic_chemistry_analysis(
    base: str = "Propane Chain (CH3-CH2-CH3)",
    action: str = "remove_h",
    position: str = "Carbon-3",
    removed: list[str] | None = None,
    added: list[str] | None = None,
    props: dict | None = None,
) -> dict:
    """Decide the product, technique and conditions using simple IF / ELSE chemistry rules."""
    removed = removed if removed is not None else ["Hydrogen (-H)"]
    added = added if added is not None else ["Organic Salt (-COO- Na+)"]

    low = [g.lower() for g in added]
    is_salt = any("salt" in g or "na+" in g or "na⁺" in g or "coo-" in g or "coo⁻" in g for g in low)
    is_amine = any("amine" in g or "nh2" in g or "nh₂" in g for g in low)
    is_acid = any("acid" in g or "cooh" in g for g in low)
    is_halide = any("halide" in g or "cl" in g for g in low)
    none_removed = (not removed) or any(r in ("None", NONE_LABEL) for r in removed)
    none_added = (not added) or any(a in ("None", NONE_LABEL) for a in added)

    n = max(1, count_carbons_in_chain(base))
    chain = alkyl_chain(n)
    k = parse_target_position(position or f"C{n}", n)["carbon_index"]
    loc = min(k, n + 1 - k)                     # IUPAC: number from the nearer chain end
    alkane = "CH4" if n == 1 else "CH3-" + "-".join(["CH2"] * (n - 2) + ["CH3"])

    def placed(group: str, fallback: str) -> str:
        return substitute_on_carbon(alkane, k, group) or fallback

    def carboxyl_name(ending: str) -> str:
        if loc == 1:
            return f"{iupac_prefix(n + 1)}{ending}"
        branch = f"{iupac_prefix(loc - 1).lower()}yl"
        return f"2-{branch}{iupac_prefix(n - loc + 2).lower()}{ending}"

    # default = generic modified derivative
    name, formula, counts = "Modified Carbon Derivative", f"{chain}-R", None
    technique, temp = "Hydrothermal Co-precipitation", "65°C - 80°C (Regulated)"
    ie = en = dipole = dh = None

    if is_salt:
        name = f"Sodium {carboxyl_name('anoate')} / Bio-Clay Organic Salt Precursor"
        formula = placed("COO⁻Na⁺", f"{chain}-COO⁻Na⁺")
        counts = {"C": n + 1, "H": 2 * n + 1, "O": 2, "Na": 1}
        technique, temp = "Room-Temperature Saponification & Neutralization", "25°C - 40°C (Low Temperature)"
        ie, en, dipole, dh = 9.12, 2.85, 6.2, -185.4
    elif is_amine:
        amine = f"{iupac_prefix(n)}ylamine" if loc == 1 else f"{iupac_prefix(n)}an-{loc}-amine"
        name = f"{amine} / Bio-Clay Cationic Intercalator"
        formula = placed("NH2", f"{chain}-NH2")
        counts = {"C": n, "H": 2 * n + 3, "N": 1}
        technique, temp = "Catalytic Reductive Amination", "110°C - 130°C (Moderate Pressure)"
        ie, en, dipole, dh = 8.78, 3.04, 1.33, -105.8
    elif is_acid:
        name = f"{carboxyl_name('anoic Acid')} Bio-Clay Functional Conjugate"
        formula = placed("COOH", f"{chain}-COOH")
        counts = {"C": n + 1, "H": 2 * n + 2, "O": 2}
        technique, temp = "Mild Catalytic Oxidation (KMnO4 or CrO3 / Phase Transfer)", "35°C - 50°C"
        ie, en, dipole, dh = 10.15, 3.12, 1.74, -534.2
    elif is_halide:
        name = f"{loc}-Chloro{iupac_prefix(n).lower()}ane Bio-Clay Alkylating Agent"
        formula = placed("Cl", f"{chain}-Cl")
        counts = {"C": n, "H": 2 * n + 1, "Cl": 1}
        technique, temp = "Nucleophilic Halogenation (SOCl2 / PCl5)", "Reflux at 45°C - 60°C"
        ie, en, dipole, dh = 10.82, 3.16, 2.1, -132.0
    elif none_added:
        k2 = max(2, n)
        tail = "CH2" if k2 == 2 else "CH-" + "-".join(["CH2"] * (k2 - 3) + ["CH3"])
        name = "Unsaturated / Dehydrogenated Carbon Scaffold"
        formula = f"CH2={tail} ({iupac_prefix(k2)}ene)"
        counts = {"C": k2, "H": 2 * k2}
        technique, temp = "Acid-Catalyzed Elimination / Dehydration", "160°C - 180°C (High Temperature)"
        ie, en, dipole, dh = 9.73, 2.55, 0.36, 20.4

    name = re.sub(r"^(\d+-)([a-z])", lambda m: m.group(1) + m.group(2).upper(), name)  # "2-ethyl…" -> "2-Ethyl…"

    # Numbers: prefer the live values from the Designer so every tab agrees with each other.
    p = props or {}

    def pick(key, fallback_orig, fallback_mod, unit, desc):
        m = p.get(key)
        if m:
            return {"original": m["original"], "modified": m["modified"], "unit": unit, "description": desc}
        return {"original": fallback_orig, "modified": fallback_mod, "unit": unit, "description": desc}

    mw_mod = molar_mass(counts) if counts else (p.get("molecularWeight", {}).get("modified", 88.1))
    mw_orig = p.get("molecularWeight", {}).get("original", 60.1)

    changes = {
        "molecularWeight": {"original": mw_orig, "modified": mw_mod, "unit": "g/mol",
                            "description": "Exact formula mass of the product (sum of atomic masses)"},
        "ionizationEnergy": pick("ionizationEnergy", 10.2, ie or 9.45, "eV", "Ionization affinity"),
        "electronegativity": pick("electronegativity", 2.55, en or 2.65, "Pauling", "Local charge density"),
        "dipoleMoment": pick("dipoleMoment", 1.68, dipole or 2.4, "Debye (D)", "Net electric dipole moment"),
        "enthalpyDeltaH": pick("enthalpyDeltaH", -303.2, dh or -220.0, "kJ/mol", "Standard enthalpy change"),
        "solubility": "Very High (Ionic Dissociation)" if is_salt else "Moderate / Hydrophilic",
        "bondAngle": pick("bondAngle", 109.5, 120.0 if is_salt else 109.5, "degrees (°)", "Valence angle"),
        "bondLength": pick("bondLength", 1.43, 1.27 if is_salt else 1.47, "Å", "Bond length at target carbon"),
    }

    return {
        "moleculeName": name,
        "chemicalFormula": _nice_formula(formula),
        "iupacName": name.split(" / ")[0],
        "isFeasibleInLab": True,
        "confidenceScore": 94,
        "synthesisTechnique": technique,
        "temperatureCondition": temp,
        "pressureCondition": "1.0 atm (Standard Ambient Pressure)",
        "catalystAndReagents": "0.1M NaOH aqueous buffer, magnetic stirrer" if is_salt else "Pt/C catalyst, ethanol solvent",
        "reactionTime": "2.5 Hours",
        "pHRange": "8.5 - 9.5" if is_salt else "6.8 - 7.4",
        "stepByStepProtocol": [
            f"Prepare {base} in a temperature-regulated three-neck flask.",
            f"Activate target {position} position under selective catalytic conditions.",
            "Proceed directly with addition/conjugation without group cleavage." if none_removed
            else f"Cleave existing {', '.join(removed)} group using stoichiometric reactant.",
            "Quench reaction to isolate eliminated unsaturated product." if none_added
            else f"Introduce {', '.join(added)} reagent dropwise with continuous monitoring.",
            "Purify precipitate via centrifuge, wash with deionized water, and vacuum dry for bio-clay intercalation.",
        ],
        "physicochemicalChanges": changes,
        "bioClayInteraction": {
            "intercalationFeasibility": "Excellent: Anionic carboxylate heads strongly bind to LDH cationic hydroxide layers."
            if is_salt else "Moderate: Hydrogen bonding with clay basal oxygen planes.",
            "bindingMechanism": "Ion exchange intercalation into Layered Double Hydroxide (LDH) interlayer spacing (d001 expansion to ~1.4 nm)."
            if is_salt else "Dipole-dipole adsorption onto bio-clay platelets.",
            "biomedicalApplications": "Sustained transdermal drug delivery, antibacterial wound dressing matrix, and biopolymer reinforcement.",
        },
        "safetyPrecautions": "Use fume hood, wear nitrile gloves, prevent thermal runaway during exothermic neutralization.",
    }


# ======================================================================================
# 2. Element Slide Game evaluator
# ======================================================================================
# Each functional fragment is expanded into the atoms it really contains.
FRAGMENT_ATOMS: dict[str, dict[str, int]] = {
    "-Cl": {"Cl": 1},
    "-NH₂": {"N": 1, "H": 2},
    "-COOH": {"C": 1, "O": 2, "H": 1},
    "-COO⁻Na⁺": {"C": 1, "O": 2, "Na": 1},
    "-CH₃": {"C": 1, "H": 3},
    "-OH": {"O": 1, "H": 1},
}

# Normal bonding capacity of each element (used by the valency check).
VALENCE: dict[str, int] = {"H": 1, "C": 4, "N": 3, "O": 2, "Na": 1, "Mg": 2, "Al": 3, "Si": 4,
                           "P": 3, "S": 2, "Cl": 1, "Ca": 2, "Br": 1, "K": 1, "F": 1, "I": 1}

# Molecules the evaluator recognises by their Hill formula.
KNOWN_MOLECULES: dict[str, dict] = {
    "H2O": dict(name="Water (H2O)", ie=12.6, en=3.44, dipole=1.85,
                explanation="Universal polar solvent, essential for bio-clay hydration galleries."),
    "CH4": dict(name="Methane (CH4)", ie=12.61, en=2.2, dipole=0.0,
                explanation="Stable tetrahedral alkane, though gaseous at standard temperature."),
    "C2H6": dict(name="Ethane (C2H6)", ie=11.52, en=2.5, dipole=0.0,
                 explanation="Saturated 2-carbon alkane; every carbon has four single bonds."),
    "C3H8": dict(name="Propane (C3H8)", ie=10.95, en=2.55, dipole=0.08,
                 explanation="Saturated 3-carbon backbone used as the precursor chain in the Designer tab."),
    "C2H6O": dict(name="Ethanol (C2H5OH)", ie=10.48, en=2.55, dipole=1.69,
                  explanation="Readily synthesizable primary alcohol with excellent bio-clay solvent miscibility."),
    "C3H8O": dict(name="Propanol (C3H7OH)", ie=10.2, en=2.55, dipole=1.68,
                  explanation="Classic 3-carbon chain alcohol. Intercalates neatly into bio-clay layers."),
    "C3H9N": dict(name="1-Propylamine (C3H7NH2)", ie=8.78, en=3.04, dipole=1.33,
                  explanation="Primary amine; the protonated -NH3+ head exchanges into montmorillonite galleries (cationic intercalation)."),
    "C4H7NaO2": dict(name="Sodium Butanoate (Bio-Clay Intercalating Salt)", ie=9.12, en=2.85, dipole=6.2,
                     explanation="The carboxylate head (-COO⁻) interacts strongly via electrostatic attraction with the positive charge of LDH clay nanosheets, making it an ideal carrier."),
    "C2H4O2": dict(name="Acetic Acid (CH3COOH)", ie=10.65, en=2.95, dipole=1.74,
                   explanation="Short carboxylic acid; neutralising it with NaOH gives the acetate salt used for LDH intercalation."),
    "C4H8O2": dict(name="Butanoic Acid (C3H7COOH)", ie=10.15, en=3.12, dipole=1.74,
                   explanation="Carboxylic acid precursor of sodium butanoate."),
    "C2H5NO2": dict(name="Glycine (H2N-CH2-COOH)", ie=8.95, en=2.92, dipole=6.55,
                    explanation="Simplest amino acid; zwitterion binds both anionic and cationic clay sites."),
    "C3H7Cl": dict(name="1-Chloropropane (C3H7Cl)", ie=10.82, en=3.16, dipole=2.1,
                   explanation="Alkyl halide; a reactive alkylating intermediate rather than a direct intercalator."),
    "C2H3NaO2": dict(name="Sodium Acetate (CH3COO⁻Na⁺)", ie=9.3, en=2.9, dipole=5.8,
                     explanation="Small carboxylate salt that exchanges readily into LDH interlayers."),
}


def expand_to_atoms(selected: dict[str, int]) -> dict[str, int]:
    """{'C':3,'H':7,'-COO⁻Na⁺':1}  ->  {'C':4,'H':7,'O':2,'Na':1}"""
    total: Counter = Counter()
    for sym, count in selected.items():
        if sym in FRAGMENT_ATOMS:
            for el, k in FRAGMENT_ATOMS[sym].items():
                total[el] += k * count
        else:
            total[sym] += count
    return dict(total)


def degree_of_unsaturation(atoms: dict[str, int]) -> float:
    """DoU = 1 + ½ Σ nᵢ (vᵢ − 2).  Negative -> impossible, x.5 -> radical, 0 -> saturated."""
    return 1 + 0.5 * sum(n * (VALENCE.get(el, 2) - 2) for el, n in atoms.items())


def evaluate_assembled_molecule(selected: dict[str, int], formula_str: str = "") -> dict:
    atoms = expand_to_atoms(selected)
    c, h, o, n = (atoms.get(k, 0) for k in ("C", "H", "O", "N"))
    na = atoms.get("Na", 0)
    total_atoms = sum(atoms.values())
    hill = hill_formula(atoms)
    mw = molar_mass(atoms) or 58.0
    dou = degree_of_unsaturation(atoms)

    is_valid, synth = True, True
    name = "Assembled Molecule"
    ie, en, dipole = 10.0, 2.5, 1.5
    explanation = "Valid organic architecture assembled from provided elements."
    valency = "All valencies satisfied"

    if total_atoms <= 1:
        is_valid = synth = False
        valency = "Single atom - no bonds formed"
        explanation = "A single atom is not a molecule. Add at least one more atom or fragment to form bonds."
    elif dou < 0:
        is_valid = synth = False
        valency = "Violates octet / valency (too many monovalent atoms)"
        explanation = (f"Degree of unsaturation = {dou:g} (< 0). There are more H / halogen / Na atoms than the "
                       "backbone can bond to, so this structure cannot exist.")
    elif dou != int(dou):
        is_valid = synth = False
        valency = "Radical - one unpaired electron"
        explanation = (f"Degree of unsaturation = {dou:g} (a half value). One atom is left with an unpaired "
                       "electron, so this is a short-lived radical that cannot be isolated in the lab. "
                       "Try adding or removing one H.")
    elif hill in KNOWN_MOLECULES:
        k = KNOWN_MOLECULES[hill]
        name, ie, en, dipole, explanation = k["name"], k["ie"], k["en"], k["dipole"], k["explanation"]
    elif c == 0 and (h > 2 or o > 2):
        is_valid = synth = False
        explanation = "No carbon backbone provided and hydrogen/oxygen ratio violates chemical stability."
    elif c >= 1 and (na > 0 or o > 0 or n > 0):
        name = f"Custom Organo-Bio-Clay Conjugate ({formula_str or 'Custom Chain'})"
        ie = js_round(9.0 + (o + n) * 0.4, 1)
        en = js_round(2.4 + o * 0.3 + n * 0.2, 1)
        dipole = js_round(1.2 + na * 2.5 + o * 0.8, 1)
        explanation = "Valid heteroatom-bearing organic scaffold capable of chemical laboratory synthesis and clay adsorption."

    if is_valid and dou >= 1 and "valencies satisfied" in valency:
        valency = f"All valencies satisfied ({int(dou)} ring / π-bond{'s' if dou > 1 else ''})"

    return {
        "isValid": is_valid,
        "isSynthesizable": synth,
        "confidence": 93 if is_valid else 30,
        "moleculeName": name,
        "formula": formula_str or hill,
        "hillFormula": hill,
        "valencyStatus": valency if is_valid else valency.replace("All valencies satisfied", "Unstable / Valency mismatch"),
        "molecularWeight": mw,
        "ionizationEnergy": ie,
        "electronegativity": en,
        "dipoleMoment": dipole,
        "solubility": "Water Soluble (Polar / Hydrophilic)" if (o > 0 or n > 0 or na > 0) else "Hydrophobic / Lipid Soluble",
        "bioClaySuitability": "High Interlayer Intercalation" if (na > 0 or o >= 2 or n > 0) else "Moderate Adsorption",
        "synthesisTechnique": "Neutralization & Salt Precipitation" if na > 0 else ("Condensation Reaction" if o > 1 else "Hydrothermal Synthesis"),
        "explanation": explanation,
        "degreeOfUnsaturation": dou,
    }


# ======================================================================================
# 3. Normalisers - make sure an AI answer always has every field the UI needs
# ======================================================================================
def _norm_metric(val, fb: dict) -> dict:
    if not val:
        return dict(fb)
    if isinstance(val, (int, float)):
        return {**fb, "modified": val}
    if not isinstance(val, dict):
        return dict(fb)
    num = lambda x, d: x if isinstance(x, (int, float)) and not isinstance(x, bool) else d
    return {
        "original": num(val.get("original"), fb.get("original")),
        "modified": num(val.get("modified"), fb.get("modified")),
        "unit": val.get("unit") or fb.get("unit"),
        "description": val.get("description") or fb.get("description"),
    }


def normalize_synthesis_report(raw, fb: dict) -> dict:
    if not isinstance(raw, dict):
        return fb
    out = copy.deepcopy(fb)
    for key in ("moleculeName", "chemicalFormula", "synthesisTechnique", "temperatureCondition",
                "pressureCondition", "catalystAndReagents", "reactionTime", "pHRange", "safetyPrecautions"):
        if raw.get(key):
            out[key] = str(raw[key])
    out["iupacName"] = raw.get("iupacName") or raw.get("moleculeName") or fb.get("iupacName")
    if isinstance(raw.get("isFeasibleInLab"), bool):
        out["isFeasibleInLab"] = raw["isFeasibleInLab"]
    if isinstance(raw.get("confidenceScore"), (int, float)):
        out["confidenceScore"] = raw["confidenceScore"]
    steps = raw.get("stepByStepProtocol")
    if isinstance(steps, list) and steps:
        out["stepByStepProtocol"] = [str(s) for s in steps]

    rc = raw.get("physicochemicalChanges") or {}
    fc = fb["physicochemicalChanges"]
    for k in ("molecularWeight", "ionizationEnergy", "electronegativity", "dipoleMoment",
              "enthalpyDeltaH", "bondAngle", "bondLength"):
        out["physicochemicalChanges"][k] = _norm_metric(rc.get(k), fc[k])
    sol = rc.get("solubility")
    if isinstance(sol, str):
        out["physicochemicalChanges"]["solubility"] = sol
    elif isinstance(sol, dict) and isinstance(sol.get("modified"), str):
        out["physicochemicalChanges"]["solubility"] = sol["modified"]

    rb = raw.get("bioClayInteraction") or {}
    for k in ("intercalationFeasibility", "bindingMechanism", "biomedicalApplications"):
        if rb.get(k):
            out["bioClayInteraction"][k] = str(rb[k])
    return out


def normalize_game_validation(raw, fb: dict) -> dict:
    if not isinstance(raw, dict):
        return fb
    out = dict(fb)
    for k in ("isValid", "isSynthesizable"):
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    for k in ("confidence", "molecularWeight", "ionizationEnergy", "electronegativity", "dipoleMoment"):
        if isinstance(raw.get(k), (int, float)) and not isinstance(raw.get(k), bool):
            out[k] = raw[k]
    for k in ("moleculeName", "formula", "valencyStatus", "solubility", "bioClaySuitability",
              "synthesisTechnique", "explanation"):
        if raw.get(k):
            out[k] = str(raw[k])
    return out


def numbers_in(text: str) -> list[float]:
    """Pull every number out of a string: '25°C - 35°C' -> [25.0, 35.0]."""
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", text or "")]
