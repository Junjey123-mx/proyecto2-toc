"""Puntos de entrada de CYK: reconocimiento, análisis medido y benchmark."""

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
    """Lanza ValueError si la gramática no está en CNF."""
    if not is_cnf(grammar):
        raise ValueError(CNF_REQUIRED)


def require_valid_runs(runs):
    """Acepta solo enteros ≥ 1 como cantidad de corridas; bool se rechaza explícitamente."""
    if isinstance(runs, bool) or not isinstance(runs, int):
        raise TypeError(RUNS_TYPE_REQUIRED)
    if runs < 1:
        raise ValueError(RUNS_RANGE_REQUIRED)


def _recognize_cnf(grammar, tokens):
    """Construye la tabla y decide la pertenencia; asume que la gramática está en CNF."""
    # La cadena vacía solo se acepta con inicial -> ε; no se construye tabla.
    if not tokens:
        return Production(grammar.start_symbol) in grammar.productions, []
    table = build_cyk_table(grammar, tokens)
    # Se acepta solo si el símbolo inicial cubre la oración completa.
    return grammar.start_symbol in table[0][len(tokens) - 1], table


def recognize_cyk(grammar, tokens):
    """Ejecuta CYK sobre los tokens con una gramática en CNF; devuelve (aceptada, tabla)."""
    require_cnf(grammar)
    return _recognize_cnf(grammar, tokens)


def parse_cyk(grammar, tokens):
    """Ejecuta CYK una vez y devuelve un CYKResult con tabla, parse tree y tiempo.

    Solo se mide la tabla y la aceptación; la validación CNF y el árbol quedan fuera.
    """
    require_cnf(grammar)
    (accepted, table), elapsed_ns = measure_ns(lambda: _recognize_cnf(grammar, tokens))
    parse_tree = reconstruct_parse_tree(grammar, table, tokens) if accepted else None
    return CYKResult(accepted, table, parse_tree, elapsed_ns)


def benchmark_cyk(grammar, tokens, runs):
    """Devuelve la mediana de `runs` reconocimientos, sin construir parse trees."""
    require_valid_runs(runs)
    require_cnf(grammar)
    samples = [measure_ns(lambda: _recognize_cnf(grammar, tokens))[1] for _ in range(runs)]
    return median_ns(samples)
