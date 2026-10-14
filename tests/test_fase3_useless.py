import unittest

from src.algorithms.simplification.epsilon import eliminate_epsilon
from src.algorithms.simplification.start_symbol import add_new_start_symbol
from src.algorithms.simplification.unit import eliminate_unit
from src.algorithms.simplification.useless import eliminate_useless, find_generating, find_reachable
from tests.grammar_helpers import grammar_from, language, load, rules


def prepared(file_name):
    grammar = load(file_name)
    for phase in (add_new_start_symbol, eliminate_epsilon, eliminate_unit):
        grammar, _ = phase(grammar)
    return grammar


def removed_symbols(trace, table):
    return [row["Símbolo"] for row in trace.tables[table]]


class GeneratingTest(unittest.TestCase):
    def test_generating_fixed_point(self):
        generating, rows = find_generating(grammar_from("S -> A B | a", "A -> a", "B -> B b"))
        self.assertEqual(generating, {"S", "A"})
        self.assertEqual(rows[-1]["Conjunto acumulado"], {"S", "A"})

    def test_epsilon_counts_as_generating(self):
        generating, _ = find_generating(grammar_from("S -> A", "A -> ε"))
        self.assertEqual(generating, {"S", "A"})


class ReachableTest(unittest.TestCase):
    def test_reachable_fixed_point(self):
        reachable, rows = find_reachable(grammar_from("S -> A", "A -> B", "B -> b", "C -> c"))
        self.assertEqual(reachable, {"S", "A", "B"})
        self.assertEqual(rows[0]["Iteración"], "Base")
        self.assertEqual([row["Nuevos"] for row in rows[1:-1]], ["A", "B"])


class EliminateUselessTest(unittest.TestCase):
    def test_removes_non_generating(self):
        result, trace = eliminate_useless(grammar_from("S -> a | A", "A -> a A"))
        self.assertEqual(rules(result), {"S": {"a"}})
        self.assertEqual(removed_symbols(trace, "3a Símbolos eliminados"), ["A"])
        self.assertEqual(len(trace.tables["3a Producciones eliminadas"]), 2)

    def test_removes_unreachable(self):
        result, trace = eliminate_useless(grammar_from("S -> a", "B -> b"))
        self.assertEqual(rules(result), {"S": {"a"}})
        self.assertEqual(removed_symbols(trace, "3b Símbolos eliminados"), ["B"])

    def test_new_unreachable_after_removing_non_generating(self):
        grammar = grammar_from("S -> a | A B", "A -> a", "B -> b B")
        result, trace = eliminate_useless(grammar)
        self.assertEqual(removed_symbols(trace, "3a Símbolos eliminados"), ["B"])
        self.assertEqual(removed_symbols(trace, "3b Símbolos eliminados"), ["A"])
        self.assertEqual(rules(result), {"S": {"a"}})

    def test_practica_removes_c_then_d(self):
        result, trace = eliminate_useless(prepared("test_practica.txt"))
        self.assertEqual(removed_symbols(trace, "3a Símbolos eliminados"), ["C"])
        self.assertEqual(removed_symbols(trace, "3b Símbolos eliminados"), ["D"])
        self.assertEqual(result.variables, {"S0", "S", "A", "B"})

    def test_empty_language(self):
        grammar = grammar_from("S -> a S | A", "A -> b A")
        result, trace = eliminate_useless(grammar)
        self.assertEqual(result.start_symbol, "S")
        self.assertEqual(result.variables, {"S"})
        self.assertEqual(result.productions, ())
        self.assertTrue(any("L(G) = ∅" in note for note in trace.notes))

    def test_no_useless_symbols_keeps_grammar(self):
        grammar = load("english.txt")
        result, trace = eliminate_useless(grammar)
        self.assertIs(result, grammar)
        self.assertEqual(trace.notes[-1], "Sin símbolos inútiles ⇒ G3 = G2")

    def test_keeps_terminal_alphabet(self):
        grammar = prepared("test_guia.txt")
        result, _ = eliminate_useless(grammar)
        self.assertEqual(result.terminals, grammar.terminals)

    def test_lab7_g3(self):
        result, trace = eliminate_useless(prepared("test_lab7.txt"))
        body = {"0 A 0", "0 0", "1 B 1", "1 1", "B B"}
        self.assertEqual(rules(result), {"S0": body | {"ε"}, "A": body, "B": body})
        self.assertEqual(set(removed_symbols(trace, "3b Símbolos eliminados")), {"S", "C"})

    def test_preserves_language(self):
        grammar = prepared("test_guia.txt")
        result, _ = eliminate_useless(grammar)
        self.assertEqual(language(result, 6), language(grammar, 6))


if __name__ == "__main__":
    unittest.main()
