from src.algorithms.grammar_tools import FIXED_POINT, NO_VALUE, lhs_closure, rebuild, variable_order
from src.model.trace import Trace
from src.utils.notation import set_text

PHASE = "Fase 3: eliminación de símbolos inútiles"
CLOSURE_COLUMNS = ("Iteración", "Regla/origen", "Nuevos", "Conjunto acumulado")


def find_generating(grammar):
    return lhs_closure(
        grammar.productions,
        lambda symbol, known: symbol in grammar.terminals or symbol in known,
        CLOSURE_COLUMNS,
        "ninguna regla formada solo por terminales",
    )


def find_reachable(grammar):
    iteration_column, rule_column, new_column, set_column = CLOSURE_COLUMNS
    reached = dict.fromkeys([grammar.start_symbol])
    rows = [
        {
            iteration_column: "Base",
            rule_column: "símbolo inicial",
            new_column: grammar.start_symbol,
            set_column: frozenset(reached),
        }
    ]
    frontier = [grammar.start_symbol]
    iteration = 1
    while True:
        found = {}
        for variable in frontier:
            for production in grammar.productions_for(variable):
                for symbol in production.rhs:
                    if symbol in grammar.variables and symbol not in reached and symbol not in found:
                        found[symbol] = production
        if not found:
            rows.append(
                {iteration_column: iteration, rule_column: FIXED_POINT, new_column: NO_VALUE, set_column: frozenset(reached)}
            )
            return frozenset(reached), rows
        for symbol, production in found.items():
            reached[symbol] = None
            rows.append(
                {iteration_column: iteration, rule_column: production, new_column: symbol, set_column: frozenset(reached)}
            )
        frontier = list(found)
        iteration += 1


def removal_rows(grammar, kept_variables, reason):
    rows = []
    for production in grammar.productions:
        offending = [
            symbol
            for symbol in dict.fromkeys((production.lhs, *production.rhs))
            if symbol in grammar.variables and symbol not in kept_variables
        ]
        if offending:
            rows.append({"Producción": production, "Motivo": f"contiene {', '.join(offending)} ({reason})"})
    return rows


def keep_productions(grammar, kept_variables):
    return tuple(
        production
        for production in grammar.productions
        if production.lhs in kept_variables
        and all(symbol in kept_variables for symbol in production.rhs if symbol in grammar.variables)
    )


def remove_non_generating(grammar):
    start = grammar.start_symbol
    generating, rows = find_generating(grammar)
    order = variable_order(grammar)
    removed = [variable for variable in order if variable not in generating]
    kept = generating | {start}
    removed_productions = removal_rows(grammar, generating, "no generadora")
    result = rebuild(grammar, keep_productions(grammar, generating), variables=kept)
    return result, rows, removed, removed_productions, start not in generating


def remove_unreachable(grammar):
    reachable, rows = find_reachable(grammar)
    order = variable_order(grammar)
    removed = [variable for variable in order if variable not in reachable]
    removed_productions = removal_rows(grammar, reachable, "inalcanzable")
    result = rebuild(grammar, keep_productions(grammar, reachable), variables=reachable)
    return result, rows, removed, removed_productions


def eliminate_useless(grammar):
    start = grammar.start_symbol
    after_generating, generating_rows, non_generating, generating_removed, empty_language = remove_non_generating(
        grammar
    )
    result, reachable_rows, unreachable, reachable_removed = remove_unreachable(after_generating)

    tables = {
        "3a Generadores": generating_rows,
        "3a Símbolos eliminados": [
            {
                "Símbolo": symbol,
                "Motivo": "no generador (se conserva solo como inicial)" if symbol == start else "no generador",
            }
            for symbol in non_generating
        ],
        "3a Producciones eliminadas": generating_removed,
        "3b Alcanzables": reachable_rows,
        "3b Símbolos eliminados": [{"Símbolo": symbol, "Motivo": "inalcanzable"} for symbol in unreachable],
        "3b Producciones eliminadas": reachable_removed,
    }

    generating_set = generating_rows[-1]["Conjunto acumulado"]
    notes = [f"3a Generadores: {set_text(generating_set)}"]
    if empty_language:
        notes.append(f"{start} no es generador ⇒ L(G) = ∅")
        notes.append(f"Se conserva {start} sin producciones para mantener un símbolo inicial válido.")
    elif non_generating:
        notes.append(f"Variables no generadoras eliminadas: {set_text(non_generating)}")
    else:
        notes.append("Todas las variables son generadoras.")
    notes.append(f"3b Alcanzables: {set_text(reachable_rows[-1]['Conjunto acumulado'])}")
    if unreachable:
        notes.append(f"Variables inalcanzables eliminadas: {set_text(unreachable)}")
    else:
        notes.append("Todas las variables son alcanzables.")
    if not non_generating and not unreachable:
        notes.append("Sin símbolos inútiles ⇒ G3 = G2")
        return grammar, Trace(PHASE, grammar, tables, notes)
    removed = [*non_generating, *unreachable]
    if empty_language:
        notes.append(f"L(G) = ∅ ⇒ G3 conserva solo el inicial {start}")
    else:
        notes.append(f"Símbolos inútiles eliminados: {set_text(removed)} ⇒ G3")
    return result, Trace(PHASE, result, tables, notes)
