"""Unit tests on all matching related function."""

# Import libraries
import unittest
import re

# Import functions to test
from scripts.string_handling import authors_match, words_match_pattern


class TestAuthorMatching(unittest.TestCase):
    """Test the author matching algorithm."""

    def test_name_versus_name(self):
        """Test names with no initials."""
        self.assertTrue(
            authors_match(
                "Andrew Sydney Withiel Thomas", "Andrew Sydney Withiel Thomas"
            )
        )
        self.assertTrue(
            authors_match("Andrew Sydney Thomas", "Andrew Sydney Withiel Thomas")
        )
        self.assertTrue(authors_match("Andrew Thomas", "Andrew Sydney Withiel Thomas"))
        self.assertTrue(authors_match("Thomas", "Andrew Sydney Withiel Thomas"))
        self.assertTrue(authors_match("Andrew Sydney Thomas", "Andrew Sydney Thomas"))
        self.assertTrue(authors_match("Andrew Thomas", "Andrew Sydney Thomas"))
        self.assertTrue(authors_match("Thomas", "Andrew Sydney Thomas"))
        self.assertTrue(authors_match("Andrew Thomas", "Andrew Thomas"))
        self.assertTrue(authors_match("Thomas", "Andrew Thomas"))
        self.assertTrue(authors_match("Thomas", "Thomas"))

    def test_name_versus_initials(self):
        """Test names with versus without initials."""
        self.assertTrue(
            authors_match("Andrew Sydney Withiel Thomas", "A. S. W. Thomas")
        )
        self.assertTrue(authors_match("Andrew Sydney Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("Andrew Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("Andrew Sydney Withiel Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("Andrew Sydney Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("Andrew Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("Andrew Sydney Withiel Thomas", "A. Thomas"))
        self.assertTrue(authors_match("Andrew Sydney Thomas", "A. Thomas"))
        self.assertTrue(authors_match("Andrew Thomas", "A. Thomas"))
        self.assertTrue(authors_match("Thomas", "A. Thomas"))

    def test_initials_whitespace(self):
        """Test names with initials."""

        # With a period
        self.assertTrue(authors_match("A. S. W. Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("A. S. W. Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A. S. W. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A. S. Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A. S. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A. Thomas"))

        # Without a period
        self.assertTrue(authors_match("A S W Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("A S W Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A S W Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A S Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A S Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A Thomas", "A. Thomas"))

    def test_initials_no_whitespace(self):
        """Test names with initials that have no whitespace match with those with whitespace, and
        test that no whitespace matches with no whitespace.
        """

        # Only one has whitespace
        self.assertTrue(authors_match("A.S.W. Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A. S. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A. S. W. Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A. S. Thomas"))

        # Neither have whitespace
        self.assertTrue(authors_match("A.S.W. Thomas", "A.S.W. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "A.S. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A.S.W. Thomas", "Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A.S.W. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A.S. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A.S. Thomas", "Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A.S.W. Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A.S. Thomas"))
        self.assertTrue(authors_match("A. Thomas", "A. Thomas"))
        self.assertTrue(authors_match("A. Thomas", "Thomas"))
        self.assertTrue(authors_match("Thomas", "A.S.W. Thomas"))
        self.assertTrue(authors_match("Thomas", "A.S. Thomas"))
        self.assertTrue(authors_match("Thomas", "A. Thomas"))

    def test_falses(self):
        """Test for cases that *should not* match."""

        self.assertFalse(
            authors_match("Andrew Sydney Withiel Thomas", "Andrew Sydney Wayne Thomas")
        )
        self.assertFalse(
            authors_match("Andrew Sydney Withiel Thomas", "A. S. W. Smith")
        )
        self.assertFalse(
            authors_match(
                "Andrew Sydney Withiel Thomas", "Alexander Sydney Withiel Thomas"
            )
        )
        self.assertFalse(authors_match("A.S.W. Thomas", "A.S.Z. Thomas"))
        self.assertFalse(authors_match("Thomas", "Smith"))

    def test_apostrophes(self):
        """Test names with apostrophes."""

        self.assertTrue(authors_match("A. O'Neill", "O'Neill"))

    def test_hyphenated(self):
        """Test hyphenated names."""

        self.assertTrue(authors_match("A. Hyphenated-Name", "Hyphenated-Name"))

    def test_particles(self):
        """Test names with particles."""

        self.assertTrue(authors_match("Ludwig van Beethoven", "Beethoven"))
        self.assertTrue(authors_match("L. van Beethoven", "Beethoven"))
        self.assertTrue(
            authors_match("Ludwig van Beethoven", "van Beethoven")
        )  # -> fails
        self.assertTrue(authors_match("L. van Beethoven", "van Beethoven"))  # -> fails

    def test_suffixes(self):
        """Test names with suffixes.
        NOTE: rare edge case
        """

        self.assertTrue(authors_match("A. Thomas Jr.", "Thomas"))  # -> fails

    def test_orders(self):
        """Test names that were input as 'surname givenname'.
        NOTE: Using non-Eurocentric orders like this should be rejected by arXiv. However, some
              submissions get through, so it should be accounted for.
        """

        self.assertTrue(authors_match("Thomas Andrew", "Thomas"))  # -> fails

    # def test_prefixes(self):
    #     """Test names with prefixes.
    #     NOTE: These will be rejected by arXiv. I have never seen one pass, so it is not necessary
    #           to account for them.
    #     """

    #     self.assertTrue(authors_match("Dr. A. Thomas", "A. Thomas"))  # -> fails


class TestWordMatching(unittest.TestCase):
    """Test that words can be found in a large block of text."""

    def test_word(self):
        """Test words"""

        pattern = words_match_pattern("word")

        self.assertIsNotNone(
            re.search(pattern, "some text word more text", re.IGNORECASE)
        )
        self.assertIsNotNone(
            re.search(pattern, "some text word, more text", re.IGNORECASE)
        )
        self.assertIsNotNone(
            re.search(pattern, "some text word: more text", re.IGNORECASE)
        )
        self.assertIsNotNone(re.search(pattern, "Word more text", re.IGNORECASE))
        self.assertIsNotNone(re.search(pattern, "some text word.", re.IGNORECASE))

    def test_words(self):
        """Test words"""

        pattern = words_match_pattern("words with spaces")

        self.assertIsNotNone(
            re.search(pattern, "some text words with spaces more text", re.IGNORECASE)
        )

    def test_acronym(self):
        """Test acronyms"""

        pattern = words_match_pattern("AGN")
        self.assertIsNone(re.search(pattern, "magnetic", re.IGNORECASE))

        pattern = words_match_pattern("H.E.S.S.")
        self.assertIsNotNone(re.search(pattern, "text H.E.S.S. text", re.IGNORECASE))
        self.assertIsNotNone(re.search(pattern, "text H.E.S.S.. Text", re.IGNORECASE))
        self.assertIsNotNone(re.search(pattern, "text H.E.S.S., text", re.IGNORECASE))

    def test_symbol(self):
        """Test acronyms"""

        pattern = words_match_pattern("ɣ")
        self.assertIsNotNone(re.search(pattern, "some text ɣ more text", re.IGNORECASE))

    def test_maths(self):
        """Test acronyms"""

        pattern = words_match_pattern(r"$\alpha$")
        self.assertIsNone(
            re.search(pattern, "some text alpha more text", re.IGNORECASE)
        )
        self.assertIsNotNone(
            re.search(pattern, r"some text $\alpha$ more text", re.IGNORECASE)
        )


if __name__ == "__main__":
    unittest.main()
