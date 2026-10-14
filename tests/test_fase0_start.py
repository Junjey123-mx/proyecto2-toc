import unittest

from src.algorithms.simplification.start_symbol import add_new_start_symbol
from src.model.production import Production
from tests.grammar_helpers import grammar_from, load


class NewStartSymbolTest(unittest.TestCase):
    def test_creates_new_start_when_start_appears_in_rhs(self):
        grammar = load("test_lab7.txt")
        result, trace = add_new_start_symbol(grammar)
        self.assertEqual(result.start_symbol, "S0")
        self.assertIn("S0", result.variables)
        self.assertEqual(result.productions[0], Production("S0", ("S",)))
        self.assertEqual(result.productions[1:], grammar.productions)
        self.assertEqual(trace.tables["Símbolo inicial"][0]["Inicial anterior"], "S")
        self.assertEqual(trace.tables["Símbolo inicial"][0]["Inicial nuevo"], "S0")
        self.assertEqual(trace.tables["Símbolo inicial"][0]["Se creó"], "sí")

    def test_keeps_grammar_when_start_not_in_rhs(self):
        grammar = load("english.txt")
        result, trace = add_new_start_symbol(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.tables["Símbolo inicial"][0]["Se creó"], "no")
        self.assertIn("no aplica", trace.notes[-1])

    def test_nullable_start_outside_rhs_keeps_start(self):
        grammar = grammar_from("S -> a | ε")
        result, trace = add_new_start_symbol(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.tables["Condiciones"][1]["Cumple"], "sí")
        self.assertIn("anulable", trace.notes[-1])

    def test_reports_nullable_start_in_rhs(self):
        result, trace = add_new_start_symbol(load("test_guia.txt"))
        self.assertEqual(result.start_symbol, "S0")
        self.assertTrue(any("conservará la producción-ε" in note for note in trace.notes))

    def test_avoids_collision_with_existing_s0(self):
        grammar = grammar_from("S -> a S0 | b S", "S0 -> c")
        result, trace = add_new_start_symbol(grammar)
        self.assertEqual(result.start_symbol, "S0_1")
        self.assertIn(Production("S0_1", ("S",)), result.productions)
        self.assertEqual(result.productions_for("S0"), (Production("S0", ("c",)),))
        self.assertTrue(any("S0 ya existe" in note for note in trace.notes))

    def test_does_not_mutate_input(self):
        grammar = load("test_lab7.txt")
        snapshot = (grammar.start_symbol, grammar.variables, grammar.productions)
        add_new_start_symbol(grammar)
        self.assertEqual((grammar.start_symbol, grammar.variables, grammar.productions), snapshot)


if __name__ == "__main__":
    unittest.main()
