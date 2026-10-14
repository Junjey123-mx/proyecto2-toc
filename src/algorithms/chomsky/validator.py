def start_in_rhs(grammar):
    return any(grammar.start_symbol in production.rhs for production in grammar.productions)


def production_violation(production, grammar):
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
    violations = []
    for production in grammar.productions:
        reason = production_violation(production, grammar)
        if reason is not None:
            violations.append((production, reason))
    return violations


def is_cnf(grammar):
    return not cnf_violations(grammar)
