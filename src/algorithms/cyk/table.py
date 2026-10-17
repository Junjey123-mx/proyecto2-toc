def build_production_indexes(grammar):
    terminal_index = {}
    binary_index = {}
    for production in grammar.productions:
        rhs = production.rhs
        if len(rhs) == 1 and rhs[0] in grammar.terminals:
            terminal_index.setdefault(rhs[0], {})[production.lhs] = None
        elif len(rhs) == 2 and all(symbol in grammar.variables for symbol in rhs):
            binary_index.setdefault(rhs, {})[production.lhs] = None
    return (
        {token: tuple(parents) for token, parents in terminal_index.items()},
        {pair: tuple(parents) for pair, parents in binary_index.items()},
    )
