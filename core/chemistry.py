"""
chemistry.py
============
All the "bio knowledge" of the Bio-Clay AI Synthesizer lives here.

This file is a line-by-line Python port of the old `src/data/chemistry.ts`.
Nothing about the chemistry changed - only the language did.

Computational-thinking ideas used in this file
----------------------------------------------
* Data modelling      -> @dataclass classes (BaseMolecule, FunctionalGroup, ElementCard)
* Pattern recognition -> regular expressions (the `re` module) to read formulas like CH3-CH2-CH3
* Decomposition       -> small functions that each do one job (count carbons, parse position ...)
* Abstraction         -> `calculate_realtime_properties()` hides the maths behind one call
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# --------------------------------------------------------------------------------------
# Small helper: JavaScript's Math.round() always rounds .5 UP, Python's round() does
# "banker's rounding". We copy the JS behaviour so every number matches the old website.
# --------------------------------------------------------------------------------------
def js_round(value: float, decimals: int = 0) -> float:
    factor = 10 ** decimals
    return math.floor(value * factor + 0.5) / factor


# ======================================================================================
# 1. DATA MODELS
# ======================================================================================
@dataclass
class BaseMolecule:
    id: str
    name: str
    formula: str
    carbons: int
    description: str
    default_position: str
    base_mw: float          # molecular weight (g/mol)
    base_ie: float          # ionisation energy (eV)
    base_en: float          # electronegativity (Pauling)
    base_dipole: float      # dipole moment (Debye)
    base_delta_h: float     # enthalpy of formation (kJ/mol)
    base_angle: float = 109.5
    base_length: float = 1.43
    category: str = "aliphatic"


@dataclass
class FunctionalGroup:
    id: str
    label: str
    formula: str
    name: str
    delta_mw: float
    delta_ie: float
    delta_en: float
    delta_dipole: float
    delta_h: float
    is_salt: bool
    is_nitrogen: bool
    category: str


@dataclass
class ElementCard:
    symbol: str
    name: str
    atomic_number: int
    atomic_mass: float
    valence: int
    electronegativity: float
    ionization_energy: float  # eV
    category: str
    color: str = "#db2777"


# ======================================================================================
# 2. BASE MOLECULE PRESETS  (same 10 molecules as the website)
# ======================================================================================
BASE_MOLECULES: list[BaseMolecule] = [
    BaseMolecule("propane", "Propane Hydrocarbon Chain (CH₃-CH₂-CH₃)", "CH₃-CH₂-CH₃", 3,
                 "Standard 3-carbon linear alkane backbone used as precursor in bio-clay functional nanocomposites.",
                 "C3 (Terminal / Omega)", 44.1, 11.07, 2.55, 0.08, -104.7, 109.5, 1.54, "aliphatic"),
    BaseMolecule("ethanol", "Ethanol Backbone (CH₃-CH₂-OH)", "CH₃-CH₂-OH", 2,
                 "2-carbon short chain, primary medical engineering solvent and bio-composite coupling agent.",
                 "C2 (Terminal / Omega)", 46.07, 10.48, 2.55, 1.69, -277.6, 108.9, 1.43, "aliphatic"),
    BaseMolecule("ethylamine", "Ethylamine / Nitrogen Backbone (CH₃-CH₂-NH₂)", "CH₃-CH₂-NH₂", 2,
                 "2-carbon nitrogenous primary amine with lone-pair donor sites for high-affinity bio-clay coordination.",
                 "C2 (Amine Carbon)", 45.08, 8.86, 2.82, 1.22, -47.5, 107.5, 1.47, "nitrogen"),
    BaseMolecule("propylamine", "1-Propylamine Chain (CH₃-CH₂-CH₂-NH₂)", "CH₃-CH₂-CH₂-NH₂", 3,
                 "3-carbon cationic intercalation precursor that creates strong basal expansion in montmorillonite clay.",
                 "C3 (Terminal Amine)", 59.11, 8.78, 2.85, 1.33, -105.8, 107.5, 1.47, "nitrogen"),
    BaseMolecule("glycine", "Amino Acid Backbone (H₂N-CH₂-COOH)", "H₂N-CH₂-COOH", 2,
                 "Zwitterionic nitrogenous precursor with dual amine/carboxylate affinity for charged bio-clay nanosheets.",
                 "C1 (Carboxyl site)", 75.07, 8.95, 2.92, 6.55, -528.1, 112.0, 1.45, "amino_acid"),
    BaseMolecule("urea", "Urea Nitrogenous Scaffold (H₂N-CO-NH₂)", "H₂N-CO-NH₂", 1,
                 "Carbonyl diamide that acts as an efficient swelling agent to exfoliate bio-clay interlayers.",
                 "C1 (Carbonyl Carbon)", 60.06, 9.8, 3.15, 4.56, -333.5, 118.0, 1.35, "nitrogen"),
    BaseMolecule("chitosan_monomer", "Chitosan / Glucosamine Fragment (C₆H₁₁NO₄)", "C₆H₁₁NO₄", 6,
                 "Biomedical amino-polysaccharide repeating unit ideal for biocompatible tissue engineering scaffolds.",
                 "C2 (Amine Ring Carbon)", 161.16, 8.45, 3.08, 3.85, -720.0, 109.5, 1.44, "polymer_fragment"),
    BaseMolecule("butanediol", "1,4-Butanediol Chain (HO-CH₂-CH₂-CH₂-CH₂-OH)", "HO-CH₂-CH₂-CH₂-CH₂-OH", 4,
                 "Bifunctional 4-carbon chain ideal for cross-linking bio-clay galleries and polymer hydrogels.",
                 "C4 (Terminal OH)", 90.12, 9.85, 2.62, 2.35, -512.4, 109.5, 1.44, "aliphatic"),
    BaseMolecule("lactic_acid", "Lactic Acid Monomer (CH₃-CH(OH)-COOH)", "CH₃-CH(OH)-COOH", 3,
                 "Biocompatible alpha-hydroxy acid for biodegradable PLA / bio-clay tissue scaffolds.",
                 "C2 (Hydroxyl site)", 90.08, 10.35, 2.85, 2.45, -694.0, 109.5, 1.41, "aliphatic"),
    BaseMolecule("acetic_acid", "Acetic Acid / Ethanoic (CH₃-COOH)", "CH₃-COOH", 2,
                 "Short carboxylic acid precursor for creating bio-clay intercalating acetate salts.",
                 "C1 (Carboxyl site)", 60.05, 10.65, 2.95, 1.74, -484.5, 119.0, 1.36, "aliphatic"),
]


# ======================================================================================
# 3. FUNCTIONAL GROUP CATALOGUE  (same 26 groups as the website)
# ======================================================================================
def _fg(id, label, formula, name, dmw, die, den, ddip, dh, salt, nitro, cat) -> FunctionalGroup:
    return FunctionalGroup(id, label, formula, name, dmw, die, den, ddip, dh, salt, nitro, cat)


FUNCTIONAL_GROUPS_CATALOG: list[FunctionalGroup] = [
    _fg("none", "None (No Action)", "-", "No Action", 0, 0, 0, 0, 0, False, False, "control"),
    _fg("H", "Hydrogen (-H)", "-H", "Hydrogen", 1.008, 0.1, 2.2, -0.5, 0, False, False, "control"),
    # Nitrogen-containing groups
    _fg("NH2", "Primary Amine (-NH₂)", "-NH₂", "Amine", 16.023, -1.3, 3.04, 1.4, -90, False, True, "nitrogen"),
    _fg("NH_CH3", "Secondary Amine (-NH-CH₃)", "-NH-CH₃", "Methylamine", 30.05, -1.5, 2.98, 1.3, -75, False, True, "nitrogen"),
    _fg("N_CH3_2", "Tertiary Amine (-N(CH₃)₂)", "-N(CH₃)₂", "Dimethylamine", 44.08, -1.7, 2.92, 1.2, -60, False, True, "nitrogen"),
    _fg("NO2", "Nitro Group (-NO₂)", "-NO₂", "Nitro", 46.01, 0.8, 3.44, 3.9, -55, False, True, "nitrogen"),
    _fg("CONH2", "Primary Amide (-CONH₂)", "-CONH₂", "Amide", 44.03, -0.2, 3.12, 3.7, -210, False, True, "nitrogen"),
    _fg("CN", "Nitrile / Cyano (-C≡N)", "-C≡N", "Nitrile", 26.02, 0.5, 3.15, 3.9, 120, False, True, "nitrogen"),
    _fg("N_QUAT", "Quaternary Ammonium Salt (-N⁺(CH₃)₃ Cl⁻)", "-N⁺(CH₃)₃ Cl⁻", "Quaternary Ammonium", 94.58, -1.8, 3.1, 6.5, 90, True, True, "nitrogen"),
    _fg("UREA", "Urea Fragment (-NH-CO-NH₂)", "-NH-CO-NH₂", "Urea", 59.05, -0.6, 3.18, 4.5, -240, False, True, "nitrogen"),
    _fg("GUANIDINE", "Guanidinium Salt (-NH-C(=NH)NH₂)", "-NH-C(=NH)NH₂", "Guanidine", 58.06, -1.9, 3.15, 5.2, -120, True, True, "nitrogen"),
    _fg("AZIDE", "Azide (-N₃)", "-N₃", "Azide", 42.02, 0.3, 3.1, 2.1, 290, False, True, "nitrogen"),
    # Oxygen groups and organic salts
    _fg("COO_Na", "Organic Salt (-COO⁻Na⁺)", "-COO⁻Na⁺", "Carboxylate Salt", 67.0, -1.1, 2.95, 4.8, 115, True, False, "salt"),
    _fg("COOH", "Carboxylic Acid (-COOH)", "-COOH", "Carboxyl", 45.018, 0.05, 3.12, 1.8, -230, False, False, "oxygen"),
    _fg("CHO", "Aldehyde (-CHO)", "-CHO", "Aldehyde", 29.018, -0.3, 2.8, 2.7, -120, False, False, "oxygen"),
    _fg("CO", "Ketone (>C=O)", ">C=O", "Ketone", 28.01, -0.5, 2.85, 2.9, -130, False, False, "oxygen"),
    _fg("Ether", "Ether (-O-)", "-O-", "Ether", 15.999, -0.15, 3.44, 1.2, -110, False, False, "oxygen"),
    # Halogens, sulfur, phosphorus
    _fg("Cl", "Halide (-Cl)", "-Cl", "Chloride", 35.45, 0.6, 3.16, 1.9, 80, False, False, "halogen"),
    _fg("Br", "Bromide (-Br)", "-Br", "Bromide", 79.9, 0.4, 2.96, 1.8, 95, False, False, "halogen"),
    _fg("F", "Fluoride (-F)", "-F", "Fluoride", 18.998, 1.2, 3.98, 2.1, -150, False, False, "halogen"),
    _fg("I", "Iodide (-I)", "-I", "Iodide", 126.9, 0.2, 2.66, 1.5, 110, False, False, "halogen"),
    _fg("COO_K", "Potassium Salt (-COO⁻K⁺)", "-COO⁻K⁺", "Potassium Carboxylate", 83.1, -1.2, 2.9, 5.1, 105, True, False, "salt"),
    _fg("SH", "Thiol (-SH)", "-SH", "Thiol", 33.07, -0.8, 2.58, 1.4, -45, False, False, "sulfur"),
    _fg("SO3_Na", "Sulfonate Salt (-SO₃⁻Na⁺)", "-SO₃⁻Na⁺", "Sulfonate", 103.06, -1.4, 3.25, 5.6, 95, True, False, "salt"),
    _fg("PO4_H", "Phosphate (-O-PO₃H₂)", "-O-PO₃H₂", "Phosphate", 97.0, -0.5, 3.3, 3.8, -320, False, False, "phosphorus"),
    _fg("CH3", "Methyl Group (-CH₃)", "-CH₃", "Methyl", 15.035, -0.4, 2.5, -0.3, 35, False, False, "hydrocarbon"),
]

NONE_LABEL = "None (No Action)"
HYDROGEN_LABEL = "Hydrogen (-H)"
SALT_LABEL = "Organic Salt (-COO⁻Na⁺)"

GROUP_BY_LABEL: dict[str, FunctionalGroup] = {g.label: g for g in FUNCTIONAL_GROUPS_CATALOG}
GROUP_BY_ID: dict[str, FunctionalGroup] = {g.id: g for g in FUNCTIONAL_GROUPS_CATALOG}


# ======================================================================================
# 4. ELEMENT GAME DATA
# ======================================================================================
PERIODIC_ELEMENTS_GAME: list[ElementCard] = [
    ElementCard("H", "Hydrogen", 1, 1.008, 1, 2.20, 13.6, "nonmetal", "#0ea5e9"),
    ElementCard("C", "Carbon", 6, 12.011, 4, 2.55, 11.26, "organic", "#334155"),
    ElementCard("N", "Nitrogen", 7, 14.007, 3, 3.04, 14.53, "nonmetal", "#4f46e5"),
    ElementCard("O", "Oxygen", 8, 15.999, 2, 3.44, 13.62, "nonmetal", "#e11d48"),
    ElementCard("Na", "Sodium", 11, 22.990, 1, 0.93, 5.14, "alkali", "#f59e0b"),
    ElementCard("Mg", "Magnesium", 12, 24.305, 2, 1.31, 7.65, "alkali", "#14b8a6"),
    ElementCard("Al", "Aluminum", 13, 26.982, 3, 1.61, 5.99, "nonmetal", "#06b6d4"),
    ElementCard("Si", "Silicon", 14, 28.085, 4, 1.90, 8.15, "nonmetal", "#0f766e"),
    ElementCard("P", "Phosphorus", 15, 30.974, 3, 2.19, 10.49, "nonmetal", "#7c3aed"),
    ElementCard("S", "Sulfur", 16, 32.06, 2, 2.58, 10.36, "nonmetal", "#eab308"),
    ElementCard("Cl", "Chlorine", 17, 35.45, 1, 3.16, 12.97, "halogen", "#059669"),
    ElementCard("Ca", "Calcium", 20, 40.078, 2, 1.00, 6.11, "alkali", "#78716c"),
]

# "-OH" is added here because two of the game challenges need it (the JS tray forgot it).
FUNCTIONAL_FRAGMENTS_GAME: list[ElementCard] = [
    ElementCard("-Cl", "Chloride", 17, 35.45, 1, 3.16, 12.97, "fragment", "#059669"),
    ElementCard("-NH₂", "Amino", 0, 16.02, 1, 3.04, 8.8, "fragment", "#6366f1"),
    ElementCard("-COOH", "Carboxyl", 0, 45.02, 1, 3.12, 10.3, "fragment", "#be185d"),
    ElementCard("-COO⁻Na⁺", "Sodium Carboxylate", 0, 67.0, 1, 2.95, 9.1, "fragment", "#f59e0b"),
    ElementCard("-CH₃", "Methyl", 0, 15.03, 1, 2.55, 9.8, "fragment", "#475569"),
    ElementCard("-OH", "Hydroxyl", 0, 17.01, 1, 3.44, 10.8, "fragment", "#e11d48"),
]

# Standard atomic masses used for every molecular-weight calculation in the app.
ATOMIC_MASS: dict[str, float] = {e.symbol: e.atomic_mass for e in PERIODIC_ELEMENTS_GAME}
ATOMIC_MASS.update({"Br": 79.904, "K": 39.098, "F": 18.998, "I": 126.90})


# ======================================================================================
# 5. PARSERS  (turn what the student types into numbers the program understands)
# ======================================================================================
_PREFIXES = [
    ("meth", "methan", None, 1), ("eth", "ethan", "ethyl", 2), ("prop", "propan", "propyl", 3),
    ("but", "butan", "butyl", 4), ("pent", "pentan", "pentyl", 5), ("hex", "hexan", "hexyl", 6),
    ("hept", "heptan", "heptyl", 7), ("oct", "octan", "octyl", 8), ("non", "nonan", "nonyl", 9),
    ("dec", "decan", "decyl", 10),
]


def count_carbons_in_chain(raw_input: str) -> int:
    """Estimate how many carbon atoms are in a typed chain such as 'CH3-CH2-CH3' or 'butane'."""
    clean = (raw_input or "").strip()
    if not clean:
        return 3
    lower = clean.lower()

    # 1. Explicit phrases like "5 carbons", "4 carbon", "5C"
    phrase = re.search(r"(\d+)\s*(?:carbons?|c\b|-c\b)", lower)
    if phrase:
        n = int(phrase.group(1))
        if 0 < n <= 50:
            return n

    # 2. IUPAC prefixes: meth(1) ... dec(10)
    for start, contains1, contains2, n in _PREFIXES:
        if lower.startswith(start) or contains1 in lower or (contains2 and contains2 in lower):
            return n

    # 3. Formula notation like C5H12 (first remove symbols that start with C but are not carbon)
    without_cl = re.sub(r"Cl|Ca|Cr|Cu|Cd|Co|Cs|Ce", "", clean)
    formula = re.search(r"\bC(\d+)", without_cl, re.I) or re.search(r"^C(\d+)", without_cl, re.I)
    if formula:
        num = int(formula.group(1))
        if 0 < num <= 50:
            return num

    # 4. Repeated units like (CH2)4, then count CH3 / CH2 / CH / C one by one
    total = 0
    for p in re.findall(r"\(CH2\)(\d+)", without_cl, re.I):
        total += int(p)
    stripped = re.sub(r"\(CH2\)\d+", "", without_cl, flags=re.I)
    total += len(re.findall(r"CH3|CH2|CH|C(?=[^a-zA-Z]|$)", stripped, re.I))

    return max(1, min(total or 3, 25))


def extract_detected_groups(formula_str: str) -> list[str]:
    s = formula_str.lower()
    groups = []
    if "nh2" in s or "amine" in s:
        groups.append("Amine (-NH₂)")
    if "no2" in s or "nitro" in s:
        groups.append("Nitro (-NO₂)")
    if "conh2" in s or "amide" in s:
        groups.append("Amide (-CONH₂)")
    if "oh" in s or "alcohol" in s or "hydroxyl" in s:
        groups.append("Alcohol (-OH)")
    if "coo-na+" in s or "coona" in s or "salt" in s:
        groups.append("Organic Salt (-COO⁻Na⁺)")
    if "cooh" in s or "carboxyl" in s:
        groups.append("Carboxylic Acid (-COOH)")
    if "cl" in s or "halide" in s:
        groups.append("Halide (-Cl)")
    if "sh" in s or "thiol" in s:
        groups.append("Thiol (-SH)")
    if "c≡n" in s or "cn" in s or "nitrile" in s:
        groups.append("Nitrile (-C≡N)")
    return groups


# A small "chemistry dictionary" of common molecules the parser recognises by name.
COMMON_MOLECULES: dict[str, dict] = {
    "methanol": dict(name="Methanol (CH₃-OH)", formula="CH₃-OH", carbons=1,
                     desc="1-carbon alcohol with high polarity for bio-clay gallery wetting.",
                     pos="C1 (Carbon-1)", mw=32.04, ie=10.84, en=2.55, dipole=1.7, dh=-239.1),
    "methane": dict(name="Methane (CH₄)", formula="CH₄", carbons=1, desc="Smallest tetrahedral hydrocarbon building block.",
                    pos="C1 (Central Carbon)", mw=16.04, ie=12.61, en=2.2, dipole=0.0, dh=-74.8),
    "ethane": dict(name="Ethane (CH₃-CH₃)", formula="CH₃-CH₃", carbons=2, desc="2-carbon saturated aliphatic backbone.",
                   pos="C2 (Terminal Carbon)", mw=30.07, ie=11.52, en=2.5, dipole=0.0, dh=-84.0),
    "propane": dict(name="Propane (CH₃-CH₂-CH₃)", formula="CH₃-CH₂-CH₃", carbons=3, desc="3-carbon aliphatic scaffold.",
                    pos="C3 (Terminal Carbon)", mw=44.1, ie=10.95, en=2.55, dipole=0.08, dh=-104.7),
    "butane": dict(name="Butane (CH₃-CH₂-CH₂-CH₃)", formula="CH₃-CH₂-CH₂-CH₃", carbons=4, desc="4-carbon linear alkane backbone.",
                   pos="C4 (Terminal Carbon)", mw=58.12, ie=10.53, en=2.55, dipole=0.05, dh=-125.7),
    "butanol": dict(name="1-Butanol (CH₃-CH₂-CH₂-CH₂-OH)", formula="CH₃-CH₂-CH₂-CH₂-OH", carbons=4,
                    desc="4-carbon primary alcohol with hydrophobic tail and hydrophilic head.",
                    pos="C4 (Terminal OH)", mw=74.12, ie=10.04, en=2.55, dipole=1.66, dh=-327.3),
    "propanoic_acid": dict(name="Propanoic Acid (CH₃-CH₂-COOH)", formula="CH₃-CH₂-COOH", carbons=3,
                           desc="3-carbon carboxylic acid precursor readily converted into bio-clay intercalating salts.",
                           pos="C1 (Carboxyl Carbon)", mw=74.08, ie=10.44, en=2.9, dipole=1.75, dh=-510.8),
    "propionic": dict(name="Propionic Acid (CH₃-CH₂-COOH)", formula="CH₃-CH₂-COOH", carbons=3,
                      desc="3-carbon carboxylic acid precursor readily converted into bio-clay intercalating salts.",
                      pos="C1 (Carboxyl Carbon)", mw=74.08, ie=10.44, en=2.9, dipole=1.75, dh=-510.8),
    "glycerol": dict(name="Glycerol / Triol (HO-CH₂-CH(OH)-CH₂-OH)", formula="HO-CH₂-CH(OH)-CH₂-OH", carbons=3,
                     desc="Tri-hydroxy compound capable of multi-site hydrogen bonding to clay platelets.",
                     pos="C1 (Terminal Hydroxyl)", mw=92.09, ie=9.9, en=2.85, dipole=2.68, dh=-668.5),
    "acetone": dict(name="Acetone (CH₃-CO-CH₃)", formula="CH₃-CO-CH₃", carbons=3, desc="Carbonyl dipolar solvent for clay dispersion.",
                    pos="C2 (Carbonyl Carbon)", mw=58.08, ie=9.7, en=2.7, dipole=2.88, dh=-248.1),
    "aniline": dict(name="Aniline (C₆H₅-NH₂)", formula="C₆H₅-NH₂", carbons=6,
                    desc="Aromatic amine with conjugated pi-electron system and strong clay adsorption.",
                    pos="C1 (Amine Ring Carbon)", mw=93.13, ie=7.72, en=2.95, dipole=1.53, dh=87.1),
    "glucosamine": dict(name="Glucosamine Monomer (C₆H₁₃NO₅)", formula="C₆H₁₃NO₅", carbons=6,
                        desc="Amine-functionalized biocompatible bio-nanocomposite precursor.",
                        pos="C2 (Amine Carbon)", mw=179.17, ie=8.5, en=3.1, dipole=4.1, dh=-780.0),
}


def _strip_dashes(s: str) -> str:
    return re.sub(r"[–—\s]", "", s)


def parse_molecule_input(raw_input: str) -> dict:
    """Recognise the base molecule typed by the student and return a BaseMolecule preset for it."""
    clean = (raw_input or "").strip()
    lower = clean.lower()
    estimated_carbons = count_carbons_in_chain(clean)

    # 1. Exact match with one of the 10 presets
    for m in BASE_MOLECULES:
        if m.name.lower() == lower or m.id.lower() == lower or _strip_dashes(m.formula.lower()) == _strip_dashes(lower):
            return dict(recognized=True, name=m.name, formula=m.formula, carbons=m.carbons,
                        description=m.description, default_position=m.default_position,
                        preset=m, detected_groups=extract_detected_groups(m.formula))

    # 2. Chemistry dictionary of common molecules
    for key, v in COMMON_MOLECULES.items():
        if key in lower or clean == v["formula"]:
            preset = BaseMolecule(key, v["name"], v["formula"], v["carbons"], v["desc"], v["pos"],
                                  v["mw"], v["ie"], v["en"], v["dipole"], v["dh"], 109.5, 1.43)
            return dict(recognized=True, name=v["name"], formula=v["formula"], carbons=v["carbons"],
                        description=v["desc"], default_position=v["pos"], preset=preset,
                        detected_groups=extract_detected_groups(v["formula"]))

    # 3. Anything else -> build an estimated custom preset from the formula itself
    detected = extract_detected_groups(clean)
    has_n = bool(re.search(r"nh2|nh|no2|cn|n\+", clean, re.I))
    has_o = bool(re.search(r"oh|cooh|cho|co|o", clean, re.I))
    has_salt = bool(re.search(r"na\+|k\+|salt|coo-", clean, re.I))

    formatted = re.sub(r"\s+", "", clean)
    est_mw = js_round((estimated_carbons * 14 + (16 if has_n else 0) + (16 if has_o else 0) + 2) * 10) / 10
    est_ie = 8.8 if has_n else (10.2 if has_o else 11.2)
    est_en = 2.85 if has_n else (2.6 if has_o else 2.5)
    est_dip = 5.5 if has_salt else (1.4 if has_n else (1.7 if has_o else 0.2))
    est_dh = -70 * estimated_carbons - (150 if has_o else 0)
    default_pos = f"C{estimated_carbons} (Terminal / Omega)"

    groups_text = ", ".join(detected) if detected else "aliphatic framework"
    preset = BaseMolecule(
        id=f"custom_{estimated_carbons}c",
        name=clean if len(clean) > 3 else f"Custom {estimated_carbons}-Carbon Chain",
        formula=formatted, carbons=estimated_carbons,
        description=f"User-defined {estimated_carbons}-carbon chain containing {groups_text} for bio-clay engineering.",
        default_position=default_pos, base_mw=est_mw, base_ie=est_ie, base_en=est_en,
        base_dipole=est_dip, base_delta_h=est_dh, base_angle=109.5, base_length=1.43,
    )
    return dict(recognized=True, name=clean, formula=formatted, carbons=estimated_carbons,
                description=preset.description, default_position=default_pos, preset=preset,
                detected_groups=detected)


def parse_target_position(raw_input: str, total_carbons: int = 3) -> dict:
    """Turn 'C3', 'carbon-2', 'alpha', 'terminal' ... into a carbon index inside the chain."""
    clean = (raw_input or "").strip()
    lower = clean.lower()
    m = re.search(r"(?:c|carbon)[-\s]?(\d+)|^(\d+)$", clean, re.I)
    carbon_num = 1
    if m:
        carbon_num = int(m.group(1) or m.group(2))
    elif "alpha" in lower:
        carbon_num = 1
    elif "beta" in lower:
        carbon_num = min(2, total_carbons)
    elif "gamma" in lower:
        carbon_num = min(3, total_carbons)
    elif "terminal" in lower or "omega" in lower:
        carbon_num = total_carbons

    idx = max(1, min(carbon_num, max(total_carbons, 1)))
    if idx == 1:
        terminal_type = "C1 (Alpha Terminal / Primary Site)"
    elif idx == total_carbons:
        terminal_type = f"C{idx} (Omega / Chain End Terminal)"
    else:
        terminal_type = f"C{idx} (Internal Secondary Position)"
    return dict(
        carbon_index=idx,
        formatted_label=f"Carbon-{idx} (C{idx})",
        terminal_type=terminal_type,
        description=f"Reaction localized at position C{idx}. Target orbital participates in functional group cleavage and bio-clay docking.",
    )


def _norm(s: str) -> str:
    return re.sub(r"[-–—\s()]", "", s.lower())


def parse_functional_group_input(raw_input: str) -> Optional[FunctionalGroup]:
    """Match free text like '-COO-Na+', 'amine' or 'Cl' to a group in the catalogue."""
    clean = (raw_input or "").strip()
    lower = _norm(clean)
    if not clean or lower in ("none", "noaction"):
        return FUNCTIONAL_GROUPS_CATALOG[0]

    # Pass 1 - exact matches (label / formula / name / id).  Doing exact matches first means
    # "-Cl" finds the Halide group instead of the Quaternary Ammonium salt that also contains "Cl".
    for g in FUNCTIONAL_GROUPS_CATALOG:
        if lower in (_norm(g.label), _norm(g.formula), _norm(g.name), _norm(g.id)):
            return g
    # Pass 2 - partial matches
    for g in FUNCTIONAL_GROUPS_CATALOG:
        if lower and (lower in _norm(g.label) or _norm(g.name) in lower):
            return g

    # Pass 3 - keyword rules
    rules = [
        (r"nh2|amine|amino", "NH2"), (r"no2|nitro", "NO2"), (r"amide|conh2", "CONH2"),
        (r"nitrile|cyano|cn", "CN"), (r"quat|ammonium", "N_QUAT"), (r"salt|coo-|coona", "COO_Na"),
        (r"acid|cooh|carboxyl", "COOH"), (r"cl|halide|chloro", "Cl"),
    ]
    for pattern, gid in rules:
        if re.search(pattern, clean, re.I):
            return GROUP_BY_ID.get(gid)
    return None


def find_group(label_or_id: str) -> Optional[FunctionalGroup]:
    return GROUP_BY_LABEL.get(label_or_id) or GROUP_BY_ID.get(label_or_id) or parse_functional_group_input(label_or_id)


# ======================================================================================
# 6. REAL-TIME PROPERTY CALCULATOR  (the "reaction matrix" on the Designer tab)
# ======================================================================================
def calculate_realtime_properties(base: BaseMolecule, removed: list[str], added: list[str]) -> dict:
    """Start from the base molecule's properties, subtract removed groups, add new groups."""
    d_mw = d_ie = d_en = d_dip = d_h = 0.0
    has_salt = has_amine = has_nitro = has_amide = False

    for rem in removed:
        g = find_group(rem)
        if g and g.id != "none":
            d_mw -= g.delta_mw
            d_ie -= g.delta_ie
            d_en -= (g.delta_en - 2.2) * 0.2
            d_dip -= g.delta_dipole * 0.7
            d_h -= g.delta_h * 0.8

    for add in added:
        g = find_group(add)
        if g and g.id != "none":
            d_mw += g.delta_mw
            d_ie += g.delta_ie
            d_en += (g.delta_en - 2.2) * 0.25
            d_dip += g.delta_dipole
            d_h += g.delta_h
            has_salt = has_salt or g.is_salt
            has_amine = has_amine or g.id == "NH2" or g.is_nitrogen
            has_nitro = has_nitro or g.id == "NO2"
            has_amide = has_amide or g.id == "CONH2"

    final_mw = max(16.0, js_round(base.base_mw + d_mw, 2))
    final_ie = max(7.0, min(15.0, js_round(base.base_ie + d_ie, 2)))
    final_en = max(1.8, min(3.8, js_round(base.base_en + d_en, 2)))
    final_dip = max(0.0, js_round(base.base_dipole + d_dip, 2))
    final_dh = js_round(base.base_delta_h + d_h, 1)
    final_angle = 120.0 if has_salt else (107.5 if has_amine else base.base_angle)
    final_length = 1.27 if has_salt else (1.47 if has_amine else base.base_length)

    # Solubility rule
    if has_salt:
        solubility = "Very High (Ionic Salt / Polar Dissociation in aqueous LDH slurry)"
    elif has_amine or final_dip > 2.0:
        solubility = "High Aqueous Solubility (Hydrogen bond donor)"
    else:
        solubility = "Moderate (Lipophilic Organic)"

    # Bio-clay binding rule
    if has_salt:
        bioclay = "Strong Electrostatic Intercalation (Anionic carboxylate to cationic LDH sheets, d₀₀₁ ~ 1.42 nm)"
    elif has_amine:
        bioclay = "Cationic Basal Intercalation & Nitrogen lone-pair coordination (Montmorillonite & Smectite)"
    elif has_nitro or has_amide:
        bioclay = "Dipolar Organic Adsorption within Clay Galleries"
    else:
        bioclay = "Moderate Hydrogen Bonding to Silicate Surface"

    def metric(orig, mod, unit, desc):
        return dict(original=orig, modified=mod, unit=unit, description=desc)

    return {
        "molecularWeight": metric(base.base_mw, final_mw, "g/mol", "Molecular mass of the synthesized molecule"),
        "ionizationEnergy": metric(base.base_ie, final_ie, "eV", "Ionization potential (IA) to remove valence electron"),
        "electronegativity": metric(base.base_en, final_en, "Pauling", "Average electron-attracting capacity of the reactive center"),
        "dipoleMoment": metric(base.base_dipole, final_dip, "Debye (D)", "Net molecular polarity and dipole magnitude"),
        "enthalpyDeltaH": metric(base.base_delta_h, final_dh, "kJ/mol", "Standard heat / enthalpy of formation (ΔH)"),
        "solubility": dict(original="Moderate Polar Aqueous", modified=solubility),
        "bondAngle": metric(base.base_angle, final_angle, "degrees (°)", "Key dihedral / valence angle around modification site"),
        "bondLength": metric(base.base_length, final_length, "Å", "Chemical bond length at target carbon junction"),
        "bioClayBinding": dict(original="Moderate Hydrogen Bonding to Silicate Layers", modified=bioclay),
    }


