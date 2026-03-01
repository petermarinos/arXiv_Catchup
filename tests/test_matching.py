"""Unit tests on all matching related functions."""

# Import libraries
import unittest

# Import functions to test
from scripts.filtering import authors_match


class TestAuthorMatching(unittest.TestCase):

    def test_surname(self):
        self.assertTrue(authors_match("Thomas", "Thomas"))


if __name__ == "__main__":
    unittest.main()
