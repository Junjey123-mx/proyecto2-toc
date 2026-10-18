import contextlib
import io
import unittest
from pathlib import Path
from unittest import mock

import main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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
        with mock.patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(output):
            self.assertEqual(main.main([]), 0)
        self.assertIn("CYK PARSER — TOC", output.getvalue())

    def test_main_reports_missing_grammar(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main.main(["--grammar", str(PROJECT_ROOT / "no_existe.txt")]), 1)
        self.assertTrue(errors.getvalue().startswith("Error: "))


if __name__ == "__main__":
    unittest.main()
