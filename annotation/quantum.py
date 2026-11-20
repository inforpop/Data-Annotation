"""Computação Quântica — anotação de estados de circuitos de 2 qubits.

Cada item é um circuito quântico simulado aqui mesmo com NumPy (vetor de
estado, sem dependências externas). A pessoa anotadora classifica o estado final:

* "base"          — separável e determinístico (um único resultado de medição)
* "superposição"  — separável, mas com mais de um resultado possível
* "emaranhado"    — não separável (concorrência > 0)

O gabarito vem da física (concorrência C = 2|ad - bc|) e a pré-anotação vem de
uma heurística ingênua ("tem H antes de CNOT? então é emaranhado"), que erra
de propósito em alguns casos — ótimo para discutir qualidade de rótulos.
"""
import math

import numpy as np

LABELS = ["base", "superposição", "emaranhado"]

# ---------------------------------------------------------------- portas
_I = np.eye(2, dtype=complex)
_H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Z = np.array([[1, 0], [0, -1]], dtype=complex)
_S = np.array([[1, 0], [0, 1j]], dtype=complex)
_T = np.array([[1, 0], [0, np.exp(1j * math.pi / 4)]], dtype=complex)


def _ry(theta):
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


SINGLE = {"H": _H, "X": _X, "Z": _Z, "S": _S, "T": _T}


def _single(gate, target, theta=None):
    u = _ry(theta) if gate == "RY" else SINGLE[gate]
    # ordem dos qubits: |q0 q1>, q0 é o mais significativo
    return np.kron(u, _I) if target == 0 else np.kron(_I, u)


def _cnot(control, target):
    m = np.zeros((4, 4), dtype=complex)
    for basis in range(4):
        bits = [(basis >> 1) & 1, basis & 1]
        if bits[control]:
            bits[target] ^= 1
        m[bits[0] * 2 + bits[1], basis] = 1
    return m


def simulate(circuit):
    state = np.zeros(4, dtype=complex)
    state[0] = 1.0  # |00>
    for op in circuit:
        name = op[0]
        if name == "CNOT":
            state = _cnot(op[1], op[2]) @ state
        elif name == "RY":
            state = _single("RY", op[1], op[2]) @ state
        else:
            state = _single(name, op[1]) @ state
    return state


def concurrence(state):
    a, b, c, d = state
    return float(2 * abs(a * d - b * c))


def gold_label(state):
    if concurrence(state) > 1e-6:
        return "emaranhado"
    probs = np.abs(state) ** 2
    return "base" if probs.max() > 1 - 1e-9 else "superposição"


def model_predict(circuit):
    """Heurística ingênua: só olha a sintaxe do circuito, não o estado."""
    seen_h = False
    for op in circuit:
        if op[0] in ("H", "RY"):
            seen_h = True
        if op[0] == "CNOT" and seen_h:
            return "emaranhado"
    return "superposição" if seen_h else "base"


# ------------------------------------------------------------- desenho ASCII
def draw(circuit):
    rows = ["q0: ─", "q1: ─"]
    for op in circuit:
        if op[0] == "CNOT":
            c, t = op[1], op[2]
            rows[c] += "─●─"
            rows[t] += "─⊕─"
        else:
            label = f"RY({op[2] / math.pi:.2g}π)" if op[0] == "RY" else op[0]
            box = f"[{label}]"
            pad = "─" * len(box)
            rows[op[1]] += box
            rows[1 - op[1]] += pad
        rows = [r + "─" for r in rows]
    return "\n".join(rows)


def _fmt_amp(z):
    re_, im = round(z.real, 3), round(z.imag, 3)
    if abs(im) < 1e-9:
        return f"{re_:+.3f}"
    if abs(re_) < 1e-9:
        return f"{im:+.3f}i"
    return f"({re_:+.3f}{im:+.3f}i)"


def ket(state):
    terms = [f"{_fmt_amp(a)}|{b:02b}⟩" for b, a in enumerate(state) if abs(a) > 1e-9]
    return "  ".join(terms)


# ------------------------------------------------------------------ dataset
PI = math.pi
CIRCUITS = [
    ("q01", [("H", 0), ("CNOT", 0, 1)]),                         # Bell Φ+
    ("q02", [("X", 0)]),                                         # |10>
    ("q03", [("H", 0), ("H", 1)]),                               # |++>
    ("q04", [("H", 1), ("CNOT", 0, 1)]),                         # H no alvo: separável!
    ("q05", [("X", 0), ("H", 0), ("CNOT", 0, 1)]),               # Bell Φ-
    ("q06", [("H", 0), ("CNOT", 0, 1), ("CNOT", 0, 1)]),         # desfaz: |+0>
    ("q07", [("RY", 0, PI / 3), ("CNOT", 0, 1)]),                # emaranhado parcial
    ("q08", [("X", 0), ("CNOT", 0, 1)]),                         # |11>
    ("q09", [("H", 0), ("H", 0)]),                               # HH = I → |00>
    ("q10", [("H", 0), ("X", 1), ("CNOT", 0, 1)]),               # Bell Ψ+
    ("q11", [("H", 0), ("T", 0), ("S", 1)]),                     # |+>|0> com fase
    ("q12", [("H", 0), ("H", 1), ("CNOT", 0, 1)]),               # |++> invariante
    ("q13", [("RY", 1, PI / 2), ("Z", 1)]),                      # superposição em q1
    ("q14", [("H", 0), ("CNOT", 0, 1), ("H", 0), ("H", 1)]),     # continua emaranhado
    ("q15", [("Z", 0), ("X", 1)]),                               # |01>
    ("q16", [("H", 0), ("CNOT", 0, 1), ("Z", 0), ("X", 1)]),     # Bell Ψ-
]


def _build(item_id, circuit):
    state = simulate(circuit)
    probs = (np.abs(state) ** 2).round(4)
    return {
        "id": item_id,
        "circuit": circuit,
        "diagram": draw(circuit),
        "ket": ket(state),
        "probs": {f"{b:02b}": float(p) for b, p in enumerate(probs)},
        "concurrence": round(concurrence(state), 4),
        "gold": gold_label(state),
        "model": model_predict(circuit),
    }


ITEMS = {item_id: _build(item_id, c) for item_id, c in CIRCUITS}


def public_item(item, reveal_physics=True):
    """Item enviado ao navegador. O vetor de estado e as probabilidades são
    mostrados como evidência; a concorrência (que entrega a resposta) não."""
    data = {
        "id": item["id"],
        "diagram": item["diagram"],
        "suggestion": item["model"],
        "probs": item["probs"],
    }
    if reveal_physics:
        data["ket"] = item["ket"]
    return data
