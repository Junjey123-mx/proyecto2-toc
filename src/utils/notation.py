"""Utilidades de texto para símbolos, producciones y conjuntos."""

EPSILON = "ε"
EMPTY_SET = "∅"


def rhs_text(rhs):
    return " ".join(rhs) if rhs else EPSILON


def production_text(production):
    return f"{production.lhs} -> {rhs_text(production.rhs)}"


def set_text(symbols):
    """Formatea un conjunto ordenado, o ∅ si está vacío."""
    if not symbols:
        return EMPTY_SET
    return "{" + ", ".join(sorted(symbols)) + "}"
