"""
molecule_builder.py
===================
The "MolView 2D/3D Lab" logic (port of MolViewCanvas.tsx) - WITHOUT any drawing code.

A molecule is stored as two plain Python lists:
    atoms = [{"id": "c1", "element": "C", "x": -55, "y": 15, "z": -10}, ...]
    bonds = [{"id": "b1", "sourceId": "c1", "targetId": "c2", "order": 1, "type": "single"}, ...]

Every function below takes (atoms, bonds), returns NEW lists plus a status message.
Returning new lists (instead of changing the old ones) makes the functions easy to test.
"""

from __future__ import annotations

import math
import random
import uuid

from .chemistry import count_carbons_in_chain

# CPK colours, drawing radius, full name and normal valence of each element
ELEMENT_STYLES: dict[str, dict] = {
    "C": {"hex": "#334155", "radius": 17, "name": "Carbon", "valence": 4, "text": "#ffffff"},
    "H": {"hex": "#f1f5f9", "radius": 11, "name": "Hydrogen", "valence": 1, "text": "#1e293b"},
    "O": {"hex": "#f43f5e", "radius": 16, "name": "Oxygen", "valence": 2, "text": "#ffffff"},
    "N": {"hex": "#2563eb", "radius": 16, "name": "Nitrogen", "valence": 3, "text": "#ffffff"},
    "Na": {"hex": "#f59e0b", "radius": 19, "name": "Sodium", "valence": 1, "text": "#ffffff"},
    "Cl": {"hex": "#059669", "radius": 18, "name": "Chlorine", "valence": 1, "text": "#ffffff"},
    "Br": {"hex": "#9a3412", "radius": 20, "name": "Bromine", "valence": 1, "text": "#ffffff"},
    "S": {"hex": "#eab308", "radius": 18, "name": "Sulfur", "valence": 2, "text": "#0f172a"},
    "P": {"hex": "#9333ea", "radius": 18, "name": "Phosphorus", "valence": 3, "text": "#ffffff"},
}
PALETTE_ELEMENTS = ["C", "N", "O", "H", "Na", "Cl", "Br", "S", "P"]
BOND_TYPES = {
    "single": ("Single (—)", "C-C, C-H, C-OH"),
    "double": ("Double (=)", "C=O, C=C"),
    "triple": ("Triple (≡)", "C≡N, C≡C"),
    "ionic": ("Ionic (•••)", "COO⁻Na⁺"),
}

ADD_GROUPS = [
    ("coo_na", "Organic Salt (-COO⁻Na⁺)", "Carboxylate Salt for LDH bio-clay intercalators"),
    ("cooh", "Carboxylic Acid (-COOH)", "Class 12 Carboxylic Acids"),
    ("nh2", "Primary Amine (-NH₂)", "Class 12 Amines & Bio-Intercalation"),
    ("cl", "Chloride (-Cl)", "Class 12 Haloalkanes Chapter"),
    ("br", "Bromide (-Br)", "Class 12 Haloalkanes Chapter"),
    ("cho", "Aldehyde (-CHO)", "Class 12 Aldehydes Chapter"),
    ("carbonyl", "Ketone (=O)", "Class 12 Carbonyl Group"),
    ("methyl", "Methyl (-CH₃)", "Class 11 Hydrocarbon chain extension"),
]

QUICK_GENERATE = [
    ("Propane (3C)", "CH3-CH2-CH3"),
    ("Butane (4C)", "CH3-CH2-CH2-CH3"),
    ("Pentane (5C)", "CH3-CH2-CH2-CH2-CH3"),
    ("Hexane (6C)", "CH3-CH2-CH2-CH2-CH2-CH3"),
    ("Sodium Butanoate (-COO⁻Na⁺)", "CH3-CH2-CH2-COO-Na+"),
    ("Ethylamine (-NH₂)", "CH3-CH2-NH2"),
    ("1-Chloropropane (-Cl)", "CH3-CH2-CH2-Cl"),
    ("Glycine Amino Acid", "H2N-CH2-COOH"),
]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def bond_order(bond_type: str) -> int:
    return {"triple": 3, "double": 2}.get(bond_type, 1)


def _a(id, el, x, y, z=0):
    return {"id": id, "element": el, "x": round(x), "y": round(y), "z": round(z)}


def _b(id, s, t, order=1, type_="single"):
    return {"id": id, "sourceId": s, "targetId": t, "order": order, "type": type_}


