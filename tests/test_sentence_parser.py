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


PDF_SHE_SENTENCE = "𝑆ℎ𝑒 𝑒𝑎𝑡𝑠 𝑎 𝑐𝑎𝑘𝑒 𝑤𝑖𝑡ℎ 𝑎 𝑓𝑜𝑟𝑘"
PDF_CAT_SENTENCE = "𝑇ℎ𝑒 𝑐𝑎𝑡 𝑑𝑟𝑖𝑛𝑘𝑠 𝑡ℎ𝑒 𝑏𝑒𝑒𝑟"
SHE_EATS_WITH_FORK = ["she", "eats", "a", "cake", "with", "a", "fork"]


class CompatibilityUnicodeTest(unittest.TestCase):
    def test_mathematical_italic_sentence_from_pdf(self):
        self.assertEqual(parse_sentence(PDF_SHE_SENTENCE), SHE_EATS_WITH_FORK)

    def test_second_pdf_sentence(self):
        self.assertEqual(parse_sentence(PDF_CAT_SENTENCE), ["the", "cat", "drinks", "the", "beer"])

    def test_mathematical_unicode_with_trailing_punctuation(self):
        self.assertEqual(parse_sentence("𝑆ℎ𝑒 𝑒𝑎𝑡𝑠 𝑎 𝑐𝑎𝑘𝑒!"), SHE_EATS_A_CAKE)
        self.assertEqual(parse_sentence("𝑆ℎ𝑒 𝑒𝑎𝑡𝑠 𝑎 𝑐𝑎𝑘𝑒."), SHE_EATS_A_CAKE)

    def test_ascii_variants_match_unicode_variant(self):
        for sentence in ("She eats a cake with a fork", "SHE EATS A CAKE WITH A FORK", PDF_SHE_SENTENCE):
            with self.subTest(sentence=sentence):
                self.assertEqual(parse_sentence(sentence), SHE_EATS_WITH_FORK)

    def test_ascii_input_is_unchanged_by_normalization(self):
        for sentence in ("cat,dog", "e.g. why? yes.", "she\teats \t a\n cake", "!!!", ""):
            with self.subTest(sentence=sentence):
                self.assertEqual(
                    parse_sentence(sentence), sentence.strip().lower().rstrip(".!?").split()
                )

    def test_other_compatibility_forms_are_normalized(self):
        self.assertEqual(parse_sentence("ｓｈｅ　ｅａｔｓ"), ["she", "eats"])
        self.assertEqual(parse_sentence("𝐒𝐇𝐄 𝐞𝐚𝐭𝐬"), ["she", "eats"])

    def test_greek_epsilon_survives_normalization(self):
        self.assertEqual(parse_sentence("ε"), ["ε"])


if __name__ == "__main__":
    unittest.main()
