import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.cyk.parser import parse_cyk
from src.algorithms.simplification.simplify import simplify
from src.model.backpointer import BinaryBackPointer, TerminalBackPointer
from src.model.parse_node import ParseNode
from src.model.production import Production
from src.output.formatter import (
    format_benchmark_ns,
    format_cyk_table,
    format_elapsed_ns,
    format_result,
    format_tokens,
    format_vocabulary_warnings,
)
from src.output.tree_formatter import format_parse_tree
from tests.grammar_helpers import load

LEAF_A = ParseNode("A", "a")
LEAF_B = ParseNode("B", "b")
BINARY_TREE = ParseNode("S", None, (LEAF_A, LEAF_B))


def tree_leaves(text):
    return [line.split("── ")[-1] for line in text.splitlines() if "── " in line and line.split("── ")[-1].islower()]


class ResultFormatterTest(unittest.TestCase):
    def test_tokens(self):
        self.assertEqual(format_tokens(["she", "eats", "a", "cake"]), "Tokens: ['she', 'eats', 'a', 'cake']")

    def test_empty_tokens(self):
        self.assertEqual(format_tokens([]), "Tokens: []")

    def test_accepted_result(self):
        self.assertEqual(format_result(True), "Resultado: SÍ pertenece al lenguaje.")

    def test_rejected_result(self):
        self.assertEqual(format_result(False), "Resultado: NO pertenece al lenguaje.")

    def test_known_elapsed_time(self):
        self.assertEqual(format_elapsed_ns(41_800), "Tiempo de esta validación: 41.800 µs  (0.000041800 s)")

    def test_zero_elapsed_time(self):
        self.assertEqual(format_elapsed_ns(0), "Tiempo de esta validación: 0.000 µs  (0.000000000 s)")

    def test_benchmark_with_integer_median(self):
        self.assertEqual(
            format_benchmark_ns(39_250, 20), "Benchmark (mediana de 20 corridas): 39.250 µs  (0.000039250 s)"
        )

    def test_benchmark_with_float_median(self):
        self.assertEqual(
            format_benchmark_ns(41_800.9, 4), "Benchmark (mediana de 4 corridas): 41.801 µs  (0.000041801 s)"
        )
        self.assertEqual(
            format_benchmark_ns(1_500.0, 2), "Benchmark (mediana de 2 corridas): 1.500 µs  (0.000001500 s)"
        )


class VocabularyWarningsTest(unittest.TestCase):
    VOCABULARY = frozenset({"she", "eats", "cake"})

    def test_no_warnings(self):
        self.assertEqual(format_vocabulary_warnings(["she", "eats", "cake"], self.VOCABULARY), "")

    def test_single_warning(self):
        self.assertEqual(
            format_vocabulary_warnings(["she", "likes", "cake"], self.VOCABULARY),
            'Aviso: "likes" no pertenece al vocabulario de la gramática.',
        )

    def test_multiple_warnings_in_first_appearance_order(self):
        text = format_vocabulary_warnings(["zebra", "she", "likes", "cake"], self.VOCABULARY)
        self.assertEqual(
            text.splitlines(),
            [
                'Aviso: "zebra" no pertenece al vocabulario de la gramática.',
                'Aviso: "likes" no pertenece al vocabulario de la gramática.',
            ],
        )

    def test_repeated_unknown_token_warns_once(self):
        text = format_vocabulary_warnings(["likes", "she", "likes", "likes"], self.VOCABULARY)
        self.assertEqual(text.count('"likes"'), 1)

    def test_accepts_terminal_index_mapping(self):
        terminal_index = {"she": ("NP",), "cake": ("N",)}
        self.assertEqual(
            format_vocabulary_warnings(["she", "eats"], terminal_index),
            'Aviso: "eats" no pertenece al vocabulario de la gramática.',
        )


