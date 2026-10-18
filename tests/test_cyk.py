import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import is_cnf
from src.algorithms.cyk.parser import recognize_cyk
from src.algorithms.cyk.table import build_cyk_table, build_production_indexes
from src.algorithms.simplification.simplify import simplify
from src.input.sentence_parser import parse_sentence
from src.model.backpointer import BinaryBackPointer, TerminalBackPointer
from src.model.grammar import Grammar
from src.model.production import Production
from tests.grammar_helpers import PROJECT_GRAMMARS, grammar_from, load


def cnf_of(file_name):
    simplified, _ = simplify(load(file_name))
    cnf, _ = to_cnf(simplified)
    return cnf


ENGLISH = cnf_of("english.txt")


def recognize_sentence(grammar, sentence):
    return recognize_cyk(grammar, parse_sentence(sentence))


class ProductionIndexesTest(unittest.TestCase):
    def test_terminal_index_for_english(self):
        terminal_index, _ = build_production_indexes(ENGLISH)
        self.assertEqual(terminal_index["she"], ("NP",))
        self.assertEqual(terminal_index["he"], ("NP",))
        self.assertEqual(terminal_index["a"], ("Det",))
        self.assertEqual(terminal_index["the"], ("Det",))

    def test_terminal_index_keeps_every_producer(self):
        terminal_index, _ = build_production_indexes(ENGLISH)
        for verb in ("eats", "drinks", "cooks", "cuts"):
            with self.subTest(verb=verb):
                self.assertEqual(set(terminal_index[verb]), {"VP", "V"})

    def test_binary_index_for_english(self):
        _, binary_index = build_production_indexes(ENGLISH)
        self.assertEqual(binary_index[("NP", "VP")], ("S",))
        self.assertEqual(binary_index[("VP", "PP")], ("VP",))
        self.assertEqual(binary_index[("V", "NP")], ("VP",))
        self.assertEqual(binary_index[("P", "NP")], ("PP",))
        self.assertEqual(binary_index[("Det", "N")], ("NP",))

    def test_epsilon_production_is_not_indexed(self):
        grammar = grammar_from("S -> ε | A A", "A -> a")
        terminal_index, binary_index = build_production_indexes(grammar)
        self.assertEqual(terminal_index, {"a": ("A",)})
        self.assertEqual(binary_index, {("A", "A"): ("S",)})
        self.assertNotIn("ε", terminal_index)
        self.assertNotIn((), binary_index)

    def test_indexes_are_deterministic(self):
        self.assertEqual(build_production_indexes(ENGLISH), build_production_indexes(ENGLISH))

    def test_every_project_grammar_builds_indexes(self):
        for file_name in PROJECT_GRAMMARS:
            with self.subTest(file_name=file_name):
                cnf = cnf_of(file_name)
                self.assertTrue(is_cnf(cnf))
                terminal_index, _ = build_production_indexes(cnf)
                self.assertTrue(terminal_index)


class CykTableTest(unittest.TestCase):
    def test_table_is_n_by_n(self):
        table = build_cyk_table(ENGLISH, ["she", "eats", "a", "cake"])
        self.assertEqual(len(table), 4)
        self.assertTrue(all(len(row) == 4 for row in table))

    def test_cells_are_independent_dictionaries(self):
        table = build_cyk_table(ENGLISH, ["she", "eats", "a"])
        cells = [cell for row in table for cell in row]
        self.assertEqual(len({id(cell) for cell in cells}), len(cells))

    def test_cells_map_variables_to_backpointers(self):
        table = build_cyk_table(ENGLISH, ["she", "eats"])
        self.assertEqual(
            table[0][1], {"S": BinaryBackPointer(Production("S", ("NP", "VP")), 0, "NP", "VP")}
        )
        self.assertEqual(
            table[1][1], {"VP": TerminalBackPointer("eats"), "V": TerminalBackPointer("eats")}
        )

    def test_diagonal_keeps_every_terminal_producer(self):
        table = build_cyk_table(grammar_from("S -> A B", "A -> a", "B -> a"), ["a"])
        self.assertEqual(set(table[0][0]), {"A", "B"})

    def test_span_keeps_every_binary_parent(self):
        grammar = grammar_from("S -> A C", "A -> B C", "D -> B C", "B -> b", "C -> c")
        table = build_cyk_table(grammar, ["b", "c"])
        self.assertEqual(set(table[0][1]), {"A", "D"})

    def test_only_contiguous_spans_are_combined(self):
        grammar = grammar_from("S -> A C", "A -> a", "B -> b", "C -> c")
        accepted, table = recognize_cyk(grammar, ["a", "b", "c"])
        self.assertFalse(accepted)
        self.assertEqual(table[0][2], {})

    def test_explores_first_split(self):
        grammar = grammar_from("S -> A X", "X -> B C", "A -> a", "B -> b", "C -> c")
        accepted, table = recognize_cyk(grammar, ["a", "b", "c"])
        self.assertTrue(accepted)
        self.assertEqual(table[0][1], {})
        self.assertIn("X", table[1][2])

    def test_explores_last_split(self):
        grammar = grammar_from("S -> Y C", "Y -> A B", "A -> a", "B -> b", "C -> c")
        accepted, table = recognize_cyk(grammar, ["a", "b", "c"])
        self.assertTrue(accepted)
        self.assertEqual(table[1][2], {})
        self.assertIn("Y", table[0][1])

    def test_explores_middle_split(self):
        grammar = grammar_from(
            "S -> P Q", "P -> A B", "Q -> C D", "A -> a", "B -> b", "C -> c", "D -> d"
        )
        accepted, table = recognize_cyk(grammar, ["a", "b", "c", "d"])
        self.assertTrue(accepted)
        self.assertEqual(table[0][2], {})
        self.assertEqual(table[1][3], {})