# ======================================================================================
# 1. Build a molecule from a typed name / chain
# ======================================================================================
def build_molecule_from_input(input_str: str) -> dict:
    clean = (input_str or "").strip()
    lower = clean.lower()

    if "glycine" in lower or lower == "h2n-ch2-cooh":
        return dict(
            displayName="Glycine Amino Acid (H₂N-CH₂-COOH)", formula="C₂H₅NO₂",
            description="Zwitterionic amino acid with dual amine and carboxylate affinity for bio-clay nanosheets.",
            atoms=[_a("n1", "N", -90, 15, 0), _a("c1", "C", -30, -20, 10), _a("c2", "C", 45, 15, -5),
                   _a("o1", "O", 60, 75, 10), _a("o2", "O", 105, -25, -10), _a("h1", "H", -125, -15, 15),
                   _a("h2", "H", -115, 55, -15), _a("h3", "H", -30, -65, 25), _a("h4", "H", -30, -65, -25),
                   _a("h5", "H", 135, 5, -5)],
            bonds=[_b("b1", "n1", "c1"), _b("b2", "c1", "c2"), _b("b3", "c2", "o1", 2, "double"),
                   _b("b4", "c2", "o2"), _b("b5", "n1", "h1"), _b("b6", "n1", "h2"), _b("b7", "c1", "h3"),
                   _b("b8", "c1", "h4"), _b("b9", "o2", "h5")],
        )

    if "urea" in lower or lower == "h2n-co-nh2":
        return dict(
            displayName="Urea Exfoliation Scaffold (H₂N-CO-NH₂)", formula="CH₄N₂O",
            description="Carbonyl diamide swelling agent that exfoliates bio-clay gallery galleries.",
            atoms=[_a("c1", "C", 0, 0, 0), _a("o1", "O", 0, -60, 0), _a("n1", "N", -65, 35, 10),
                   _a("n2", "N", 65, 35, -10), _a("h1", "H", -105, 20, 25), _a("h2", "H", -80, 80, -10),
                   _a("h3", "H", 105, 20, -25), _a("h4", "H", 80, 80, 10)],
            bonds=[_b("b1", "c1", "o1", 2, "double"), _b("b2", "c1", "n1"), _b("b3", "c1", "n2"),
                   _b("b4", "n1", "h1"), _b("b5", "n1", "h2"), _b("b6", "n2", "h3"), _b("b7", "n2", "h4")],
        )

    if "acetone" in lower or lower == "ch3-co-ch3":
        return dict(
            displayName="Acetone (CH₃-CO-CH₃)", formula="C₃H₆O",
            description="Ketone dipolar solvent with carbonyl oxygen for clay dispersion.",
            atoms=[_a("c1", "C", -65, 20, 0), _a("c2", "C", 0, -20, 0), _a("c3", "C", 65, 20, 0),
                   _a("o1", "O", 0, -80, 10), _a("h1", "H", -105, 0, 25), _a("h2", "H", -85, 65, -20),
                   _a("h3", "H", -50, 65, 20), _a("h4", "H", 105, 0, -25), _a("h5", "H", 85, 65, 20),
                   _a("h6", "H", 50, 65, -20)],
            bonds=[_b("b1", "c1", "c2"), _b("b2", "c2", "c3"), _b("b3", "c2", "o1", 2, "double"),
                   _b("b4", "c1", "h1"), _b("b5", "c1", "h2"), _b("b6", "c1", "h3"), _b("b7", "c3", "h4"),
                   _b("b8", "c3", "h5"), _b("b9", "c3", "h6")],
        )

    # ---- Generic carbon chain + one terminal functional group --------------------------
    n = max(1, min(10, count_carbons_in_chain(clean)))
    is_salt = any(k in lower for k in ("salt", "coo-na", "coona", "butanoate", "propanoate", "acetate", "pentanoate"))
    is_amine = any(k in lower for k in ("amine", "nh2", "amino"))
    is_chloride = any(k in lower for k in ("cl", "chloro", "halide"))
    if is_salt and "coo" in lower:  # the carboxylate carbon in "-COO-Na+" is part of the chain too
        n = min(10, n + 1)

    atoms: list[dict] = []
    bonds: list[dict] = []
    dx = 55
    start_x = -((n - 1) * dx) / 2
    c_ids = []
    for i in range(n):
        cid = f"c{i + 1}"
        c_ids.append(cid)
        atoms.append(_a(cid, "C", start_x + i * dx, 15 if i % 2 == 0 else -20, -10 if i % 2 == 0 else 15))
        if i > 0:
            bonds.append(_b(f"b_c{i}_c{i + 1}", c_ids[i - 1], cid))

    h_counter = [1]

    def add_h(cid, x, y, z):
        hid = f"h{h_counter[0]}"
        h_counter[0] += 1
        atoms.append(_a(hid, "H", x, y, z))
        bonds.append(_b(f"b_{cid}_{hid}", cid, hid))

    if n == 1:
        c = atoms[0]
        add_h("c1", c["x"], c["y"] - 42, c["z"])
        add_h("c1", c["x"] - 40, c["y"] + 20, c["z"] + 20)
        add_h("c1", c["x"] + 40, c["y"] + 20, c["z"] + 20)
        add_h("c1", c["x"], c["y"] + 20, c["z"] - 40)
    else:
        c0 = atoms[0]
        s = 1 if c0["y"] > 0 else -1
        add_h("c1", c0["x"] - 38, c0["y"] + 30 * s, c0["z"] + 22)
        add_h("c1", c0["x"] - 38, c0["y"] - 25 * s, c0["z"] - 25)
        add_h("c1", c0["x"] - 48, c0["y"], c0["z"])
        for i in range(1, n - 1):
            ci = atoms[i]
            s = 1 if ci["y"] > 0 else -1
            add_h(c_ids[i], ci["x"], ci["y"] + 40 * s, ci["z"] + 28)
            add_h(c_ids[i], ci["x"], ci["y"] + 40 * s, ci["z"] - 28)

        last, last_id = atoms[n - 1], c_ids[n - 1]
        lx, ly, lz = last["x"], last["y"], last["z"]
        s = 1 if ly > 0 else -1
        if is_salt:
            atoms += [_a("o1", "O", lx + 35, ly - 38, lz + 15), _a("o2", "O", lx + 45, ly + 28, lz - 10),
                      _a("na1", "Na", lx + 95, ly + 42, lz + 10)]
            bonds += [_b(f"b_{last_id}_o1", last_id, "o1", 2, "double"), _b(f"b_{last_id}_o2", last_id, "o2"),
                      _b("b_o2_na", "o2", "na1", 1, "ionic")]
        elif is_amine:
            atoms.append(_a("n1", "N", lx + 48, ly + 10, lz + 8))
            bonds.append(_b(f"b_{last_id}_n1", last_id, "n1"))
            add_h(last_id, lx, ly + 38 * s, lz + 25)
            add_h(last_id, lx, ly + 38 * s, lz - 25)
            atoms += [_a("h_n1", "H", lx + 80, ly - 15, lz + 25), _a("h_n2", "H", lx + 80, ly + 35, lz - 15)]
            bonds += [_b("b_n1_h_n1", "n1", "h_n1"), _b("b_n1_h_n2", "n1", "h_n2")]
        elif is_chloride:
            atoms.append(_a("cl1", "Cl", lx + 50, ly + 10, lz + 10))
            bonds.append(_b(f"b_{last_id}_cl1", last_id, "cl1"))
            add_h(last_id, lx, ly + 38 * s, lz + 25)
            add_h(last_id, lx, ly + 38 * s, lz - 25)
        else:
            add_h(last_id, lx + 38, ly + 30 * s, lz + 22)
            add_h(last_id, lx + 38, ly - 25 * s, lz - 25)
            add_h(last_id, lx + 48, ly, lz)

    names = ["Methane", "Ethane", "Propane", "Butane", "Pentane", "Hexane", "Heptane", "Octane", "Nonane", "Decane"]
    base_name = names[n - 1] if n <= len(names) else f"{n}-Carbon Chain"
    display, formula = base_name, f"C{n}H{2 * n + 2}"
    if is_salt:
        salt = {4: "Butanoate", 3: "Propanoate", 2: "Acetate"}.get(n, base_name + " Salt")
        display, formula = f"Sodium {salt} (-COO⁻Na⁺)", f"C{n}H{2 * n - 1}O₂Na"
    elif is_amine:
        am = {2: "Ethylamine", 3: "1-Propylamine"}.get(n, base_name + " Amine")
        display, formula = f"{am} (-NH₂)", f"C{n}H{2 * n + 3}N"
    elif is_chloride:
        cl = {3: "1-Chloropropane", 2: "Chloroethane"}.get(n, "Alkyl Chloride")
        display, formula = f"{cl} (-Cl)", f"C{n}H{2 * n + 1}Cl"

    return dict(displayName=display, formula=formula, atoms=atoms, bonds=bonds,
                description=f"Constructed {n}-carbon chain with 3D tetrahedral coordinates and 2D skeletal projection.")


