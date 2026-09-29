"""
Unit tests for the chemistry "brain" (no browser needed).

Run from the project folder with:
    python -m unittest discover tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import ai_engine  # noqa: E402
from core.chemistry import (  # noqa: E402
    calculate_realtime_properties, count_carbons_in_chain, display_formula, parse_functional_group_input,
    parse_molecule_input, parse_target_position, substitute_on_carbon,
)
from core.computation import analyze_molecule, optimize_geometry, simulate_kinetics  # noqa: E402
from core.molecule_builder import add_functional_group, build_molecule_from_input, remove_group  # noqa: E402
from core.rules_engine import (  # noqa: E402
    degree_of_unsaturation, evaluate_assembled_molecule, generate_deterministic_chemistry_analysis, hill_formula,
    molar_mass,
)


class TestParsers(unittest.TestCase):
    def test_count_carbons(self):
        cases = {"CH3-CH2-CH3": 3, "butane": 4, "C5H12": 5, "CH3-(CH2)4-CH3": 6, "8 carbons": 8, "CH3-CH2-CH2-Cl": 3}
        for text, n in cases.items():
            self.assertEqual(count_carbons_in_chain(text), n, text)

    def test_target_position(self):
        self.assertEqual(parse_target_position("C2", 3)["carbon_index"], 2)
        self.assertEqual(parse_target_position("C9", 3)["carbon_index"], 3)      # clamped to the chain
        self.assertEqual(parse_target_position("terminal", 5)["carbon_index"], 5)

    def test_group_parser_prefers_exact_match(self):
        self.assertEqual(parse_functional_group_input("-Cl").id, "Cl")          # not the quaternary ammonium salt
        self.assertEqual(parse_functional_group_input("-COO-Na+").id, "COO_Na")
        self.assertEqual(parse_functional_group_input("amine").id, "NH2")
        self.assertIsNone(parse_functional_group_input("xyz"))


class TestProperties(unittest.TestCase):
    def test_propane_to_salt(self):
        base = parse_molecule_input("CH3-CH2-CH3")["preset"]
        props = calculate_realtime_properties(base, ["Hydrogen (-H)"], ["Organic Salt (-COO⁻Na⁺)"])
        self.assertAlmostEqual(props["molecularWeight"]["modified"], 44.0 - 1.008 + 67.0, places=1)
        self.assertEqual(props["bondAngle"]["modified"], 120.0)
        self.assertIn("Electrostatic", props["bioClayBinding"]["modified"])

    def test_formula_substitution(self):
        self.assertEqual(substitute_on_carbon("CH3-CH2-CH3", 3, "COO⁻Na⁺"), "CH₃-CH₂-CH₂-COO⁻Na⁺")
        self.assertEqual(substitute_on_carbon("CH3-CH2-CH3", 2, "NH₂"), "CH₃-CH(NH₂)-CH₃")
        self.assertIn("CH(NH₂)", display_formula("CH3-CH2-CH2-CH3", ["Primary Amine (-NH₂)"], "remove_h", 2))


class TestRulesEngine(unittest.TestCase):
    def test_molar_mass_and_hill(self):
        self.assertAlmostEqual(molar_mass({"C": 4, "H": 7, "Na": 1, "O": 2}), 110.09, places=2)
        self.assertEqual(hill_formula({"O": 2, "Na": 1, "H": 7, "C": 4}), "C4H7NaO2")

    def test_synthesis_names(self):
        r = generate_deterministic_chemistry_analysis("CH3-CH2-CH3", "remove_h", "C3", ["Hydrogen (-H)"], ["Organic Salt (-COO⁻Na⁺)"])
        self.assertTrue(r["moleculeName"].startswith("Sodium Butanoate"))
        r = generate_deterministic_chemistry_analysis("CH3-CH2-CH2-CH3", "remove_h", "C2", ["Hydrogen (-H)"], ["Primary Amine (-NH₂)"])
        self.assertTrue(r["moleculeName"].startswith("Butan-2-amine"))

    def test_game_challenges(self):
        self.assertEqual(evaluate_assembled_molecule({"C": 3, "H": 7, "-COO⁻Na⁺": 1})["hillFormula"], "C4H7NaO2")
        self.assertTrue(evaluate_assembled_molecule({"C": 3, "H": 7, "-OH": 1})["isValid"])
        self.assertTrue(evaluate_assembled_molecule({"C": 3, "H": 7, "-NH₂": 1})["isValid"])
        self.assertFalse(evaluate_assembled_molecule({"C": 3, "H": 7})["isValid"])   # propyl radical
        self.assertFalse(evaluate_assembled_molecule({"C": 1, "H": 6})["isValid"])   # impossible

    def test_degree_of_unsaturation(self):
        self.assertEqual(degree_of_unsaturation({"C": 3, "H": 8}), 0)
        self.assertEqual(degree_of_unsaturation({"C": 2, "H": 4}), 1)


class TestMolView(unittest.TestCase):
    def test_builder_and_graph(self):
        mol = build_molecule_from_input("CH3-CH2-CH2-COO-Na+")
        self.assertTrue(mol["displayName"].startswith("Sodium Butanoate"))
        an = analyze_molecule(mol["atoms"], mol["bonds"])
        self.assertEqual(an["hill"], "C4H7NaO2")
        self.assertEqual(an["longest_chain"], 4)
        self.assertTrue(an["all_valences_ok"])

    def test_add_and_remove_groups(self):
        mol = build_molecule_from_input("CH3-CH2-CH3")
        atoms, bonds, _ = add_functional_group(mol["atoms"], mol["bonds"], "c2", "cl")
        self.assertTrue(analyze_molecule(atoms, bonds)["all_valences_ok"])
        atoms, bonds, _ = remove_group(atoms, bonds, None, "chloride")
        self.assertEqual(analyze_molecule(atoms, bonds)["hill"], "C3H7")

    def test_geometry_optimisation_lowers_energy(self):
        mol = build_molecule_from_input("glycine")
        _, before, after = optimize_geometry(mol["atoms"], mol["bonds"])
        self.assertLess(after, before)


class TestKinetics(unittest.TestCase):
    def test_calibration_and_arrhenius(self):
        ref = simulate_kinetics(30, 2.0, "Saponification", 30)
        self.assertAlmostEqual(ref["t95_conversion"], 2.0, delta=0.1)       # calibrated to the protocol time
        hot = simulate_kinetics(30, 2.0, "Saponification", 60)
        self.assertGreater(hot["rate_factor"], 1.0)                          # hotter = faster
        self.assertLess(hot["t95_conversion"], ref["t95_conversion"])


class TestGeminiFallback(unittest.TestCase):
    def test_uses_gemini_answer_when_available(self):
        class FakeResp:
            text = '```json\n{"moleculeName": "Test Salt", "confidenceScore": 88}\n```'

        class FakeModels:
            def generate_content(self, **_kw):
                return FakeResp()

        class FakeClient:
            models = FakeModels()

        old = ai_engine.get_client
        ai_engine.get_client = lambda _key: FakeClient()
        try:
            source, report = ai_engine.synthesize("CH3-CH2-CH3", "remove_h", "C3", ["Hydrogen (-H)"],
                                                  ["Organic Salt (-COO⁻Na⁺)"], api_key="fake")
        finally:
            ai_engine.get_client = old
        self.assertTrue(source.startswith("gemini"))
        self.assertEqual(report["moleculeName"], "Test Salt")
        self.assertEqual(report["confidenceScore"], 88)
        self.assertTrue(report["stepByStepProtocol"])  # missing fields filled from the rules engine

    def test_offline_fallback(self):
        source, report = ai_engine.synthesize("CH3-CH2-CH3", "remove_h", "C3", ["Hydrogen (-H)"],
                                              ["Organic Salt (-COO⁻Na⁺)"], api_key=None)
        self.assertEqual(source, "rules_engine")
        self.assertIn("moleculeName", report)


if __name__ == "__main__":
    unittest.main()
