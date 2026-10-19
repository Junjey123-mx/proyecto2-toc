"""Traza de transformación por fase."""

from dataclasses import dataclass, field
from typing import Any

from src.model.grammar import Grammar


@dataclass
class Trace:
    """Tablas y notas producidas por una fase, junto con su gramática resultante.

    Las tablas asocian un nombre con filas (diccionarios); la capa de salida les da formato.
    """
    phase: str
    result: Grammar
    tables: dict[str, list[Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
