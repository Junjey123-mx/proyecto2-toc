import tempfile
import unittest
from pathlib import Path

from src.input.grammar_loader import GrammarLoadError, load_grammar_lines


class GrammarLoaderTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write_source(self, content, encoding="utf-8"):
        path = self.root / "grammar.txt"
        path.write_bytes(content.encode(encoding))
        return path

    def test_loads_valid_file_as_numbered_lines(self):
        path = self.write_source("S -> A\nA -> a\n")
        self.assertEqual(load_grammar_lines(path), [(1, "S -> A"), (2, "A -> a")])

    def test_accepts_string_path(self):
        path = self.write_source("S -> a\n")
        self.assertEqual(load_grammar_lines(str(path)), [(1, "S -> a")])

    def test_reads_utf8_symbols(self):
        path = self.write_source("A -> ε | ñ\n")
        self.assertEqual(load_grammar_lines(path), [(1, "A -> ε | ñ")])

    def test_ignores_utf8_byte_order_mark(self):
        path = self.write_source("S -> a\n", encoding="utf-8-sig")
        self.assertEqual(load_grammar_lines(path), [(1, "S -> a")])

    def test_preserves_original_line_numbers_including_blank_and_comment_lines(self):
        path = self.write_source("# header\n\nS -> A\n\n  \nA -> a")
        self.assertEqual(
            load_grammar_lines(path),
            [(1, "# header"), (2, ""), (3, "S -> A"), (4, ""), (5, "  "), (6, "A -> a")],
        )

    def test_empty_file_has_no_lines(self):
        path = self.write_source("")
        self.assertEqual(load_grammar_lines(path), [])

    def test_missing_file_raises_load_error(self):
        with self.assertRaisesRegex(GrammarLoadError, "not found"):
            load_grammar_lines(self.root / "missing.txt")

    def test_directory_raises_load_error(self):
        with self.assertRaisesRegex(GrammarLoadError, "not a file"):
            load_grammar_lines(self.root)

    def test_invalid_utf8_raises_load_error(self):
        path = self.root / "invalid.txt"
        path.write_bytes(b"S -> \xff\n")
        with self.assertRaisesRegex(GrammarLoadError, "Cannot read"):
            load_grammar_lines(path)


if __name__ == "__main__":
    unittest.main()
