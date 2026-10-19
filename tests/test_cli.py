import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def terminal(is_tty):
    return mock.patch("sys.stdin", mock.Mock(isatty=mock.Mock(return_value=is_tty)))


def parse_silently(argv):
    with contextlib.redirect_stderr(io.StringIO()):
        return main.parse_arguments(argv)


class ArgumentParserTest(unittest.TestCase):
    def test_defaults_without_arguments(self):
        arguments = main.parse_arguments([])
        self.assertFalse(arguments.trace)
        self.assertFalse(arguments.show_cnf)
        self.assertFalse(arguments.show_table)
        self.assertEqual(arguments.runs, 1)

    def test_default_grammar_is_english_relative_to_project(self):
        grammar = main.parse_arguments([]).grammar
        self.assertEqual(grammar, PROJECT_ROOT / "grammars" / "english.txt")
        self.assertTrue(grammar.is_absolute())
        self.assertTrue(grammar.is_file())

    def test_grammar_option(self):
        self.assertEqual(main.parse_arguments(["--grammar", "otra.txt"]).grammar, Path("otra.txt"))

    def test_trace_option(self):
        self.assertTrue(main.parse_arguments(["--trace"]).trace)

    def test_show_cnf_option(self):
        self.assertTrue(main.parse_arguments(["--show-cnf"]).show_cnf)

    def test_show_table_option(self):
        self.assertTrue(main.parse_arguments(["--show-table"]).show_table)

    def test_runs_one(self):
        self.assertEqual(main.parse_arguments(["--runs", "1"]).runs, 1)

    def test_runs_five(self):
        self.assertEqual(main.parse_arguments(["--runs", "5"]).runs, 5)

    def test_combined_flags(self):
        arguments = main.parse_arguments(
            ["--grammar", "g.txt", "--trace", "--show-cnf", "--show-table", "--runs", "20"]
        )
        self.assertEqual(
            (arguments.grammar, arguments.trace, arguments.show_cnf, arguments.show_table, arguments.runs),
            (Path("g.txt"), True, True, True, 20),
        )

    def test_rejects_zero_runs(self):
        with self.assertRaises(SystemExit):
            parse_silently(["--runs", "0"])

    def test_rejects_negative_runs(self):
        with self.assertRaises(SystemExit):
            parse_silently(["--runs=-1"])

    def test_rejects_text_runs(self):
        with self.assertRaises(SystemExit):
            parse_silently(["--runs", "texto"])

    def test_rejects_unknown_option(self):
        with self.assertRaises(SystemExit):
            parse_silently(["--desconocida"])

    def test_positive_runs_validator(self):
        self.assertEqual(main.positive_runs("3"), 3)
        for text in ("0", "-2", "1.5", "x"):
            with self.subTest(text=text):
                with self.assertRaises(main.argparse.ArgumentTypeError):
                    main.positive_runs(text)


class MainModuleTest(unittest.TestCase):
    def test_import_does_not_start_loop(self):
        with mock.patch("builtins.input") as fake_input:
            import importlib

            importlib.reload(main)
        fake_input.assert_not_called()

    def test_main_exits_cleanly_on_eof(self):
        output = io.StringIO()
        with terminal(False), mock.patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(output):
            self.assertEqual(main.main([]), 0)
        self.assertIn("CYK PARSER — TOC", output.getvalue())

    def test_main_reports_missing_grammar(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.main(["--grammar", str(PROJECT_ROOT / "no_existe.txt")]), 1)
        self.assertTrue(errors.getvalue().startswith("Error: "))


