import copy
import unittest
from dataclasses import FrozenInstanceError

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.cyk.parser import recognize_cyk
from src.algorithms.cyk.reconstruction import reconstruct_parse_tree
from src.algorithms.simplification.simplify import simplify
from src.input.sentence_parser import parse_sentence
from src.model.backpointer import BinaryBackPointer, TerminalBackPointer
from src.model.parse_node import ParseNode
from src.model.production import Production
from tests.grammar_helpers import grammar_from, load


def cnf_of(file_name):
    simplified, _ = simplify(load(file_name))
    cnf, _ = to_cnf(simplified)
    return cnf


ENGLISH = cnf_of("english.txt")
BINARY_GRAMMAR = grammar_from("S -> A B", "A -> a", "B -> b")


def leaves(node):
    if not node.children:
        return [node.token]
    return [token for child in node.children for token in leaves(child)]


def symbols(node):
    return [node.symbol] + [symbol for child in node.children for symbol in symbols(child)]


def parse(grammar, tokens):
    accepted, table = recognize_cyk(grammar, tokens)
    return accepted, table, reconstruct_parse_tree(grammar, table, tokens)


class BackPointerModelTest(unittest.TestCase):
    def test_terminal_pointer_keeps_token(self):
        self.assertEqual(TerminalBackPointer("she").token, "she")

    def test_terminal_pointer_equality(self):
        self.assertEqual(TerminalBackPointer("a"), TerminalBackPointer("a"))
        self.assertNotEqual(TerminalBackPointer("a"), TerminalBackPointer("b"))

    def test_terminal_pointer_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            TerminalBackPointer("a").token = "b"

    def test_binary_pointer_keeps_fields(self):
        production = Production("S", ("NP", "VP"))
        pointer = BinaryBackPointer(production, 2, "NP", "VP")
        self.assertIs(pointer.production, production)
        self.assertEqual(pointer.split, 2)
        self.assertEqual(pointer.left_symbol, "NP")
        self.assertEqual(pointer.right_symbol, "VP")

    def test_binary_pointer_equality(self):
        production = Production("S", ("A", "B"))
        self.assertEqual(BinaryBackPointer(production, 0, "A", "B"), BinaryBackPointer(production, 0, "A", "B"))
        self.assertNotEqual(BinaryBackPointer(production, 0, "A", "B"), BinaryBackPointer(production, 1, "A", "B"))

    def test_binary_pointer_is_immutable(self):
        pointer = BinaryBackPointer(Production("S", ("A", "B")), 0, "A", "B")
        with self.assertRaises(FrozenInstanceError):
            pointer.split = 1


class ParseNodeModelTest(unittest.TestCase):
    def test_leaf_node(self):
        node = ParseNode("A", "a")
        self.assertEqual((node.symbol, node.token, node.children), ("A", "a", ()))

    def test_binary_node(self):
        left, right = ParseNode("A", "a"), ParseNode("B", "b")
        node = ParseNode("S", None, (left, right))
        self.assertIsNone(node.token)
        self.assertEqual(node.children, (left, right))

    def test_equality(self):
        self.assertEqual(
            ParseNode("S", None, (ParseNode("A", "a"),)), ParseNode("S", None, (ParseNode("A", "a"),))
        )
        self.assertNotEqual(ParseNode("A", "a"), ParseNode("A", "b"))

    def test_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            ParseNode("A", "a").symbol = "B"


class TableBackPointerTest(unittest.TestCase):
    def test_diagonal_stores_terminal_pointer(self):
        _, table = recognize_cyk(grammar_from("S -> a"), ["a"])
        pointer = table[0][0]["S"]
        self.assertIsInstance(pointer, TerminalBackPointer)
        self.assertEqual(pointer.token, "a")

    def test_span_stores_binary_pointer(self):
        _, table = recognize_cyk(BINARY_GRAMMAR, ["a", "b"])
        pointer = table[0][1]["S"]
        self.assertIsInstance(pointer, BinaryBackPointer)
        self.assertEqual(pointer.production, Production("S", ("A", "B")))
        self.assertEqual(pointer.split, 0)
        self.assertEqual((pointer.left_symbol, pointer.right_symbol), ("A", "B"))

    def test_populated_cells_never_hold_none(self):
        tokens = parse_sentence("she eats a cake with a fork")
        _, table = recognize_cyk(ENGLISH, tokens)
        values = [pointer for row in table for cell in row for pointer in cell.values()]
        self.assertTrue(values)
        self.assertTrue(all(isinstance(value, (TerminalBackPointer, BinaryBackPointer)) for value in values))

    def test_binary_pointer_matches_its_cell(self):
        tokens = parse_sentence("she eats a cake with a fork")
        _, table = recognize_cyk(ENGLISH, tokens)
        for start, row in enumerate(table):
            for end, cell in enumerate(row):
                for symbol, pointer in cell.items():
                    if isinstance(pointer, BinaryBackPointer):
                        self.assertEqual(pointer.production.lhs, symbol)
                        self.assertTrue(start <= pointer.split < end)
                        self.assertIn(pointer.left_symbol, table[start][pointer.split])
                        self.assertIn(pointer.right_symbol, table[pointer.split + 1][end])

    def test_first_witness_is_deterministic(self):
        grammar = grammar_from("S -> A B | C D", "A -> a", "B -> b", "C -> a", "D -> b")
        expected = BinaryBackPointer(Production("S", ("A", "B")), 0, "A", "B")
        for _ in range(5):
            _, table = recognize_cyk(grammar, ["a", "b"])
            self.assertEqual(table[0][1]["S"], expected)

    def test_first_split_witness_is_kept(self):
        grammar = grammar_from("S -> A T | T A", "T -> A A", "A -> a")
        _, table = recognize_cyk(grammar, ["a", "a", "a"])
        self.assertEqual(table[0][2]["S"].split, 0)
        self.assertEqual(table[0][2]["S"].production, Production("S", ("A", "T")))


