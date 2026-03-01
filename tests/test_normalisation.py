"""Unit tests on string normalisation function."""

# Import libraries
import unittest

# Import functions to test
from scripts.string_handling import normalise_string


class TestStringNormalisation(unittest.TestCase):
    """Test the string normalisation algorithm for all characters/LaTeX commands that could appear
    in the author fields."""

    def test_latex_nonbraced_accents(self):
        """Test strings with non-braced LaTeX accents."""

        self.assertEqual(normalise_string(r"\`a"), "a")
        self.assertEqual(normalise_string(r"\'i"), "i")
        self.assertEqual(normalise_string(r"\'o"), "o")
        self.assertEqual(normalise_string(r"\"o"), "o")
        self.assertEqual(normalise_string(r"\"u"), "u")

    def test_latex_braced_accents(self):
        """Test strings with braced LaTeX accents."""

        self.assertEqual(normalise_string(r"{\`a}"), "a")
        self.assertEqual(normalise_string(r"{\'{e}}"), "e")
        self.assertEqual(normalise_string(r"{\'i}"), "i")
        self.assertEqual(normalise_string(r"{\'o}"), "o")
        self.assertEqual(normalise_string(r"{\"o}"), "o")
        self.assertEqual(normalise_string(r"{\"{o}}"), "o")
        self.assertEqual(normalise_string(r"{\"u}"), "u")

    def test_latex_special_accents_upper(self):
        """Test strings with special LaTeX accents on upper-case letters."""

        self.assertEqual(normalise_string(r"{\c C}"), "C")
        self.assertEqual(normalise_string(r"{\v S}"), "S")

    def test_latex_special_accents_lower(self):
        """Test strings with special LaTeX commands on lower-case letters."""

        self.assertEqual(normalise_string(r"\^e"), "e")
        self.assertEqual(normalise_string(r"\r{a}"), "a")
        self.assertEqual(normalise_string(r"\v{c}"), "c")
        self.assertEqual(normalise_string(r"\u{g}"), "g")
        self.assertEqual(normalise_string(r"\i"), "i")
        self.assertEqual(normalise_string(r"\j"), "j")
        self.assertEqual(normalise_string(r"\l"), "l")
        self.assertEqual(normalise_string(r"\o"), "o")
        self.assertEqual(normalise_string(r"\=o"), "o")
        self.assertEqual(normalise_string(r"\H{o}"), "o")
        self.assertEqual(normalise_string(r"\underbar{o}"), "o")
        self.assertEqual(normalise_string(r"\~n"), "n")
        self.assertEqual(normalise_string(r"\c{s}"), "s")
        self.assertEqual(normalise_string(r"\ss"), "ss")
        self.assertEqual(normalise_string(r"\d{u}"), "u")

    def test_latex_special_characters_upper(self):
        """Test strings with LaTeX special upper-case characters."""

        self.assertEqual(normalise_string(r"\AA"), "A")
        self.assertEqual(normalise_string(r"\AE"), "AE")
        self.assertEqual(normalise_string(r"\OE"), "OE")

    def test_latex_special_characters_lower(self):
        """Test strings with LaTeX special lower-case characters."""

        self.assertEqual(normalise_string(r"\aa"), "a")
        self.assertEqual(normalise_string(r"\ae"), "ae")
        self.assertEqual(normalise_string(r"\oe"), "oe")

    def test_ligatures(self):
        """Test strings with non-ASCII ligatures."""

        self.assertEqual(normalise_string("ﬁ"), "fi")
        self.assertEqual(normalise_string("ﬂ"), "fl")
        self.assertEqual(normalise_string("ﬀ"), "ff")
        self.assertEqual(normalise_string("ﬃ"), "ffi")
        self.assertEqual(normalise_string("ﬄ"), "ffl")

    def test_unicode_accents_upper(self):
        """Test strings with unicode accents on upper-case characters."""

        self.assertEqual(normalise_string("Ä"), "A")
        self.assertEqual(normalise_string("Å"), "A")
        self.assertEqual(normalise_string("Ö"), "O")
        self.assertEqual(normalise_string("Ø"), "O")
        self.assertEqual(normalise_string("Ş"), "S")
        self.assertEqual(normalise_string("Ü"), "U")

    def test_unicode_accents_lower(self):
        """Test strings with unicode accents on lower-case characters"""

        self.assertEqual(normalise_string("å"), "a")
        self.assertEqual(normalise_string("a\u030a"), "a")  # ring above
        self.assertEqual(normalise_string("ä"), "a")
        self.assertEqual(normalise_string("ć"), "c")
        self.assertEqual(normalise_string("č"), "c")
        self.assertEqual(normalise_string("ç"), "c")
        self.assertEqual(normalise_string("e\u0301"), "e")  # e + combining acute
        self.assertEqual(normalise_string("đ"), "d")
        self.assertEqual(normalise_string("ń"), "n")
        self.assertEqual(normalise_string("ó"), "o")
        self.assertEqual(normalise_string("ö"), "o")
        self.assertEqual(normalise_string("ø"), "o")
        self.assertEqual(normalise_string("o͡o"), "oo")
        self.assertEqual(normalise_string("š"), "s")
        self.assertEqual(normalise_string("ş"), "s")
        self.assertEqual(normalise_string("ü"), "u")
        self.assertEqual(normalise_string("ụ"), "u")
        self.assertEqual(normalise_string("ž"), "z")

    def test_unicode_nonenglish_upper(self):
        """Test strings with unicode non-English upper-case characters."""

        self.assertEqual(normalise_string("Æ"), "AE")
        self.assertEqual(normalise_string("Ð"), "D")
        self.assertEqual(normalise_string("İ"), "I")
        self.assertEqual(normalise_string("Ł"), "L")
        self.assertEqual(normalise_string("ẞ"), "SS")
        self.assertEqual(normalise_string("Þ"), "Th")

    def test_unicode_nonenglish_lower(self):
        """Test strings with unicode non-English lower-case characters."""

        self.assertEqual(normalise_string("æ"), "ae")
        self.assertEqual(normalise_string("ð"), "d")
        self.assertEqual(normalise_string("ı"), "i")
        self.assertEqual(normalise_string("ł"), "l")
        self.assertEqual(normalise_string("ß"), "ss")
        self.assertEqual(normalise_string("þ"), "th")
