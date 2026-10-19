from pathlib import Path

from src.input.grammar_parser import parse_grammar_file, parse_grammar_lines

GRAMMARS_DIRECTORY = Path(__file__).resolve().parent.parent / "grammars"
PROJECT_GRAMMARS = (
    "english.txt",
    "1.txt",
    "1-cnf.txt",
    "test_lab7.txt",
    "test_guia.txt",
    "test_practica.txt",
    "test_corto_p3.txt",
    "test_corto_p4.txt",
    "test_corto_p5.txt",
    "test_long_rules.txt",
)


EXPRESSION_GRAMMAR_LINES = (
    "E -> T X",
    "X -> + T X | e",
    "T -> F Y",
    "Y -> * F Y | e",
    "F -> ( E ) | id",
)


EXPRESSION_CNF_GRAMMAR_LINES = (
    "E -> T X | F Y | L Z | id",
    "X -> P W | P T",
    "T -> F Y | L Z | id",
    "Y -> M V | M F",
    "F -> L Z | id",
    "Z -> E R",
    "W -> T X",
    "V -> F Y",
    "L -> (",
    "R -> )",
    "P -> +",
    "M -> *",
)


def grammar_from(*lines):
    return parse_grammar_lines(enumerate(lines, start=1)).grammar


def load(file_name):
    return parse_grammar_file(GRAMMARS_DIRECTORY / file_name).grammar


def rules(grammar):
    table = {}
    for production in grammar.productions:
        table.setdefault(production.lhs, set()).add(" ".join(production.rhs) or "ε")
    return table


def language(grammar, max_length):
    derived = {variable: set() for variable in grammar.variables}
    changed = True
    while changed:
        changed = False
        for production in grammar.productions:
            strings = {()}
            for symbol in production.rhs:
                options = derived[symbol] if symbol in grammar.variables else {(symbol,)}
                strings = {
                    prefix + suffix
                    for prefix in strings
                    for suffix in options
                    if len(prefix) + len(suffix) <= max_length
                }
            new_strings = strings - derived[production.lhs]
            if new_strings:
                derived[production.lhs] |= new_strings
                changed = True
    return derived[grammar.start_symbol]
