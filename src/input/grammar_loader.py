from pathlib import Path


class GrammarLoadError(Exception):
    pass


def load_grammar_lines(path):
    source = Path(path)
    if not source.exists():
        raise GrammarLoadError(f"Grammar file not found: {source}")
    if not source.is_file():
        raise GrammarLoadError(f"Grammar path is not a file: {source}")
    try:
        text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise GrammarLoadError(f"Cannot read grammar file {source}: {error}") from error
    return [(line_number, line) for line_number, line in enumerate(text.splitlines(), start=1)]
