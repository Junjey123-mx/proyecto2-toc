import argparse
from pathlib import Path

DEFAULT_GRAMMAR = Path(__file__).resolve().parent / "grammars" / "english.txt"


def positive_runs(text):
    try:
        runs = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' no es un entero") from None
    if runs < 1:
        raise argparse.ArgumentTypeError("debe ser un entero mayor o igual que 1")
    return runs


def build_argument_parser():
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Determina con CYK si una oración pertenece al lenguaje de una gramática libre de contexto.",
    )
    parser.add_argument("--grammar", type=Path, default=DEFAULT_GRAMMAR, metavar="RUTA", help="archivo .txt de la gramática")
    parser.add_argument("--trace", action="store_true", help="muestra las tablas de cada fase")
    parser.add_argument("--show-cnf", action="store_true", help="imprime la gramática final en CNF")
    parser.add_argument("--show-table", action="store_true", help="imprime la tabla CYK de cada oración")
    parser.add_argument("--runs", type=positive_runs, default=1, metavar="N", help="repite CYK N veces y reporta la mediana")
    return parser


def parse_arguments(argv=None):
    return build_argument_parser().parse_args(argv)


def main(argv=None):
    parse_arguments(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
