import re
import unittest

from src.algorithms.chomsky.converter import to_cnf
from src.algorithms.chomsky.validator import cnf_violations
from src.algorithms.simplification.simplify import simplify
from src.model.production import Production
from src.model.trace import Trace
from src.output.trace_formatter import (
    banner,
    format_cnf_check,
    format_cnf_grammar,
    format_cnf_validation,
    format_conclusions,
    format_grammar,
    format_table,
    format_trace,
    format_traces,
    format_value,
)
from tests.grammar_helpers import grammar_from, load


class FormatValueTest(unittest.TestCase):
    def test_formats_productions_sets_and_pairs(self):
        self.assertEqual(format_value(Production("A", ("B", "c"))), "A -> B c")
        self.assertEqual(format_value(Production("A")), "A -> ε")
        self.assertEqual(format_value(frozenset({"B", "A"})), "{A, B}")
        self.assertEqual(format_value(frozenset()), "∅")
        self.assertEqual(format_value((("S", "A"), ("S", "B"))), "(S, A), (S, B)")
        self.assertEqual(format_value(()), "—")


class FormatTableTest(unittest.TestCase):
    def test_aligns_columns(self):
        lines = format_table([{"Col": "a", "Otra": "bbb"}, {"Col": "cccc", "Otra": "d"}])
        self.assertEqual(lines[0], "Col  | Otra")
        self.assertEqual(lines[2], "a    | bbb")
        self.assertEqual(lines[3], "cccc | d")

    def test_empty_table(self):
        self.assertEqual(format_table([]), ["(sin filas)"])


class FormatGrammarTest(unittest.TestCase):
    def test_groups_alternatives_with_start_first(self):
        grammar = grammar_from("S -> A b | ε", "A -> a | A a")
        self.assertEqual(format_grammar(grammar), "S -> A b | ε\nA -> a | A a")

    def test_grammar_without_productions(self):
        _, traces = simplify(grammar_from("S -> a S"))
        self.assertEqual(format_grammar(traces[-1].result), "(sin producciones)")


class FormatTraceTest(unittest.TestCase):
    def test_renders_every_phase_of_english(self):
        grammar = load("english.txt")
        simplified, simplification_traces = simplify(grammar)
        _, cnf_traces = to_cnf(simplified)
        text = format_traces(simplification_traces + cnf_traces)
        for expected in (
            "FASE 0 — NUEVO SÍMBOLO INICIAL",
            "FASE 1 — ELIMINACIÓN DE ε",
            "N = ∅ ⇒ G1 = G0",
            "No hay producciones unitarias",
            "Sin símbolos inútiles ⇒ G3 = G2",
            "Ningún terminal acompañado ⇒ G4 = G3",
            "Ningún RHS tiene longitud > 2 ⇒ no aplica",
        ):
            self.assertIn(expected, text)

    def test_renders_tables_and_result(self):
        _, traces = simplify(load("test_corto_p3.txt"))
        text = format_trace(traces[1])
        self.assertIn("Anulables", text)
        self.assertIn("Variantes", text)
        self.assertIn("S -> A B C d | A B d | A C d | B C d | A d | B d | C d | d", text)

    def test_can_hide_tables(self):
        _, traces = simplify(load("test_corto_p3.txt"))
        self.assertNotIn("Variantes", format_trace(traces[1], show_tables=False))

    def test_conclusions_have_one_line_per_phase(self):
        _, traces = simplify(load("test_guia.txt"))
        self.assertEqual(len(format_conclusions(traces).splitlines()), 4)

    def test_cnf_check(self):
        cnf = load("english.txt")
        self.assertEqual(
            format_cnf_check(cnf, cnf_violations(cnf)),
            "✓ Gramática en CNF\n  30 producciones válidas",
        )
        invalid = grammar_from("S -> A", "A -> a")
        self.assertIn("producción unitaria", format_cnf_check(invalid, cnf_violations(invalid)))


STEP_PATTERN = re.compile(r"^(\d+)\. ", re.MULTILINE)
PHASE_BANNERS = (
    "FASE 0 — NUEVO SÍMBOLO INICIAL",
    "FASE 1 — ELIMINACIÓN DE ε",
    "FASE 2 — PRODUCCIONES UNITARIAS",
    "FASE 3 — SÍMBOLOS INÚTILES",
    "FASE 4 — AISLAR TERMINALES",
    "FASE 5 — BINARIZACIÓN",
)


def all_traces(file_name):
    simplified, simplification_traces = simplify(load(file_name))
    cnf, cnf_traces = to_cnf(simplified)
    return cnf, simplification_traces + cnf_traces


def step_numbers(text):
    return [int(number) for number in STEP_PATTERN.findall(text)]


