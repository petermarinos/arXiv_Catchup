"""Unit tests on all matching related function."""

# Import libraries
import unittest

# Import functions to test
from scripts.string_handling import authors_match


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

    def test_whitespace(self):
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

    def test_no_whitespace(self):
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

    # # SPECIAL CASES

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

    def test_prefixes(self):
        """Test names with prefixes."""

        self.assertTrue(authors_match("Dr. A. Thomas", "A. Thomas"))  # -> fails

    def test_suffixes(self):
        """Test names with suffixes."""

        self.assertTrue(authors_match("A. Thomas, Jr.", "Thomas"))  # -> fails

    def test_orders(self):
        """Test names that were input as 'surname, given'."""

        self.assertTrue(authors_match("Thomas, Andrew", "Thomas"))  # -> fails


# class TestWordMatching(unittest.TestCase):
#     """Test that words can be found in a large block of text.
#     Currently do these operations via regex and don't have a specific function for it."""

# Turn the following into a function so that the word matching can be tested here:
# # Lines 249 to 256 in paper.py
# pattern = rf"(?<!\w){re.escape(word)}(?!\w)"
# title = self.paper_info.title  # DO NOT ESCAPE
# title_match = re.search(pattern, title, re.IGNORECASE)

# cases to test:
# "word" in "some text word more text"
# "word" in "some text word: more text"
# "word" in "some text word, more text"
# "word" in "Word more text"
# "word" in "some text word."
# "H.E.S.S." in "text H.E.S.S. text"
# "H.E.S.S." in "text H.E.S.S.. Text"
# "H.E.S.S." in "text H.E.S.S., text"
# "AGN" not in "magnetic"

#     def test_word_matching(self):
#         """."""

#         self.assertTrue()


if __name__ == "__main__":
    unittest.main()
