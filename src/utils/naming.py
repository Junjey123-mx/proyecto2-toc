"""Nombres sin colisiones para variables auxiliares."""

def candidate_names(base):
    """Genera base, base_1, base_2, … en un orden fijo."""
    yield base
    index = 1
    while True:
        yield f"{base}_{index}"
        index += 1


def fresh_variable(base, existing_symbols):
    """Devuelve el primer nombre candidato que no esté en `existing_symbols`."""
    for name in candidate_names(base):
        if name not in existing_symbols:
            return name


def fresh_indexed_variable(prefix, existing_symbols, start=1):
    """Devuelve el primer prefix<n> libre con n ≥ start, junto con n."""
    index = start
    while f"{prefix}{index}" in existing_symbols:
        index += 1
    return f"{prefix}{index}", index
