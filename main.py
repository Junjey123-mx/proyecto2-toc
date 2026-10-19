import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import cnf_violations
from src.algorithms.cyk.parser import benchmark_cyk, parse_cyk
from src.algorithms.cyk.table import build_production_indexes
from src.algorithms.simplification.simplify import simplify
from src.input.grammar_loader import GrammarLoadError
from src.input.grammar_parser import parse_grammar_file, parse_grammar_lines
from src.input.sentence_parser import parse_sentence
from src.model.grammar import Grammar
from src.output.formatter import (
    format_benchmark_ns,
    format_cyk_table,
    format_elapsed_ns,
    format_result,
    format_tokens,
    format_vocabulary_warnings,
)
from src.output.trace_formatter import (
    banner,
    format_cnf_grammar,
    format_cnf_validation,
    format_conclusions,
    format_original_grammar,
    format_traces,
    grammar_version,
)
from src.output.tree_formatter import format_parse_tree

GRAMMARS_DIRECTORY = Path(__file__).resolve().parent / "grammars"
GRAMMAR_MENU_SECTIONS = (
    (
        "Gramáticas proporcionadas por Bidkar Pojoy:",
        (
            ("English", GRAMMARS_DIRECTORY / "english.txt"),
            ("1.txt — Gramática de expresiones", GRAMMARS_DIRECTORY / "1.txt"),
            ("1-cnf.txt — Gramática de expresiones en CNF", GRAMMARS_DIRECTORY / "1-cnf.txt"),
        ),
    ),
    (
        "Ejercicios propios de prueba:",
        (
            ("Laboratorio 7", GRAMMARS_DIRECTORY / "test_lab7.txt"),
            ("Guía", GRAMMARS_DIRECTORY / "test_guia.txt"),
            ("Práctica", GRAMMARS_DIRECTORY / "test_practica.txt"),
            ("Corto P3", GRAMMARS_DIRECTORY / "test_corto_p3.txt"),
            ("Corto P4", GRAMMARS_DIRECTORY / "test_corto_p4.txt"),
            ("Corto P5", GRAMMARS_DIRECTORY / "test_corto_p5.txt"),
            ("Long Rules", GRAMMARS_DIRECTORY / "test_long_rules.txt"),
        ),
    ),
)
GRAMMAR_MENU_OPTIONS = tuple(option for _, options in GRAMMAR_MENU_SECTIONS for option in options)
OTHER_OPTIONS_TITLE = "Otras opciones:"
DEFAULT_GRAMMAR = GRAMMAR_MENU_OPTIONS[0][1]
MANUAL_OPTION = str(len(GRAMMAR_MENU_OPTIONS) + 1)
MANUAL_SOURCE = "entrada manual"
MANUAL_TERMINATOR = "FIN"
MANUAL_INSTRUCTIONS = "\n".join(
    [
        "Ingrese las producciones de la gramática.",
        "Use el mismo formato que los archivos .txt.",
        f"Escriba {MANUAL_TERMINATOR} en una línea independiente para terminar.",
        "",
        "Ejemplo:",
        "S -> NP VP",
        "VP -> V NP | eats",
        "NP -> Det N | she",
        "V -> eats",
        "Det -> a | the",
        "N -> cake",
    ]
)
EXIT_OPTION = "0"
BANNER = "\n".join(["=" * 40, "CYK PARSER — TOC".center(40).rstrip(), "=" * 40])
MENU_BANNER = "\n".join(["=" * 40, "SELECCIÓN DE GRAMÁTICA".center(40).rstrip(), "=" * 40])
SEPARATOR = "-" * 40
PROMPT = "Ingrese una oración (vacío para salir):"
MENU_SENTENCE_PROMPT = "Cadena:"
VALIDATION_BANNER = "\n".join(
    [
        banner("VALIDACIÓN DE CADENAS"),
        "",
        "Ingrese una oración o cadena para evaluarla con CYK.",
        "",
        "• Enter una vez:",
        "  validar la cadena vacía ε.",
        "",
        "• Enter dos veces consecutivas:",
        "  regresar al menú de gramáticas.",
    ]
)
REPORT_HEADER = "\n".join(["-" * 40, "CADENA ANALIZADA", "-" * 40])
RETURN_HINT = "Presione Enter nuevamente para volver al menú,\no escriba otra cadena para continuar."
INVALID_OPTION = "Opción inválida. Intente nuevamente."