class AcademicTracePresentationTest(unittest.TestCase):
    def setUp(self):
        _, self.english_traces = all_traces("english.txt")
        _, self.lab7_traces = all_traces("test_lab7.txt")
        self.english = format_traces(self.english_traces)
        self.lab7 = format_traces(self.lab7_traces)

    def test_every_phase_has_centered_banner(self):
        for title in PHASE_BANNERS:
            with self.subTest(title=title):
                self.assertIn(f"{'=' * 40}\n{title.center(40).rstrip()}\n{'=' * 40}", self.lab7)

    def test_phase_banners_follow_phase_order(self):
        positions = [self.lab7.index(title) for title in PHASE_BANNERS]
        self.assertEqual(positions, sorted(positions))

    def test_banner_has_blank_line_before_and_after(self):
        for title in PHASE_BANNERS[1:]:
            with self.subTest(title=title):
                index = self.lab7.index(banner(title))
                self.assertEqual(self.lab7[index - 2 : index], "\n\n")
                self.assertTrue(self.lab7[index + len(banner(title)) :].startswith("\n\n"))

    def test_step_numbering_is_continuous_across_phases(self):
        for text in (self.english, self.lab7):
            numbers = step_numbers(text)
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_each_phase_ends_with_grammar_step(self):
        for phase in range(6):
            with self.subTest(phase=phase):
                block = self.lab7.split(PHASE_BANNERS[phase], 1)[1].split("Conclusión de la fase:", 1)[0]
                last_step = STEP_PATTERN.split(block)[-1]
                self.assertTrue(last_step.startswith(f"Construir G{phase}"))
                self.assertIn(f"Gramática resultante G{phase} (", last_step)

    def test_steps_are_separated_by_two_blank_lines(self):
        self.assertIn("\n\n\n2. Determinar el símbolo inicial resultante", self.lab7)
        self.assertIn("\n\n\n5. Generar las variantes sin producciones-ε", self.lab7)
        self.assertIn("\n\n\n12. Eliminar las variables no generadoras", self.lab7)

    def test_tables_stay_under_numbered_steps(self):
        for table in ("Condiciones", "Anulables", "Variantes", "Unitarias", "Pares unitarios", "No unitarias",
                      "3a Generadores", "3b Alcanzables", "Envoltorios", "Binarización"):
            with self.subTest(table=table):
                self.assertRegex(self.lab7, rf"\n\d+\. [^\n]+\n\n +{re.escape(table)}\n")
        step_nine = self.lab7.split("\n9. Transferir las producciones no unitarias", 1)[1].split("\n10. ", 1)[0]
        self.assertIn("\n   Transferencias\n", step_nine)

    def test_results_are_on_their_own_line(self):
        self.assertIn("   Resultado:\n   N = {A, B, C, S, S0}", self.lab7)
        self.assertIn("Resultado:\n    3b Alcanzables: {A, B, S0}", self.lab7)
        self.assertIn("Resultado:\n    Terminales acompañados: 0, 1", self.lab7)

    def test_not_applicable_steps_do_not_invent_tables(self):
        block = self.english.split("FASE 2 — PRODUCCIONES UNITARIAS", 1)[1].split("FASE 3", 1)[0]
        self.assertIn("8. Calcular los pares unitarios\n\n   Resultado:\n   No aplica.", block)
        self.assertNotIn("Pares unitarios\n", block)

    def test_empty_operations_report_clear_results(self):
        self.assertIn("No existen producciones unitarias.", self.english)
        self.assertIn("No se requieren variables envoltorio.", self.english)
        self.assertIn("Ningún RHS tiene longitud mayor que 2.", self.english)

    def test_conclusion_is_separated_from_grammar(self):
        self.assertIn("\n\n\nConclusión de la fase:\nN = ∅ ⇒ G1 = G0", self.english)
        self.assertEqual(self.lab7.count("Conclusión de la fase:"), 6)

    def test_conclusion_skips_notes_already_shown_as_results(self):
        block = self.lab7.split("FASE 1 — ELIMINACIÓN DE ε", 1)[1].split("FASE 2", 1)[0]
        conclusion = block.split("Conclusión de la fase:", 1)[1]
        self.assertNotIn("\nN = {A, B, C, S, S0}\n", conclusion)
        self.assertIn("N = {A, B, C, S, S0} ⇒ G1 sin producciones-ε, salvo S0 -> ε", conclusion)

    def test_conclusion_keeps_final_note_even_if_repeated(self):
        trace = Trace("Fase 9: extra", grammar_from("S -> a"), {}, ["única nota"])
        self.assertTrue(format_trace(trace).endswith("Conclusión de la fase:\núnica nota"))

    def test_lab7_details_are_not_hidden(self):
        for detail in ("Nuevo símbolo inicial: S0", "S0 -> ε", "U_0", "U_1", "X6", "Variables auxiliares creadas: X1, X2, X3, X4, X5, X6"):
            with self.subTest(detail=detail):
                self.assertIn(detail, self.lab7)

    def test_single_trace_starts_numbering_at_one(self):
        self.assertTrue(format_trace(self.lab7_traces[3]).split("\n\n", 2)[1].startswith("1. "))

    def test_unknown_phase_uses_generic_steps(self):
        trace = Trace("unit", grammar_from("S -> a"), {"Pasos": [{"Columna": "valor"}]}, ["fin"])
        text = format_trace(trace)
        self.assertIn("UNIT", text)
        self.assertIn("1. Pasos", text)
        self.assertIn("2. Construir la gramática resultante", text)

    def test_hidden_tables_keep_results(self):
        text = format_trace(self.lab7_traces[1], show_tables=False)
        self.assertNotIn("Iteración |", text)
        self.assertIn("N = {A, B, C, S, S0}", text)


class CnfSectionsTest(unittest.TestCase):
    def test_final_cnf_section(self):
        cnf, _ = all_traces("test_lab7.txt")
        text = format_cnf_grammar(cnf)
        self.assertTrue(text.startswith(banner("GRAMÁTICA FINAL EN CNF")))
        self.assertIn("|V| = 11\n|Σ| = 2\n|R| = 24\nInicial: S0\n\nS0 -> ε | U_0 X1", text)

    def test_cnf_validation_section(self):
        cnf, _ = all_traces("english.txt")
        self.assertEqual(
            format_cnf_validation(cnf, cnf_violations(cnf)),
            f"{banner('VALIDACIÓN DE CNF')}\n\n✓ Gramática en CNF\n  30 producciones válidas",
        )

    def test_banner_width(self):
        lines = banner("VALIDACIÓN DE CNF").splitlines()
        self.assertEqual(lines[0], "=" * 40)
        self.assertEqual(lines[2], "=" * 40)
        self.assertLessEqual(len(lines[1]), 40)


if __name__ == "__main__":
    unittest.main()
