from src.model.grammar import Grammar


def variable_order(grammar):
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
    iteration_column, rule_column, new_column, set_column = columns
    known = {}
    rows = []
    iteration = 0
    while True:
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
    return tuple(production for production in grammar.productions if symbol in production.rhs)


def rebuild(grammar, productions, variables=None, start_symbol=None):
    return Grammar(
        start_symbol=grammar.start_symbol if start_symbol is None else start_symbol,
        variables=grammar.variables if variables is None else variables,
        terminals=grammar.terminals,
        productions=productions,
    )


def run_phases(grammar, phases):
    traces = []
    for phase in phases:
        grammar, trace = phase(grammar)
        traces.append(trace)
    return grammar, traces
