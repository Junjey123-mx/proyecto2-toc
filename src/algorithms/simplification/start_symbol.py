from src.algorithms.grammar_tools import productions_using, rebuild
from src.algorithms.simplification.epsilon import find_nullable
from src.model.production import Production
from src.model.trace import Trace
from src.utils.naming import fresh_variable
from src.utils.notation import production_text

PHASE = "Fase 0: nuevo símbolo inicial"


def new_start_base(start_symbol):
    return f"{start_symbol}0"


def add_new_start_symbol(grammar):
    start = grammar.start_symbol
    occurrences = productions_using(grammar, start)
    nullable, nullable_rows = find_nullable(grammar)
    is_nullable = start in nullable
    nullable_evidence = next((row["Regla aplicada"] for row in nullable_rows if row["Nuevo"] == start), "—")
    created = bool(occurrences)
    new_start = fresh_variable(new_start_base(start), grammar.variables | grammar.terminals) if created else start

    tables = {
        "Condiciones": [
            {
                "Condición": f"{start} aparece en algún lado derecho",
                "Cumple": "sí" if occurrences else "no",
                "Evidencia": occurrences or "—",
            },
            {
                "Condición": f"{start} es anulable",
                "Cumple": "sí" if is_nullable else "no",
                "Evidencia": nullable_evidence,
            },
        ],
        "Símbolo inicial": [
            {
                "Inicial anterior": start,
                "Inicial nuevo": new_start,
                "Se creó": "sí" if created else "no",
            }
        ],
    }

    if not created:
        if is_nullable:
            reason = f"{start} es anulable pero no aparece en ningún lado derecho ⇒ {start} puede conservar ε; no aplica"
        else:
            reason = f"{start} no aparece en ningún lado derecho y no es anulable ⇒ no aplica"
        return grammar, Trace(PHASE, grammar, tables, [reason])

    new_production = Production(new_start, (start,))
    notes = [f"{start} aparece en un lado derecho ⇒ el inicial de la CNF no puede aparecer a la derecha"]
    if is_nullable:
        notes.append(f"{start} es anulable ⇒ {new_start} conservará la producción-ε")
    if new_start != new_start_base(start):
        notes.append(f"{new_start_base(start)} ya existe ⇒ se usa el nombre libre {new_start}")
    notes.append(f"Se agrega {production_text(new_production)} y el inicial pasa de {start} a {new_start}")

    result = rebuild(
        grammar,
        (new_production, *grammar.productions),
        variables=grammar.variables | {new_start},
        start_symbol=new_start,
    )
    return result, Trace(PHASE, result, tables, notes)