class ReconstructParseTreeTest(unittest.TestCase):
    def test_terminal_tree(self):
        accepted, _, tree = parse(grammar_from("S -> a"), ["a"])
        self.assertTrue(accepted)
        self.assertEqual(tree, ParseNode("S", "a"))

    def test_binary_tree(self):
        _, _, tree = parse(BINARY_GRAMMAR, ["a", "b"])
        self.assertEqual(tree.symbol, "S")
        self.assertIsNone(tree.token)
        self.assertEqual(len(tree.children), 2)
        left, right = tree.children
        self.assertEqual((left.symbol, left.token), ("A", "a"))
        self.assertEqual((right.symbol, right.token), ("B", "b"))

    def test_official_sentence_tree(self):
        tokens = parse_sentence("She eats a cake with a fork.")
        accepted, _, tree = parse(ENGLISH, tokens)
        self.assertTrue(accepted)
        self.assertEqual(tree.symbol, ENGLISH.start_symbol)
        self.assertEqual(leaves(tree), ["she", "eats", "a", "cake", "with", "a", "fork"])

    def test_official_sentence_tree_structure(self):
        _, _, tree = parse(ENGLISH, parse_sentence("she eats a cake with a fork"))
        noun_phrase, verb_phrase = tree.children
        self.assertEqual(noun_phrase, ParseNode("NP", "she"))
        self.assertEqual([child.symbol for child in verb_phrase.children], ["VP", "PP"])

    def test_leaves_match_tokens_for_accepted_sentences(self):
        for sentence in (
            "she eats a cake",
            "she eats a cake with a fork",
            "the cat drinks the beer",
            "he cuts the meat with a knife",
        ):
            with self.subTest(sentence=sentence):
                tokens = parse_sentence(sentence)
                accepted, _, tree = parse(ENGLISH, tokens)
                self.assertTrue(accepted)
                self.assertEqual(leaves(tree), tokens)

    def test_rejected_sentence_has_no_tree(self):
        accepted, _, tree = parse(ENGLISH, parse_sentence("she likes cake"))
        self.assertFalse(accepted)
        self.assertIsNone(tree)

    def test_rejected_sentence_with_non_empty_final_cell_has_no_tree(self):
        grammar = grammar_from("S -> A B", "C -> A A", "A -> a", "B -> b")
        accepted, table, tree = parse(grammar, ["a", "a"])
        self.assertFalse(accepted)
        self.assertIn("C", table[0][1])
        self.assertIsNone(tree)

    def test_accepted_epsilon_tree(self):
        accepted, table, tree = parse(grammar_from("S -> ε"), [])
        self.assertTrue(accepted)
        self.assertEqual(table, [])
        self.assertEqual(tree, ParseNode("S", "ε", ()))

    def test_rejected_empty_sentence_has_no_tree(self):
        accepted, _, tree = parse(grammar_from("S -> a"), [])
        self.assertFalse(accepted)
        self.assertIsNone(tree)

    def test_tree_keeps_binarization_auxiliaries(self):
        tokens = ["a", "b", "c", "d"]
        accepted, _, tree = parse(cnf_of("test_long_rules.txt"), tokens)
        self.assertTrue(accepted)
        self.assertEqual(leaves(tree), tokens)
        self.assertEqual(symbols(tree), ["S", "A", "X1", "B", "X2", "C", "D"])

    def test_tree_keeps_terminal_wrappers(self):
        cnf = cnf_of("test_guia.txt")
        tokens = ["a", "a", "b", "b"]
        accepted, _, tree = parse(cnf, tokens)
        self.assertTrue(accepted)
        self.assertEqual(tree.symbol, "S0")
        self.assertEqual(leaves(tree), tokens)
        self.assertIn("U_a", symbols(tree))
        self.assertIn("U_b", symbols(tree))

    def test_reconstruction_does_not_mutate_inputs(self):
        tokens = parse_sentence("she eats a cake with a fork")
        _, table = recognize_cyk(ENGLISH, tokens)
        table_before = copy.deepcopy(table)
        tokens_before = list(tokens)
        grammar_before = (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions)
        reconstruct_parse_tree(ENGLISH, table, tokens)
        self.assertEqual(table, table_before)
        self.assertEqual(tokens, tokens_before)
        self.assertEqual(
            (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions), grammar_before
        )

    def test_reconstruction_is_deterministic(self):
        tokens = parse_sentence("he cuts the meat with a knife")
        self.assertEqual(parse(ENGLISH, tokens)[2], parse(ENGLISH, tokens)[2])


if __name__ == "__main__":
    unittest.main()
