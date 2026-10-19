import unicodedata

TRAILING_PUNCTUATION = ".!?"
COMPATIBILITY_FORM = "NFKC"


def parse_sentence(text):
    normalized = unicodedata.normalize(COMPATIBILITY_FORM, text)
    return normalized.strip().lower().rstrip(TRAILING_PUNCTUATION).split()
