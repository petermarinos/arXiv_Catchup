"""Functions used in the filtering operations."""

# Import functions
from .string_handling import split_initials, find_token


def authors_match(name_1: str, name_2: str) -> bool:
    """Check if two author strings match.

    inputs
    ------
    name_1, name_2 : The two authors that are being tested against one another.

    outputs
    -------
    match : True if a matches b, False otherwise.
    """

    # Initialise the output
    # Assume true, then search for ways it could be false
    match = False

    # Strip the two names
    a = name_1.strip().split()
    b = name_2.strip().split()

    # Ensure both stripped strings have an entry
    if not a or not b:
        match = False

    # If the surnames are not exact matches
    if a[-1] != b[-1]:
        match = False

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
            match = False

        # If both tokens are initials and are not equal
        if token_a == "initial" and token_b == "initial" and value_a != value_b:
            match = False

        # If one is an initial and one is full,
        #     and the initial doesn't match the first letter of the full:
        if token_a == "initial" and token_b == "full" and value_a != value_b[0]:
            match = False
        if token_a == "full" and token_b == "initial" and value_a[0] != value_b:
            match = False

    # If passing all tests for all surnames and given names, match will be True
    return match
