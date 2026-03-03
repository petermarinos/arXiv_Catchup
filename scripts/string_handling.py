"""Functions used for handling strings."""

# Import standard libraries
# from unicodedata import normalize as normalise  # Fix a spelling error
from typing import cast
import re

# Import non-standard libraries
from pylatexenc.latex2text import LatexNodes2Text  # type: ignore[import-untyped]
from unidecode import unidecode


def authors_match(name_1: str, name_2: str) -> bool:
    """Check if two author strings match.

    inputs
    ------
    name_1, name_2 : The two authors that are being tested against one another.

    outputs
    -------
    : True if a matches b, False otherwise.
    """

    # If any of the if statements hits -> not a match and can return False
    # If reaching the end without any hits -> names match so return True
    # Slight performance benefit to return as soon as *any* of these statements hit
    # pylint: disable=R0911

    # Strip the two names
    a = name_1.strip().split()
    b = name_2.strip().split()

    # Ensure both stripped strings have an entry
    if not a or not b:
        return False

    # If the surnames are not exact matches
    if a[-1] != b[-1]:
        return False

    # Extract given names
    givens_a, givens_b = a[:-1], b[:-1]

    # Split initials (if they are initials without whitespace)
    givens_a = split_initials(givens_a)
    givens_b = split_initials(givens_b)

    # Compute number of given names
    n = min(len(givens_a), len(givens_b))

    # Loop through the given names
    for i in range(n):

        # Extract the tokens (i.e. full name or initial) and their values
        token_a, value_a = find_token(givens_a[i])
        token_b, value_b = find_token(givens_b[i])

        # # Check if the tokens and values don't match
        # If both tokens are full names but are not equal:
        if token_a == "full" and token_b == "full" and value_a != value_b:
            return False

        # If both tokens are initials and are not equal
        if token_a == "initial" and token_b == "initial" and value_a != value_b:
            return False

        # If one is an initial and one is full,
        #     and the initial doesn't match the first letter of the full:
        if token_a == "initial" and token_b == "full" and value_a != value_b[0]:
            return False
        if token_a == "full" and token_b == "initial" and value_a[0] != value_b:
            return False

    # If passing all tests for all surnames and given names, match will be True
    return True


def words_match_pattern(word: str) -> str:
    """Check if a word is contained within a larger string.

    inputs
    ------
    word : the word to search for.

    outputs
    -------
    : the regex pattern that will be searched for
    """

    return rf"(?<!\w){re.escape(word)}(?!\w)"


def normalise_string(s: str | None) -> str:
    """First removes LaTeX commands, then normalises the string, then converts to ASCII.

    inputs
    ------
    s : Any string that may (or may not) contain LaTeX commands, accented characters, etc..

    outputs
    -------
    s_asci : The input string in basic ASCII encoding. No accents or LaTeX commands, etc..

    examples
    --------
    '{\'o}' -> 'o'
    '\'o'   -> 'o'
    'ó'     -> 'o'
    """

    # If s is None then return an empty string
    if s is None:
        return ""

    # Convert any latex commands to unicode
    # pylatexenc doesn't have type hints.
    # Explicity cast the result to a string and ignore type hinting.
    # If the input is not a string then pylatexenc will raise an error.
    s_unicode = cast(str, LatexNodes2Text().latex_to_text(s))  # type: ignore

    # Normalise the string
    # # Use "compatibility decomposition"
    # s_normalised = normalise("NFKD", s_unicode)  # Function from unicodedata
    # Use unidecode
    s_normalised = unidecode(s_unicode)

    # Convert the string to ASCII
    s_ascii = s_normalised.encode("ascii", "ignore").decode("ascii")

    return s_ascii


def split_initials(name: list[str]) -> list[str]:
    """Splits initials that are not separated by whitespace.
    Does nothing if there are no initials or the initials were already split.
    NOTE: arXiv demands authors are listed with whitespace between initials. However, some entries
          do not obey this rule, so we should always check.

    inputs
    ------
    name : List containing the author name that has been split on all whitespace

    outputs
    -------
    name : List containing the author name that has been split on all whitespace and initials

    examples
    --------
    ['A.S.W,', 'Thomas']        -> ['A.', 'S.', 'W.', 'Thomas']
    ['A.', 'S.', 'W.', 'Thomas] -> ['A.', 'S.', 'W.', 'Thomas']
    ['Andrew', 'Thomas']        -> ['Andrew', 'Thomas']
    """

    # If the name is empty, return it back
    if not name:
        return name

    # Join names in the case a list is passed
    joined_name = " ".join(name)

    # Split at the whitespace, and take the first block
    split_name = joined_name.split()[0]

    # Define regex token for two initials, with periods, not separated by whitespace
    token = r"^(?:[A-Z]\.){2,}$"

    if len(re.findall(token, split_name)) >= 1:

        initial_list = re.findall(r"[A-Z]\.", split_name)
        name = list(initial_list)

    return name


def find_token(name: str) -> tuple[str, str]:
    """Determine if the supplied string is a 'full' name or an initial.

    inputs
    ------
    name : The author's name

    outputs
    -------
    : Tuple describing the name as an initial or full name.

    examples
    --------
    'Name' -> full
    'G.'   -> initial
    """

    # Define the regex for an initial
    initial_regex = re.compile(r"^[A-Z]\.?$")

    # Strip the name into a list
    name = name.strip()

    # If it is an initial:
    if initial_regex.match(name):
        return ("initial", name[0])

    # Else it is a full name
    return ("full", name)