# ======================================================================================
# 2. Small graph helpers
# ======================================================================================
def neighbours(atom_id: str, bonds: list[dict]) -> list[str]:
    return [b["targetId"] if b["sourceId"] == atom_id else b["sourceId"]
            for b in bonds if atom_id in (b["sourceId"], b["targetId"])]


def find_atom(atoms: list[dict], atom_id: str | None) -> dict | None:
    return next((a for a in atoms if a["id"] == atom_id), None)


def carbons_sorted(atoms: list[dict]) -> list[dict]:
    return sorted((a for a in atoms if a["element"] == "C"), key=lambda a: a["x"])


def target_carbon(atoms: list[dict], selected_id: str | None) -> dict | None:
    """Selected atom if it is a carbon, otherwise the right-most carbon (the chain end)."""
    sel = find_atom(atoms, selected_id)
    if sel and sel["element"] == "C":
        return sel
    cs = [a for a in atoms if a["element"] == "C"]
    return max(cs, key=lambda a: a["x"]) if cs else None


def _remove_ids(atoms, bonds, ids: set):
    return ([a for a in atoms if a["id"] not in ids],
            [b for b in bonds if b["sourceId"] not in ids and b["targetId"] not in ids])


# ======================================================================================
# 3. Editing actions
# ======================================================================================
def attach_atom(atoms, bonds, selected_id, element, bond_type):
    parent = find_atom(atoms, selected_id)
    if parent:
        k = len(neighbours(parent["id"], bonds))
        ang = (k * math.pi * 2) / 3 - math.pi / 4
        x, y = parent["x"] + math.cos(ang) * 55, parent["y"] + math.sin(ang) * 55
        z = parent["z"] + (random.random() - 0.5) * 20
    else:
        x, y, z = (len(atoms) % 5) * 35 - 70, (len(atoms) % 3) * 30 - 30, 0
    new = _a(new_id("a"), element, x, y, z)
    atoms = atoms + [new]
    if parent:
        bonds = bonds + [_b(new_id("b"), parent["id"], new["id"], bond_order(bond_type), bond_type)]
        msg = f"Formed {bond_type.upper()} bond between {parent['element']} and new {element}!"
    else:
        msg = f"Placed new {element} atom on canvas. Select it to attach bonds!"
    return atoms, bonds, new["id"], msg


