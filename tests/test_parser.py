import unittest
from pathlib import Path

from src.input.grammar_parser import parse_grammar_file, parse_grammar_lines
from src.input.grammar_validator import GrammarSyntaxError
from src.model.production import Production

GRAMMARS_DIRECTORY = Path(__file__).resolve().parent.parent / "grammars"

AUXILIARY_GRAMMARS = {
    "test_lab7.txt": ({"S", "A", "B", "C"}, {"0", "1"}, 8),
    "test_guia.txt": ({"S", "A", "B", "C"}, {"a", "b", "c"}, 7),
    "test_practica.txt": ({"S", "A", "B", "C", "D"}, {"a", "b", "c", "d"}, 9),
    "test_corto_p3.txt": ({"S", "A", "B", "C"}, {"b", "c", "d"}, 6),
    "test_corto_p4.txt": ({"S", "A", "B"}, {"a", "b"}, 6),
    "test_corto_p5.txt": ({"S", "A", "B", "C"}, {"a", "b"}, 6),
    "test_long_rules.txt": ({"S", "A", "B", "C", "D"}, {"a", "b", "c", "d"}, 5),
}


def parse_text(*lines):
    return parse_grammar_lines(enumerate(lines, start=1))


class EnglishGrammarTest(unittest.TestCase):
    def setUp(self):
        self.result = parse_grammar_file(GRAMMARS_DIRECTORY / "english.txt")
        self.grammar = self.result.grammar

    def test_start_symbol(self):
        self.assertEqual(self.grammar.start_symbol, "S")

    def test_variable_count(self):
        self.assertEqual(len(self.grammar.variables), 8)
        self.assertEqual(self.grammar.variables, {"S", "VP", "PP", "NP", "V", "P", "N", "Det"})

    def test_terminal_count(self):
        self.assertEqual(len(self.grammar.terminals), 21)
        self.assertIn("cooks", self.grammar.terminals)
        self.assertIn("spoon", self.grammar.terminals)

    def test_production_count(self):
        self.assertEqual(len(self.grammar.productions), 30)

    def test_has_no_warnings(self):
        self.assertEqual(self.result.warnings, ())


class AuxiliaryGrammarsTest(unittest.TestCase):
    def test_all_auxiliary_grammars_load(self):
        for file_name, (variables, terminals, production_count) in AUXILIARY_GRAMMARS.items():
            with self.subTest(file_name=file_name):
                result = parse_grammar_file(GRAMMARS_DIRECTORY / file_name)
                self.assertEqual(result.grammar.start_symbol, "S")
                self.assertEqual(result.grammar.variables, variables)
                self.assertEqual(result.grammar.terminals, terminals)
                self.assertEqual(len(result.grammar.productions), production_count)
                self.assertEqual(result.warnings, ())

    def test_lab7_epsilon_production(self):
        grammar = parse_grammar_file(GRAMMARS_DIRECTORY / "test_lab7.txt").grammar
        self.assertIn(Production("C", ()), grammar.productions)


class GrammarParserTest(unittest.TestCase):
    def test_splits_alternatives_into_productions(self):
        grammar = parse_text("A -> B C | a | ε", "B -> b", "C -> c").grammar
        self.assertEqual(
            grammar.productions_for("A"),
            (Production("A", ("B", "C")), Production("A", ("a",)), Production("A", ())),
        )

    def test_epsilon_becomes_empty_rhs(self):
        grammar = parse_text("S -> ε").grammar
        self.assertEqual(grammar.productions, (Production("S", ()),))
        self.assertNotIn("ε", grammar.terminals)

    def test_epsilon_word_and_symbol_are_equivalent(self):
        grammar = parse_text("S -> a | epsilon", "S -> ε").grammar
        self.assertEqual(grammar.productions, (Production("S", ("a",)), Production("S", ())))
        self.assertEqual(grammar.terminals, {"a"})

    def test_forward_references_are_variables(self):
        grammar = parse_text("S -> A B", "A -> a", "B -> b").grammar
        self.assertEqual(grammar.variables, {"S", "A", "B"})
        self.assertEqual(grammar.terminals, {"a", "b"})

    def test_duplicate_productions_are_removed(self):
        grammar = parse_text("S -> a | a", "S -> a | b").grammar
        self.assertEqual(grammar.productions, (Production("S", ("a",)), Production("S", ("b",))))

    def test_first_declared_variable_is_start_symbol(self):
        grammar = parse_text("# comment", "", "E -> T", "T -> x", "S -> E").grammar
        self.assertEqual(grammar.start_symbol, "E")

    def test_infers_terminals_from_non_variable_symbols(self):
        grammar = parse_text("S -> 0 A 0 | 1 S 1", "A -> x y").grammar
        self.assertEqual(grammar.terminals, {"0", "1", "x", "y"})

    def test_unknown_variable_like_symbol_warns_without_correction(self):
        result = parse_text("S -> Np VP", "NP -> Det N", "VP -> eats", "Det -> the", "N -> dog")
        self.assertIn("Np", result.grammar.terminals)
        self.assertNotIn("Np", result.grammar.variables)
        self.assertIn(Production("S", ("Np", "VP")), result.grammar.productions)
        self.assertEqual([(w.line_number, w.symbol) for w in result.warnings], [(1, "Np")])

    def test_warns_once_per_unknown_symbol(self):
        result = parse_text("S -> X a | X", "S -> X")
        self.assertEqual([w.symbol for w in result.warnings], ["X"])

    def test_lowercase_terminals_do_not_warn(self):
        self.assertEqual(parse_text("S -> a b 0").warnings, ())

    def test_syntax_errors_propagate_with_line_number(self):
        with self.assertRaises(GrammarSyntaxError) as context:
            parse_text("S -> a", "S A -> b")
        self.assertEqual(context.exception.line_number, 2)


if __name__ == "__main__":
    unittest.main()
