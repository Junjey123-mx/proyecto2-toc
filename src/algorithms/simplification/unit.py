from collections import deque

from src.algorithms.grammar_tools import NO_VALUE, rebuild, variable_order
from src.model.production import Production
from src.model.trace import Trace

PHASE = "Fase 2: eliminación de producciones unitarias"


def is_unit(production, variables):
    return len(production.rhs) == 1 and production.rhs[0] in variables


def unit_successors(grammar):
    successors = {}
    for production in grammar.productions:
        if is_unit(production, grammar.variables):
            successors.setdefault(production.lhs, []).append(production.rhs[0])
    return successors


def unit_reach(successors, variable):
    reached = dict.fromkeys([variable])
    pending = deque([variable])
    while pending:
        current = pending.popleft()
        for target in successors.get(current, ()):
            if target not in reached:
                reached[target] = None
                pending.append(target)
    return tuple(reached)


def eliminate_unit(grammar):
    units = [production for production in grammar.productions if is_unit(production, grammar.variables)]
    tables = {"Unitarias": [{"Producción": production, "¿Unitaria?": "sí"} for production in units]}
    if not units:
        notes = ["No hay producciones unitarias X -> Y ⇒ G2 = G1"]
        return grammar, Trace(PHASE, grammar, tables, notes)

    order = variable_order(grammar)
    lhs_order = list(dict.fromkeys([production.lhs for production in grammar.productions] + order))
    successors = unit_successors(grammar)
    reach = {variable: unit_reach(successors, variable) for variable in lhs_order}
    non_unit = {
        variable: tuple(
            production
            for production in grammar.productions_for(variable)
            if not is_unit(production, grammar.variables)
        )
        for variable in lhs_order
    }

    tables["Pares unitarios"] = [
        {
            "Origen": variable,
            "Alcanza (solo unitarias)": frozenset(reach[variable]),
            "Pares": tuple((variable, target) for target in reach[variable]),
        }
        for variable in lhs_order
    ]
    tables["No unitarias"] = [
        {"Variable": variable, "Producciones no unitarias": non_unit[variable] or NO_VALUE}
        for variable in lhs_order
    ]

    transfer_rows = []
    productions = []
    for variable in lhs_order:
        for target in reach[variable]:
            received = tuple(Production(variable, production.rhs) for production in non_unit[target])
            productions.extend(received)
            if target != variable:
                transfer_rows.append(
                    {"Variable": variable, "Par": f"({variable}, {target})", "Recibe": received or NO_VALUE}
                )
    tables["Transferencias"] = transfer_rows

    notes = [
        f"Se encontraron {len(units)} producciones unitarias.",
        "Cada variable X recibe las producciones no unitarias de toda Y con (X, Y) par unitario.",
        "Se eliminan todas las producciones unitarias y los duplicados.",
        f"{len(units)} producciones unitarias eliminadas ⇒ G2 sin producciones unitarias",
    ]
    result = rebuild(grammar, productions)
    return result, Trace(PHASE, result, tables, notes)
