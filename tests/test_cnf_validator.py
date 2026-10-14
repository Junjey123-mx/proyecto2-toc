import unittest

from src.algorithms.chomsky.validator import cnf_violations, is_cnf
from tests.grammar_helpers import grammar_from


class CnfValidatorTest(unittest.TestCase):
    def test_accepts_binary_variables(self):
        self.assertTrue(is_cnf(grammar_from("S -> A B", "A -> a", "B -> b")))

    def test_accepts_single_terminal(self):
        self.assertTrue(is_cnf(grammar_from("S -> a")))

    def test_accepts_epsilon_from_start_outside_rhs(self):
        self.assertTrue(is_cnf(grammar_from("S0 -> ε | A A", "A -> a")))

    def test_rejects_epsilon_from_start_in_rhs(self):
        self.assertFalse(is_cnf(grammar_from("S -> ε | A S", "A -> a")))

    def test_rejects_epsilon_outside_start(self):
        grammar = grammar_from("S -> A A", "A -> a | ε")
        self.assertFalse(is_cnf(grammar))
        self.assertEqual(cnf_violations(grammar)[0][1], "producción-ε fuera del símbolo inicial")

    def test_rejects_unit_production(self):
        self.assertFalse(is_cnf(grammar_from("S -> A", "A -> a")))

    def test_rejects_mixed_terminal_and_variable(self):
        self.assertFalse(is_cnf(grammar_from("S -> a A", "A -> a")))

    def test_rejects_rhs_longer_than_two(self):
        self.assertFalse(is_cnf(grammar_from("S -> A A A", "A -> a")))

    def test_rejects_two_terminals(self):
        self.assertFalse(is_cnf(grammar_from("S -> a b")))

    def test_violations_list_every_invalid_production(self):
        grammar = grammar_from("S -> A | A A A | a", "A -> a")
        self.assertEqual(len(cnf_violations(grammar)), 2)


if __name__ == "__main__":
    unittest.main()
