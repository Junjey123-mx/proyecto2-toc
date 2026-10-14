import unittest

from src.algorithms.chomsky.binarize import binarize
from src.model.production import Production
from tests.grammar_helpers import grammar_from, language, load, rules


class BinarizeTest(unittest.TestCase):
    def test_length_two_is_unchanged(self):
        grammar = grammar_from("S -> A B", "A -> a", "B -> b")
        result, trace = binarize(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.notes, ["Ningún RHS tiene longitud > 2 ⇒ no aplica"])

    def test_length_three(self):
        result, trace = binarize(grammar_from("S -> A B C", "A -> a", "B -> b", "C -> c"))
        self.assertEqual(rules(result)["S"], {"A X1"})
        self.assertEqual(rules(result)["X1"], {"B C"})
        self.assertEqual(trace.tables["Binarización"][0]["Variables auxiliares"], ("X1",))

    def test_long_rules_fixture(self):
        result, trace = binarize(load("test_long_rules.txt"))
        self.assertEqual(
            result.productions[:3],
            (
                Production("S", ("A", "X1")),
                Production("X1", ("B", "X2")),
                Production("X2", ("C", "D")),
            ),
        )
        row = trace.tables["Binarización"][0]
        self.assertEqual(row["Producción original"], Production("S", ("A", "B", "C", "D")))
        self.assertEqual(row["Variables auxiliares"], ("X1", "X2"))

    def test_creates_k_minus_two_variables(self):
        result, _ = binarize(grammar_from("S -> A A A A A A", "A -> a"))
        self.assertEqual(result.variables - {"S", "A"}, {"X1", "X2", "X3", "X4"})
        self.assertTrue(all(len(production.rhs) <= 2 for production in result.productions))

    def test_avoids_existing_auxiliary_names(self):
        grammar = grammar_from("S -> A B C D | X1 X2", "A -> a", "B -> b", "C -> c", "D -> d", "X1 -> x", "X2 -> y")
        result, trace = binarize(grammar)
        self.assertEqual(rules(result)["S"], {"A X3", "X1 X2"})
        self.assertEqual(rules(result)["X3"], {"B X4"})
        self.assertEqual(rules(result)["X4"], {"C D"})
        self.assertEqual(rules(result)["X1"], {"x"})
        self.assertTrue(any("Ya existían X1, X2" in note for note in trace.notes))

    def test_preserves_language(self):
        grammar = grammar_from("S -> A S B C | A B C", "A -> a", "B -> b", "C -> c")
        result, _ = binarize(grammar)
        self.assertEqual(language(result, 9), language(grammar, 9))


if __name__ == "__main__":
    unittest.main()
