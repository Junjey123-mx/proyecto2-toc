import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import is_cnf
from src.algorithms.cyk.parser import benchmark_cyk, parse_cyk
from src.algorithms.cyk.table import build_production_indexes
from src.algorithms.simplification.simplify import simplify
from src.input.grammar_parser import parse_grammar_file
from src.input.sentence_parser import parse_sentence
from src.output.formatter import format_cyk_table, format_elapsed_ns, format_result, format_vocabulary_warnings
from src.output.tree_formatter import format_parse_tree
from tests.grammar_helpers import GRAMMARS_DIRECTORY, PROJECT_GRAMMARS

ACCEPTED_SENTENCES = (
    "she eats a cake",
    "she eats a cake with a fork",
    "the cat drinks the beer",
    "he cuts the meat with a knife",
)
REJECTED_SENTENCES = ("cat the drinks beer", "she likes cake", "a dog the beer", "eats")


def prepare(file_name):
    parsed = parse_grammar_file(GRAMMARS_DIRECTORY / file_name)
    simplified, simplification_traces = simplify(parsed.grammar)
    cnf, cnf_traces = to_cnf(simplified)
    return parsed.grammar, cnf, simplification_traces + cnf_traces


def leaves(node):
    if not node.children:
        return [node.token]
    return [token for child in node.children for token in leaves(child)]


ENGLISH_ORIGINAL, ENGLISH, ENGLISH_TRACES = prepare("english.txt")


def validate(sentence, grammar=ENGLISH):
    tokens = parse_sentence(sentence)
    return tokens, parse_cyk(grammar, tokens)


class GrammarPreparationIntegrationTest(unittest.TestCase):
    def test_every_project_grammar_reaches_cnf(self):
        for file_name in PROJECT_GRAMMARS:
            with self.subTest(file_name=file_name):
                _, cnf, traces = prepare(file_name)
                self.assertTrue(is_cnf(cnf))
                self.assertEqual(len(traces), 6)

    def test_english_needs_no_synthetic_variables(self):
        self.assertTrue(is_cnf(ENGLISH))
        self.assertEqual(ENGLISH.variables - ENGLISH_ORIGINAL.variables, frozenset())
        self.assertEqual(ENGLISH, ENGLISH_ORIGINAL)


class SentenceIntegrationTest(unittest.TestCase):
    def test_official_sentences_are_accepted(self):
        for sentence in ACCEPTED_SENTENCES:
            with self.subTest(sentence=sentence):
                tokens, result = validate(sentence)
                self.assertTrue(result.accepted)
                self.assertIsNotNone(result.parse_tree)
                self.assertEqual(result.parse_tree.symbol, ENGLISH.start_symbol)
                self.assertEqual(leaves(result.parse_tree), tokens)
                self.assertIsInstance(result.elapsed_ns, int)
                self.assertGreaterEqual(result.elapsed_ns, 0)

    def test_official_sentences_are_rejected(self):
        for sentence in REJECTED_SENTENCES:
            with self.subTest(sentence=sentence):
                _, result = validate(sentence)
                self.assertFalse(result.accepted)
                self.assertIsNone(result.parse_tree)
                self.assertGreaterEqual(result.elapsed_ns, 0)

    def test_sentence_normalization_is_integrated(self):
        expected_tokens, expected = validate("she eats a cake with a fork")
        for sentence in ("She eats a cake with a fork.", "   SHE   EATS   A   CAKE   WITH A FORK!  "):
            with self.subTest(sentence=sentence):
                tokens, result = validate(sentence)
                self.assertEqual(tokens, expected_tokens)
                self.assertTrue(result.accepted)
                self.assertEqual(result.parse_tree, expected.parse_tree)

    def test_unknown_token_reaches_cyk_without_prefiltering(self):
        terminal_index, _ = build_production_indexes(ENGLISH)
        tokens, result = validate("she likes cake")
        self.assertEqual(tokens, ["she", "likes", "cake"])
        self.assertNotIn("likes", terminal_index)
        self.assertFalse(result.accepted)
        self.assertEqual(len(result.table), 3)
        self.assertEqual(result.table[1][1], {})

    def test_english_rejects_empty_sentence(self):
        _, result = validate("!!!")
        self.assertFalse(result.accepted)
        self.assertEqual(result.table, [])
        self.assertIsNone(result.parse_tree)

    def test_project_grammar_accepts_empty_sentence(self):
        for file_name in ("test_lab7.txt", "test_guia.txt"):
            with self.subTest(file_name=file_name):
                _, cnf, _ = prepare(file_name)
                result = parse_cyk(cnf, [])
                self.assertTrue(result.accepted)
                self.assertEqual(result.parse_tree.symbol, cnf.start_symbol)
                self.assertEqual(result.parse_tree.token, "ε")

    def test_long_rules_sentence(self):
        _, cnf, _ = prepare("test_long_rules.txt")
        tokens, result = validate("a b c d", cnf)
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.parse_tree)
        self.assertEqual(leaves(result.parse_tree), ["a", "b", "c", "d"])
        self.assertFalse(validate("a b c", cnf)[1].accepted)

    def test_lab7_sentences_after_full_pipeline(self):
        _, cnf, _ = prepare("test_lab7.txt")
        for sentence, expected in (("0 0", True), ("1 1", True), ("0 1 1 0", True), ("0", False), ("0 1", False)):
            with self.subTest(sentence=sentence):
                self.assertEqual(validate(sentence, cnf)[1].accepted, expected)

    def test_residual_terminal_is_rejected(self):
        _, cnf, _ = prepare("test_corto_p5.txt")
        self.assertIn("b", cnf.terminals)
        _, result = validate("b", cnf)
        self.assertFalse(result.accepted)


