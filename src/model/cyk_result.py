"""Resultado de una validación con CYK."""

from dataclasses import dataclass

from src.model.backpointer import BackPointer
from src.model.parse_node import ParseNode


@dataclass(frozen=True)
class CYKResult:
    """Contiene la aceptación, la tabla, el parse tree y el tiempo de una validación."""
    accepted: bool
    table: list[list[dict[str, BackPointer]]]
    parse_tree: ParseNode | None
    elapsed_ns: int
