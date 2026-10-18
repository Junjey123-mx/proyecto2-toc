from src.algorithms.chomsky.validator import is_cnf
from src.algorithms.cyk.reconstruction import reconstruct_parse_tree
from src.algorithms.cyk.table import build_cyk_table
from src.model.cyk_result import CYKResult
from src.model.production import Production
from src.utils.timer import measure_ns, median_ns

CNF_REQUIRED = "CYK requires a grammar in Chomsky normal form"
RUNS_TYPE_REQUIRED = "runs must be an integer"
RUNS_RANGE_REQUIRED = "runs must be at least 1"


def require_cnf(grammar):
    if not is_cnf(grammar):
        raise ValueError(CNF_REQUIRED)


def require_valid_runs(runs):
    if isinstance(runs, bool) or not isinstance(runs, int):
        raise TypeError(RUNS_TYPE_REQUIRED)
    if runs < 1:
        raise ValueError(RUNS_RANGE_REQUIRED)


def _recognize_cnf(grammar, tokens):
    if not tokens:
        return Production(grammar.start_symbol) in grammar.productions, []
    table = build_cyk_table(grammar, tokens)
    return grammar.start_symbol in table[0][len(tokens) - 1], table


def recognize_cyk(grammar, tokens):
    require_cnf(grammar)
    return _recognize_cnf(grammar, tokens)


def parse_cyk(grammar, tokens):
    require_cnf(grammar)
    (accepted, table), elapsed_ns = measure_ns(lambda: _recognize_cnf(grammar, tokens))
    parse_tree = reconstruct_parse_tree(grammar, table, tokens) if accepted else None
    return CYKResult(accepted, table, parse_tree, elapsed_ns)


def benchmark_cyk(grammar, tokens, runs):
    require_valid_runs(runs)
    require_cnf(grammar)
    samples = [measure_ns(lambda: _recognize_cnf(grammar, tokens))[1] for _ in range(runs)]
    return median_ns(samples)
