import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import cnf_violations
from src.algorithms.simplification.simplify import simplify
from src.model.production import Production
from src.output.trace_formatter import (
    format_cnf_check,
    format_conclusions,
    format_grammar,
    format_table,
    format_trace,
    format_traces,
    format_value,
)
from tests.grammar_helpers import grammar_from, load


class FormatValueTest(unittest.TestCase):
    def test_formats_productions_sets_and_pairs(self):
        self.assertEqual(format_value(Production("A", ("B", "c"))), "A -> B c")
        self.assertEqual(format_value(Production("A")), "A -> ε")
        self.assertEqual(format_value(frozenset({"B", "A"})), "{A, B}")
        self.assertEqual(format_value(frozenset()), "∅")
        self.assertEqual(format_value((("S", "A"), ("S", "B"))), "(S, A), (S, B)")
        self.assertEqual(format_value(()), "—")


class FormatTableTest(unittest.TestCase):
    def test_aligns_columns(self):
        lines = format_table([{"Col": "a", "Otra": "bbb"}, {"Col": "cccc", "Otra": "d"}])
        self.assertEqual(lines[0], "Col  | Otra")
        self.assertEqual(lines[2], "a    | bbb")
        self.assertEqual(lines[3], "cccc | d")

    def test_empty_table(self):
        self.assertEqual(format_table([]), ["(sin filas)"])


class FormatGrammarTest(unittest.TestCase):
    def test_groups_alternatives_with_start_first(self):
        grammar = grammar_from("S -> A b | ε", "A -> a | A a")
        self.assertEqual(format_grammar(grammar), "S -> A b | ε\nA -> a | A a")

    def test_grammar_without_productions(self):
        _, traces = simplify(grammar_from("S -> a S"))
        self.assertEqual(format_grammar(traces[-1].result), "(sin producciones)")


class FormatTraceTest(unittest.TestCase):
    def test_renders_every_phase_of_english(self):
        grammar = load("english.txt")
        simplified, simplification_traces = simplify(grammar)
        _, cnf_traces = to_cnf(simplified)
        text = format_traces(simplification_traces + cnf_traces)
        for expected in (
            "Fase 0",
            "Fase 1",
            "N = ∅ ⇒ G1 = G0",
            "No hay producciones unitarias",
            "Sin símbolos inútiles ⇒ G3 = G2",
            "Ningún terminal acompañado ⇒ G4 = G3",
            "Ningún RHS tiene longitud > 2 ⇒ no aplica",
        ):
            self.assertIn(expected, text)

    def test_renders_tables_and_result(self):
        _, traces = simplify(load("test_corto_p3.txt"))
        text = format_trace(traces[1])
        self.assertIn("Anulables", text)
        self.assertIn("Variantes", text)
        self.assertIn("S -> A B C d | A B d | A C d | B C d | A d | B d | C d | d", text)

    def test_can_hide_tables(self):
        _, traces = simplify(load("test_corto_p3.txt"))
        self.assertNotIn("Variantes", format_trace(traces[1], show_tables=False))

    def test_conclusions_have_one_line_per_phase(self):
        _, traces = simplify(load("test_guia.txt"))
        self.assertEqual(len(format_conclusions(traces).splitlines()), 4)

    def test_cnf_check(self):
        cnf = load("english.txt")
        self.assertEqual(
            format_cnf_check(cnf, cnf_violations(cnf)),
            "✓ Gramática en CNF (validador: 30 producciones válidas)",
        )
        invalid = grammar_from("S -> A", "A -> a")
        self.assertIn("producción unitaria", format_cnf_check(invalid, cnf_violations(invalid)))


if __name__ == "__main__":
    unittest.main()
