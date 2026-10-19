"""Coordina las fases de CNF 4–5."""

from src.algorithms.chomsky.binarize import binarize
from src.algorithms.chomsky.terminals import isolate_terminals
from src.algorithms.grammar_tools import run_phases

CNF_PHASES = (isolate_terminals, binarize)


def to_cnf(grammar):
    """Ejecuta las Fases 4–5 sobre una gramática simplificada y devuelve (gramática, trazas)."""
    return run_phases(grammar, CNF_PHASES)
