import unittest

from src.algorithms.simplification.epsilon import eliminate_epsilon, expand_variants, find_nullable
from src.algorithms.simplification.start_symbol import add_new_start_symbol
from src.model.production import Production
from tests.grammar_helpers import EXPRESSION_GRAMMAR_LINES, grammar_from, language, load, rules


class NullableTest(unittest.TestCase):
    def test_empty_nullable_set(self):
        nullable, rows = find_nullable(load("test_corto_p5.txt"))
        self.assertEqual(nullable, frozenset())
        self.assertEqual(rows[0]["Iteración"], "Base")
        self.assertEqual(rows[0]["Conjunto N"], frozenset())

    def test_direct_nullable(self):
        nullable, rows = find_nullable(grammar_from("S -> A b", "A -> a | ε"))
        self.assertEqual(nullable, {"A"})
        self.assertEqual(rows[0]["Regla aplicada"], Production("A", ()))

    def test_transitive_nullable(self):
        nullable, rows = find_nullable(grammar_from("S -> A B", "A -> B", "B -> C", "C -> ε"))
        self.assertEqual(nullable, {"S", "A", "B", "C"})
        discovered = [(row["Iteración"], row["Nuevo"]) for row in rows if row["Nuevo"] != "—"]
        self.assertEqual(discovered, [("Base", "C"), (1, "B"), (2, "A"), (3, "S")])
        self.assertEqual(rows[-1]["Conjunto N"], {"S", "A", "B", "C"})

    def test_terminal_blocks_nullability(self):
        nullable, _ = find_nullable(grammar_from("S -> A a", "A -> ε"))
        self.assertEqual(nullable, {"A"})

    def test_corto_p3_nullable_set(self):
        nullable, _ = find_nullable(load("test_corto_p3.txt"))
        self.assertEqual(nullable, {"A", "B", "C"})


class VariantTest(unittest.TestCase):
    def test_three_occurrences_generate_eight_cases(self):
        variants = expand_variants(("A", "B", "C", "d"), {"A", "B", "C"})
        self.assertEqual(
            [" ".join(variant) for variant in variants],
            ["A B C d", "A B d", "A C d", "B C d", "A d", "B d", "C d", "d"],
        )

    def test_counts_repeated_occurrences(self):
        variants = expand_variants(("B", "B"), {"B"})
        self.assertEqual(len(variants), 4)
        self.assertEqual(set(variants), {("B", "B"), ("B",), ()})

    def test_never_removes_terminals(self):
        self.assertEqual(expand_variants(("a", "A"), {"A"}), [("a", "A"), ("a",)])


class EliminateEpsilonTest(unittest.TestCase):
    def test_no_nullable_keeps_grammar(self):
        grammar = load("test_corto_p5.txt")
        result, trace = eliminate_epsilon(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.notes, ["N = ∅ ⇒ G1 = G0"])

    def test_corto_p3_result(self):
        result, trace = eliminate_epsilon(load("test_corto_p3.txt"))
        self.assertEqual(
            rules(result),
            {
                "S": {"A B C d", "A B d", "A C d", "B C d", "A d", "B d", "C d", "d"},
                "A": {"B C", "B", "C"},
                "B": {"b B", "b"},
                "C": {"c C", "c"},
            },
        )
        row = trace.tables["Variantes"][0]
        self.assertEqual(row["Producción"], Production("S", ("A", "B", "C", "d")))
        self.assertEqual(row["m"], 3)
        self.assertEqual(row["2^m"], 8)
        self.assertEqual(len(row["Casos conservados"]), 8)

    def test_epsilon_variant_discarded_for_non_start(self):
        _, trace = eliminate_epsilon(load("test_corto_p3.txt"))
        row = next(row for row in trace.tables["Variantes"] if row["Producción"] == Production("A", ("B", "C")))
        self.assertIn(Production("A", ()), row["Casos generados"])
        self.assertNotIn(Production("A", ()), row["Casos conservados"])

    def test_preserves_epsilon_only_from_start(self):
        grammar, _ = add_new_start_symbol(load("test_lab7.txt"))
        result, trace = eliminate_epsilon(grammar)
        epsilon_lhs = {production.lhs for production in result.productions if production.is_epsilon}
        self.assertEqual(epsilon_lhs, {"S0"})
        self.assertTrue(any("S0 ∈ N" in note for note in trace.notes))

    def test_non_nullable_start_loses_all_epsilon(self):
        result, trace = eliminate_epsilon(grammar_from("S -> a A", "A -> b | ε"))
        self.assertFalse(any(production.is_epsilon for production in result.productions))
        self.assertEqual(rules(result), {"S": {"a A", "a"}, "A": {"b"}})
        self.assertTrue(any("S ∉ N" in note for note in trace.notes))

    def test_deduplicates_variants(self):
        result, trace = eliminate_epsilon(grammar_from("S -> a A A", "A -> b | ε"))
        self.assertEqual(rules(result)["S"], {"a A A", "a A", "a"})
        self.assertEqual(len(result.productions_for("S")), 3)
        row = trace.tables["Variantes"][0]
        self.assertEqual(len(row["Casos generados"]), 4)
        self.assertEqual(len(row["Casos conservados"]), 3)

    def test_preserves_language_without_epsilon(self):
        grammar = load("test_corto_p3.txt")
        result, _ = eliminate_epsilon(grammar)
        self.assertEqual(language(result, 6), language(grammar, 6) - {()})


class LiteralETerminalTest(unittest.TestCase):
    def test_literal_e_does_not_make_variables_nullable(self):
        grammar = grammar_from(*EXPRESSION_GRAMMAR_LINES)
        nullable, rows = find_nullable(grammar)
        self.assertEqual(nullable, frozenset())
        self.assertNotIn("X", nullable)
        self.assertNotIn("Y", nullable)
        self.assertEqual(rows[-1]["Conjunto N"], frozenset())

    def test_literal_e_keeps_grammar_unchanged_in_phase_one(self):
        grammar = grammar_from(*EXPRESSION_GRAMMAR_LINES)
        result, trace = eliminate_epsilon(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.notes, ["N = ∅ ⇒ G1 = G0"])

    def test_epsilon_symbol_and_literal_e_stay_distinct(self):
        grammar = grammar_from("S -> A", "A -> ε | e")
        self.assertIn("e", grammar.terminals)
        self.assertNotIn("ε", grammar.terminals)
        self.assertEqual(grammar.productions_for("A"), (Production("A", ()), Production("A", ("e",))))
        nullable, rows = find_nullable(grammar)
        self.assertEqual(nullable, {"A", "S"})
        base_rows = [row for row in rows if row["Iteración"] == "Base"]
        self.assertEqual([(row["Nuevo"], row["Regla aplicada"]) for row in base_rows], [("A", Production("A", ()))])


if __name__ == "__main__":
    unittest.main()
