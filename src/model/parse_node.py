"""Modelo de nodo del parse tree."""

from dataclasses import dataclass

EPSILON_TOKEN = "ε"


@dataclass(frozen=True)
class ParseNode:
    """Representa un nodo del parse tree reconstruido.

    Las hojas llevan un token (ε para la cadena vacía); los nodos internos, dos hijos.
    """
    symbol: str
    token: str | None = None
    children: tuple["ParseNode", ...] = ()
