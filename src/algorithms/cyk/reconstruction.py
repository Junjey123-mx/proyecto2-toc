"""Reconstrucción del parse tree a partir de los backpointers de CYK."""

from src.model.backpointer import TerminalBackPointer
from src.model.parse_node import EPSILON_TOKEN, ParseNode
from src.model.production import Production


def reconstruct_parse_tree(grammar, table, tokens):
    """Reconstruye un parse tree válido desde los backpointers, o None si se rechaza.

    El árbol es de la gramática CNF, así que pueden aparecer variables auxiliares.
    """
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
    """Expande recursivamente el backpointer de `symbol` sobre tokens[start..end]."""
    pointer = table[start][end][symbol]
    if isinstance(pointer, TerminalBackPointer):
        return ParseNode(symbol, pointer.token)
    left = build_node(table, pointer.left_symbol, start, pointer.split)
    right = build_node(table, pointer.right_symbol, pointer.split + 1, end)
    return ParseNode(symbol, None, (left, right))
