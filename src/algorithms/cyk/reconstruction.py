from src.model.backpointer import TerminalBackPointer
from src.model.parse_node import EPSILON_TOKEN, ParseNode
from src.model.production import Production


def reconstruct_parse_tree(grammar, table, tokens):
    start = grammar.start_symbol
    if not tokens:
        if Production(start) in grammar.productions:
            return ParseNode(start, EPSILON_TOKEN)
        return None
    last = len(tokens) - 1
    if start not in table[0][last]:
        return None
    return build_node(table, start, 0, last)


def build_node(table, symbol, start, end):
    pointer = table[start][end][symbol]
    if isinstance(pointer, TerminalBackPointer):
        return ParseNode(symbol, pointer.token)
    left = build_node(table, pointer.left_symbol, start, pointer.split)
    right = build_node(table, pointer.right_symbol, pointer.split + 1, end)
    return ParseNode(symbol, None, (left, right))
