from src.utils.notation import EMPTY_SET, set_text

NANOSECONDS_PER_MICROSECOND = 1_000
NANOSECONDS_PER_SECOND = 1_000_000_000


def format_tokens(tokens):
    return f"Tokens: {list(tokens)}"


def format_result(accepted):
    verdict = "SÍ" if accepted else "NO"
    return f"Resultado: {verdict} pertenece al lenguaje."


def format_duration_ns(nanoseconds):
    microseconds = nanoseconds / NANOSECONDS_PER_MICROSECOND
    seconds = nanoseconds / NANOSECONDS_PER_SECOND
    return f"{microseconds:.3f} µs  ({seconds:.9f} s)"


def format_elapsed_ns(elapsed_ns):
    return f"Tiempo de esta validación: {format_duration_ns(elapsed_ns)}"


def format_benchmark_ns(median_ns, runs):
    return f"Benchmark (mediana de {runs} corridas): {format_duration_ns(median_ns)}"


def unknown_tokens(tokens, vocabulary):
    return [token for token in dict.fromkeys(tokens) if token not in vocabulary]


def format_vocabulary_warnings(tokens, vocabulary):
    return "\n".join(
        f'Aviso: "{token}" no pertenece al vocabulario de la gramática.'
        for token in unknown_tokens(tokens, vocabulary)
    )


def format_cyk_table(table, tokens):
    if not tokens:
        return f"Tabla CYK: {EMPTY_SET} (frase vacía)"
    lines = ["Tabla CYK:"]
    size = len(tokens)
    for length in range(1, size + 1):
        for start in range(size - length + 1):
            end = start + length - 1
            span = " ".join(tokens[start : end + 1])
            lines.append(f'[{start},{end}] "{span}" = {set_text(table[start][end])}')
    return "\n".join(lines)