@dataclass(frozen=True)
class PreparedGrammar:
    source: str
    original: Grammar
    warnings: tuple
    traces: tuple
    cnf: Grammar
    violations: tuple
    vocabulary: frozenset
    synthetic_variables: frozenset


def positive_runs(text):
    try:
        runs = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' no es un entero") from None
    if runs < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor o igual que 1")
    return runs


def build_argument_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Determina con CYK si una oración pertenece al lenguaje de una gramática libre de contexto.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--grammar", type=Path, metavar="RUTA", help="archivo .txt de la gramática")
    source.add_argument("--menu", action="store_true", help="elige la gramática desde un menú interactivo")
    parser.add_argument("--trace", action="store_true", help="muestra las tablas de cada fase")
    parser.add_argument("--show-cnf", action="store_true", help="imprime la gramática final en CNF")
    parser.add_argument("--show-table", action="store_true", help="imprime la tabla CYK de cada oración")
    parser.add_argument("--runs", type=positive_runs, default=1, metavar="N", help="repite CYK N veces y reporta la mediana")
    return parser


def parse_arguments(argv=None):
    arguments = build_argument_parser().parse_args(argv)
    arguments.grammar_given = arguments.grammar is not None
    if not arguments.grammar_given:
        arguments.grammar = DEFAULT_GRAMMAR
    return arguments


def prepare_grammar(path):
    return prepare_parsed_grammar(parse_grammar_file(path), display_path(path))


def prepare_parsed_grammar(parsed, source):
    simplified, simplification_traces = simplify(parsed.grammar)
    cnf, cnf_traces = to_cnf(simplified)
    terminal_index, _ = build_production_indexes(cnf)
    return PreparedGrammar(
        source=source,
        original=parsed.grammar,
        warnings=parsed.warnings,
        traces=tuple(simplification_traces + cnf_traces),
        cnf=cnf,
        violations=tuple(cnf_violations(cnf)),
        vocabulary=frozenset(terminal_index),
        synthetic_variables=cnf.variables - parsed.grammar.variables,
    )


def display_path(path):
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def format_parse_warnings(warnings):
    return "\n".join(
        f'Aviso (línea {warning.line_number}): "{warning.symbol}" {warning.reason}' for warning in warnings
    )


def format_preparation(prepared, show_trace, show_cnf):
    sections = [f"{BANNER}\n\nGramática: {prepared.source}", format_original_grammar(prepared.original)]
    if prepared.warnings:
        sections.append(format_parse_warnings(prepared.warnings))
    traces = list(prepared.traces)
    final_version = grammar_version(len(traces))
    sections.append(format_traces(traces, original=prepared.original) if show_trace else format_conclusions(traces))
    if show_cnf:
        sections.append(format_cnf_grammar(prepared.cnf, final_version))
    sections.append(format_cnf_validation(prepared.cnf, list(prepared.violations), final_version))
    return "\n\n\n".join(sections)


def format_sentence_report(prepared, tokens, runs, show_table):
    result = parse_cyk(prepared.cnf, tokens)
    token_block = [format_tokens(tokens)]
    warnings = format_vocabulary_warnings(tokens, prepared.vocabulary)
    if warnings:
        token_block.append(warnings)
    timing_block = [format_elapsed_ns(result.elapsed_ns)]
    if runs > 1:
        timing_block.append(format_benchmark_ns(benchmark_cyk(prepared.cnf, tokens, runs), runs))
    blocks = [REPORT_HEADER, "\n".join(token_block), format_result(result.accepted), "\n".join(timing_block)]
    if result.accepted:
        blocks.append(f"Parse tree:\n\n{format_parse_tree(result.parse_tree, prepared.synthetic_variables)}")
    if show_table:
        blocks.append(format_cyk_table(result.table, tokens))
    return "\n\n".join(blocks)


