"""Fase 1: calcula las variables anulables y elimina las producciones-ε."""

from itertools import combinations

from src.algorithms.grammar_tools import lhs_closure, rebuild
from src.model.production import Production
from src.model.trace import Trace
from src.utils.notation import production_text, set_text

PHASE = "Fase 1: eliminación de producciones-ε"
NULLABLE_COLUMNS = ("Iteración", "Regla aplicada", "Nuevo", "Conjunto N")


def find_nullable(grammar):
    """Encuentra todas las variables que derivan ε mediante una búsqueda de punto fijo."""
    # Una variable es anulable si algún RHS suyo es totalmente anulable; un terminal nunca lo es.
    return lhs_closure(
        grammar.productions,
        lambda symbol, known: symbol in known,
        NULLABLE_COLUMNS,
        "ninguna X -> ε",
    )


def nullable_positions(rhs, nullable):
    """Devuelve las posiciones de las ocurrencias anulables; las repeticiones cuentan por separado."""
    return [index for index, symbol in enumerate(rhs) if symbol in nullable]


def expand_variants(rhs, nullable):
    """Devuelve cada RHS obtenido al conservar o quitar cada ocurrencia anulable."""
    positions = nullable_positions(rhs, nullable)
    variants = []
    # m ocurrencias anulables generan 2^m variantes; los duplicados se eliminan después.
    for removed_count in range(len(positions) + 1):
        for removed in combinations(reversed(positions), removed_count):
            variants.append(tuple(symbol for index, symbol in enumerate(rhs) if index not in removed))
    return variants


def eliminate_epsilon(grammar):
    """Reemplaza cada producción por sus variantes y elimina las producciones-ε.

    Solo el inicial puede conservar ε, y únicamente si ε pertenece al lenguaje.
    """
    start = grammar.start_symbol
    nullable, nullable_rows = find_nullable(grammar)
    tables = {"Anulables": nullable_rows}
    notes = [f"N = {set_text(nullable)}"]
    if not nullable:
        notes = ["N = ∅ ⇒ G1 = G0"]
        return grammar, Trace(PHASE, grammar, tables, notes)

    variant_rows = []
    productions = []
    for production in grammar.productions:
        positions = nullable_positions(production.rhs, nullable)
        if not positions and not production.is_epsilon:
            productions.append(production)
            continue
        generated = [Production(production.lhs, rhs) for rhs in expand_variants(production.rhs, nullable)]
        # Solo el inicial conserva ε; la Fase 0 garantiza que no aparece en ningún RHS.
        kept = tuple(
            dict.fromkeys(
                variant for variant in generated if not variant.is_epsilon or variant.lhs == start
            )
        )
        productions.extend(kept)
        variant_rows.append(
            {
                "Producción": production,
                "Ocurrencias anulables": tuple(f"{production.rhs[index]} (pos. {index + 1})" for index in positions),
                "m": len(positions),
                "2^m": 2 ** len(positions),
                "Casos generados": tuple(generated),
                "Casos conservados": kept,
            }
        )
    tables["Variantes"] = variant_rows

    if start in nullable:
        notes.append(f"{start} ∈ N ⇒ ε ∈ L(G); se conserva {production_text(Production(start))}")
    else:
        notes.append(f"{start} ∉ N ⇒ ε ∉ L(G); no se conserva ninguna producción-ε")
    notes.append("Las producciones sin ocurrencias anulables se conservan sin cambios.")
    notes.append("Se eliminan las producciones-ε restantes y las variantes duplicadas.")
    exception = f", salvo {production_text(Production(start))}" if start in nullable else ""
    notes.append(f"N = {set_text(nullable)} ⇒ G1 sin producciones-ε{exception}")

    result = rebuild(grammar, productions)
    return result, Trace(PHASE, result, tables, notes)
