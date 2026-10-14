import unittest

from src.algorithms.chomsky.terminals import isolate_terminals
from src.model.production import Production
from tests.grammar_helpers import grammar_from, language, load, rules


class IsolateTerminalsTest(unittest.TestCase):
    def test_single_terminal_is_unchanged(self):
        grammar = grammar_from("S -> a")
        result, trace = isolate_terminals(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.notes, ["Ningún terminal acompañado ⇒ G4 = G3"])

    def test_terminal_next_to_variable(self):
        result, trace = isolate_terminals(grammar_from("S -> a S | b"))
        self.assertEqual(rules(result), {"S": {"U_a S", "b"}, "U_a": {"a"}})
        self.assertEqual(trace.tables["Envoltorios"], [{"Terminal": "a", "Envoltorio": "U_a", "Acción": "creado"}])

    def test_multiple_terminals_in_long_rhs(self):
        result, trace = isolate_terminals(grammar_from("A -> a B c", "B -> b"))
        self.assertIn(Production("A", ("U_a", "B", "U_c")), result.productions)
        self.assertEqual(rules(result)["U_a"], {"a"})
        self.assertEqual(rules(result)["U_c"], {"c"})
        self.assertEqual(rules(result)["B"], {"b"})
        row = trace.tables["Lados derechos de longitud ≥ 2"][0]
        self.assertEqual(row["Longitud"], 3)
        self.assertEqual(row["Terminales acompañados"], ("a", "c"))

    def test_one_wrapper_per_terminal(self):
        result, _ = isolate_terminals(grammar_from("S -> a S a | a a"))
        self.assertEqual(rules(result), {"S": {"U_a S U_a", "U_a U_a"}, "U_a": {"a"}})
        self.assertEqual(len(result.productions_for("U_a")), 1)

    def test_reuses_existing_exact_wrapper(self):
        grammar = grammar_from("S -> a S | U_a", "U_a -> a")
        result, trace = isolate_terminals(grammar)
        self.assertEqual(rules(result), {"S": {"U_a S", "U_a"}, "U_a": {"a"}})
        self.assertEqual(trace.tables["Envoltorios"][0]["Acción"], "reutilizado")

    def test_wrapper_collision_creates_fresh_name(self):
        grammar = grammar_from("S -> a S | U_a", "U_a -> b")
        result, trace = isolate_terminals(grammar)
        self.assertEqual(rules(result), {"S": {"U_a_1 S", "U_a"}, "U_a": {"b"}, "U_a_1": {"a"}})
        self.assertEqual(trace.tables["Envoltorios"][0]["Envoltorio"], "U_a_1")

    def test_variables_are_not_wrapped(self):
        grammar = load("english.txt")
        result, _ = isolate_terminals(grammar)
        self.assertIs(result, grammar)

    def test_preserves_language(self):
        grammar = grammar_from("S -> a S b | a b")
        result, _ = isolate_terminals(grammar)
        self.assertEqual(language(result, 8), language(grammar, 8))


if __name__ == "__main__":
    unittest.main()
