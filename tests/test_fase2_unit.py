import unittest

from src.algorithms.simplification.unit import eliminate_unit, is_unit
from src.model.production import Production
from tests.grammar_helpers import grammar_from, language, load, rules


def pairs(trace):
    return {row["Origen"]: set(row["Alcanza (solo unitarias)"]) for row in trace.tables["Pares unitarios"]}


class UnitDetectionTest(unittest.TestCase):
    def test_only_single_variable_rhs_is_unit(self):
        variables = {"X", "Y", "Z"}
        self.assertTrue(is_unit(Production("X", ("Y",)), variables))
        self.assertFalse(is_unit(Production("X", ("a",)), variables))
        self.assertFalse(is_unit(Production("X", ("Y", "Z")), variables))
        self.assertFalse(is_unit(Production("X", ("a", "Y")), variables))
        self.assertFalse(is_unit(Production("X", ()), variables))


class EliminateUnitTest(unittest.TestCase):
    def test_no_unit_productions_keeps_grammar(self):
        grammar = load("english.txt")
        result, trace = eliminate_unit(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.tables["Unitarias"], [])
        self.assertIn("No hay producciones unitarias", trace.notes[-1])

    def test_unit_chain(self):
        result, trace = eliminate_unit(grammar_from("S -> A", "A -> B", "B -> b"))
        self.assertEqual(pairs(trace)["S"], {"S", "A", "B"})
        self.assertEqual(rules(result), {"S": {"b"}, "A": {"b"}, "B": {"b"}})

    def test_cycle_corto_p4(self):
        result, trace = eliminate_unit(load("test_corto_p4.txt"))
        self.assertEqual(pairs(trace), {"S": {"S", "A", "B"}, "A": {"A", "B"}, "B": {"B", "A"}})
        self.assertEqual(
            rules(result),
            {"S": {"A a", "a", "b"}, "A": {"a", "b"}, "B": {"a", "b"}},
        )

    def test_reflexive_pair_always_present(self):
        _, trace = eliminate_unit(grammar_from("S -> A | s", "A -> a", "B -> b"))
        for variable, reached in pairs(trace).items():
            self.assertIn(variable, reached)
        row = next(row for row in trace.tables["Pares unitarios"] if row["Origen"] == "B")
        self.assertEqual(row["Pares"], (("B", "B"),))

    def test_transfers_all_non_unit_productions(self):
        grammar = grammar_from("S -> A | s", "A -> B | a A | a", "B -> b B | b")
        result, trace = eliminate_unit(grammar)
        self.assertEqual(
            rules(result),
            {"S": {"s", "a A", "a", "b B", "b"}, "A": {"a A", "a", "b B", "b"}, "B": {"b B", "b"}},
        )
        transfers = {(row["Variable"], row["Par"]) for row in trace.tables["Transferencias"]}
        self.assertEqual(transfers, {("S", "(S, A)"), ("S", "(S, B)"), ("A", "(A, B)")})
        self.assertFalse(any(is_unit(production, result.variables) for production in result.productions))

    def test_keeps_variables_even_if_now_unreachable(self):
        result, _ = eliminate_unit(load("test_corto_p5.txt"))
        self.assertEqual(result.variables, {"S", "A", "B", "C"})

    def test_preserves_language(self):
        grammar = load("test_corto_p4.txt")
        result, _ = eliminate_unit(grammar)
        self.assertEqual(language(result, 5), language(grammar, 5))


if __name__ == "__main__":
    unittest.main()
