"""Backpointers de CYK guardados en cada celda de la tabla."""

from dataclasses import dataclass

from src.model.production import Production


@dataclass(frozen=True)
class TerminalBackPointer:
    """Testigo de A -> token en una celda de la diagonal."""
    token: str


@dataclass(frozen=True)
class BinaryBackPointer:
    """Testigo de A -> B C, con B sobre [i..split] y C sobre [split+1..j]."""
    production: Production
    split: int
    left_symbol: str
    right_symbol: str


# Cualquier valor guardado en una celda de CYK.
type BackPointer = TerminalBackPointer | BinaryBackPointer