def place_atom_at(atoms, bonds, selected_id, element, bond_type, x, y, z=0):
    new = _a(new_id("a"), element, x, y, z)
    atoms = atoms + [new]
    msg = f"Placed {element} atom at ({round(x)}, {round(y)}, {round(z)})."
    if find_atom(atoms, selected_id):
        bonds = bonds + [_b(new_id("b"), selected_id, new["id"], bond_order(bond_type), bond_type)]
        msg = f"Placed {element} atom and formed {bond_type.upper()} bond from selected atom!"
    return atoms, bonds, new["id"], msg


def connect_atoms(bonds, id1, id2, bond_type):
    if not id1 or not id2 or id1 == id2:
        return bonds, "Pick two different atoms to connect."
    order = bond_order(bond_type)
    for i, b in enumerate(bonds):
        if {b["sourceId"], b["targetId"]} == {id1, id2}:
            bonds = bonds.copy()
            bonds[i] = {**b, "order": order, "type": bond_type}
            return bonds, f"Updated bond between atoms to {bond_type.upper()} bond."
    return bonds + [_b(new_id("b"), id1, id2, order, bond_type)], f"Created {bond_type.upper()} bond between selected atoms."


def delete_atom(atoms, bonds, atom_id):
    if not atom_id:
        return atoms, bonds, "Select an atom first."
    atoms, bonds = _remove_ids(atoms, bonds, {atom_id})
    return atoms, bonds, "Deleted selected atom and its attached bonds."


