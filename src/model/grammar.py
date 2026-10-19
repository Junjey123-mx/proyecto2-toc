"""Modelo de gramática libre de contexto."""

from dataclasses import dataclass

from src.model.production import Production


@dataclass(frozen=True)
class Grammar:
    """Representación inmutable de una gramática libre de contexto G = (V, Σ, R, S).

    Valida sus invariantes al crearse y elimina producciones duplicadas.
    """
    start_symbol: str
    variables: frozenset[str]
    terminals: frozenset[str]
    productions: tuple[Production, ...]

    def __post_init__(self):
        object.__setattr__(self, "variables", frozenset(self.variables))
        object.__setattr__(self, "terminals", frozenset(self.terminals))
        object.__setattr__(self, "productions", tuple(dict.fromkeys(self.productions)))
        self._check_invariants()

    def _check_invariants(self):
        """Asegura S ∈ V, V ∩ Σ = ∅ y que toda producción use símbolos declarados."""
        if self.start_symbol not in self.variables:
            raise ValueError(f"Start symbol {self.start_symbol!r} is not a variable")
        shared_symbols = self.variables & self.terminals
        if shared_symbols:
            raise ValueError(f"Symbols are both variables and terminals: {sorted(shared_symbols)}")
        symbols = self.variables | self.terminals
        for production in self.productions:
            if not isinstance(production, Production):
                raise TypeError(f"Expected Production, got {type(production).__name__}")
            if production.lhs not in self.variables:
                raise ValueError(f"Production left-hand side {production.lhs!r} is not a variable")
            unknown_symbols = [symbol for symbol in production.rhs if symbol not in symbols]
            if unknown_symbols:
                raise ValueError(f"Production uses undeclared symbols: {unknown_symbols}")

    def productions_for(self, variable):
        """Devuelve las producciones de `variable` en orden de declaración."""
        return tuple(production for production in self.productions if production.lhs == variable)