def property_contributions(removed: list[str], added: list[str]) -> list[dict]:
    """Show HOW calculate_realtime_properties() got its answer: one row per group, same weights."""
    rows = []
    for label_ in removed:
        g = find_group(label_)
        if g and g.id != "none":
            rows.append({"Group": g.label, "Action": "Removed", "ΔMW (g/mol)": round(-g.delta_mw, 3),
                         "ΔIE (eV)": round(-g.delta_ie, 3), "ΔEN": round(-(g.delta_en - 2.2) * 0.2, 3),
                         "Δμ (D)": round(-g.delta_dipole * 0.7, 3), "ΔH (kJ/mol)": round(-g.delta_h * 0.8, 1)})
    for label_ in added:
        g = find_group(label_)
        if g and g.id != "none":
            rows.append({"Group": g.label, "Action": "Added", "ΔMW (g/mol)": round(g.delta_mw, 3),
                         "ΔIE (eV)": round(g.delta_ie, 3), "ΔEN": round((g.delta_en - 2.2) * 0.25, 3),
                         "Δμ (D)": round(g.delta_dipole, 3), "ΔH (kJ/mol)": round(g.delta_h, 1)})
    return rows


# ======================================================================================
# 7. DESIGNER HELPERS (formula preview + headline) - moved out of the old React component
# ======================================================================================
_SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_UNSUB = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def substitute_on_carbon(base_formula: str, carbon_index: int, group: str) -> Optional[str]:
    """
    Put a group on carbon number `carbon_index` of a condensed chain and take one H away.
        substitute_on_carbon("CH3-CH2-CH3", 3, "COO⁻Na⁺") -> "CH₃-CH₂-CH₂-COO⁻Na⁺"
        substitute_on_carbon("CH3-CH2-CH3", 2, "NH₂")     -> "CH₃-CH(NH₂)-CH₃"
    Returns None when the formula is not a simple CHn-CHn-... chain (then the caller falls back).
    """
    units = base_formula.translate(_UNSUB).split("-")
    parsed = []
    for u in units:
        m = re.fullmatch(r"CH(\d*)|C", u)
        if not m:
            return None
        parsed.append(0 if u == "C" else int(m.group(1) or 1))
    if not 1 <= carbon_index <= len(parsed) or parsed[carbon_index - 1] == 0:
        return None

    parsed[carbon_index - 1] -= 1  # one H is replaced by the new group
    text = []
    for k, h in enumerate(parsed, start=1):
        unit = "C" + ("H" + (str(h) if h > 1 else "") if h > 0 else "")
        unit = unit.translate(_SUB)
        if k == carbon_index and k != len(parsed):
            unit += f"({group})"
        text.append(unit)
    out = "-".join(text)
    if carbon_index == len(parsed):
        out += f"-{group}"
    return out


