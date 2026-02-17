# Import libraries
from pylatexenc.latex2text import LatexNodes2Text
from unicodedata           import normalize       as normalise
import re

def LaTeX_to_unicode(s):
    """Stip LaTeX-style accents, special characters, and ligatures from the string and convert to unicode (e.g. {\'o} and \'o -> ó).
    This function covers all commands built into LaTeX.

    inputs
    ------
    s : str
        Any string that may (or may not) contain LaTeX commands.

    outputs
    -------
    s_unicode : str
        The input string, stripped of all LaTeX commands.
    """

    # if s is None:
    #     return ""

    # Convert LaTeX accents/ligatures/special characters to unicode
    s_unicode = LatexNodes2Text().latex_to_text(s)

    return s_unicode

def normalise_string(s):
    """First removes LaTeX commands/etc., then normalises the string (i.e. ensures a consisted unicode encoding), then converts to ASCII.

    inputs
    ------
    s : str
        Any string that may (or may not) contain LaTeX commands, accented characters, etc..

    outputs
    -------
    s_asci : str
        The input string in basic ASCII encoding. No accents or LaTeX commands, etc..
    """

    # If s is None then return an empty string
    if s is None:
        return ""
    
    # Define the form for the normalisation
    form = "NFKD" # "compatibility deecomposition"
    
    # Convert any latex commands to unicode
    s_unicode = LaTeX_to_unicode(s)

    # Normalise the string
    s_normalised = normalise(form, s_unicode) # Function from unicodedata

    # Convert the string to ASCII
    s_ascii = s_normalised.encode("ascii", "ignore").decode("ascii")
    
    return s_ascii

def split_initials(name: list[str]) -> list[str]:
    """Splits initials that are not separated by whitespace

    example
    -------
    ['A.S.W']          -> ['A.', 'S.', 'W.']
    ['A.', 'S.', 'W.'] -> ['A.', 'S.', 'W.']
    """

    # If the name is empty, return it back
    if not name:
        return name

    # Join names in the case a list is passed
    joined_name = " ".join([_ for _ in name])

    # Split at the whitespace, and take the first block
    split_name  = joined_name.split()[0]

    # Define regex token for two initials, with periods, not separated by whitespace
    token = r"^(?:[A-Z]\.){2,}$"

    if re.findall(token, split_name):

        initial_list = re.findall(r"[A-Z]\.", split_name)
        name = [_ for _ in initial_list]

    return name