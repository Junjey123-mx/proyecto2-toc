from src.algorithms.chomsky.validator import is_cnf
from src.algorithms.cyk.table import build_cyk_table
from src.model.production import Production

CNF_REQUIRED = "CYK requires a grammar in Chomsky normal form"


def recognize_cyk(grammar, tokens):
    if not is_cnf(grammar):
        raise ValueError(CNF_REQUIRED)
    if not tokens:
        return Production(grammar.start_symbol) in grammar.productions, []
    table = build_cyk_table(grammar, tokens)
    return grammar.start_symbol in table[0][len(tokens) - 1], table
