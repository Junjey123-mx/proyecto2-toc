"""Tokenización de oraciones para la entrada de CYK."""

import unicodedata

TRAILING_PUNCTUATION = ".!?"
COMPATIBILITY_FORM = "NFKC"


def parse_sentence(text):
    """Normaliza el texto de la oración y devuelve los tokens que usa CYK.

    NFKC convierte letras estilo PDF (𝑆ℎ𝑒) a ASCII; solo se quitan '.', '!' y '?' finales.
    Un resultado vacío representa la cadena vacía ε.
    """
    normalized = unicodedata.normalize(COMPATIBILITY_FORM, text)
    return normalized.strip().lower().rstrip(TRAILING_PUNCTUATION).split()
