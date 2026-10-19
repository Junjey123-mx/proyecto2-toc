"""Fase 5: divide los RHS de más de dos símbolos en producciones binarias."""

from src.algorithms.grammar_tools import rebuild
from src.model.production import Production
from src.model.trace import Trace
from src.utils.naming import fresh_indexed_variable

PHASE = "Fase 5: binarizar"
AUXILIARY_PREFIX = "X"


def binarize(grammar):
    """Divide A -> B1 … Bk (k > 2) en una cadena de producciones binarias.

    Cada producción recibe k - 2 auxiliares nuevas, así se preserva el lenguaje.
    """
    taken = set(grammar.variables | grammar.terminals)
    next_index = 1
    rows = []
    productions = []
    created = []

    def new_variable():
        """Devuelve el siguiente nombre X<n> libre y lo reserva."""
        nonlocal next_index
        name, index = fresh_indexed_variable(AUXILIARY_PREFIX, taken, next_index)
        taken.add(name)
        next_index = index + 1
        created.append(name)
        return name

    for production in grammar.productions:
        rhs = production.rhs
        if len(rhs) <= 2:
            productions.append(production)
            continue
        auxiliaries = [new_variable() for _ in range(len(rhs) - 2)]
        # A -> B1 X1, X1 -> B2 X2, …, X(k-2) -> B(k-1) Bk.
        heads = (production.lhs, *auxiliaries)
        tails = (*auxiliaries, rhs[-1])
        chain = tuple(
            Production(head, (rhs[position], tails[position])) for position, head in enumerate(heads)
        )
        productions.extend(chain)
        rows.append(
            {
                "Producción original": production,
                "Producciones binarias": chain,
                "Variables auxiliares": tuple(auxiliaries),
            }
        )

    tables = {"Binarización": rows}
    if not rows:
        notes = ["Ningún RHS tiene longitud > 2 ⇒ no aplica"]
        return grammar, Trace(PHASE, grammar, tables, notes)

    notes = ["Cada A -> B1 B2 … Bk con k > 2 se reemplaza por una cadena de k - 2 variables nuevas."]
    skipped = sorted(
        (name for name in grammar.variables | grammar.terminals if name.startswith(AUXILIARY_PREFIX) and name[1:].isdigit()),
        key=lambda name: int(name[1:]),
    )
    if skipped:
        notes.append(f"Ya existían {', '.join(skipped)} ⇒ se usan los siguientes índices libres")
    notes.append(f"Variables auxiliares creadas: {', '.join(created)}")
    result = rebuild(grammar, productions, variables=grammar.variables | set(created))
    return result, Trace(PHASE, result, tables, notes)
