"""
computation.py
==============
The "computational thinking" layer - things the old JavaScript website could NOT do,
built with the scientific Python libraries taught in class.

1. NetworkX  -> treat a molecule as a GRAPH (atoms = nodes, bonds = edges) and analyse it
2. NumPy     -> vector maths for bond lengths
3. SciPy     -> (a) optimise a messy 3D structure   (scipy.optimize.minimize)
                (b) simulate reaction + intercalation kinetics (scipy.integrate.solve_ivp)
                (c) find atoms that are too close    (scipy.spatial.distance)
4. Pandas    -> put every result into a neat DataFrame table
"""

from __future__ import annotations

import math

import networkx as nx
import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import minimize
from scipy.spatial.distance import pdist, squareform

from .molecule_builder import ELEMENT_STYLES
from .rules_engine import VALENCE, degree_of_unsaturation, hill_formula, molar_mass, numbers_in

# The drawing uses "screen units": 55 units = one C-C bond = 1.54 Å
UNIT_TO_ANGSTROM = 1.54 / 55.0
COVALENT_RADIUS = {"H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "Na": 1.66, "Cl": 1.02,
                   "Br": 1.20, "S": 1.05, "P": 1.07}


# ======================================================================================
# 1. Molecule as a graph (NetworkX)
# ======================================================================================
def molecule_graph(atoms: list[dict], bonds: list[dict]) -> nx.Graph:
    g = nx.Graph()
    for a in atoms:
        g.add_node(a["id"], element=a["element"])
    for b in bonds:
        if g.has_node(b["sourceId"]) and g.has_node(b["targetId"]):
            g.add_edge(b["sourceId"], b["targetId"], order=b.get("order", 1), type=b.get("type", "single"))
    return g


def longest_carbon_chain(g: nx.Graph) -> int:
    """Longest path through carbon atoms only (this is how IUPAC picks the parent chain)."""
    carbons = [n for n, d in g.nodes(data=True) if d["element"] == "C"]
    cg = g.subgraph(carbons)
    best = 0
    for comp in nx.connected_components(cg):
        sub = cg.subgraph(comp)
        if len(sub) == 1:
            best = max(best, 1)
            continue
        if nx.is_tree(sub):  # trees: diameter + 1 = longest chain (fast and exact)
            best = max(best, nx.diameter(sub) + 1)
        else:  # rings: try all simple paths between carbons (fine for small molecules)
            nodes = list(sub)
            for i, u in enumerate(nodes):
                for v in nodes[i + 1:]:
                    for p in nx.all_simple_paths(sub, u, v, cutoff=25):
                        best = max(best, len(p))
    return best


def analyze_molecule(atoms: list[dict], bonds: list[dict]) -> dict:
    g = molecule_graph(atoms, bonds)
    counts: dict[str, int] = {}
    for a in atoms:
        counts[a["element"]] = counts.get(a["element"], 0) + 1

    rows = []
    for a in atoms:
        used = sum(d.get("order", 1) for _, _, d in g.edges(a["id"], data=True))
        expected = VALENCE.get(a["element"], ELEMENT_STYLES.get(a["element"], {}).get("valence", 2))
        if used == expected:
            status = "✅ satisfied"
        elif used < expected:
            status = f"⚠️ {expected - used} open (radical site)"
        else:
            status = f"❌ over by {used - expected}"
        rows.append({"Atom": a["id"], "Element": a["element"], "Bonds used": used,
                     "Normal valence": expected, "Status": status})
    valence_df = pd.DataFrame(rows)

    n_components = nx.number_connected_components(g) if len(g) else 0
    rings = len(nx.cycle_basis(g)) if len(g) else 0
    ok = bool(len(valence_df)) and valence_df["Status"].str.startswith("✅").all()
    return {
        "graph": g,
        "hill": hill_formula(counts),
        "mw": molar_mass(counts),
        "counts": counts,
        "n_atoms": len(atoms),
        "n_bonds": len(bonds),
        "components": n_components,
        "rings": rings,
        "longest_chain": longest_carbon_chain(g) if len(g) else 0,
        "dou": degree_of_unsaturation(counts) if counts else 0,
        "valence_table": valence_df,
        "all_valences_ok": bool(ok),
    }


