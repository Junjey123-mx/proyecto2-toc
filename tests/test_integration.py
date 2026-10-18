import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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


def run_cli(*arguments, stdin=""):
    return subprocess.run(
        [sys.executable, "main.py", *arguments],
        input=stdin,
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
        timeout=120,
    )


class CliSubprocessTest(unittest.TestCase):
    def assert_clean_exit(self, completed):
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def assert_clean_error(self, completed):
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        self.assertNotIn("Resultado:", completed.stdout)

    def test_default_accepted_sentence(self):
        completed = run_cli(stdin="she eats a cake\n\n")
        self.assert_clean_exit(completed)
        for expected in (
            "CYK PARSER — TOC",
            "Gramática: grammars/english.txt",
            "|V| = 8   |Σ| = 21   |R| = 30",
            "✓ Gramática en CNF (validador: 30 producciones válidas)",
            "Tokens: ['she', 'eats', 'a', 'cake']",
            "Resultado: SÍ pertenece al lenguaje.",
            "Tiempo de esta validación: ",
            "Parse tree:",
            "└── VP",
        ):
            self.assertIn(expected, completed.stdout)

    def test_default_rejected_sentence(self):
        completed = run_cli(stdin="cat the drinks beer\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Resultado: NO pertenece al lenguaje.", completed.stdout)
        self.assertIn("Tiempo de esta validación: ", completed.stdout)
        self.assertNotIn("Parse tree:", completed.stdout)

    def test_unknown_token_warns_and_rejects(self):
        completed = run_cli(stdin="she likes cake\n\n")
        self.assert_clean_exit(completed)
        self.assertIn('Aviso: "likes" no pertenece al vocabulario de la gramática.', completed.stdout)
        self.assertIn("Tokens: ['she', 'likes', 'cake']", completed.stdout)
        self.assertIn("Resultado: NO pertenece al lenguaje.", completed.stdout)

    def test_show_table(self):
        completed = run_cli("--show-table", stdin="she eats a cake\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Tabla CYK:", completed.stdout)
        self.assertIn('[0,0] "she" = {NP}', completed.stdout)
        self.assertIn('[0,3] "she eats a cake" = {S}', completed.stdout)
        self.assertNotIn("BinaryBackPointer(", completed.stdout)
        self.assertNotIn("TerminalBackPointer(", completed.stdout)

    def test_show_cnf(self):
        completed = run_cli("--show-cnf", "--grammar", "grammars/test_guia.txt", stdin="\n")
        self.assert_clean_exit(completed)
        self.assertIn("Gramática CNF", completed.stdout)
        self.assertIn("S0 -> ε | U_a X1 | U_a U_b | U_a A | a", completed.stdout)
        self.assertIn("✓ Gramática en CNF", completed.stdout)

    def test_trace(self):
        completed = run_cli("--trace", stdin="\n")
        self.assert_clean_exit(completed)
        for phase in range(6):
            self.assertIn(f"Fase {phase}:", completed.stdout)
        self.assertIn("Anulables", completed.stdout)
        self.assertIn("3a Generadores", completed.stdout)
        self.assertIn("Gramática resultante", completed.stdout)

    def test_conclusions_without_trace(self):
        completed = run_cli(stdin="\n")
        self.assert_clean_exit(completed)
        for phase in range(6):
            self.assertIn(f"Fase {phase}:", completed.stdout)
        self.assertNotIn("Anulables", completed.stdout)

    def test_runs_three_adds_benchmark(self):
        completed = run_cli("--runs", "3", stdin="she eats a cake\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Tiempo de esta validación: ", completed.stdout)
        self.assertIn("Benchmark (mediana de 3 corridas): ", completed.stdout)

    def test_runs_one_has_no_benchmark(self):
        completed = run_cli("--runs", "1", stdin="she eats a cake\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Tiempo de esta validación: ", completed.stdout)
        self.assertNotIn("Benchmark", completed.stdout)

    def test_custom_grammar(self):
        completed = run_cli("--grammar", "grammars/test_long_rules.txt", stdin="a b c d\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Gramática: grammars/test_long_rules.txt", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_missing_grammar_file(self):
        completed = run_cli("--grammar", "grammars/no_existe.txt", stdin="she eats a cake\n\n")
        self.assert_clean_error(completed)
        self.assertTrue(completed.stderr.startswith("Error: "))

    def test_malformed_grammar_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformada.txt"
            path.write_text("S -> a | | b\n", encoding="utf-8")
            completed = run_cli("--grammar", str(path), stdin="a\n\n")
        self.assert_clean_error(completed)
        self.assertEqual(completed.stderr.strip(), "Error: Line 1: empty alternative")

    def test_invalid_runs(self):
        for value in ("0", "-1", "texto"):
            with self.subTest(value=value):
                completed = run_cli(f"--runs={value}", stdin="she eats a cake\n\n")
                self.assert_clean_error(completed)
                self.assertIn("--runs", completed.stderr)
                self.assertNotIn("CYK PARSER", completed.stdout)

    def test_eof_exits_cleanly(self):
        completed = run_cli(stdin="")
        self.assert_clean_exit(completed)
        self.assertNotIn("Resultado:", completed.stdout)

    def test_blank_line_exits_without_validation(self):
        completed = run_cli(stdin="\n")
        self.assert_clean_exit(completed)
        self.assertNotIn("Resultado:", completed.stdout)
        self.assertNotIn("Tokens:", completed.stdout)

    def test_whitespace_line_exits_without_validation(self):
        completed = run_cli(stdin="   \t \nshe eats a cake\n")
        self.assert_clean_exit(completed)
        self.assertNotIn("Tokens:", completed.stdout)

    def test_punctuation_only_validates_empty_sentence(self):
        completed = run_cli(stdin="!!!\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Tokens: []", completed.stdout)
        self.assertIn("Resultado: NO pertenece al lenguaje.", completed.stdout)

    def test_punctuation_only_accepts_with_epsilon_grammar(self):
        completed = run_cli("--grammar", "grammars/test_lab7.txt", stdin="?\n\n")
        self.assert_clean_exit(completed)
        self.assertIn("Tokens: []", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)
        self.assertIn("└── ε", completed.stdout)

    def test_multiple_sentences_in_one_session(self):
        completed = run_cli(stdin="she eats a cake\nshe likes cake\n\n")
        self.assert_clean_exit(completed)
        accepted = completed.stdout.index("Resultado: SÍ pertenece al lenguaje.")
        rejected = completed.stdout.index("Resultado: NO pertenece al lenguaje.")
        self.assertLess(accepted, rejected)
        self.assertEqual(completed.stdout.count("CYK PARSER — TOC"), 1)

    def test_combined_flags(self):
        completed = run_cli("--trace", "--show-cnf", "--show-table", "--runs", "2", stdin="she eats\n\n")
        self.assert_clean_exit(completed)
        for expected in (
            "Fase 5: binarizar",
            "Gramática CNF",
            "Tabla CYK:",
            "Benchmark (mediana de 2 corridas): ",
            "Resultado: SÍ pertenece al lenguaje.",
        ):
            self.assertIn(expected, completed.stdout)


if __name__ == "__main__":
    unittest.main()