def display_formula(base_formula: str, added: list[str], action_type: str, carbon_index: int) -> str:
    none_added = (not added) or (NONE_LABEL in added)
    trimmed = re.sub(r"-OH|-H|H\d+O", "", base_formula)
    any_in = lambda *keys: any(any(k in g for k in keys) for g in added)

    def build(group: str, note: str) -> str:
        smart = substitute_on_carbon(base_formula, carbon_index, group)
        return f"{smart or trimmed + '-' + group} ({note})"

    if any_in("Salt", "COO⁻Na⁺", "COO⁻K⁺", "SO₃⁻Na⁺"):
        if any_in("SO₃⁻Na⁺"):
            return build("SO₃⁻Na⁺", "Sodium Sulfonate Nanocomposite")
        if any_in("COO⁻K⁺"):
            return build("COO⁻K⁺", "Potassium Carboxylate Salt")
        return build("COO⁻Na⁺", "Bio-Clay Intercalating Salt")
    if any_in("Amine", "-NH₂"):
        return build("NH₂", "Bio-Clay Cationic Amine")
    if any_in("Nitro", "-NO₂"):
        return build("NO₂", "Nitro Derivative")
    if any_in("Halide", "-Cl", "-Br", "-F", "-I"):
        sym = "Cl" if any_in("-Cl") else "Br" if any_in("-Br") else "F" if any_in("-F") else "I"
        return build(sym, f"Alkyl Halide @ C{carbon_index}")
    if none_added:
        if action_type == "remove_h":
            return f"{base_formula} [-H Cleaved Radical Site @ C{carbon_index}]"
        return f"{base_formula} [Functional Group Cleaved @ C{carbon_index}]"
    added_str = ", ".join(g for g in added if g != NONE_LABEL)
    return f"{base_formula} [C{carbon_index} modified: +{added_str}]"


def blueprint_headline(added: list[str]) -> str:
    if any("Salt" in g for g in added):
        return "Bio-Clay Intercalating Organic Salt Derivative"
    if any(("Halide" in g) or ("-Cl" in g) or ("-Br" in g) for g in added):
        return "Halogen-Functionalized Reactive Intermediate"
    if any(("Amine" in g) or ("Nitro" in g) or ("NH₂" in g) for g in added):
        return "Nitrogen-Functionalized Basal Intercalator"
    return "Modified Bio-Clay Polymer Precursor"


def to_plain_dict(obj) -> dict:
    """Convert a dataclass to a normal dict (handy for pandas / JSON)."""
    return asdict(obj)
