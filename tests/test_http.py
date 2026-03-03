"""Unit tests on http requests."""

# Import libraries
from email.message import Message
from unittest.mock import patch, MagicMock
import unittest
import ssl
import urllib.error
import xml.etree.ElementTree as ET

# Import functions to test
from scripts.http_client import HttpClient, TooManyAttempts


class TestHttpRequests(unittest.TestCase):
    """Test the http requests and error handling.
    NOTE: Patch the prett_sleep function for all tests to prevent unnecessary sleeps.
    """

    def setUp(self) -> None:
        self.url_template = "http://example.test/?start={start_num}&max={blocksize}"

    @patch("scripts.http_client.pretty_sleep")
    def test_arxiv_query_success(self, _sleep_mock: float):
        """Test that the arxiv_query returns a result if there are no errors."""

        # Prepare a fake response context manager
        response = MagicMock()
        response.read.return_value = b"<feed></feed>"
        cm = MagicMock()
        cm.__enter__.return_value = response

        with patch(
            "scripts.http_client.urllib.request.urlopen", return_value=cm
        ) as mock_urlopen, patch(
            "scripts.http_client.convert_request_to_xml_root",
            return_value=ET.Element("feed"),
        ) as mock_convert:

            client = HttpClient()
            result = client.arxiv_query(self.url_template, 0, 1)

            # validate return and that urlopen was called
            self.assertIsInstance(result, ET.Element)
            mock_urlopen.assert_called()
            mock_convert.assert_called()

    @patch("scripts.http_client.pretty_sleep")
    def test_http_error_non_retryable(self, _sleep_mock: float):
        """Test that a non-retryable HTTPError should raise RuntimeError."""

        # Define some empty headers
        headers = Message()
        err = urllib.error.HTTPError("None_URL", 400, "bad", headers, None)

        with patch("scripts.http_client.urllib.request.urlopen", side_effect=err):
            client = HttpClient()

            # Should hit the RuntimeError for non-retryable errors
            with self.assertRaises(RuntimeError):
                client.arxiv_query(self.url_template, 0, 1)

    @patch("scripts.http_client.pretty_sleep")
    def test_http_error_retryable(self, _sleep_mock: float):
        """Test that a retryable HTTPError will re-attempt the connection until the maximum attempt
        limit is reached.
        """

        # Define some empty headers
        headers = Message()
        err = urllib.error.HTTPError("None_URL", 408, "request timeout", headers, None)

        with patch("scripts.http_client.urllib.request.urlopen", side_effect=err):
            client = HttpClient()

            # The same error is injected for all attempts.
            # Should reach the custom TooManyAttempts raise
            with self.assertRaises(TooManyAttempts):
                client.arxiv_query(self.url_template, 0, 1)

    @patch("scripts.http_client.pretty_sleep")
    def test_http_error_429_without_retry(self, _sleep_mock: float):
        """Test that a 429 HTTPError without a Retry-After command will increase the wait time to 90
        seconds.
        """

        # Require that a header is returned by the error
        headers = Message()
        headers["mock entry"] = "nothing of note"
        err = urllib.error.HTTPError("None_URL", 429, "too many", headers, None)

        # successful response context
        response = MagicMock()
        response.read.return_value = b"<feed></feed>"
        cm = MagicMock()
        cm.__enter__.return_value = response

        side_effects: list[urllib.error.HTTPError | MagicMock] = [err, cm]

        with patch(
            "scripts.http_client.urllib.request.urlopen", side_effect=side_effects
        ) as _mock_urlopen, patch(
            "scripts.http_client.convert_request_to_xml_root",
            return_value=ET.Element("feed"),
        ):

            client = HttpClient()
            result = client.arxiv_query(self.url_template, 0, 1)

            self.assertIsInstance(result, ET.Element)
            self.assertEqual(client.retry_after, 90.0)

    @patch("scripts.http_client.pretty_sleep")
    def test_http_error_429_with_retry(self, _sleep_mock: float):
        """Test that the if server replies with a retryable HTTPError that includes a Retry-After
        command, that the client will wait for the requested amount of time.
        """

        test_retry_value = "5"

        headers = Message()
        headers["Retry-After"] = "5"
        err = urllib.error.HTTPError("None_URL", 429, "too many", headers, None)

        # successful response context
        response = MagicMock()
        response.read.return_value = b"<feed></feed>"
        cm = MagicMock()
        cm.__enter__.return_value = response

        side_effects: list[urllib.error.HTTPError | MagicMock] = [err, cm]

        with patch(
            "scripts.http_client.urllib.request.urlopen", side_effect=side_effects
        ) as _mock_urlopen, patch(
            "scripts.http_client.convert_request_to_xml_root",
            return_value=ET.Element("feed"),
        ):

            client = HttpClient()
            result = client.arxiv_query(self.url_template, 0, 1)

            self.assertIsInstance(result, ET.Element)
            self.assertEqual(client.retry_after, float(test_retry_value))

    @patch("scripts.http_client.pretty_sleep")
    def test_cert_url_error(self, _sleep_mock: float):
        """Test that a certificate verification URLError updates the cert_error_bool flag (and
        therefore the ssl certificate).
        """

        ssl_err = ssl.SSLCertVerificationError("certificate verify failed")
        err = urllib.error.URLError(ssl_err)

        # successful response context after first failure
        response = MagicMock()
        response.read.return_value = b"<feed></feed>"
        cm = MagicMock()
        cm.__enter__.return_value = response

        side_effects: list[urllib.error.HTTPError | MagicMock] = [err, cm]

        with patch(
            "scripts.http_client.urllib.request.urlopen", side_effect=side_effects
        ) as _mock_urlopen, patch(
            "scripts.http_client.convert_request_to_xml_root",
            return_value=ET.Element("feed"),
        ):

            client = HttpClient()
            result = client.arxiv_query(self.url_template, 0, 1)

            self.assertIsInstance(result, ET.Element)
            self.assertTrue(client.cert_error_bool)

    @patch("scripts.http_client.pretty_sleep")
    def test_timeout_error(self, _sleep_mock: float):
        """Test that a timeout error correctly updates the retry timer to 60 seconds."""

        err = TimeoutError

        # successful response context
        response = MagicMock()
        response.read.return_value = b"<feed></feed>"
        cm = MagicMock()
        cm.__enter__.return_value = response

        side_effects: list[urllib.error.HTTPError | MagicMock] = [err, cm]

        with patch(
            "scripts.http_client.urllib.request.urlopen", side_effect=side_effects
        ) as _mock_urlopen, patch(
            "scripts.http_client.convert_request_to_xml_root",
            return_value=ET.Element("feed"),
        ):

            client = HttpClient()
            result = client.arxiv_query(self.url_template, 0, 1)

            self.assertIsInstance(result, ET.Element)
            self.assertEqual(client.retry_after, 60.0)