def add_functional_group(atoms, bonds, selected_id, group):
    target = target_carbon(atoms, selected_id)
    if not target:
        return atoms, bonds, "No carbon atom found in molecule to attach functional group. Place a Carbon (C) first!"

    nb = set(neighbours(target["id"], bonds))
    hs = [a for a in atoms if a["element"] == "H" and a["id"] in nb]
    n_remove = 2 if group in ("coo_na", "cooh", "cho", "carbonyl") else 1
    atoms, bonds = _remove_ids(atoms, bonds, {h["id"] for h in hs[:n_remove]})

    tx, ty, tz, tid = target["x"], target["y"], target["z"], target["id"]
    ts = uuid.uuid4().hex[:5]
    A, B = [], []
    label = tid.upper()
    if group == "coo_na":
        A += [_a(f"o1_{ts}", "O", tx + 36, ty - 38, tz + 15), _a(f"o2_{ts}", "O", tx + 46, ty + 28, tz - 10),
              _a(f"na_{ts}", "Na", tx + 96, ty + 42, tz + 10)]
        B += [_b(new_id("b"), tid, f"o1_{ts}", 2, "double"), _b(new_id("b"), tid, f"o2_{ts}"),
              _b(new_id("b"), f"o2_{ts}", f"na_{ts}", 1, "ionic")]
        msg = f"Attached Organic Salt (-COO⁻Na⁺) to Carbon {label}."
    elif group == "cooh":
        A += [_a(f"o1_{ts}", "O", tx + 36, ty - 38, tz + 15), _a(f"o2_{ts}", "O", tx + 46, ty + 28, tz - 10),
              _a(f"ha_{ts}", "H", tx + 86, ty + 36, tz - 10)]
        B += [_b(new_id("b"), tid, f"o1_{ts}", 2, "double"), _b(new_id("b"), tid, f"o2_{ts}"),
              _b(new_id("b"), f"o2_{ts}", f"ha_{ts}")]
        msg = f"Attached Carboxylic Acid (-COOH) to Carbon {label}."
    elif group == "nh2":
        A += [_a(f"n_{ts}", "N", tx + 48, ty + 12, tz + 8), _a(f"hn1_{ts}", "H", tx + 80, ty - 15, tz + 25),
              _a(f"hn2_{ts}", "H", tx + 80, ty + 35, tz - 15)]
        B += [_b(new_id("b"), tid, f"n_{ts}"), _b(new_id("b"), f"n_{ts}", f"hn1_{ts}"),
              _b(new_id("b"), f"n_{ts}", f"hn2_{ts}")]
        msg = f"Attached Primary Amine (-NH₂) to Carbon {label}."
    elif group == "cl":
        A.append(_a(f"cl_{ts}", "Cl", tx + 50, ty + 12, tz + 10))
        B.append(_b(new_id("b"), tid, f"cl_{ts}"))
        msg = f"Attached Chloro Halide (-Cl) to Carbon {label}."
    elif group == "br":
        A.append(_a(f"br_{ts}", "Br", tx + 54, ty + 12, tz + 12))
        B.append(_b(new_id("b"), tid, f"br_{ts}"))
        msg = f"Attached Bromo Halide (-Br) to Carbon {label}."
    elif group == "cho":
        A += [_a(f"o_{ts}", "O", tx + 36, ty - 38, tz + 15), _a(f"h_{ts}", "H", tx + 46, ty + 25, tz - 10)]
        B += [_b(new_id("b"), tid, f"o_{ts}", 2, "double"), _b(new_id("b"), tid, f"h_{ts}")]
        msg = f"Attached Aldehyde (-CHO) to Carbon {label}."
    elif group == "carbonyl":
        A.append(_a(f"o_{ts}", "O", tx, ty - 45, tz + 15))
        B.append(_b(new_id("b"), tid, f"o_{ts}", 2, "double"))
        msg = f"Attached Carbonyl Oxygen (=O) to Carbon {label}."
    elif group == "methyl":
        ny = ty + (-35 if ty > 0 else 35)
        cid = f"c_{ts}"
        A += [_a(cid, "C", tx + 55, ny, tz + 10), _a(f"hm1_{ts}", "H", tx + 90, ny + 20, tz + 25),
              _a(f"hm2_{ts}", "H", tx + 90, ny - 20, tz - 20), _a(f"hm3_{ts}", "H", tx + 75, ny + 35, tz)]
        B += [_b(new_id("b"), tid, cid)] + [_b(new_id("b"), cid, f"hm{k}_{ts}") for k in (1, 2, 3)]
        msg = f"Extended chain with Methyl (-CH₃) on Carbon {label}."
    else:
        return atoms, bonds, "Unknown group."
    return atoms + A, bonds + B, msg