class BenchmarkIntegrationTest(unittest.TestCase):
    def test_benchmark_on_real_pipeline(self):
        tokens = parse_sentence("she eats a cake with a fork")
        tokens_before = list(tokens)
        grammar_before = (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions)
        median = benchmark_cyk(ENGLISH, tokens, 3)
        self.assertGreaterEqual(median, 0)
        self.assertEqual(tokens, tokens_before)
        self.assertEqual(
            (ENGLISH.start_symbol, ENGLISH.variables, ENGLISH.terminals, ENGLISH.productions), grammar_before
        )

    def test_benchmark_does_not_change_individual_decision(self):
        tokens = parse_sentence("she likes cake")
        benchmark_cyk(ENGLISH, tokens, 3)
        self.assertFalse(parse_cyk(ENGLISH, tokens).accepted)


class DeterminismIntegrationTest(unittest.TestCase):
    def test_repeated_validation_is_identical_except_time(self):
        for sentence in ("he cuts the meat with a knife", "a dog the beer"):
            with self.subTest(sentence=sentence):
                _, first = validate(sentence)
                _, second = validate(sentence)
                self.assertEqual(first.accepted, second.accepted)
                self.assertEqual(first.table, second.table)
                self.assertEqual(first.parse_tree, second.parse_tree)

    def test_repeated_preparation_is_identical(self):
        _, cnf, traces = prepare("test_guia.txt")
        _, cnf_again, traces_again = prepare("test_guia.txt")
        self.assertEqual(cnf, cnf_again)
        self.assertEqual([trace.notes for trace in traces], [trace.notes for trace in traces_again])


class OutputIntegrationTest(unittest.TestCase):
    def test_formatters_render_real_accepted_result(self):
        tokens, result = validate("She eats a cake with a fork.")
        self.assertEqual(format_result(result.accepted), "Resultado: SÍ pertenece al lenguaje.")
        self.assertTrue(format_elapsed_ns(result.elapsed_ns).startswith("Tiempo de esta validación: "))
        tree = format_parse_tree(result.parse_tree)
        self.assertEqual(tree.splitlines()[0], "S")
        for token in tokens:
            self.assertIn(f"── {token}", tree)
        table = format_cyk_table(result.table, tokens)
        self.assertIn('[0,6] "she eats a cake with a fork" = {S}', table)
        self.assertNotIn("BackPointer", table)

    def test_formatters_render_real_rejected_result(self):
        terminal_index, _ = build_production_indexes(ENGLISH)
        tokens, result = validate("she likes cake")
        self.assertEqual(format_result(result.accepted), "Resultado: NO pertenece al lenguaje.")
        self.assertEqual(
            format_vocabulary_warnings(tokens, terminal_index),
            'Aviso: "likes" no pertenece al vocabulario de la gramática.',
        )
        self.assertIn('[1,1] "likes" = ∅', format_cyk_table(result.table, tokens))

    def test_hidden_synthetic_variables_restore_original_shape(self):
        original, cnf, _ = prepare("test_long_rules.txt")
        tokens, result = validate("a b c d", cnf)
        hidden = format_parse_tree(result.parse_tree, cnf.variables - original.variables)
        self.assertNotIn("X1", hidden)
        self.assertEqual([line[4:] for line in hidden.splitlines() if line.startswith(("├── ", "└── "))], ["A", "B", "C", "D"])


if __name__ == "__main__":
    unittest.main()
