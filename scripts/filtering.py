"""Functions used in the filtering operations."""

# Import functions
from .string_handling import split_initials, find_token


def authors_match(a: str, b: str) -> bool:
    """Check if two author strings match.

    inputs
    ------
    a, b : The two authors that are being tested against one another.

    outputs
    -------
    : True if a matches b, False otherwise.
    """

    # Strip the two names
    A = a.strip().split()
    B = b.strip().split()

    # Ensure both stripped strings have an entry
    if not A or not B:
        return False

    # If the surnames are not exact matches
    if A[-1] != B[-1]:
        return False

    # Extract given names
    givens_a, givens_b = A[:-1], B[:-1]

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

        # If one is an initial and one is full, and the initial doesn't match the first letter of the full:
        if token_a == "initial" and token_b == "full" and value_a != value_b[0]:
            return False
        if token_a == "full" and token_b == "initial" and value_a[0] != value_b:
            return False

    # If passing all tests for all surnames and given names, it is a match!
    return True
