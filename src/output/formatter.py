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
