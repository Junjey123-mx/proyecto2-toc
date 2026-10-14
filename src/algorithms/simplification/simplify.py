from src.algorithms.grammar_tools import run_phases
from src.algorithms.simplification.epsilon import eliminate_epsilon
from src.algorithms.simplification.start_symbol import add_new_start_symbol
from src.algorithms.simplification.unit import eliminate_unit
from src.algorithms.simplification.useless import eliminate_useless

SIMPLIFICATION_PHASES = (add_new_start_symbol, eliminate_epsilon, eliminate_unit, eliminate_useless)


def simplify(grammar):
    return run_phases(grammar, SIMPLIFICATION_PHASES)
