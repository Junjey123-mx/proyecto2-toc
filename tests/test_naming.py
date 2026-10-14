import unittest

from src.utils.naming import candidate_names, fresh_indexed_variable, fresh_variable


class FreshVariableTest(unittest.TestCase):
    def test_returns_base_when_free(self):
        self.assertEqual(fresh_variable("S0", {"S", "A"}), "S0")

    def test_adds_suffix_on_collision(self):
        self.assertEqual(fresh_variable("S0", {"S", "S0"}), "S0_1")

    def test_skips_every_taken_suffix(self):
        self.assertEqual(fresh_variable("U_a", {"U_a", "U_a_1", "U_a_2"}), "U_a_3")

    def test_candidates_are_deterministic(self):
        names = candidate_names("U_a")
        self.assertEqual([next(names) for _ in range(3)], ["U_a", "U_a_1", "U_a_2"])


class FreshIndexedVariableTest(unittest.TestCase):
    def test_starts_at_first_index(self):
        self.assertEqual(fresh_indexed_variable("X", {"S"}), ("X1", 1))

    def test_skips_existing_indices(self):
        self.assertEqual(fresh_indexed_variable("X", {"X1", "X2", "X4"}), ("X3", 3))

    def test_continues_from_given_index(self):
        self.assertEqual(fresh_indexed_variable("X", {"X4"}, start=4), ("X5", 5))


if __name__ == "__main__":
    unittest.main()
