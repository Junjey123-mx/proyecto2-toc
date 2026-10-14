from src.algorithms.grammar_tools import NO_VALUE, rebuild
from src.model.production import Production
from src.model.trace import Trace
from src.utils.naming import candidate_names

PHASE = "Fase 4: aislar terminales"


def wrapper_base(terminal):
    return f"U_{terminal}"


def is_exact_wrapper(grammar, variable, terminal):
    return grammar.productions_for(variable) == (Production(variable, (terminal,)),)


def choose_wrapper(grammar, terminal, taken):
    for name in candidate_names(wrapper_base(terminal)):
        if name in grammar.variables and is_exact_wrapper(grammar, name, terminal):
            return name, "reutilizado"
        if name not in grammar.variables and name not in grammar.terminals and name not in taken:
            return name, "creado"


def isolate_terminals(grammar):
    wrappers = {}
    wrapper_rows = []
    production_rows = []
    productions = []
    created_productions = []

    def wrapper_for(terminal):
        if terminal not in wrappers:
            name, action = choose_wrapper(grammar, terminal, set(wrappers.values()))
            wrappers[terminal] = name
            wrapper_rows.append({"Terminal": terminal, "Envoltorio": name, "Acción": action})
            if action == "creado":
                created_productions.append(Production(name, (terminal,)))
        return wrappers[terminal]

    for production in grammar.productions:
        if len(production.rhs) < 2:
            productions.append(production)
            continue
        accompanied = tuple(dict.fromkeys(symbol for symbol in production.rhs if symbol in grammar.terminals))
        if not accompanied:
            productions.append(production)
            production_rows.append(
                {
                    "Producción original": production,
                    "Longitud": len(production.rhs),
                    "Terminales acompañados": NO_VALUE,
                    "Producción resultante": production,
                }
            )
            continue
        rhs = tuple(wrapper_for(symbol) if symbol in grammar.terminals else symbol for symbol in production.rhs)
        replaced = Production(production.lhs, rhs)
        productions.append(replaced)
        production_rows.append(
            {
                "Producción original": production,
                "Longitud": len(production.rhs),
                "Terminales acompañados": accompanied,
                "Producción resultante": replaced,
            }
        )

    tables = {"Lados derechos de longitud ≥ 2": production_rows, "Envoltorios": wrapper_rows}
    if not wrappers:
        notes = ["Ningún terminal acompañado ⇒ G4 = G3"]
        return grammar, Trace(PHASE, grammar, tables, notes)

    notes = [
        "Cada terminal acompañado se reemplaza por su envoltorio U_a -> a.",
        "Las producciones A -> a de longitud 1 se conservan sin cambios.",
    ]
    for row in wrapper_rows:
        if row["Acción"] == "reutilizado":
            notes.append(f"{row['Envoltorio']} ya existía exactamente como {row['Envoltorio']} -> {row['Terminal']} ⇒ se reutiliza")
        elif row["Envoltorio"] != wrapper_base(row["Terminal"]):
            notes.append(
                f"{wrapper_base(row['Terminal'])} ya existe con otro significado ⇒ se usa {row['Envoltorio']}"
            )
    notes.append("Envoltorios: " + ", ".join(f"{row['Envoltorio']} -> {row['Terminal']}" for row in wrapper_rows))
    new_variables = {production.lhs for production in created_productions}
    result = rebuild(
        grammar,
        (*productions, *created_productions),
        variables=grammar.variables | new_variables,
    )
    return result, Trace(PHASE, result, tables, notes)