# ======================================================================================
# 2. Bond geometry (NumPy + SciPy spatial)
# ======================================================================================
def coords_array(atoms: list[dict]) -> np.ndarray:
    return np.array([[a["x"], a["y"], a.get("z", 0)] for a in atoms], dtype=float).reshape(-1, 3)


def bond_geometry_table(atoms: list[dict], bonds: list[dict]) -> pd.DataFrame:
    idx = {a["id"]: i for i, a in enumerate(atoms)}
    xyz = coords_array(atoms)
    rows = []
    for b in bonds:
        if b["sourceId"] not in idx or b["targetId"] not in idx:
            continue
        i, j = idx[b["sourceId"]], idx[b["targetId"]]
        r = float(np.linalg.norm(xyz[i] - xyz[j])) * UNIT_TO_ANGSTROM
        e1, e2 = atoms[i]["element"], atoms[j]["element"]
        rows.append({"Bond": f"{e1}{'=' if b['order'] == 2 else '≡' if b['order'] == 3 else '···' if b.get('type') == 'ionic' else '-'}{e2}",
                     "Atoms": f"{atoms[i]['id']} – {atoms[j]['id']}",
                     "Type": b.get("type", "single"),
                     "Model length (Å)": round(r, 2),
                     "Ideal length (Å)": round(ideal_length(e1, e2, b), 2)})
    return pd.DataFrame(rows)


def close_contacts(atoms: list[dict], bonds: list[dict], cutoff_angstrom: float = 0.9) -> list[tuple[str, str, float]]:
    """Pairs of NON-bonded atoms closer than the cutoff (atoms overlapping in the drawing)."""
    if len(atoms) < 2:
        return []
    d = squareform(pdist(coords_array(atoms))) * UNIT_TO_ANGSTROM
    bonded = {frozenset((b["sourceId"], b["targetId"])) for b in bonds}
    out = []
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            if d[i, j] < cutoff_angstrom and frozenset((atoms[i]["id"], atoms[j]["id"])) not in bonded:
                out.append((atoms[i]["id"], atoms[j]["id"], round(float(d[i, j]), 2)))
    return out


def ideal_length(e1: str, e2: str, bond: dict) -> float:
    if bond.get("type") == "ionic":
        return 2.35
    r = COVALENT_RADIUS.get(e1, 0.75) + COVALENT_RADIUS.get(e2, 0.75)
    return r - {2: 0.20, 3: 0.34}.get(bond.get("order", 1), 0.0)


