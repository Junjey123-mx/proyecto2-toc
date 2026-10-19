import re
from dataclasses import dataclass
from itertools import count

from src.model.production import Production
from src.utils.notation import production_text, rhs_text, set_text

INDENT = "  "
EMPTY_TABLE = "(sin filas)"
EMPTY_GRAMMAR = "(sin producciones)"
BANNER_WIDTH = 40
NOT_APPLICABLE = "No aplica."
PHASE_PATTERN = re.compile(r"^Fase (\d+):")
PHASE_TITLES = {
    0: "NUEVO SÍMBOLO INICIAL",
    1: "ELIMINACIÓN DE ε",
    2: "PRODUCCIONES UNITARIAS",
    3: "SÍMBOLOS INÚTILES",
    4: "AISLAR TERMINALES",
    5: "BINARIZACIÓN",
}


def format_value(value, nested=False):
    if isinstance(value, Production):
        return production_text(value)
    if isinstance(value, (set, frozenset)):
        return set_text(value)
    if isinstance(value, (tuple, list)):
        if not value:
            return "—"
        text = ", ".join(format_value(item, nested=True) for item in value)
        return f"({text})" if nested else text
    return str(value)


def format_table(rows):
    if not rows:
        return [EMPTY_TABLE]
    headers = list(rows[0])
    cells = [[format_value(row.get(header, "")) for header in headers] for row in rows]
    widths = [max(len(header), *(len(line[index]) for line in cells)) for index, header in enumerate(headers)]
    lines = [" | ".join(header.ljust(width) for header, width in zip(headers, widths)).rstrip()]
    lines.append("-+-".join("-" * width for width in widths))
    for line in cells:
        lines.append(" | ".join(cell.ljust(width) for cell, width in zip(line, widths)).rstrip())
    return lines


def grammar_lines(grammar):
    alternatives = {}
    for production in grammar.productions:
        alternatives.setdefault(production.lhs, []).append(rhs_text(production.rhs))
    if not alternatives:
        return [EMPTY_GRAMMAR]
    order = [grammar.start_symbol, *alternatives]
    return [f"{lhs} -> {' | '.join(alternatives[lhs])}" for lhs in dict.fromkeys(order) if lhs in alternatives]


def format_grammar(grammar):
    return "\n".join(grammar_lines(grammar))


def format_grammar_summary(grammar):
    return (
        f"|V| = {len(grammar.variables)}   |Σ| = {len(grammar.terminals)}   "
        f"|R| = {len(grammar.productions)}   Inicial: {grammar.start_symbol}"
    )


def banner(title):
    rule = "=" * BANNER_WIDTH
    return "\n".join([rule, title.center(BANNER_WIDTH).rstrip(), rule])


def last_value(rows, column):
    return rows[-1][column] if rows else frozenset()


def start_symbol_result(tables):
    row = tables["Símbolo inicial"][0]
    if row["Se creó"] == "sí":
        return f"Nuevo símbolo inicial: {row['Inicial nuevo']}"
    return f"Se conserva {row['Inicial anterior']} como símbolo inicial."


def nullable_result(tables):
    return f"N = {set_text(last_value(tables['Anulables'], 'Conjunto N'))}"


def unit_result(tables):
    units = tables["Unitarias"]
    if not units:
        return "No existen producciones unitarias."
    return f"Se encontraron {len(units)} producciones unitarias."


def generating_result(tables):
    return f"3a Generadores: {set_text(last_value(tables['3a Generadores'], 'Conjunto acumulado'))}"


def reachable_result(tables):
    return f"3b Alcanzables: {set_text(last_value(tables['3b Alcanzables'], 'Conjunto acumulado'))}"


def accompanied_result(tables):
    rows = tables["Lados derechos de longitud ≥ 2"]
    terminals = dict.fromkeys(
        terminal for row in rows if isinstance(row["Terminales acompañados"], tuple) for terminal in row["Terminales acompañados"]
    )
    if not terminals:
        return "Ningún lado derecho de longitud ≥ 2 contiene terminales."
    return f"Terminales acompañados: {', '.join(terminals)}"


def wrapper_result(tables):
    return None if tables["Envoltorios"] else "No se requieren variables envoltorio."


def binarization_result(tables):
    return None if tables["Binarización"] else "Ningún RHS tiene longitud mayor que 2."


@dataclass(frozen=True)
class StepLayout:
    title: str
    tables: tuple
    result: object = None


