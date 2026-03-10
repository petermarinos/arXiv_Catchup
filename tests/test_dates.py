"""Unit tests on all date-related function."""

# Import libraries
import datetime
import unittest
import logging

# Import class used to set up the tests
from src.arxiv_catchup.config import Config

# Import functions to test
from src.arxiv_catchup.dates import (
    InvalidDateError,
    is_posting_day_bool,
    is_searching_day_bool,
    calc_search_endtime,
    calc_next_posttime,
    parse_date,
)


class TestAuthorMatching(unittest.TestCase):
    """Test the author matching algorithm."""

    def setUp(self) -> None:
        """Set up some dates required for the tests"""

        self.logger = logging.getLogger()

        config = Config()

        self.search_time = config.SEARCH_TIME
        self.post_time = config.POST_TIME

    def test_posting_day(self):
        """Test that all weekdays return the correct bool value for the posting days."""

        # True for Monday -> Friday
        self.assertTrue(is_posting_day_bool(datetime.date(year=2026, month=1, day=5)))
        self.assertTrue(is_posting_day_bool(datetime.date(year=2026, month=1, day=6)))
        self.assertTrue(is_posting_day_bool(datetime.date(year=2026, month=1, day=7)))
        self.assertTrue(is_posting_day_bool(datetime.date(year=2026, month=1, day=8)))
        self.assertTrue(is_posting_day_bool(datetime.date(year=2026, month=1, day=9)))

        # False for Saturday and Sunday
        self.assertFalse(is_posting_day_bool(datetime.date(year=2026, month=1, day=10)))
        self.assertFalse(is_posting_day_bool(datetime.date(year=2026, month=1, day=11)))

    def test_searching_day(self):
        """Test that all weekdays return the correct bool value for the searching days."""

        # True for Sunday -> Thursday
        self.assertTrue(is_searching_day_bool(datetime.date(year=2026, month=1, day=4)))
        self.assertTrue(is_searching_day_bool(datetime.date(year=2026, month=1, day=5)))
        self.assertTrue(is_searching_day_bool(datetime.date(year=2026, month=1, day=6)))
        self.assertTrue(is_searching_day_bool(datetime.date(year=2026, month=1, day=7)))
        self.assertTrue(is_searching_day_bool(datetime.date(year=2026, month=1, day=8)))

        # False for Friday and Saturday
        self.assertFalse(
            is_searching_day_bool(datetime.date(year=2026, month=1, day=9))
        )
        self.assertFalse(
            is_searching_day_bool(datetime.date(year=2026, month=1, day=10))
        )

    def test_search_endtime(self):
        """Test that the search end time is computed correctly for a variety of cases."""

        test_datetimes = [
            [
                # Wednesday, just before the list is posted. Should return Monday 19:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=5,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=5,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just after the list is posted. Should return Tuesday 19:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=6,
                    minute=0,
                    second=1,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=6,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Monday, just before the list is posted. Should return Thursday 19:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=5,
                    hour=5,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=1,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Monday, just after the list is posted. Should return Sunday 19:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=5,
                    hour=6,
                    minute=0,
                    second=1,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=4,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just before the list is posted, but in a +ve timezone.
                # Should return Monday 19:00 UTC
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=15,
                    minute=29,
                    second=59,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=9, minutes=30)),
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=5,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just before the list is posted, but in a -ve timezone.
                # Should return Monday 19:00 UTC
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=6,
                    hour=22,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=7)),
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=5,
                    hour=19,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
        ]

        for test_datetime, expected_datetime in test_datetimes:

            self.assertEqual(
                calc_search_endtime(
                    test_datetime,
                    self.search_time,
                    self.post_time,
                ),
                expected_datetime,
            )

    def test_next_posttime(self):
        """Test that the next list post time is computed correctly for a variety of cases."""

        test_datetimes = [
            [
                # Wednesday, just before the list is posted. Should return Wednesday 06:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=5,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just after the list is posted. Should return Thursday 06:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=6,
                    minute=0,
                    second=1,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=8,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Friday, just before the list is posted. Should return Friday 06:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=9,
                    hour=5,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=9,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Friday, just after the list is posted. Should return Monday 06:00
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=9,
                    hour=6,
                    minute=0,
                    second=1,
                    tzinfo=datetime.timezone.utc,
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=12,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just before the list is posted, but in a +ve timezone.
                # Should return Wednesday 06:00 UTC
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=15,
                    minute=29,
                    second=59,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=9, minutes=30)),
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
            [
                # Wednesday, just before the list is posted, but in a -ve timezone.
                # Should return Wednesday 06:00 UTC
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=6,
                    hour=22,
                    minute=59,
                    second=59,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=7)),
                ),
                datetime.datetime(
                    year=2026,
                    month=1,
                    day=7,
                    hour=6,
                    minute=0,
                    second=0,
                    tzinfo=datetime.timezone.utc,
                ),
            ],
        ]

        for test_datetime, expected_datetime in test_datetimes:

            self.assertEqual(
                calc_next_posttime(
                    test_datetime,
                    self.post_time,
                ),
                expected_datetime,
            )

    def test_parse_date(self):
        """Test the date parsing."""

        # Test a valid date format
        self.assertEqual(
            (
                parse_date(
                    self.logger, "2026-01-06", "", self.search_time, self.post_time
                )
            ),
            (
                datetime.datetime(
                    year=2026, month=1, day=6, hour=19, tzinfo=datetime.timezone.utc
                ),
                datetime.date(year=2026, month=1, day=6),
            ),
        )

        # Test a non-valid date format raises an error
        with self.assertRaises(InvalidDateError):
            parse_date(
                self.logger, "invalid date format", "", self.search_time, self.post_time
            )