class GrammarSourceArgumentsTest(unittest.TestCase):
    def test_menu_flag(self):
        self.assertTrue(main.parse_arguments(["--menu"]).menu)
        self.assertFalse(main.parse_arguments([]).menu)

    def test_menu_and_grammar_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            parse_silently(["--menu", "--grammar", "grammars/english.txt"])

    def test_grammar_given_is_tracked(self):
        self.assertFalse(main.parse_arguments([]).grammar_given)
        self.assertTrue(main.parse_arguments(["--grammar", "grammars/english.txt"]).grammar_given)

    def test_menu_activation_rules(self):
        cases = (
            ([], True, True),
            ([], False, False),
            (["--menu"], False, True),
            (["--grammar", "grammars/english.txt"], True, False),
            (["--trace", "--runs", "3"], True, True),
        )
        for argv, is_tty, expected in cases:
            with self.subTest(argv=argv, is_tty=is_tty):
                with terminal(is_tty):
                    self.assertEqual(main.uses_menu(main.parse_arguments(argv)), expected)

    def test_non_interactive_default_is_english(self):
        output = io.StringIO()
        with terminal(False), mock.patch("builtins.input", side_effect=["she eats a cake", ""]):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main.main([]), 0)
        self.assertIn("Gramática: grammars/english.txt", output.getvalue())
        self.assertNotIn("SELECCIÓN DE GRAMÁTICA", output.getvalue())
        self.assertIn("Resultado: SÍ pertenece al lenguaje.", output.getvalue())


class GrammarMenuTest(unittest.TestCase):
    def test_bundled_options_map_to_existing_files(self):
        expected = (
            "english.txt",
            "1.txt",
            "1-cnf.txt",
            "test_lab7.txt",
            "test_guia.txt",
            "test_practica.txt",
            "test_corto_p3.txt",
            "test_corto_p4.txt",
            "test_corto_p5.txt",
            "test_long_rules.txt",
        )
        self.assertEqual(tuple(path.name for _, path in main.GRAMMAR_MENU_OPTIONS), expected)
        for number, (_, path) in enumerate(main.GRAMMAR_MENU_OPTIONS, start=1):
            with self.subTest(number=number):
                self.assertTrue(path.is_file())
                self.assertEqual(main.bundled_grammar_path(str(number)), path)

    def test_instructor_and_internal_grammars_are_grouped(self):
        titles = [title for title, _ in main.GRAMMAR_MENU_SECTIONS]
        self.assertEqual(titles, ["Gramáticas proporcionadas por Bidkar Pojoy:", "Ejercicios propios de prueba:"])
        instructor = [path.name for _, path in main.GRAMMAR_MENU_SECTIONS[0][1]]
        self.assertEqual(instructor, ["english.txt", "1.txt", "1-cnf.txt"])
        self.assertEqual(main.bundled_grammar_path("2").name, "1.txt")
        self.assertEqual(main.bundled_grammar_path("3").name, "1-cnf.txt")
        self.assertEqual(main.bundled_grammar_path("10").name, "test_long_rules.txt")
        self.assertEqual((main.CUSTOM_FILE_OPTION, main.MANUAL_OPTION), ("11", "12"))

    def test_default_grammar_is_first_menu_option(self):
        self.assertEqual(main.DEFAULT_GRAMMAR, main.GRAMMAR_MENU_OPTIONS[0][1])

    def test_menu_lists_every_option(self):
        menu = main.format_menu()
        expected_order = (
            "SELECCIÓN DE GRAMÁTICA",
            "Gramáticas proporcionadas por Bidkar Pojoy:",
            "1. English",
            "2. 1.txt — Gramática de expresiones",
            "3. 1-cnf.txt — Gramática de expresiones en CNF",
            "Ejercicios propios de prueba:",
            "4. Laboratorio 7",
            "5. Guía",
            "6. Práctica",
            "7. Corto P3",
            "8. Corto P4",
            "9. Corto P5",
            "10. Long Rules",
            "Otras opciones:",
            "11. Cargar otro archivo .txt",
            "12. Ingresar gramática manualmente",
            "0. Salir",
            "Opción:",
        )
        menu_lines = [line.strip() for line in menu.splitlines()]
        positions = [menu_lines.index(line) for line in expected_order]
        self.assertEqual(positions, sorted(positions))

    def test_invalid_choices_are_not_bundled(self):
        for choice in ("", "abc", "-1", "0", "11", "12", "15", "1.5"):
            with self.subTest(choice=choice):
                self.assertIsNone(main.bundled_grammar_path(choice))

    def test_tty_without_arguments_shows_menu_and_exits_on_eof(self):
        output = io.StringIO()
        with terminal(True), mock.patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(output):
            self.assertEqual(main.main([]), 0)
        self.assertIn("SELECCIÓN DE GRAMÁTICA", output.getvalue())

    def test_exit_option_does_not_load_grammar(self):
        with mock.patch("builtins.input", return_value="0"), mock.patch.object(main, "prepare_grammar") as prepare:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main.main(["--menu"]), 0)
        prepare.assert_not_called()

    def test_keyboard_interrupt_in_menu_exits_cleanly(self):
        with mock.patch("builtins.input", side_effect=KeyboardInterrupt), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.main(["--menu"]), 0)