PHASE_LAYOUTS = {
    0: (
        StepLayout("Verificar las condiciones del símbolo inicial", ("Condiciones",)),
        StepLayout("Determinar el símbolo inicial resultante", ("Símbolo inicial",), start_symbol_result),
    ),
    1: (
        StepLayout("Calcular el conjunto de variables anulables", ("Anulables",), nullable_result),
        StepLayout("Generar las variantes sin producciones-ε", ("Variantes",)),
    ),
    2: (
        StepLayout("Identificar las producciones unitarias", ("Unitarias",), unit_result),
        StepLayout("Calcular los pares unitarios", ("Pares unitarios",)),
        StepLayout("Transferir las producciones no unitarias", ("No unitarias", "Transferencias")),
    ),
    3: (
        StepLayout("Calcular las variables generadoras", ("3a Generadores",), generating_result),
        StepLayout("Eliminar las variables no generadoras", ("3a Símbolos eliminados", "3a Producciones eliminadas")),
        StepLayout("Calcular las variables alcanzables", ("3b Alcanzables",), reachable_result),
        StepLayout("Eliminar las variables no alcanzables", ("3b Símbolos eliminados", "3b Producciones eliminadas")),
    ),
    4: (
        StepLayout("Identificar y sustituir los terminales acompañados", ("Lados derechos de longitud ≥ 2",), accompanied_result),
        StepLayout("Crear o reutilizar variables envoltorio", ("Envoltorios",), wrapper_result),
    ),
    5: (StepLayout("Binarizar los lados derechos de longitud mayor que 2", ("Binarización",), binarization_result),),
}


def phase_number(trace):
    match = PHASE_PATTERN.match(trace.phase)
    return int(match.group(1)) if match else None


def phase_layout(trace, number):
    if number in PHASE_LAYOUTS:
        return PHASE_LAYOUTS[number]
    return tuple(StepLayout(name, (name,)) for name in trace.tables)


def format_step(number, title, body):
    prefix = f"{number}. "
    indent = " " * len(prefix)
    lines = [f"{prefix}{title}"]
    for block in body:
        lines.append("")
        lines.extend(f"{indent}{line}".rstrip() for line in block)
    return "\n".join(lines)


def step_body(layout, trace, show_tables):
    present = [name for name in layout.tables if name in trace.tables]
    body = []
    if show_tables:
        for name in present:
            body.append([name, *format_table(trace.tables[name])])
    result = layout.result(trace.tables) if layout.result and present else None
    if not present:
        result = NOT_APPLICABLE
    if result:
        body.append(["Resultado:", result])
    return body, result


def grammar_step_body(trace, number):
    label = f"Gramática resultante G{number}" if number is not None else "Gramática resultante"
    return [[f"{label} ({format_grammar_summary(trace.result)}):"], grammar_lines(trace.result)]


def conclusion_lines(trace, shown_results):
    notes = trace.notes
    return [note for index, note in enumerate(notes) if index == len(notes) - 1 or note not in shown_results]


def format_phase(trace, steps, show_tables=True, show_grammar=True):
    number = phase_number(trace)
    title = f"FASE {number} — {PHASE_TITLES[number]}" if number in PHASE_TITLES else trace.phase.upper()
    sections = []
    shown_results = set()
    for layout in phase_layout(trace, number):
        body, result = step_body(layout, trace, show_tables)
        shown_results.add(result)
        sections.append(format_step(next(steps), layout.title, body))
    if show_grammar:
        grammar_title = f"Construir G{number}" if number is not None else "Construir la gramática resultante"
        sections.append(format_step(next(steps), grammar_title, grammar_step_body(trace, number)))
    conclusion = conclusion_lines(trace, shown_results)
    if conclusion:
        sections.append("\n".join(["Conclusión de la fase:", *conclusion]))
    return f"{banner(title)}\n\n" + "\n\n\n".join(sections)


def format_trace(trace, show_tables=True, show_grammar=True):
    return format_phase(trace, count(1), show_tables, show_grammar)


def format_traces(traces, show_tables=True, show_grammar=True):
    steps = count(1)
    return "\n\n".join(format_phase(trace, steps, show_tables, show_grammar) for trace in traces)


def format_conclusions(traces):
    return "\n".join(f"{trace.phase}: {trace.notes[-1]}" for trace in traces if trace.notes)


def format_cnf_grammar(grammar):
    return "\n".join(
        [
            banner("GRAMÁTICA FINAL EN CNF"),
            "",
            f"|V| = {len(grammar.variables)}",
            f"|Σ| = {len(grammar.terminals)}",
            f"|R| = {len(grammar.productions)}",
            f"Inicial: {grammar.start_symbol}",
            "",
            *grammar_lines(grammar),
        ]
    )


def format_cnf_check(grammar, violations):
    if not violations:
        return f"✓ Gramática en CNF\n{INDENT}{len(grammar.productions)} producciones válidas"
    lines = [f"✗ La gramática no está en CNF ({len(violations)} producciones inválidas)"]
    lines.extend(f"{INDENT}{production_text(production)}: {reason}" for production, reason in violations)
    return "\n".join(lines)


def format_cnf_validation(grammar, violations):
    return f"{banner('VALIDACIÓN DE CNF')}\n\n{format_cnf_check(grammar, violations)}"
