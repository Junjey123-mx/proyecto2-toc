"""Validación de la Forma Normal de Chomsky."""

def start_in_rhs(grammar):
    """Indica si el símbolo inicial aparece en algún RHS."""
    return any(grammar.start_symbol in production.rhs for production in grammar.productions)


def production_violation(production, grammar):
    """Devuelve por qué una producción no cumple CNF, o None si es válida."""
    # La CNF acepta A -> B C, A -> a y S -> ε solo si S no está en ningún RHS.
    rhs = production.rhs
    if not rhs:
        if production.lhs != grammar.start_symbol:
            return "producción-ε fuera del símbolo inicial"
        if start_in_rhs(grammar):
            return "producción-ε en el inicial, pero el inicial aparece en un lado derecho"
        return None
    if len(rhs) == 1:
        if rhs[0] in grammar.variables:
            return "producción unitaria"
        return None
    if len(rhs) == 2:
        if all(symbol in grammar.variables for symbol in rhs):
            return None
        return "lado derecho de longitud 2 con terminales"
    return "lado derecho de longitud mayor que 2"


def cnf_violations(grammar):
    """Lista cada producción inválida junto con su motivo."""
    violations = []
    for production in grammar.productions:
        reason = production_violation(production, grammar)
        if reason is not None:
            violations.append((production, reason))
    return violations


def is_cnf(grammar):
    """Verifica si todas las producciones cumplen la Forma Normal de Chomsky."""
    return not cnf_violations(grammar)
