from dataclasses import dataclass

ARROW = "->"
ALTERNATIVE_SEPARATOR = "|"
COMMENT_PREFIX = "#"
EPSILON_SYMBOLS = frozenset({"ε", "epsilon"})


class GrammarSyntaxError(ValueError):
    def __init__(self, reason, line_number=None):
        message = reason if line_number is None else f"Line {line_number}: {reason}"
        super().__init__(message)
        self.reason = reason
        self.line_number = line_number


@dataclass(frozen=True)
class ValidatedRule:
    line_number: int
    lhs: str
    alternatives: tuple[tuple[str, ...], ...]


def validate_grammar_lines(lines):
    rules = []
    for line_number, text in lines:
        content = text.strip()
        if not content or content.startswith(COMMENT_PREFIX):
            continue
        rules.append(validate_rule(line_number, content))
    if not rules:
        raise GrammarSyntaxError("Grammar has no productions")
    return rules


def validate_rule(line_number, content):
    if content.count(ARROW) != 1:
        raise GrammarSyntaxError(f"expected exactly one '{ARROW}'", line_number)
    lhs_text, rhs_text = content.split(ARROW)
    lhs_symbols = lhs_text.split()
    if not lhs_symbols:
        raise GrammarSyntaxError("missing left-hand side", line_number)
    if len(lhs_symbols) > 1 or ALTERNATIVE_SEPARATOR in lhs_text:
        raise GrammarSyntaxError("left-hand side must be a single variable", line_number)
    if lhs_symbols[0] in EPSILON_SYMBOLS:
        raise GrammarSyntaxError("left-hand side cannot be epsilon", line_number)
    if not rhs_text.strip():
        raise GrammarSyntaxError("missing right-hand side", line_number)
    alternatives = []
    for alternative_text in rhs_text.split(ALTERNATIVE_SEPARATOR):
        symbols = tuple(alternative_text.split())
        if not symbols:
            raise GrammarSyntaxError("empty alternative", line_number)
        if len(symbols) > 1 and EPSILON_SYMBOLS.intersection(symbols):
            raise GrammarSyntaxError("epsilon must appear alone in an alternative", line_number)
        alternatives.append(symbols)
    return ValidatedRule(line_number, lhs_symbols[0], tuple(alternatives))
