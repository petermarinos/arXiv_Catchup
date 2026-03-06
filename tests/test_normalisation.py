"""Unit tests on string normalisation function."""

# Import libraries
import unittest

# Import functions to test
from src.arxiv_catchup.string_handling import normalise_string


class TestStringNormalisation(unittest.TestCase):
    """Test the string normalisation algorithm for all characters/LaTeX commands that could appear
    in the author fields.
    NOTE: All LaTeX commands and accents explicitly allowed by arXiv are tested here. All other
          unicode characters should also work.
          https://info.arxiv.org/help/prep.html#accents
    """

    def test_ligatures(self):
        """Test strings with non-ASCII ligatures."""

        test_list = [["ﬁ", "fi"], ["ﬂ", "fl"], ["ﬀ", "ff"], ["ﬃ", "ffi"], ["ﬄ", "ffl"]]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_latex_braced_vs_nonbraced(self):
        """Test that all representations of LaTeX accents are accepted."""

        test_list = [
            [r"\`e", "e"],
            [r"{\`e}", "e"],
            [r"{\'{e}}", "e"],
            [r"{\c C}", "C"],
            [r"\c{C}", "C"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_latex_accents_upper(self):
        """Test strings with special LaTeX accents on upper-case letters."""

        test_list = [
            [r"\"A", "A"],
            [r"\'A", "A"],
            [r"\.A", "A"],
            [r"\=A", "A"],
            [r"\^A", "A"],
            [r"\`A", "A"],
            [r"\k{A}", "A"],
            [r"\r{A}", "A"],
            [r"\u{A}", "A"],
            [r"\v{A}", "A"],
            [r"\~A", "A"],
            [r"\'C", "C"],
            [r"\.C", "C"],
            [r"\^C", "C"],
            [r"\c{C}", "C"],
            [r"\v{C}", "C"],
            [r"\v{D}", "D"],
            [r"\"E", "E"],
            [r"\'E", "E"],
            [r"\.E", "E"],
            [r"\=E", "E"],
            [r"\^E", "E"],
            [r"\`E", "E"],
            [r"\c{E}", "E"],
            [r"\k{E}", "E"],
            [r"\u{E}", "E"],
            [r"\v{E}", "E"],
            [r"\.G", "G"],
            [r"\^G", "G"],
            [r"\c{G}", "G"],
            [r"\u{G}", "G"],
            [r"\v{G}", "G"],
            [r"\^H", "H"],
            [r"\v{H}", "H"],
            [r"\"I", "I"],
            [r"\'I", "I"],
            [r"\.I", "I"],
            [r"\=I", "I"],
            [r"\^I", "I"],
            [r"\`I", "I"],
            [r"\k{I}", "I"],
            [r"\u{I}", "I"],
            [r"\v{I}", "I"],
            [r"\~I", "I"],
            [r"\^J", "J"],
            [r"\c{K}", "K"],
            [r"\v{K}", "K"],
            [r"\'L", "L"],
            [r"\c{L}", "L"],
            [r"\v{L}", "L"],
            [r"\'N", "N"],
            [r"\c{N}", "N"],
            [r"\v{N}", "N"],
            [r"\~N", "N"],
            [r"\"O", "O"],
            [r"\'O", "O"],
            [r"\.O", "O"],
            [r"\=O", "O"],
            [r"\^O", "O"],
            [r"\`O", "O"],
            [r"\H{O}", "O"],
            [r"\k{O}", "O"],
            [r"\u{O}", "O"],
            [r"\v{O}", "O"],
            [r"\~O", "O"],
            [r"\'R", "R"],
            [r"\c{R}", "R"],
            [r"\v{R}", "R"],
            [r"\'S", "S"],
            [r"\^S", "S"],
            [r"\c{S}", "S"],
            [r"\v{S}", "S"],
            [r"\c{T}", "T"],
            [r"\v{T}", "T"],
            [r"\"U", "U"],
            [r"\'U", "U"],
            [r"\=U", "U"],
            [r"\^U", "U"],
            [r"\`U", "U"],
            [r"\H{U}", "U"],
            [r"\k{U}", "U"],
            [r"\r{U}", "U"],
            [r"\u{U}", "U"],
            [r"\v{U}", "U"],
            [r"\~U", "U"],
            [r"\^W", "W"],
            [r"\"Y", "Y"],
            [r"\'Y", "Y"],
            [r"\=Y", "Y"],
            [r"\^Y", "Y"],
            [r"\'Z", "Z"],
            [r"\.Z", "Z"],
            [r"\v{Z}", "Z"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_unicode_accents_upper(self):
        """Test strings with unicode accents on upper-case characters."""

        test_list = [
            ["Ä", "A"],
            ["Á", "A"],
            ["Ȧ", "A"],
            ["Ā", "A"],
            ["Â", "A"],
            ["À", "A"],
            ["Å", "A"],
            ["Ą", "A"],
            ["Ă", "A"],
            ["Ǎ", "A"],
            ["Ã", "A"],
            ["Ć", "C"],
            ["Ċ", "C"],
            ["Ĉ", "C"],
            ["Ç", "C"],
            ["Č", "C"],
            ["Ď", "D"],
            ["Ë", "E"],
            ["É", "E"],
            ["Ė", "E"],
            ["Ē", "E"],
            ["Ê", "E"],
            ["È", "E"],
            ["Ȩ", "E"],
            ["Ę", "E"],
            ["Ĕ", "E"],
            ["Ě", "E"],
            ["Ġ", "G"],
            ["Ĝ", "G"],
            ["Ģ", "G"],
            ["Ğ", "G"],
            ["Ǧ", "G"],
            ["Ĥ", "H"],
            ["Ȟ", "H"],
            ["Ï", "I"],
            ["Í", "I"],
            ["İ", "I"],
            ["Ī", "I"],
            ["Î", "I"],
            ["Ì", "I"],
            ["Į", "I"],
            ["Ĭ", "I"],
            ["Ǐ", "I"],
            ["Ĩ", "I"],
            ["Ĵ", "J"],
            ["Ķ", "K"],
            ["Ǩ", "K"],
            ["Ĺ", "L"],
            ["Ļ", "L"],
            ["Ľ", "L"],
            ["Ń", "N"],
            ["Ņ", "N"],
            ["Ň", "N"],
            ["Ñ", "N"],
            ["Ö", "O"],
            ["Ó", "O"],
            ["Ȯ", "O"],
            ["Ō", "O"],
            ["Ô", "O"],
            ["Ò", "O"],
            ["Ő", "O"],
            ["Ǫ", "O"],
            ["Ŏ", "O"],
            ["Ǒ", "O"],
            ["Õ", "O"],
            ["Ŕ", "R"],
            ["Ŗ", "R"],
            ["Ř", "R"],
            ["Ś", "S"],
            ["Ŝ", "S"],
            ["Ş", "S"],
            ["Š", "S"],
            ["Ţ", "T"],
            ["Ť", "T"],
            ["Ü", "U"],
            ["Ú", "U"],
            ["Ū", "U"],
            ["Û", "U"],
            ["Ù", "U"],
            ["Ű", "U"],
            ["Ų", "U"],
            ["Ů", "U"],
            ["Ŭ", "U"],
            ["Ǔ", "U"],
            ["Ũ", "U"],
            ["Ŵ", "W"],
            ["Ÿ", "Y"],
            ["Ý", "Y"],
            ["Ȳ", "Y"],
            ["Ŷ", "Y"],
            ["Ź", "Z"],
            ["Ż", "Z"],
            ["Ž", "Z"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_latex_accents_lower(self):
        """Test strings with special LaTeX commands on lower-case letters."""

        test_list = [
            [r"\"a", "a"],
            [r"\'a", "a"],
            [r"\.a", "a"],
            [r"\=a", "a"],
            [r"\^a", "a"],
            [r"\`a", "a"],
            [r"\k{a}", "a"],
            [r"\r{a}", "a"],
            [r"\u{a}", "a"],
            [r"\v{a}", "a"],
            [r"\~a", "a"],
            [r"\'c", "c"],
            [r"\.c", "c"],
            [r"\^c", "c"],
            [r"\c{c}", "c"],
            [r"\v{c}", "c"],
            [r"\v{d}", "d"],
            [r"\"e", "e"],
            [r"\'e", "e"],
            [r"\.e", "e"],
            [r"\=e", "e"],
            [r"\^e", "e"],
            [r"\`e", "e"],
            [r"\c{e}", "e"],
            [r"\k{e}", "e"],
            [r"\u{e}", "e"],
            [r"\v{e}", "e"],
            [r"\.g", "g"],
            [r"\^g", "g"],
            [r"\c{g}", "g"],
            [r"\u{g}", "g"],
            [r"\v{g}", "g"],
            [r"\^h", "h"],
            [r"\v{h}", "h"],
            [r"\"i", "i"],
            [r"\'i", "i"],
            [r"\=i", "i"],
            [r"\^i", "i"],
            [r"\`i", "i"],
            [r"\k{i}", "i"],
            [r"\u{i}", "i"],
            [r"\v{i}", "i"],
            [r"\~i", "i"],
            [r"\^j", "j"],
            [r"\c{k}", "k"],
            [r"\v{k}", "k"],
            [r"\'l", "l"],
            [r"\c{l}", "l"],
            [r"\v{l}", "l"],
            [r"\'n", "n"],
            [r"\c{n}", "n"],
            [r"\v{n}", "n"],
            [r"\~n", "n"],
            [r"\"o", "o"],
            [r"\'o", "o"],
            [r"\.o", "o"],
            [r"\=o", "o"],
            [r"\^o", "o"],
            [r"\`o", "o"],
            [r"\H{o}", "o"],
            [r"\k{o}", "o"],
            [r"\u{o}", "o"],
            [r"\v{o}", "o"],
            [r"\~o", "o"],
            [r"\underbar{o}", "o"],
            [r"\'r", "r"],
            [r"\c{r}", "r"],
            [r"\v{r}", "r"],
            [r"\'s", "s"],
            [r"\^s", "s"],
            [r"\c{s}", "s"],
            [r"\v{s}", "s"],
            [r"\c{t}", "t"],
            [r"\v{t}", "t"],
            [r"\"u", "u"],
            [r"\'u", "u"],
            [r"\=u", "u"],
            [r"\^u", "u"],
            [r"\`u", "u"],
            [r"\d{u}", "u"],
            [r"\H{u}", "u"],
            [r"\k{u}", "u"],
            [r"\r{u}", "u"],
            [r"\u{u}", "u"],
            [r"\v{u}", "u"],
            [r"\~u", "u"],
            [r"\^w", "w"],
            [r"\"y", "y"],
            [r"\'y", "y"],
            [r"\=y", "y"],
            [r"\^y", "y"],
            [r"\'z", "z"],
            [r"\.z", "z"],
            [r"\v{z}", "z"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_unicode_accents_lower(self):
        """Test strings with unicode accents on lower-case characters"""

        test_list = [
            ["ä", "a"],
            ["á", "a"],
            ["ȧ", "a"],
            ["ā", "a"],
            ["â", "a"],
            ["à", "a"],
            ["ą", "a"],
            ["å", "a"],
            ["a\u030a", "a"],  # ring above
            ["ă", "a"],
            ["ǎ", "a"],
            ["ã", "a"],
            ["ć", "c"],
            ["ċ", "c"],
            ["ĉ", "c"],
            ["ç", "c"],
            ["č", "c"],
            ["ď", "d"],
            ["ë", "e"],
            ["é", "e"],
            ["e\u0301", "e"],  # e + combining acute
            ["ė", "e"],
            ["ē", "e"],
            ["ê", "e"],
            ["è", "e"],
            ["ȩ", "e"],
            ["ę", "e"],
            ["ĕ", "e"],
            ["ě", "e"],
            ["ġ", "g"],
            ["ĝ", "g"],
            ["ģ", "g"],
            ["ğ", "g"],
            ["ǧ", "g"],
            ["ĥ", "h"],
            ["ȟ", "h"],
            ["ï", "i"],
            ["í", "i"],
            ["ī", "i"],
            ["î", "i"],
            ["ì", "i"],
            ["į", "i"],
            ["ĭ", "i"],
            ["ǐ", "i"],
            ["ĩ", "i"],
            ["ĵ", "j"],
            ["ķ", "k"],
            ["ǩ", "k"],
            ["ĺ", "l"],
            ["ļ", "l"],
            ["ľ", "l"],
            ["ń", "n"],
            ["ņ", "n"],
            ["ň", "n"],
            ["ñ", "n"],
            ["ö", "o"],
            ["ó", "o"],
            ["ȯ", "o"],
            ["ō", "o"],
            ["ô", "o"],
            ["ò", "o"],
            ["ő", "o"],
            ["ǫ", "o"],
            ["ŏ", "o"],
            ["ǒ", "o"],
            ["õ", "o"],
            ["o͡o", "oo"],
            ["ŕ", "r"],
            ["ŗ", "r"],
            ["ř", "r"],
            ["ś", "s"],
            ["ŝ", "s"],
            ["ş", "s"],
            ["š", "s"],
            ["ţ", "t"],
            ["ť", "t"],
            ["ü", "u"],
            ["ú", "u"],
            ["ū", "u"],
            ["û", "u"],
            ["ù", "u"],
            ["ű", "u"],
            ["ų", "u"],
            ["ů", "u"],
            ["ŭ", "u"],
            ["ǔ", "u"],
            ["ũ", "u"],
            ["ụ", "u"],
            ["ŵ", "w"],
            ["ÿ", "y"],
            ["ý", "y"],
            ["ȳ", "y"],
            ["ŷ", "y"],
            ["ź", "z"],
            ["ż", "z"],
            ["ž", "z"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_latex_nonenglish_upper(self):
        """Test strings with LaTeX special upper-case characters."""

        test_list = [
            [r"{\AA}", "A"],
            [r"{\AE}", "AE"],
            [r"{\DH}", "D"],
            [r"{\DJ}", "D"],
            # [r"{\ETH}", "D"], # not accepted by arXiv
            [r"{\L}", "L"],
            [r"{\NG}", "NG"],
            [r"{\O}", "O"],
            [r"{\OE}", "OE"],
            # [r"{\SS}", "SS"], # not accepted by arXiv
            [r"{\TH}", "Th"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_unicode_nonenglish_upper(self):
        """Test strings with unicode non-English upper-case characters."""

        test_list = [
            ["Å", "A"],
            ["Æ", "AE"],
            ["Ð", "D"],  # NOTE: These are different
            ["Đ", "D"],  # NOTE: These are different
            ["Ð", "D"],  # NOTE: These are different
            ["Ł", "L"],
            ["Ŋ", "NG"],
            ["Ø", "O"],
            ["Œ", "OE"],
            ["ẞ", "SS"],
            ["Þ", "Th"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_latex_nonenglish_lower(self):
        """Test strings with LaTeX special lower-case characters."""

        test_list = [
            [r"{\aa}", "a"],
            [r"{\ae}", "ae"],
            [r"{\dh}", "d"],
            [r"{\dj}", "d"],
            [r"{\eth}", "sh"],
            [r"{\i}", "i"],
            [r"{\j}", "j"],
            [r"{\l}", "l"],
            [r"{\ng}", "ng"],
            [r"{\o}", "o"],
            [r"{\oe}", "oe"],
            [r"{\ss}", "ss"],
            [r"{\th}", "th"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)

    def test_unicode_nonenglish_lower(self):
        """Test strings with unicode non-English lower-case characters."""

        test_list = [
            ["å", "a"],
            ["æ", "ae"],
            ["ð", "d"],
            ["đ", "d"],
            ["ð", "d"],
            ["ı", "i"],
            ["ł", "l"],
            ["ŋ", "ng"],
            ["ø", "o"],
            ["œ", "oe"],
            ["ß", "ss"],
            ["þ", "th"],
        ]

        for test_str, expected_str in test_list:
            self.assertEqual(normalise_string(test_str), expected_str)


if __name__ == "__main__":
    unittest.main()
