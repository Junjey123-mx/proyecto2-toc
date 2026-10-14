from dataclasses import dataclass

from src.input.grammar_loader import load_grammar_lines
from src.input.grammar_validator import EPSILON_SYMBOLS, validate_grammar_lines
from src.model.grammar import Grammar
from src.model.production import Production


@dataclass(frozen=True)
class GrammarWarning:
    line_number: int
    symbol: str
    reason: str


@dataclass(frozen=True)
class ParseResult:
    grammar: Grammar
    warnings: tuple[GrammarWarning, ...]


def parse_grammar_file(path):
    return parse_grammar_lines(load_grammar_lines(path))


def parse_grammar_lines(lines):
    rules = validate_grammar_lines(lines)
    variables = dict.fromkeys(rule.lhs for rule in rules)
    terminals = {}
    productions = []
    warnings = {}
    for rule in rules:
        for alternative in rule.alternatives:
            rhs = () if alternative[0] in EPSILON_SYMBOLS else alternative
            for symbol in rhs:
                if symbol in variables:
                    continue
                terminals.setdefault(symbol)
                if looks_like_variable(symbol) and symbol not in warnings:
                    warnings[symbol] = GrammarWarning(
                        rule.line_number,
                        symbol,
                        "looks like a variable but has no production; treated as terminal",
                    )
            productions.append(Production(rule.lhs, rhs))
    grammar = Grammar(rules[0].lhs, variables, terminals, productions)
    return ParseResult(grammar, tuple(warnings.values()))


def looks_like_variable(symbol):
    return symbol[0].isupper()
