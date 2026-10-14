import subprocess
import sys
import unittest
from dataclasses import FrozenInstanceError, replace

from src.model.grammar import Grammar
from src.model.production import Production
from src.model.trace import Trace


def build_sample_grammar():
    return Grammar(
        start_symbol="S",
        variables={"S", "A"},
        terminals={"a", "b"},
        productions=[
            Production("S", ("A", "b")),
            Production("A", ("a",)),
            Production("A", ()),
        ],
    )


class ProductionTest(unittest.TestCase):
    def test_equal_when_lhs_and_rhs_match(self):
        self.assertEqual(Production("A", ("B", "C")), Production("A", ("B", "C")))

    def test_rhs_sequence_type_does_not_affect_equality(self):
        self.assertEqual(Production("A", ["B", "C"]), Production("A", ("B", "C")))

    def test_not_equal_when_lhs_differs(self):
        self.assertNotEqual(Production("A", ("a",)), Production("B", ("a",)))

    def test_not_equal_when_rhs_differs(self):
        self.assertNotEqual(Production("A", ("a",)), Production("A", ("b",)))

    def test_rhs_order_is_preserved_and_significant(self):
        production = Production("A", ("B", "C", "d"))
        self.assertEqual(production.rhs, ("B", "C", "d"))
        self.assertNotEqual(production, Production("A", ("C", "B", "d")))

    def test_epsilon_is_empty_rhs(self):
        epsilon = Production("A", ())
        self.assertEqual(epsilon.rhs, ())
        self.assertTrue(epsilon.is_epsilon)
        self.assertEqual(epsilon, Production("A"))

    def test_non_empty_rhs_is_not_epsilon(self):
        self.assertFalse(Production("A", ("a",)).is_epsilon)

    def test_duplicates_collapse_in_set(self):
        productions = {
            Production("A", ("B", "C")),
            Production("A", ("B", "C")),
            Production("A", ()),
            Production("A", ()),
        }
        self.assertEqual(len(productions), 2)

    def test_is_immutable(self):
        production = Production("A", ("a",))
        with self.assertRaises(FrozenInstanceError):
            production.lhs = "B"


class GrammarTest(unittest.TestCase):
    def test_exposes_components(self):
        grammar = build_sample_grammar()
        self.assertEqual(grammar.start_symbol, "S")
        self.assertEqual(grammar.variables, {"S", "A"})
        self.assertEqual(grammar.terminals, {"a", "b"})
        self.assertEqual(len(grammar.productions), 3)
        self.assertTrue(all(isinstance(p, Production) for p in grammar.productions))

    def test_start_symbol_is_variable(self):
        grammar = build_sample_grammar()
        self.assertIn(grammar.start_symbol, grammar.variables)

    def test_variables_and_terminals_are_disjoint(self):
        grammar = build_sample_grammar()
        self.assertTrue(grammar.variables.isdisjoint(grammar.terminals))

    def test_symbol_sets_are_immutable(self):
        grammar = build_sample_grammar()
        self.assertIsInstance(grammar.variables, frozenset)
        self.assertIsInstance(grammar.terminals, frozenset)
        self.assertIsInstance(grammar.productions, tuple)

    def test_duplicate_productions_are_removed(self):
        grammar = Grammar("S", {"S"}, {"a"}, [Production("S", ("a",))] * 3)
        self.assertEqual(grammar.productions, (Production("S", ("a",)),))

    def test_production_order_is_insertion_order(self):
        productions = [
            Production("S", ("A", "b")),
            Production("A", ()),
            Production("S", ("b",)),
            Production("A", ("a",)),
            Production("A", ()),
        ]
        grammar = Grammar("S", {"S", "A"}, {"a", "b"}, productions)
        self.assertEqual(grammar.productions, tuple(productions[:4]))

    def test_productions_for_variable_keep_order(self):
        grammar = build_sample_grammar()
        self.assertEqual(
            grammar.productions_for("A"),
            (Production("A", ("a",)), Production("A", ())),
        )
        self.assertEqual(grammar.productions_for("S"), (Production("S", ("A", "b")),))

    def test_equal_grammars_compare_and_hash_equal(self):
        self.assertEqual(build_sample_grammar(), build_sample_grammar())
        self.assertEqual(hash(build_sample_grammar()), hash(build_sample_grammar()))

    def test_replace_builds_new_validated_grammar(self):
        grammar = build_sample_grammar()
        rebuilt = replace(grammar, productions=grammar.productions[:1])
        self.assertEqual(rebuilt.productions, (Production("S", ("A", "b")),))
        self.assertEqual(len(grammar.productions), 3)
        with self.assertRaises(ValueError):
            replace(grammar, start_symbol="Z")

    def test_rejects_start_symbol_outside_variables(self):
        with self.assertRaises(ValueError):
            Grammar("X", {"S"}, {"a"}, [Production("S", ("a",))])

    def test_rejects_overlapping_variables_and_terminals(self):
        with self.assertRaises(ValueError):
            Grammar("S", {"S", "a"}, {"a"}, [Production("S", ("a",))])

    def test_rejects_production_with_unknown_lhs(self):
        with self.assertRaises(ValueError):
            Grammar("S", {"S"}, {"a"}, [Production("B", ("a",))])

    def test_rejects_production_with_undeclared_rhs_symbol(self):
        with self.assertRaises(ValueError):
            Grammar("S", {"S"}, {"a"}, [Production("S", ("z",))])

    def test_rejects_non_production_items(self):
        with self.assertRaises(TypeError):
            Grammar("S", {"S"}, {"a"}, [("S", ("a",))])


class TraceTest(unittest.TestCase):
    def test_keeps_phase_tables_notes_and_result(self):
        grammar = build_sample_grammar()
        tables = {
            "nullable": [{"iteration": 1, "variables": ["A"]}],
            "unit_pairs": [("S", "S"), ("A", "A")],
        }
        notes = ["N = ∅ ⇒ G1 = G0"]
        trace = Trace(phase="epsilon", result=grammar, tables=tables, notes=notes)
        self.assertEqual(trace.phase, "epsilon")
        self.assertEqual(trace.tables, tables)
        self.assertEqual(trace.notes, notes)
        self.assertIs(trace.result, grammar)

    def test_defaults_to_empty_tables_and_notes(self):
        first = Trace("unit", build_sample_grammar())
        second = Trace("unit", build_sample_grammar())
        first.notes.append("changed")
        first.tables["pairs"] = []
        self.assertEqual(second.notes, [])
        self.assertEqual(second.tables, {})

    def test_does_not_depend_on_output_modules(self):
        check = (
            "import sys, src.model.trace; "
            "sys.exit(any(name.startswith('src.output') for name in sys.modules))"
        )
        completed = subprocess.run([sys.executable, "-c", check])
        self.assertEqual(completed.returncode, 0)


if __name__ == "__main__":
    unittest.main()
