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
            "✓ G6 está en Forma Normal de Chomsky.\n  30 producciones válidas",
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
        self.assertIn("GRAMÁTICA FINAL EN CNF", completed.stdout)
        self.assertIn("S0 -> ε | U_a X1 | U_a U_b | U_a A | a", completed.stdout)
        self.assertIn("✓ G6 está en Forma Normal de Chomsky.", completed.stdout)

    def test_trace(self):
        completed = run_cli("--trace", stdin="\n")
        self.assert_clean_exit(completed)
        for phase in range(6):
            self.assertIn(f"FASE {phase} — ", completed.stdout)
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
            "FASE 5 — BINARIZACIÓN",
            "GRAMÁTICA FINAL EN CNF",
            "Tabla CYK:",
            "Benchmark (mediana de 2 corridas): ",
            "Resultado: SÍ pertenece al lenguaje.",
        ):
            self.assertIn(expected, completed.stdout)


MANUAL_GRAMMAR = "10\nS -> A B\nA -> a\nB -> b\nFIN\n"


class MenuSubprocessTest(unittest.TestCase):
    def run_menu(self, stdin, *arguments):
        completed = run_cli("--menu", *arguments, stdin=stdin)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        return completed

    def test_selects_english(self):
        completed = self.run_menu("1\nshe eats a cake\n\n\n0\n")
        self.assertIn("SELECCIÓN DE GRAMÁTICA", completed.stdout)
        self.assertIn("Gramática: grammars/english.txt", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)
        self.assertIn("Enter dos veces consecutivas", completed.stdout)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)

    def test_selects_long_rules(self):
        completed = self.run_menu("8\na b c d\n\n0\n")
        self.assertIn("Gramática: grammars/test_long_rules.txt", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_every_bundled_option_loads(self):
        stdin = "".join(f"{number}\n\n\n" for number in range(1, 9)) + "0\n"
        completed = self.run_menu(stdin)
        self.assertEqual(completed.stdout.count("está en Forma Normal de Chomsky."), 8)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 9)

    def test_custom_file(self):
        completed = self.run_menu("9\ngrammars/test_long_rules.txt\na b c d\n\n0\n")
        self.assertIn("Ruta del archivo .txt:", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_missing_custom_file_returns_to_menu(self):
        completed = self.run_menu("9\nnope.txt\n1\nshe eats\n\n0\n")
        self.assertIn("Error: Grammar file not found: nope.txt", completed.stderr)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_invalid_options_are_reported(self):
        completed = self.run_menu("xyz\n99\n-1\n0\n")
        self.assertEqual(completed.stdout.count("Opción inválida. Intente nuevamente."), 3)
        self.assertNotIn("Gramática:", completed.stdout)

    def test_exit_option(self):
        completed = self.run_menu("0\n")
        self.assertNotIn("Gramática:", completed.stdout)

    def test_eof_in_menu(self):
        completed = self.run_menu("")
        self.assertIn("SELECCIÓN DE GRAMÁTICA", completed.stdout)

    def test_manual_grammar_accepts(self):
        completed = self.run_menu(MANUAL_GRAMMAR + "a b\n\n0\n")
        self.assertIn("Gramática: entrada manual", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_manual_grammar_rejects(self):
        completed = self.run_menu(MANUAL_GRAMMAR + "a a\n\n0\n")
        self.assertIn("Resultado: NO pertenece al lenguaje.", completed.stdout)
        self.assertNotIn("Resultado: SÍ", completed.stdout)

    def test_invalid_manual_grammar_returns_to_menu(self):
        completed = self.run_menu("10\nS -> a | | b\nFIN\n0\n")
        self.assertIn("Error: Line 1: empty alternative", completed.stderr)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)
        self.assertNotIn("Gramática: entrada manual", completed.stdout)

    def test_empty_manual_grammar_is_rejected(self):
        completed = self.run_menu("10\nFIN\n0\n")
        self.assertIn("Error: Grammar has no productions", completed.stderr)

    def test_lowercase_terminator(self):
        completed = self.run_menu("10\nS -> a\nfin\na\n\n0\n")
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_manual_grammar_with_epsilon(self):
        completed = self.run_menu("10\nS -> a S | ε\nFIN\n!!!\na a\nb\n\n\n0\n")
        self.assertIn("Tokens: []", completed.stdout)
        self.assertIn("└── ε", completed.stdout)
        self.assertEqual(completed.stdout.count("Resultado: SÍ pertenece al lenguaje."), 3)
        self.assertIn("Resultado: NO pertenece al lenguaje.", completed.stdout)

    def test_manual_grammar_goes_through_full_pipeline(self):
        stdin = "10\n# demo\nS -> a S b | a b c\n\nC -> c\nFIN\na b c\na a b c b\na b\n\n\n0\n"
        completed = self.run_menu(stdin, "--trace", "--show-cnf")
        for phase in range(6):
            self.assertIn(f"FASE {phase} — ", completed.stdout)
        self.assertIn("GRAMÁTICA FINAL EN CNF", completed.stdout)
        self.assertIn("S0 -> ", completed.stdout)
        self.assertEqual(completed.stdout.count("Resultado: SÍ pertenece al lenguaje."), 2)
        self.assertEqual(completed.stdout.count("Resultado: NO pertenece al lenguaje."), 2)

    def test_switches_grammar_in_same_session(self):
        completed = self.run_menu("1\nshe eats a cake\n\n\n8\na b c d\n\n\n0\n")
        english = completed.stdout.index("Gramática: grammars/english.txt")
        long_rules = completed.stdout.index("Gramática: grammars/test_long_rules.txt")
        self.assertLess(english, long_rules)
        self.assertEqual(completed.stdout.count("Resultado: SÍ pertenece al lenguaje."), 2)

    def test_menu_applies_view_flags(self):
        completed = self.run_menu("1\nshe eats\n\n0\n", "--show-table", "--show-cnf", "--runs", "2")
        self.assertIn("GRAMÁTICA FINAL EN CNF", completed.stdout)
        self.assertIn("Tabla CYK:", completed.stdout)
        self.assertIn('[0,1] "she eats" = {S}', completed.stdout)
        self.assertIn("Benchmark (mediana de 2 corridas): ", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_menu_rejects_explicit_grammar(self):
        completed = subprocess.run(
            [sys.executable, "main.py", "--menu", "--grammar", "grammars/english.txt"],
            input="",
            text=True,
            capture_output=True,
            cwd=PROJECT_ROOT,
            timeout=120,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not allowed with argument", completed.stderr)


class LegacyCompatibilityTest(unittest.TestCase):
    def test_redirected_stdin_skips_menu(self):
        completed = run_cli(stdin="she eats a cake\n\n")
        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("SELECCIÓN DE GRAMÁTICA", completed.stdout)
        self.assertIn("Gramática: grammars/english.txt", completed.stdout)
        self.assertIn("vacío para salir", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_explicit_grammar_skips_menu(self):
        completed = run_cli("--grammar", "grammars/test_long_rules.txt", stdin="a b c d\n\n")
        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("SELECCIÓN DE GRAMÁTICA", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)

    def test_blank_line_still_ends_legacy_session(self):
        completed = run_cli(stdin="\nshe eats a cake\n")
        self.assertEqual(completed.returncode, 0)
        self.assertNotIn("Tokens:", completed.stdout)
        self.assertNotIn("SELECCIÓN DE GRAMÁTICA", completed.stdout)


PDF_SHE_SENTENCE = "𝑆ℎ𝑒 𝑒𝑎𝑡𝑠 𝑎 𝑐𝑎𝑘𝑒 𝑤𝑖𝑡ℎ 𝑎 𝑓𝑜𝑟𝑘"
PDF_CAT_SENTENCE = "𝑇ℎ𝑒 𝑐𝑎𝑡 𝑑𝑟𝑖𝑛𝑘𝑠 𝑡ℎ𝑒 𝑏𝑒𝑒𝑟"


class UnicodeSentenceIntegrationTest(unittest.TestCase):
    def test_pdf_sentence_is_accepted_by_cyk(self):
        tokens, result = validate(PDF_SHE_SENTENCE)
        self.assertTrue(result.accepted)
        self.assertIsNotNone(result.parse_tree)
        self.assertEqual(leaves(result.parse_tree), ["she", "eats", "a", "cake", "with", "a", "fork"])

    def test_second_pdf_sentence_is_accepted_by_cyk(self):
        tokens, result = validate(PDF_CAT_SENTENCE)
        self.assertEqual(tokens, ["the", "cat", "drinks", "the", "beer"])
        self.assertTrue(result.accepted)

    def test_pdf_sentence_has_no_vocabulary_warnings(self):
        terminal_index, _ = build_production_indexes(ENGLISH)
        self.assertEqual(format_vocabulary_warnings(parse_sentence(PDF_SHE_SENTENCE), terminal_index), "")


class DemonstrationFlowSubprocessTest(unittest.TestCase):
    def run_menu(self, stdin, *arguments):
        completed = run_cli("--menu", *arguments, stdin=stdin)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("Traceback", completed.stdout + completed.stderr)
        return completed

    def validation_section(self, completed):
        return completed.stdout.split("VALIDACIÓN DE CADENAS", 1)[1]

    def test_menu_shows_complete_procedure_for_lab7(self):
        completed = self.run_menu("2\n\n\n0\n")
        procedure = completed.stdout.split("VALIDACIÓN DE CADENAS", 1)[0]
        for phase in range(6):
            self.assertIn(f"FASE {phase} — ", procedure)
        for detail in (
            "  Condiciones",
            "  Anulables",
            "  Variantes",
            "  Unitarias",
            "  Pares unitarios",
            "  Transferencias",
            "  3a Generadores",
            "  3b Alcanzables",
            "  Envoltorios",
            "  Binarización",
            "Gramática resultante",
        ):
            self.assertIn(detail, procedure)

    def test_menu_shows_cnf_and_check_before_validation(self):
        completed = self.run_menu("2\n\n\n0\n")
        cnf = completed.stdout.index("GRAMÁTICA FINAL EN CNF")
        check = completed.stdout.index("✓ G6 está en Forma Normal de Chomsky.")
        validation = completed.stdout.index("VALIDACIÓN DE CADENAS")
        self.assertLess(cnf, check)
        self.assertLess(check, validation)
        self.assertIn("S0 -> ε | U_0 X1", completed.stdout)

    def test_menu_does_not_print_one_line_conclusions(self):
        completed = self.run_menu("1\n\n\n0\n")
        self.assertNotIn("Fase 0: nuevo símbolo inicial: ", completed.stdout)
        self.assertEqual(completed.stdout.count("FASE 1 — ELIMINACIÓN DE ε"), 1)

    def test_validation_banner_explains_navigation(self):
        completed = self.run_menu("1\n\n\n0\n")
        validation = self.validation_section(completed)
        self.assertIn("• Enter una vez:\n  validar la cadena vacía ε.", validation)
        self.assertIn("• Enter dos veces consecutivas:\n  regresar al menú de gramáticas.", validation)

    def test_first_enter_validates_epsilon_and_second_returns(self):
        completed = self.run_menu("2\n\n\n0\n")
        validation = self.validation_section(completed)
        self.assertEqual(validation.count("Tokens: []"), 1)
        self.assertEqual(validation.count("Resultado: SÍ pertenece al lenguaje."), 1)
        self.assertIn("Presione Enter nuevamente para volver al menú,", validation)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)

    def test_english_rejects_epsilon_on_first_enter(self):
        completed = self.run_menu("1\n\n\n0\n")
        validation = self.validation_section(completed)
        self.assertEqual(validation.count("Tokens: []"), 1)
        self.assertIn("Resultado: NO pertenece al lenguaje.", validation)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)

    def test_non_empty_input_resets_double_enter(self):
        completed = self.run_menu("2\n\n0 0\n\n\n0\n")
        validation = self.validation_section(completed)
        self.assertEqual(validation.count("Tokens: []"), 2)
        self.assertIn("Tokens: ['0', '0']", validation)
        self.assertEqual(validation.count("Presione Enter nuevamente"), 2)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)

    def test_zero_and_one_are_validated_as_strings(self):
        completed = self.run_menu("2\n0\n1\n\n\n0\n")
        validation = self.validation_section(completed)
        self.assertIn("Tokens: ['0']", validation)
        self.assertIn("Tokens: ['1']", validation)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)
        self.assertNotIn("Opción inválida", completed.stdout)

    def test_arbitrary_text_is_validated_as_string(self):
        completed = self.run_menu("1\nFase 0\nvolver\nexit\n\n\n0\n")
        validation = self.validation_section(completed)
        for tokens in ("['fase', '0']", "['volver']", "['exit']"):
            self.assertIn(f"Tokens: {tokens}", validation)
        self.assertEqual(completed.stdout.count("SELECCIÓN DE GRAMÁTICA"), 2)

    def test_pdf_sentence_from_menu(self):
        completed = self.run_menu(f"1\n{PDF_SHE_SENTENCE}\n\n\n0\n")
        self.assertIn("Tokens: ['she', 'eats', 'a', 'cake', 'with', 'a', 'fork']", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)
        self.assertNotIn("Aviso:", completed.stdout)

    def test_menu_flags_apply_in_demonstration_flow(self):
        completed = self.run_menu("2\n0 0\n\n\n0\n", "--show-table", "--runs", "2")
        validation = self.validation_section(completed)
        self.assertIn('[0,1] "0 0" = {A, B, S0}', validation)
        self.assertIn("Tabla CYK: ∅ (frase vacía)", validation)
        self.assertEqual(validation.count("Benchmark (mediana de 2 corridas): "), 2)


class DirectModeCompatibilityTest(unittest.TestCase):
    def test_direct_mode_keeps_conclusions_and_single_enter_exit(self):
        completed = run_cli("--grammar", "grammars/test_lab7.txt", stdin="0 0\n\n0 0\n")
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Fase 0: nuevo símbolo inicial: ", completed.stdout)
        self.assertNotIn("  Anulables", completed.stdout)
        self.assertNotIn("VALIDACIÓN DE CADENAS", completed.stdout)
        self.assertEqual(completed.stdout.count("Resultado:"), 1)

    def test_direct_mode_still_honors_trace_flag(self):
        completed = run_cli("--trace", stdin="\n")
        self.assertEqual(completed.returncode, 0)
        self.assertIn("  Anulables", completed.stdout)
        self.assertNotIn("VALIDACIÓN DE CADENAS", completed.stdout)

    def test_direct_mode_accepts_pdf_sentence(self):
        completed = run_cli(stdin=f"{PDF_CAT_SENTENCE}\n\n")
        self.assertEqual(completed.returncode, 0)
        self.assertIn("Tokens: ['the', 'cat', 'drinks', 'the', 'beer']", completed.stdout)
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", completed.stdout)


if __name__ == "__main__":
    unittest.main()