def remove_group(atoms, bonds, selected_id, kind):
    """kind: h | terminal_c | salt | amine | chloride | bromide | functional_group"""
    if kind == "terminal_c":
        cs = [a for a in atoms if a["element"] == "C"]
        if len(cs) <= 1:
            return atoms, bonds, "Molecule must retain at least 1 carbon atom in the chain."
        term = max(cs, key=lambda a: a["x"])
        nb = set(neighbours(term["id"], bonds))
        ids = {term["id"]} | {a["id"] for a in atoms if a["element"] == "H" and a["id"] in nb}
        atoms, bonds = _remove_ids(atoms, bonds, ids)
        return atoms, bonds, f"Removed terminal Carbon {term['id'].upper()} (-CH₃) from chain."

    if kind == "salt":
        nas = [a for a in atoms if a["element"] == "Na"]
        if not nas:
            return atoms, bonds, "No Organic Salt (-COO⁻Na⁺) found on current chain to remove."
        ids = set()
        for na in nas:
            ids.add(na["id"])
            ids.update(neighbours(na["id"], bonds))
        for a in atoms:  # oxygens attached to the carboxyl carbon of the salt
            if a["element"] == "O" and any(x in ids for x in neighbours(a["id"], bonds)):
                ids.add(a["id"])
        atoms, bonds = _remove_ids(atoms, bonds, ids)
        return atoms, bonds, "Removed Organic Salt (-COO⁻Na⁺) group from chain."

    if kind == "amine":
        ns = [a for a in atoms if a["element"] == "N"]
        if not ns:
            return atoms, bonds, "No Amine (-NH₂) group found on current chain to remove."
        ids = set()
        for nat in ns:
            ids.add(nat["id"])
            ids.update(x for x in neighbours(nat["id"], bonds) if (find_atom(atoms, x) or {}).get("element") == "H")
        atoms, bonds = _remove_ids(atoms, bonds, ids)
        return atoms, bonds, "Removed Primary Amine (-NH₂) group from chain."

    if kind in ("chloride", "bromide"):
        el, nm = ("Cl", "Chloride (-Cl)") if kind == "chloride" else ("Br", "Bromide (-Br)")
        hal = [a for a in atoms if a["element"] == el]
        if not hal:
            return atoms, bonds, f"No {nm} found on molecule to remove."
        atoms, bonds = _remove_ids(atoms, bonds, {hal[-1]["id"]})
        return atoms, bonds, f"Removed {nm} from chain."

    target = target_carbon(atoms, selected_id)
    if not target:
        return atoms, bonds, "No carbon found in molecule to remove groups from."
    nb = set(neighbours(target["id"], bonds))
    label = target["id"].upper()

    if kind == "h":
        h = next((a for a in atoms if a["element"] == "H" and a["id"] in nb), None)
        if not h:
            return atoms, bonds, f"No Hydrogen (-H) found on Carbon {label} to remove."
        atoms, bonds = _remove_ids(atoms, bonds, {h["id"]})
        return atoms, bonds, f"Removed Hydrogen (-H) from Carbon {label}. Created unsaturated radical site."

    if kind == "functional_group":
        subs = [a for a in atoms if a["element"] not in ("C", "H") and a["id"] in nb]
        if not subs:
            return atoms, bonds, f"No non-hydrocarbon functional group found on Carbon {label} to remove."
        ids = set()
        for s in subs:
            ids.add(s["id"])
            ids.update(x for x in neighbours(s["id"], bonds) if x != target["id"])
        atoms, bonds = _remove_ids(atoms, bonds, ids)
        return atoms, bonds, f"Removed functional group from Carbon {label}."

    return atoms, bonds, "Nothing removed."


def chain_analysis(atoms: list[dict]) -> dict:
    els = {a["element"] for a in atoms}
    return dict(hasSalt="Na" in els, hasAmine="N" in els, hasChloride="Cl" in els,
                hasBromide="Br" in els, hasOxygen="O" in els, hasHydrogen="H" in els)
