"""Unit tests for QuantumSubsetSum."""

import unittest

from qss import QuantumSubsetSum


class TestQuantumSubsetSum(unittest.TestCase):
    """QuantumSubsetSum tests."""

    def test_no_solution(self):
        """Tests that no subsets are returned if none add up to the target sum."""
        values = [1, 3, 11]

        target_sum = 8

        expected_answer_subsets = []

        self.check_answer_subsets(values, target_sum, expected_answer_subsets)

    def test_single_solution(self):
        """Tests that a single subset is returned if only one adds up to the target sum."""
        values = [5, 2, 1]

        target_sum = 3

        expected_answer_subsets = [[2, 1]]

        self.check_answer_subsets(values, target_sum, expected_answer_subsets)

    def test_multiple_solutions(self):
        """Tests that multiple subsets are returned if multiple add up to the target sum."""
        values = [5, 7, 8, 9, 1]

        target_sum = 16

        expected_answer_subsets = [
            [7, 8, 1],
            [7, 9],
        ]

        self.check_answer_subsets(values, target_sum, expected_answer_subsets)

    def test_target_sum_in_set(self):
        """
        Tests that a subset containing only the target sum is returned
        when the target sum is present in the input set.
        """
        values = [1, 3, 6, 4, 2]

        target_sum = 6

        expected_answer_subsets = [
            [6],
            [4, 2],
            [1, 3, 2],
        ]

        self.check_answer_subsets(values, target_sum, expected_answer_subsets)

    def test_negative_numbers_in_set(self):
        """
        Tests that the algorithm solves the subset sum problem for negative integers.
        """
        values = [1, -3, 7]

        target_sum = 5

        expected_answer_subsets = [
            [1, -3, 7],
        ]

        self.check_answer_subsets(values, target_sum, expected_answer_subsets)

    def check_answer_subsets(self, values, target_sum, expected_answers):
        """A helper function for determining if a set of answer subsets is valid."""
        qss = QuantumSubsetSum(values, target_sum)
        answer_subsets = qss.execute()

        self.assertEqual(len(answer_subsets), len(expected_answers))

        for subset, _ in answer_subsets:
            self.assertIn(subset, expected_answers)
