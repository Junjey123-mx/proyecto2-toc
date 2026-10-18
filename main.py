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
from src.input.grammar_parser import parse_grammar_file
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
    format_cnf_check,
    format_conclusions,
    format_grammar,
    format_grammar_summary,
    format_traces,
)
from src.output.tree_formatter import format_parse_tree

DEFAULT_GRAMMAR = Path(__file__).resolve().parent / "grammars" / "english.txt"
BANNER = "\n".join(["=" * 40, "CYK PARSER — TOC".center(40).rstrip(), "=" * 40])
SEPARATOR = "-" * 40
PROMPT = "Ingrese una oración (vacío para salir):"


@dataclass(frozen=True)
class PreparedGrammar:
    path: Path
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
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR, metavar="RUTA", help="archivo .txt de la gramática")
    parser.add_argument("--trace", action="store_true", help="muestra las tablas de cada fase")
    parser.add_argument("--show-cnf", action="store_true", help="imprime la gramática final en CNF")
    parser.add_argument("--show-table", action="store_true", help="imprime la tabla CYK de cada oración")
    parser.add_argument("--runs", type=positive_runs, default=1, metavar="N", help="repite CYK N veces y reporta la mediana")
    return parser


def parse_arguments(argv=None):
    return build_argument_parser().parse_args(argv)


def prepare_grammar(path):
    parsed = parse_grammar_file(path)
    simplified, simplification_traces = simplify(parsed.grammar)
    cnf, cnf_traces = to_cnf(simplified)
    terminal_index, _ = build_production_indexes(cnf)
    return PreparedGrammar(
        path=path,
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
    sections = [
        BANNER,
        "\n".join(
            [
                f"Gramática: {display_path(prepared.path)}",
                format_grammar_summary(prepared.original),
                f"Símbolo inicial: {prepared.original.start_symbol}",
            ]
        ),
    ]
    if prepared.warnings:
        sections.append(format_parse_warnings(prepared.warnings))
    traces = list(prepared.traces)
    sections.append(format_traces(traces) if show_trace else format_conclusions(traces))
    if show_cnf:
        sections.append(
            f"Gramática CNF ({format_grammar_summary(prepared.cnf)}):\n{format_grammar(prepared.cnf)}"
        )
    sections.append(format_cnf_check(prepared.cnf, list(prepared.violations)))
    return "\n\n".join(sections)


def format_sentence_report(prepared, tokens, runs, show_table):
    result = parse_cyk(prepared.cnf, tokens)
    lines = [format_tokens(tokens)]
    warnings = format_vocabulary_warnings(tokens, prepared.vocabulary)
    if warnings:
        lines.append(warnings)
    lines.append(format_result(result.accepted))
    lines.append(format_elapsed_ns(result.elapsed_ns))
    if runs > 1:
        lines.append(format_benchmark_ns(benchmark_cyk(prepared.cnf, tokens, runs), runs))
    if result.accepted:
        lines.append("")
        lines.append("Parse tree:")
        lines.append(format_parse_tree(result.parse_tree, prepared.synthetic_variables))
    if show_table:
        lines.append("")
        lines.append(format_cyk_table(result.table, tokens))
    return "\n".join(lines)


def interactive_loop(prepared, runs, show_table):
    while True:
        print(SEPARATOR)
        print(PROMPT)
        raw = input("> ")
        if not raw.strip():
            return
        print()
        print(format_sentence_report(prepared, parse_sentence(raw), runs, show_table))
        print()


def main(argv=None):
    arguments = parse_arguments(argv)
    try:
        prepared = prepare_grammar(arguments.grammar)
        print(format_preparation(prepared, arguments.trace, arguments.show_cnf))
        print()
        if prepared.violations:
            return 1
        interactive_loop(prepared, arguments.runs, arguments.show_table)
    except (GrammarLoadError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