def interactive_loop(prepared, runs, show_table, prompt=PROMPT):
    while True:
        print(SEPARATOR)
        print(prompt)
        raw = input("> ")
        if not raw.strip():
            return
        print()
        print(format_sentence_report(prepared, parse_sentence(raw), runs, show_table))
        print()


def format_menu():
    lines = [MENU_BANNER]
    number = 1
    for title, options in GRAMMAR_MENU_SECTIONS:
        lines.extend(["", title, ""])
        for label, _ in options:
            lines.append(f"{number}. {label}")
            number += 1
    lines.extend(["", OTHER_OPTIONS_TITLE, ""])
    lines.append(f"{MANUAL_OPTION}. Ingresar gramática manualmente")
    lines.append(f"{EXIT_OPTION}. Salir")
    lines.append("")
    lines.append("Opción:")
    return "\n".join(lines)


def bundled_grammar_path(choice):
    if choice.isdigit() and 1 <= int(choice) <= len(GRAMMAR_MENU_OPTIONS):
        return GRAMMAR_MENU_OPTIONS[int(choice) - 1][1]
    return None


def prepare_menu_choice(choice):
    path = bundled_grammar_path(choice)
    if path is not None:
        return prepare_grammar(path)
    if choice == MANUAL_OPTION:
        return prepare_parsed_grammar(parse_grammar_lines(read_manual_lines()), MANUAL_SOURCE)
    return None


def read_manual_lines():
    print(MANUAL_INSTRUCTIONS)
    print()
    lines = []
    while True:
        line = input("> ")
        if line.strip().upper() == MANUAL_TERMINATOR:
            return list(enumerate(lines, start=1))
        lines.append(line)


def run_grammar_session(prepared, arguments):
    print(format_preparation(prepared, arguments.trace, arguments.show_cnf))
    print()
    if prepared.violations:
        return False
    interactive_loop(prepared, arguments.runs, arguments.show_table)
    return True


def menu_validation_loop(prepared, runs, show_table):
    previous_input_was_empty = False
    while True:
        print(SEPARATOR)
        print(MENU_SENTENCE_PROMPT)
        raw = input("> ")
        is_empty = not raw.strip()
        if is_empty and previous_input_was_empty:
            return
        print()
        print(format_sentence_report(prepared, parse_sentence(raw), runs, show_table))
        if is_empty:
            print()
            print(RETURN_HINT)
        print()
        previous_input_was_empty = is_empty


def run_menu_grammar_session(prepared, arguments):
    print(format_preparation(prepared, show_trace=True, show_cnf=True))
    print()
    if prepared.violations:
        return
    print()
    print()
    print(VALIDATION_BANNER)
    print()
    menu_validation_loop(prepared, arguments.runs, arguments.show_table)


def menu_session(arguments):
    while True:
        print(format_menu())
        choice = input("> ").strip()
        if choice == EXIT_OPTION:
            return
        try:
            prepared = prepare_menu_choice(choice)
        except (GrammarLoadError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)
            print()
            continue
        if prepared is None:
            print(INVALID_OPTION)
            print()
            continue
        run_menu_grammar_session(prepared, arguments)
        print()


def uses_menu(arguments):
    return not arguments.grammar_given and (arguments.menu or sys.stdin.isatty())


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        if uses_menu(arguments):
            menu_session(arguments)
            return 0
        prepared = prepare_grammar(arguments.grammar)
        if not run_grammar_session(prepared, arguments):
            return 1
    except (GrammarLoadError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