# ======================================================================================
# 3. Geometry clean-up with scipy.optimize (a tiny "force field")
# ======================================================================================
def _pair_terms(atoms, bonds):
    """Build every spring in the model: (i, j, target distance in units, stiffness, repulsive_only)."""
    idx = {a["id"]: i for i, a in enumerate(atoms)}
    g = molecule_graph(atoms, bonds)
    terms, bonded_pairs = [], set()

    for b in bonds:  # 1) bond stretching
        if b["sourceId"] in idx and b["targetId"] in idx:
            i, j = idx[b["sourceId"]], idx[b["targetId"]]
            r0 = ideal_length(atoms[i]["element"], atoms[j]["element"], b) / UNIT_TO_ANGSTROM
            terms.append((i, j, r0, 1.0, False))
            bonded_pairs.add(frozenset((i, j)))

    angle_pairs = set()
    for centre in g.nodes:  # 2) angle bending as a 1-3 distance spring (law of cosines)
        nb = list(g.neighbors(centre))
        orders = [g.edges[centre, n].get("order", 1) for n in nb]
        element = atoms[idx[centre]]["element"]
        if 3 in orders:
            angle = 180.0      # sp  (linear)
        elif 2 in orders:
            angle = 120.0      # sp2 (trigonal planar)
        elif element == "O":
            angle = 104.5      # water-like bent oxygen
        elif element == "N":
            angle = 107.0      # pyramidal amine nitrogen
        else:
            angle = 109.5      # sp3 (tetrahedral)
        theta = math.radians(angle)
        for a_i in range(len(nb)):
            for b_i in range(a_i + 1, len(nb)):
                i, j = idx[nb[a_i]], idx[nb[b_i]]
                ra = ideal_length(atoms[idx[centre]]["element"], atoms[i]["element"], g.edges[centre, nb[a_i]]) / UNIT_TO_ANGSTROM
                rb = ideal_length(atoms[idx[centre]]["element"], atoms[j]["element"], g.edges[centre, nb[b_i]]) / UNIT_TO_ANGSTROM
                r13 = math.sqrt(ra * ra + rb * rb - 2 * ra * rb * math.cos(theta))
                terms.append((i, j, r13, 0.4, False))
                angle_pairs.add(frozenset((i, j)))

    n = len(atoms)  # 3) everything else just must not overlap
    for i in range(n):
        for j in range(i + 1, n):
            key = frozenset((i, j))
            if key in bonded_pairs or key in angle_pairs:
                continue
            both_h = atoms[i]["element"] == "H" and atoms[j]["element"] == "H"
            r_min = (2.0 if both_h else 2.6) / UNIT_TO_ANGSTROM
            terms.append((i, j, r_min, 0.3, True))
    return terms


def optimize_geometry(atoms: list[dict], bonds: list[dict], seed: int = 7) -> tuple[list[dict], float, float]:
    """Relax the 3D coordinates so bond lengths and angles become realistic.
    Returns (new_atoms, energy_before, energy_after)."""
    if len(atoms) < 2:
        return atoms, 0.0, 0.0
    terms = _pair_terms(atoms, bonds)
    I = np.array([t[0] for t in terms])
    J = np.array([t[1] for t in terms])
    R0 = np.array([t[2] for t in terms])
    K = np.array([t[3] for t in terms])
    REP = np.array([t[4] for t in terms])

    x0 = coords_array(atoms)
    rng = np.random.default_rng(seed)
    x0 = x0 + rng.normal(0, 2.0, x0.shape)  # tiny shake so flat (z=0) drawings can become 3D

    def energy_and_grad(flat):
        X = flat.reshape(-1, 3)
        diff = X[I] - X[J]
        r = np.linalg.norm(diff, axis=1) + 1e-9
        dr = r - R0
        active = np.where(REP, dr < 0, True)
        e = float(np.sum(K * dr * dr * active))
        coef = (2 * K * dr * active / r)[:, None] * diff
        grad = np.zeros_like(X)
        np.add.at(grad, I, coef)
        np.add.at(grad, J, -coef)
        return e, grad.ravel()

    e_before = energy_and_grad(coords_array(atoms).ravel())[0]
    res = minimize(energy_and_grad, x0.ravel(), jac=True, method="L-BFGS-B", options={"maxiter": 2000})
    X = res.x.reshape(-1, 3)
    X -= X.mean(axis=0)  # keep the molecule centred on the screen
    new_atoms = [{**a, "x": round(float(X[k, 0])), "y": round(float(X[k, 1])), "z": round(float(X[k, 2]))}
                 for k, a in enumerate(atoms)]
    return new_atoms, round(e_before, 1), round(float(res.fun), 1)


# ======================================================================================
# 4. Reaction + intercalation kinetics (scipy.integrate.solve_ivp)
# ======================================================================================
R_GAS = 8.314  # J/(mol·K)

