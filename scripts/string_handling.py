# Import libraries
from pylatexenc.latex2text import LatexNodes2Text

import unicodedata

def LaTeX_to_unicode(s):
    """Stip LaTeX-style accents, special characters, and ligatures from the string and convert to unicode (e.g. {\'o} and \'o -> ó
    This function covers all commands built into LaTeX.
    """

    if s is None:
        return ""

    # Convert LaTeX accents/ligatures/special characters to unicode
    s_unicode = LatexNodes2Text().latex_to_text(s)

    return s_unicode

def normalise_string(s):
    """Normalise a string, i.e. remove accents (e.g. ó -> o)
    Also accounts for LaTeX accents, ligatures, and special characters
    """

    # If s is None then return an empty string
    if s is None:
        return ""
    
    # Define the form for the normalisation
    form = "NFKD" # "compatibility deecomposition"
    
    # Convert any latex commands to unicode
    s_unicode = LaTeX_to_unicode(s)

    # Normalise the string
    s_normalised = unicodedata.normalize(form, s_unicode)

    # Convert the string to ASCII
    s_ascii = s_normalised.encode("ascii", "ignore").decode("ascii")
    
    return s_ascii