class CykTableFormatterTest(unittest.TestCase):
    def test_empty_sentence(self):
        self.assertEqual(format_cyk_table([], []), "Tabla CYK: ∅ (frase vacía)")

    def test_single_token(self):
        table = [[{"NP": TerminalBackPointer("she")}]]
        self.assertEqual(format_cyk_table(table, ["she"]), 'Tabla CYK:\n[0,0] "she" = {NP}')

    def test_spans_ordered_by_length_then_start(self):
        pointer = BinaryBackPointer(Production("S", ("A", "B")), 0, "A", "B")
        table = [
            [{"A": TerminalBackPointer("a")}, {"S": pointer}],
            [{}, {"B": TerminalBackPointer("b")}],
        ]
        self.assertEqual(
            format_cyk_table(table, ["a", "b"]).splitlines(),
            ["Tabla CYK:", '[0,0] "a" = {A}', '[1,1] "b" = {B}', '[0,1] "a b" = {S}'],
        )

    def test_unknown_token_keeps_position_with_empty_cell(self):
        table = [
            [{"NP": TerminalBackPointer("she")}, {}],
            [{}, {}],
        ]
        lines = format_cyk_table(table, ["she", "likes"]).splitlines()
        self.assertIn('[1,1] "likes" = ∅', lines)
        self.assertIn('[0,1] "she likes" = ∅', lines)

    def test_cell_variables_are_sorted(self):
        table = [[{"VP": TerminalBackPointer("eats"), "V": TerminalBackPointer("eats")}]]
        self.assertIn("{V, VP}", format_cyk_table(table, ["eats"]))

    def test_real_table_hides_backpointer_objects(self):
        simplified, _ = simplify(load("english.txt"))
        cnf, _ = to_cnf(simplified)
        tokens = ["she", "eats", "a", "cake"]
        text = format_cyk_table(parse_cyk(cnf, tokens).table, tokens)
        self.assertEqual(len(text.splitlines()), 1 + 10)
        self.assertIn('[0,3] "she eats a cake" = {S}', text)
        for hidden in ("BackPointer", "Production(", "None"):
            self.assertNotIn(hidden, text)


class ParseTreeFormatterTest(unittest.TestCase):
    def test_missing_tree(self):
        self.assertEqual(format_parse_tree(None), "Parse tree: no disponible.")

    def test_terminal_tree(self):
        self.assertEqual(format_parse_tree(ParseNode("NP", "she")), "NP\n└── she")

    def test_epsilon_tree(self):
        self.assertEqual(format_parse_tree(ParseNode("S", "ε")), "S\n└── ε")

    def test_binary_tree_connectors(self):
        self.assertEqual(format_parse_tree(BINARY_TREE), "S\n├── A\n│   └── a\n└── B\n    └── b")

    def test_multilevel_tree(self):
        tree = ParseNode(
            "S",
            None,
            (
                ParseNode("NP", "she"),
                ParseNode("VP", None, (ParseNode("V", "eats"), ParseNode("NP", None, (ParseNode("Det", "a"), ParseNode("N", "cake"))))),
            ),
        )
        expected = "\n".join(
            [
                "S",
                "├── NP",
                "│   └── she",
                "└── VP",
                "    ├── V",
                "    │   └── eats",
                "    └── NP",
                "        ├── Det",
                "        │   └── a",
                "        └── N",
                "            └── cake",
            ]
        )
        self.assertEqual(format_parse_tree(tree), expected)

    def test_empty_hidden_symbols_shows_full_tree(self):
        self.assertEqual(format_parse_tree(BINARY_TREE, ()), format_parse_tree(BINARY_TREE))

    def test_hidden_binary_auxiliary_promotes_children(self):
        tree = ParseNode("S", None, (LEAF_A, ParseNode("X1", None, (LEAF_B, ParseNode("C", "c")))))
        self.assertEqual(
            format_parse_tree(tree, {"X1"}),
            "S\n├── A\n│   └── a\n├── B\n│   └── b\n└── C\n    └── c",
        )

    def test_hidden_terminal_wrapper_promotes_token(self):
        tree = ParseNode("S", None, (ParseNode("U_a", "a"), LEAF_B))
        self.assertEqual(format_parse_tree(tree, {"U_a"}), "S\n├── a\n└── B\n    └── b")

    def test_original_x1_is_kept_when_not_hidden(self):
        tree = ParseNode("S", None, (LEAF_A, ParseNode("X1", "x")))
        text = format_parse_tree(tree, {"U_a"})
        self.assertIn("X1", text)
        self.assertEqual(text, "S\n├── A\n│   └── a\n└── X1\n    └── x")

    def test_root_is_never_hidden(self):
        self.assertEqual(format_parse_tree(BINARY_TREE, {"S"}).splitlines()[0], "S")

    def test_hiding_preserves_leaf_order(self):
        tree = ParseNode(
            "S0",
            None,
            (ParseNode("U_a", "a"), ParseNode("X1", None, (ParseNode("S", None, (ParseNode("U_a", "a"), ParseNode("U_b", "b"))), ParseNode("U_b", "b")))),
        )
        full = format_parse_tree(tree)
        hidden = format_parse_tree(tree, {"S0", "U_a", "U_b", "X1"})
        self.assertEqual(tree_leaves(full), ["a", "a", "b", "b"])
        self.assertEqual(tree_leaves(hidden), ["a", "a", "b", "b"])
        self.assertEqual(hidden, "S0\n├── a\n├── S\n│   ├── a\n│   └── b\n└── b")


if __name__ == "__main__":
    unittest.main()
