import os
import subprocess
import sys
import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import is_cnf
from src.algorithms.simplification.simplify import simplify
from tests.grammar_helpers import PROJECT_GRAMMARS, grammar_from, language, load, rules

LANGUAGE_BOUNDS = {"english.txt": 5}
DEFAULT_LANGUAGE_BOUND = 7


def pipeline(grammar):
    simplified, simplification_traces = simplify(grammar)
    cnf, cnf_traces = to_cnf(simplified)
    return simplified, cnf, simplification_traces + cnf_traces


class PipelineTest(unittest.TestCase):
    def test_every_project_grammar_reaches_cnf(self):
        for file_name in PROJECT_GRAMMARS:
            with self.subTest(file_name=file_name):
                _, cnf, traces = pipeline(load(file_name))
                self.assertTrue(is_cnf(cnf))
                self.assertEqual(len(traces), 6)

    def test_every_project_grammar_preserves_language(self):
        for file_name in PROJECT_GRAMMARS:
            with self.subTest(file_name=file_name):
                grammar = load(file_name)
                _, cnf, _ = pipeline(grammar)
                bound = LANGUAGE_BOUNDS.get(file_name, DEFAULT_LANGUAGE_BOUND)
                self.assertEqual(language(cnf, bound), language(grammar, bound))

    def test_traces_follow_phase_order(self):
        _, _, traces = pipeline(load("test_guia.txt"))
        self.assertEqual([trace.phase.split(":")[0] for trace in traces], [f"Fase {index}" for index in range(6)])

    def test_english_is_unchanged(self):
        grammar = load("english.txt")
        _, cnf, traces = pipeline(grammar)
        self.assertEqual(cnf.productions, grammar.productions)
        self.assertEqual(cnf.variables, grammar.variables)
        self.assertEqual(cnf.terminals, grammar.terminals)
        self.assertEqual(cnf.start_symbol, "S")
        self.assertEqual([trace.result for trace in traces], [grammar] * 6)
        self.assertTrue(all(trace.notes for trace in traces))

    def test_guia_cnf(self):
        _, cnf, _ = pipeline(load("test_guia.txt"))
        table = rules(cnf)
        self.assertEqual(cnf.start_symbol, "S0")
        self.assertEqual(table["S0"], {"ε", "U_a X1", "U_a U_b", "U_a A", "a"})
        self.assertEqual(table["X1"], {"S U_b"})
        self.assertEqual(table["U_a"], {"a"})
        self.assertEqual(table["U_b"], {"b"})

    def test_practica_cnf(self):
        _, cnf, _ = pipeline(load("test_practica.txt"))
        table = rules(cnf)
        self.assertEqual(table["S0"], {"A X1", "S U_b", "B U_c", "c"})
        self.assertEqual(table["X1"], {"S U_b"})
        self.assertEqual(table["A"], {"U_a A", "a"})
        self.assertEqual(table["B"], {"b"})
        self.assertNotIn("C", cnf.variables)
        self.assertNotIn("D", cnf.variables)

    def test_corto_p5_cnf(self):
        _, cnf, _ = pipeline(load("test_corto_p5.txt"))
        self.assertEqual(rules(cnf), {"S0": {"U_a S", "a"}, "S": {"U_a S", "a"}, "U_a": {"a"}})

    def test_long_rules_cnf(self):
        _, cnf, _ = pipeline(load("test_long_rules.txt"))
        table = rules(cnf)
        self.assertEqual(table["S"], {"A X1"})
        self.assertEqual(table["X1"], {"B X2"})
        self.assertEqual(table["X2"], {"C D"})

    def test_lab7_start_keeps_epsilon(self):
        _, cnf, _ = pipeline(load("test_lab7.txt"))
        self.assertIn("ε", rules(cnf)["S0"])
        self.assertTrue(all(cnf.start_symbol not in production.rhs for production in cnf.productions))

    def test_empty_language_still_valid_cnf(self):
        _, cnf, traces = pipeline(grammar_from("S -> a S"))
        self.assertTrue(is_cnf(cnf))
        self.assertEqual(cnf.productions, ())
        self.assertTrue(any("L(G) = ∅" in note for note in traces[3].notes))

    def test_input_grammar_is_not_mutated(self):
        grammar = load("test_lab7.txt")
        snapshot = (grammar.start_symbol, grammar.variables, grammar.terminals, grammar.productions)
        pipeline(grammar)
        self.assertEqual((grammar.start_symbol, grammar.variables, grammar.terminals, grammar.productions), snapshot)

    def test_result_is_deterministic_across_hash_seeds(self):
        script = (
            "from src.algorithms.simplification.simplify import simplify;"
            "from src.algorithms.chomsky.converter import to_cnf;"
            "from tests.grammar_helpers import PROJECT_GRAMMARS, load;"
            "print([to_cnf(simplify(load(name))[0])[0].productions for name in PROJECT_GRAMMARS])"
        )
        outputs = set()
        for seed in ("1", "2", "3"):
            environment = {**os.environ, "PYTHONHASHSEED": seed}
            completed = subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True, env=environment, check=True
            )
            outputs.add(completed.stdout)
        self.assertEqual(len(outputs), 1)


if __name__ == "__main__":
    unittest.main()