class RecognizeCykTest(unittest.TestCase):
    def test_single_word_accepted(self):
        accepted, table = recognize_cyk(grammar_from("S -> a"), ["a"])
        self.assertTrue(accepted)
        self.assertIn("S", table[0][0])

    def test_single_word_with_non_start_cell_rejected(self):
        accepted, table = recognize_cyk(grammar_from("S -> a | A A", "A -> b"), ["b"])
        self.assertFalse(accepted)
        self.assertIn("A", table[0][0])
        self.assertNotIn("S", table[0][0])

    def test_non_empty_final_cell_without_start_is_rejected(self):
        grammar = grammar_from("S -> A B", "C -> A A", "A -> a", "B -> b")
        accepted, table = recognize_cyk(grammar, ["a", "a"])
        self.assertEqual(set(table[0][1]), {"C"})
        self.assertFalse(accepted)

    def test_empty_sentence_with_start_epsilon(self):
        self.assertEqual(recognize_cyk(grammar_from("S -> ε"), []), (True, []))

    def test_empty_sentence_without_epsilon(self):
        self.assertEqual(recognize_cyk(grammar_from("S -> a"), []), (False, []))

    def test_empty_sentence_uses_project_cnf_epsilon(self):
        self.assertEqual(recognize_cyk(cnf_of("test_lab7.txt"), []), (True, []))
        self.assertEqual(recognize_cyk(ENGLISH, []), (False, []))

    def test_empty_language(self):
        grammar = Grammar("S", {"S"}, {"a"}, [])
        self.assertTrue(is_cnf(grammar))
        self.assertEqual(recognize_cyk(grammar, []), (False, []))
        self.assertEqual(recognize_cyk(grammar, ["a"]), (False, [[{}]]))

    def test_rejects_non_cnf_grammar(self):
        with self.assertRaises(ValueError):
            recognize_cyk(grammar_from("S -> A", "A -> a"), ["a"])

    def test_unknown_token_keeps_its_position(self):
        accepted, table = recognize_sentence(ENGLISH, "she likes cake")
        self.assertFalse(accepted)
        self.assertEqual(len(table), 3)
        self.assertEqual(table[1][1], {})
        self.assertEqual(table[0][0], {"NP": TerminalBackPointer("she")})

    def test_residual_terminal_without_production_is_not_vocabulary(self):
        cnf = cnf_of("test_corto_p5.txt")
        terminal_index, _ = build_production_indexes(cnf)
        residual = cnf.terminals - set(terminal_index)
        self.assertEqual(residual, {"b"})
        accepted, table = recognize_cyk(cnf, ["b"])
        self.assertFalse(accepted)
        self.assertEqual(table[0][0], {})

    def test_does_not_mutate_tokens_or_grammar(self):
        tokens = ["she", "eats", "a", "cake"]
        tokens_before = list(tokens)
        snapshot = (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions)
        recognize_cyk(ENGLISH, tokens)
        self.assertEqual(tokens, tokens_before)
        self.assertEqual(
            (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions), snapshot
        )

    def test_is_deterministic(self):
        tokens = parse_sentence("she eats a cake with a fork")
        self.assertEqual(recognize_cyk(ENGLISH, tokens), recognize_cyk(ENGLISH, tokens))

    def test_long_rules_grammar(self):
        cnf = cnf_of("test_long_rules.txt")
        self.assertTrue(recognize_cyk(cnf, ["a", "b", "c", "d"])[0])
        self.assertFalse(recognize_cyk(cnf, ["a", "b", "c"])[0])
        self.assertFalse(recognize_cyk(cnf, ["a", "b", "d", "c"])[0])


class OfficialSentencesTest(unittest.TestCase):
    def test_accepted_sentences(self):
        for sentence in (
            "she eats a cake",
            "she eats a cake with a fork",
            "the cat drinks the beer",
            "he cuts the meat with a knife",
            "She eats a cake with a fork.",
        ):
            with self.subTest(sentence=sentence):
                self.assertTrue(recognize_sentence(ENGLISH, sentence)[0])

    def test_rejected_sentences(self):
        for sentence in ("cat the drinks beer", "she likes cake", "a dog the beer", "eats"):
            with self.subTest(sentence=sentence):
                self.assertFalse(recognize_sentence(ENGLISH, sentence)[0])


if __name__ == "__main__":
    unittest.main()
