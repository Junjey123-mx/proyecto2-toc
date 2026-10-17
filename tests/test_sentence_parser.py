import unittest

from src.input.sentence_parser import parse_sentence

SHE_EATS_A_CAKE = ["she", "eats", "a", "cake"]


class SentenceNormalizationTest(unittest.TestCase):
    def test_converts_to_lowercase(self):
        self.assertEqual(parse_sentence("She Eats A Cake"), SHE_EATS_A_CAKE)

    def test_strips_outer_whitespace(self):
        self.assertEqual(parse_sentence("   she eats a cake   "), SHE_EATS_A_CAKE)

    def test_collapses_multiple_inner_spaces(self):
        self.assertEqual(parse_sentence("she    eats    a    cake"), SHE_EATS_A_CAKE)

    def test_splits_on_tabs_and_newlines(self):
        self.assertEqual(parse_sentence("she\teats \t a\n cake"), SHE_EATS_A_CAKE)

    def test_already_normalized_sentence_is_unchanged(self):
        self.assertEqual(
            parse_sentence("the cat drinks the beer"),
            ["the", "cat", "drinks", "the", "beer"],
        )

    def test_returns_list_of_strings(self):
        tokens = parse_sentence("She eats.")
        self.assertIsInstance(tokens, list)
        self.assertTrue(all(isinstance(token, str) for token in tokens))


class TrailingPunctuationTest(unittest.TestCase):
    def test_removes_final_period(self):
        self.assertEqual(parse_sentence("she eats a cake."), SHE_EATS_A_CAKE)

    def test_removes_final_exclamation(self):
        self.assertEqual(parse_sentence("she eats a cake!"), SHE_EATS_A_CAKE)

    def test_removes_final_question_mark(self):
        self.assertEqual(parse_sentence("she eats a cake?"), SHE_EATS_A_CAKE)

    def test_removes_mixed_final_sequence(self):
        self.assertEqual(parse_sentence("she eats a cake?!?"), SHE_EATS_A_CAKE)

    def test_removes_final_punctuation_before_trailing_whitespace(self):
        self.assertEqual(parse_sentence("  She eats a cake!  "), SHE_EATS_A_CAKE)

    def test_keeps_inner_punctuation(self):
        self.assertEqual(parse_sentence("cat,dog"), ["cat,dog"])

    def test_keeps_inner_period_and_question_mark(self):
        self.assertEqual(parse_sentence("e.g. why? yes."), ["e.g.", "why?", "yes"])


class EdgeSentenceTest(unittest.TestCase):
    def test_empty_sentence(self):
        self.assertEqual(parse_sentence(""), [])

    def test_whitespace_only_sentence(self):
        self.assertEqual(parse_sentence(" \t\n  "), [])

    def test_punctuation_only_sentence(self):
        self.assertEqual(parse_sentence("!!!"), [])

    def test_single_word(self):
        self.assertEqual(parse_sentence("She."), ["she"])

    def test_unknown_token_is_kept(self):
        self.assertEqual(parse_sentence("She likes cake."), ["she", "likes", "cake"])

    def test_project_example_sentence(self):
        self.assertEqual(
            parse_sentence("She eats a cake with a fork."),
            ["she", "eats", "a", "cake", "with", "a", "fork"],
        )


if __name__ == "__main__":
    unittest.main()