ACTIVATION_ENERGY = [  # (keyword in technique, Ea in kJ/mol)  - typical textbook magnitudes
    ("saponification", 45), ("neutraliz", 45), ("precipitation", 40), ("amination", 80),
    ("oxidation", 60), ("halogenation", 70), ("elimination", 110), ("dehydration", 110),
    ("hydrothermal", 65), ("sol-gel", 55), ("reflux", 65),
]


def parse_temperature_c(text: str, default: float = 25.0) -> float:
    nums = [v for v in numbers_in(text) if -50 <= v <= 400]
    if "room" in (text or "").lower() and not nums:
        return 25.0
    return float(np.mean(nums[:2])) if nums else default


def parse_hours(text: str, default: float = 2.0) -> float:
    nums = [v for v in numbers_in(text) if v > 0]
    if not nums:
        return default
    val = float(np.mean(nums[:2]))
    return val / 60.0 if "min" in (text or "").lower() and "hour" not in (text or "").lower() else val


def activation_energy_for(technique: str) -> float:
    t = (technique or "").lower()
    for key, ea in ACTIVATION_ENERGY:
        if key in t:
            return float(ea)
    return 60.0


def simulate_kinetics(report_temp_c: float, report_hours: float, technique: str,
                      sim_temp_c: float, t_end_hours: float | None = None) -> dict:
    """
    Two-step model (all amounts normalised 0..1):
        precursor  --k1-->  product            (the organic synthesis step)
        product + clay site --k2--> intercalated product  (ion exchange into LDH galleries)
        (precursor starts at 2x the clay's exchange capacity, as in real LDH protocols)

        dP/dt = -k1·P
        dS/dt =  k1·P − k2·S·(1 − I)
        dI/dt =  k2·S·(1 − I)

    Calibration: k1 is chosen so the protocol reaches 95 % conversion in its stated time at
    its stated temperature.  The Arrhenius equation k = A·e^(−Ea/RT) then predicts what
    happens at any other temperature the student picks with the slider.
    """
    ea1 = activation_energy_for(technique) * 1000.0
    ea2 = 25_000.0  # ion exchange is fast and barely temperature-dependent
    t_ref = report_temp_c + 273.15
    t_sim = sim_temp_c + 273.15
    k1_ref = math.log(20.0) / max(report_hours, 0.05)  # 95 % at the stated time
    k2_ref = 1.5 * k1_ref
    k1 = k1_ref * math.exp(-ea1 / R_GAS * (1 / t_sim - 1 / t_ref))
    k2 = k2_ref * math.exp(-ea2 / R_GAS * (1 / t_sim - 1 / t_ref))

    t_end = t_end_hours or max(2.5 * report_hours, 0.5)
    p0 = 2.0  # organic precursor is used in 2x excess of the clay's anion-exchange capacity

    def rhs(_t, y):
        p, s, i = y
        return [-k1 * p, k1 * p - k2 * s * (1 - i), k2 * s * (1 - i)]

    t_eval = np.linspace(0, t_end, 300)
    sol = solve_ivp(rhs, (0, t_end), [p0, 0.0, 0.0], t_eval=t_eval, method="LSODA", rtol=1e-7, atol=1e-9)
    p, s, i = sol.y
    p, s = p / p0, s / p0          # show precursor / free product as fractions of what we started with
    conversion = 1 - p
    d001 = 0.88 + (1.42 - 0.88) * i  # nm, basal spacing grows as galleries fill

    def first_time(arr, level):
        hit = np.where(arr >= level)[0]
        return float(sol.t[hit[0]]) if len(hit) else None

    df = pd.DataFrame({"time_h": sol.t, "Precursor": p, "Product (free)": s,
                       "Intercalated": i, "Conversion": conversion, "d001_nm": d001})
    return {
        "df": df, "k1": k1, "k2": k2, "Ea_kJ": ea1 / 1000, "rate_factor": k1 / k1_ref,
        "t95_conversion": first_time(conversion, 0.95),
        "t90_intercalated": first_time(i, 0.90),
        "final_d001": float(d001[-1]),
    }
