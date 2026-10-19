"""Modelo de producción de una CFG."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Production:
    """Representa una producción A -> α de la CFG; un RHS vacío significa ε."""
    lhs: str
    rhs: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "rhs", tuple(self.rhs))

    @property
    def is_epsilon(self):
        return not self.rhs
