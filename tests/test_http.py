"""Unit tests on http requests."""

# Import libraries
from email.message import Message
from unittest.mock import patch
import unittest

# Import functions to test
# from scripts.string_handling import authors_match, words_match_pattern


class TestHttpRequests(unittest.TestCase):
    """Test the http requests and error handling."""


# Test error handling
# Add an indent to the "attempt to connect to arXiv"--"return parsed_xml_date" lines
# -- add proper testing in the future

# # HTTP ERRORS

# # http error with a random code and no header
# err = urllib.error.HTTPError(
#     url=None, code=47, msg="fake error that should exit", hdrs=None, fp=None
# )
# with patch("urllib.request.urlopen", side_effect=err):

# # http repeating error code with no header
# err = urllib.error.HTTPError(
#     url=None, code=408, msg="non-repeating code", hdrs=None, fp=None
# )
# with patch("urllib.request.urlopen", side_effect=err):

# # http non-repeating error code with a useless header
# headers = Message()
# headers["blank"] = "nothing"
# err = urllib.error.HTTPError(
#     url=None, code=408, msg="non-repeating code", hdrs=headers, fp=None
# )
# with patch("urllib.request.urlopen", side_effect=err):

# # http error with a retry-after header
# headers = Message()
# headers["Retry-After"] = 40
# err = urllib.error.HTTPError(
#     url=None, code=429, msg="repeating code", hdrs=headers, fp=None
# )
# with patch("urllib.request.urlopen", side_effect=err):

# # URL ERRORS

# # non-Verification errors
# with patch(
#     "urllib.request.urlopen", side_effect=urllib.error.URLError("DNS fail")
# ):

# # Verification errors
# err = urllib.error.URLError(
#     ssl.SSLCertVerificationError(
#         "certificate verify failed: unable to get local issuer certificate"
#     )
# )
# with patch("urllib.request.urlopen", side_effect=err):
