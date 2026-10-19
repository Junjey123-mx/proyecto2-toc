"""Utilidades compartidas por todas las fases de simplificación y CNF."""

from src.model.grammar import Grammar


def variable_order(grammar):
    """Devuelve las variables en un orden estable de presentación, con el inicial primero."""
    order = dict.fromkeys([grammar.start_symbol])
    for production in grammar.productions:
        order.setdefault(production.lhs)
        for symbol in production.rhs:
            if symbol in grammar.variables:
                order.setdefault(symbol)
    for variable in sorted(grammar.variables):
        order.setdefault(variable)
    return list(order)


NO_VALUE = "—"
FIXED_POINT = "sin cambios ⇒ punto fijo"


def lhs_closure(productions, qualifies, columns, empty_base):
    """Amplía un conjunto de variables hasta un punto fijo y registra cada iteración.

    Una variable entra cuando alguna producción tiene todo su RHS aceptado por `qualifies`.
    """
    iteration_column, rule_column, new_column, set_column = columns
    known = {}
    rows = []
    iteration = 0
    while True:
        # Cada ronda se evalúa contra la anterior, así la tabla muestra capas reales.
        snapshot = frozenset(known)
        found = {}
        for production in productions:
            if production.lhs in snapshot or production.lhs in found:
                continue
            if all(qualifies(symbol, snapshot) for symbol in production.rhs):
                found[production.lhs] = production
        label = "Base" if iteration == 0 else iteration
        if not found:
            rule = empty_base if iteration == 0 else FIXED_POINT
            rows.append({iteration_column: label, rule_column: rule, new_column: NO_VALUE, set_column: snapshot})
            return snapshot, rows
        for variable, production in found.items():
            known[variable] = production
            rows.append(
                {
                    iteration_column: label,
                    rule_column: production,
                    new_column: variable,
                    set_column: frozenset(known),
                }
            )
        iteration += 1


def productions_using(grammar, symbol):
    """Devuelve las producciones cuyo RHS contiene `symbol`."""
    return tuple(production for production in grammar.productions if symbol in production.rhs)


def rebuild(grammar, productions, variables=None, start_symbol=None):
    """Construye una nueva Grammar validada y conserva los componentes no indicados."""
    return Grammar(
        start_symbol=grammar.start_symbol if start_symbol is None else start_symbol,
        variables=grammar.variables if variables is None else variables,
        terminals=grammar.terminals,
        productions=productions,
    )


def run_phases(grammar, phases):
    """Aplica las fases en orden y reúne una Trace por fase."""
    traces = []
    for phase in phases:
        grammar, trace = phase(grammar)
        traces.append(trace)
    return grammar, traces