class ManualGrammarInputTest(unittest.TestCase):
    def read(self, lines):
        with mock.patch("builtins.input", side_effect=lines), contextlib.redirect_stdout(io.StringIO()):
            return main.read_manual_lines()

    def test_stops_at_terminator_without_including_it(self):
        self.assertEqual(self.read(["S -> a", "FIN", "ignored"]), [(1, "S -> a")])

    def test_terminator_is_case_insensitive(self):
        for terminator in ("fin", "Fin", "  FIN  "):
            with self.subTest(terminator=terminator):
                self.assertEqual(self.read(["S -> a", terminator]), [(1, "S -> a")])

    def test_blank_and_comment_lines_are_kept_for_the_shared_parser(self):
        self.assertEqual(
            self.read(["# demo", "", "S -> a", "FIN"]), [(1, "# demo"), (2, ""), (3, "S -> a")]
        )

    def test_manual_grammar_uses_shared_parser(self):
        with mock.patch.object(main, "parse_grammar_lines", wraps=main.parse_grammar_lines) as parser:
            with mock.patch("builtins.input", side_effect=["S -> A B", "A -> a", "B -> b", "FIN"]):
                with contextlib.redirect_stdout(io.StringIO()):
                    prepared = main.prepare_menu_choice(main.MANUAL_OPTION)
        parser.assert_called_once_with([(1, "S -> A B"), (2, "A -> a"), (3, "B -> b")])
        self.assertEqual(prepared.source, "entrada manual")
        self.assertEqual(len(prepared.traces), 6)
        self.assertEqual(prepared.violations, ())


class MenuValidationLoopTest(unittest.TestCase):
    def run_loop(self, inputs, grammar="test_lab7.txt"):
        prepared = main.prepare_grammar(PROJECT_ROOT / "grammars" / grammar)
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=inputs) as fake_input, contextlib.redirect_stdout(output):
            main.menu_validation_loop(prepared, 1, False)
        return output.getvalue(), fake_input.call_count

    def test_two_consecutive_empty_inputs_return(self):
        output, calls = self.run_loop(["", ""])
        self.assertEqual(calls, 2)
        self.assertEqual(output.count("Tokens: []"), 1)

    def test_whitespace_counts_as_empty(self):
        output, calls = self.run_loop(["   ", "\t"])
        self.assertEqual(calls, 2)
        self.assertEqual(output.count("Tokens: []"), 1)

    def test_non_empty_input_resets_counter(self):
        output, calls = self.run_loop(["", "1 1", "", ""])
        self.assertEqual(calls, 4)
        self.assertEqual(output.count("Tokens: []"), 2)
        self.assertIn("Tokens: ['1', '1']", output)

    def test_no_reserved_commands(self):
        output, calls = self.run_loop(["0", "1", "q", "exit", "", ""])
        self.assertEqual(calls, 6)
        for tokens in ("['0']", "['1']", "['q']", "['exit']"):
            self.assertIn(f"Tokens: {tokens}", output)

    def test_menu_session_forces_complete_trace_and_cnf(self):
        prepared = main.prepare_grammar(PROJECT_ROOT / "grammars" / "english.txt")
        arguments = main.parse_arguments(["--menu"])
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=["", ""]), contextlib.redirect_stdout(output):
            main.run_menu_grammar_session(prepared, arguments)
        text = output.getvalue()
        self.assertFalse(arguments.trace)
        self.assertIn("  Anulables", text)
        self.assertIn("GRAMÁTICA FINAL EN CNF", text)
        self.assertLess(text.index("✓ G6 está en Forma Normal de Chomsky."), text.index("VALIDACIÓN DE CADENAS"))


if __name__ == "__main__":
    unittest.main()
