from dataclasses import dataclass, field
from typing import Any

from src.model.grammar import Grammar


@dataclass
class Trace:
    phase: str
    result: Grammar
    tables: dict[str, list[Any]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
