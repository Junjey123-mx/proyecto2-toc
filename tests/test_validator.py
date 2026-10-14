import unittest

from src.input.grammar_validator import GrammarSyntaxError, validate_grammar_lines


def numbered(*lines):
    return list(enumerate(lines, start=1))


class ValidGrammarSyntaxTest(unittest.TestCase):
    def assert_single_rule(self, line, lhs, alternatives):
        rules = validate_grammar_lines(numbered(line))
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].lhs, lhs)
        self.assertEqual(rules[0].alternatives, alternatives)

    def test_accepts_sequence_of_symbols(self):
        self.assert_single_rule("S -> NP VP", "S", (("NP", "VP"),))

    def test_accepts_alternatives(self):
        self.assert_single_rule("A -> a | b", "A", (("a",), ("b",)))

    def test_accepts_multi_symbol_alternatives(self):
        self.assert_single_rule(
            "NP -> Det N | he | she", "NP", (("Det", "N"), ("he",), ("she",))
        )

    def test_accepts_epsilon_symbol(self):
        self.assert_single_rule("A -> ε", "A", (("ε",),))

    def test_accepts_epsilon_word(self):
        self.assert_single_rule("A -> epsilon", "A", (("epsilon",),))

    def test_accepts_digit_terminals(self):
        self.assert_single_rule("S -> 0 A 0", "S", (("0", "A", "0"),))

    def test_accepts_flexible_spacing_around_arrow_and_bars(self):
        self.assert_single_rule("  S->a   |b|  c   d  ", "S", (("a",), ("b",), ("c", "d")))

    def test_skips_blank_lines(self):
        rules = validate_grammar_lines(numbered("", "   ", "S -> a"))
        self.assertEqual([rule.line_number for rule in rules], [3])

    def test_skips_comment_lines(self):
        rules = validate_grammar_lines(numbered("# comment", "   # indented", "S -> a"))
        self.assertEqual([rule.line_number for rule in rules], [3])

    def test_keeps_source_line_numbers_and_order(self):
        rules = validate_grammar_lines(numbered("S -> A", "", "A -> a", "# x", "A -> b"))
        self.assertEqual([(rule.line_number, rule.lhs) for rule in rules], [(1, "S"), (3, "A"), (5, "A")])


class InvalidGrammarSyntaxTest(unittest.TestCase):
    def assert_rejected_at_line(self, line, line_number=3):
        source = numbered("S -> a", "", line)
        with self.assertRaises(GrammarSyntaxError) as context:
            validate_grammar_lines(source)
        self.assertEqual(context.exception.line_number, line_number)
        self.assertIn(f"Line {line_number}", str(context.exception))

    def test_rejects_missing_arrow(self):
        self.assert_rejected_at_line("S NP VP")

    def test_rejects_missing_rhs(self):
        self.assert_rejected_at_line("S -> ")

    def test_rejects_empty_alternative_between_bars(self):
        self.assert_rejected_at_line("S -> a | | b")

    def test_rejects_trailing_empty_alternative(self):
        self.assert_rejected_at_line("S -> a |")

    def test_rejects_multiple_lhs_symbols(self):
        self.assert_rejected_at_line("S A -> a")

    def test_rejects_multiple_arrows(self):
        self.assert_rejected_at_line("S -> a -> b")

    def test_rejects_missing_lhs(self):
        self.assert_rejected_at_line("-> a")

    def test_rejects_epsilon_lhs(self):
        self.assert_rejected_at_line("ε -> a")

    def test_rejects_epsilon_mixed_with_symbols(self):
        self.assert_rejected_at_line("A -> a ε")

    def test_rejects_alternatives_on_lhs(self):
        self.assert_rejected_at_line("A|B -> a")

    def test_rejects_source_without_productions(self):
        with self.assertRaises(GrammarSyntaxError) as context:
            validate_grammar_lines(numbered("", "# only comments"))
        self.assertIsNone(context.exception.line_number)


if __name__ == "__main__":
    unittest.main()
