from src.model.backpointer import BinaryBackPointer, TerminalBackPointer
from src.model.production import Production


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


def build_cyk_table(grammar, tokens):
    terminal_index, binary_index = build_production_indexes(grammar)
    size = len(tokens)
    table = [[{} for _ in range(size)] for _ in range(size)]
    for position, token in enumerate(tokens):
        for variable in terminal_index.get(token, ()):
            table[position][position].setdefault(variable, TerminalBackPointer(token))
    for length in range(2, size + 1):
        for start in range(size - length + 1):
            end = start + length - 1
            cell = table[start][end]
            for split in range(start, end):
                left_cell = table[start][split]
                right_cell = table[split + 1][end]
                for left in sorted(left_cell):
                    for right in sorted(right_cell):
                        for parent in binary_index.get((left, right), ()):
                            cell.setdefault(
                                parent,
                                BinaryBackPointer(Production(parent, (left, right)), split, left, right),
                            )
    return table
