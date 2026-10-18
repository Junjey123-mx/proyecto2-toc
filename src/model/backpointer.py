from dataclasses import dataclass

from src.model.production import Production


@dataclass(frozen=True)
class TerminalBackPointer:
    token: str


@dataclass(frozen=True)
class BinaryBackPointer:
    production: Production
    split: int
    left_symbol: str
    right_symbol: str


type BackPointer = TerminalBackPointer | BinaryBackPointer
