"""Functions used for handling strings."""

# Import standard libraries
from unicodedata import normalize as normalise  # Fix a spelling error
from typing import cast
import re

# Import non-standard libraries
from pylatexenc.latex2text import LatexNodes2Text  # type: ignore[import-untyped]


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
    # Use "compatibility decomposition"
    s_normalised = normalise("NFKD", s_unicode)  # Function from unicodedata

    # Convert the string to ASCII
    s_ascii = s_normalised.encode("ascii", "ignore").decode("ascii")

    return s_ascii


def split_initials(name: list[str]) -> list[str]:
    """Splits initials that are not separated by whitespace.
    Does nothing if there are no initials or the initials were already split.

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
