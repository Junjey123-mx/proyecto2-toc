TRAILING_PUNCTUATION = ".!?"


def parse_sentence(text):
    return text.strip().lower().rstrip(TRAILING_PUNCTUATION).split()
