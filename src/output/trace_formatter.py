from src.model.production import Production
from src.utils.notation import production_text, rhs_text, set_text

INDENT = "  "
EMPTY_TABLE = "(sin filas)"
EMPTY_GRAMMAR = "(sin producciones)"


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


def format_trace(trace, show_tables=True, show_grammar=True):
    lines = [trace.phase]
    if show_tables:
        for name, rows in trace.tables.items():
            lines.append(f"{INDENT}{name}")
            lines.extend(f"{INDENT * 2}{line}" for line in format_table(rows))
    lines.extend(f"{INDENT}{note}" for note in trace.notes)
    if show_grammar:
        lines.append(f"{INDENT}Gramática resultante ({format_grammar_summary(trace.result)}):")
        lines.extend(f"{INDENT * 2}{line}" for line in grammar_lines(trace.result))
    return "\n".join(lines)


def format_traces(traces, show_tables=True, show_grammar=True):
    return "\n\n".join(format_trace(trace, show_tables, show_grammar) for trace in traces)


def format_conclusions(traces):
    return "\n".join(f"{trace.phase}: {trace.notes[-1]}" for trace in traces if trace.notes)


def format_cnf_check(grammar, violations):
    if not violations:
        return f"✓ Gramática en CNF (validador: {len(grammar.productions)} producciones válidas)"
    lines = [f"✗ La gramática no está en CNF ({len(violations)} producciones inválidas)"]
    lines.extend(f"{INDENT}{production_text(production)}: {reason}" for production, reason in violations)
    return "\n".join(lines)
