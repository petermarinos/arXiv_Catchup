"""Config class."""

# Import dependency type checking libraries
from __future__ import annotations
from typing import TYPE_CHECKING

# Import standard libraries
import argparse
import datetime
import logging

# Import functions
from .dates import parse_date, calc_search_endtime, calc_next_posttime

# Import classes for type checking
if TYPE_CHECKING:
    from .storage_manager import SearchTermsDict, Storage


class Config:
    """Defines important parameters required for the search."""

    # There are 10 attributes. All of which are required to set up the execution of the script.
    # Disable linting warnings
    # pylint: disable=R0902

    # Define some datetime objects
    # Posting time of the daily list
    POST_TIME = datetime.time(6, 0, tzinfo=datetime.timezone.utc)
    # Time the searches will be bound by
    SEARCH_TIME = datetime.time(19, 0, tzinfo=datetime.timezone.utc)

    def __init__(self) -> None:
        """
        Create the CatchupPipeline object, which will store important values used throughout the
        search, scoring, and filtering sections.
        - May want to break apart to separate pipelines in the future
        """

        # Obtain the logger
        self.logger = logging.getLogger(__name__)

        # Obtain the current time, converted to the UTC timezone
        self.current_time = datetime.datetime.now(datetime.timezone.utc)

        self.start_time: datetime.datetime
        self.start_date: datetime.date
        self.end_time: datetime.datetime
        self.end_date: datetime.date

        self.search_terms: SearchTermsDict

        self.cat_printstring = ""
        self.cat_urlstring = ""

    def get_searchterms(self, storage: Storage) -> None:
        """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary."""

        # Read the file containing all search terms
        self.search_terms = storage.read_search_term_file()

        # Define category string for the urls/API calls
        self.cat_urlstring = "+OR+".join(
            f"cat:{cat}" for cat in self.search_terms["categories"]
        )

        # Define category string to make nice print statements
        if len(self.search_terms["categories"]) == 2:

            self.cat_printstring = " and ".join(
                f"{c}" for c in self.search_terms["categories"]
            )

        elif len(self.search_terms["categories"]) > 2:

            catstring_temp = ", ".join(
                f"{c}" for c in self.search_terms["categories"][:-1]
            )
            self.cat_printstring = ", and ".join(
                [catstring_temp, self.search_terms["categories"][-1]]
            )

        else:

            self.cat_printstring = ", ".join(
                f"{c}" for c in self.search_terms["categories"]
            )

        # Print which categories are being searched over
        self.logger.info("Searching the %s categories", self.cat_printstring)

    def get_dates(self, storage: Storage, cli_args: argparse.Namespace) -> None:
        """Set up the dates that the script uses for the arXiv API calls.

        inputs
        ------
        cli_args : CLI arguments.
        """

        # If the end_date was passed on the command line, use it
        if cli_args.end_date:

            self.logger.debug("Attempting to use the end_date: %s", cli_args.end_date)

            self.end_time, self.end_date = parse_date(
                self.logger,
                cli_args.end_date,
                "end-date",
                self.SEARCH_TIME,
                self.POST_TIME,
            )

        # If the end_date was not passed in the command line, compute it
        else:

            self.logger.debug(
                "No end date was input. Computing based on the current time."
            )

            self.end_time = calc_search_endtime(
                self.current_time, self.SEARCH_TIME, self.POST_TIME
            )
            self.end_date = self.end_time.date()

        # If the start_date was passed on the command line, use it
        if cli_args.start_date:

            self.logger.debug(
                "Attempting to use the start_date: %s", cli_args.start_date
            )

            self.start_time, self.start_date = parse_date(
                self.logger,
                cli_args.start_date,
                "start-date",
                self.SEARCH_TIME,
                self.POST_TIME,
            )

        else:

            # If the start_date was not passed on the command line, attempt to load it
            self.start_time, self.start_date = storage.read_previous_date_file(
                self.end_time, self.SEARCH_TIME, self.POST_TIME
            )

        # Log the dates
        # Compute the string first. Too many values to be readable with lazy-formatting, and the
        #     values are guaranteed to be of the correct type if they are extracted from the
        #     datetime objects.
        s_yyyy = self.start_date.year
        s_mm = self.start_date.month
        s_dd = self.start_date.day
        e_yyyy = self.end_date.year
        e_mm = self.end_date.month
        e_dd = self.end_date.day
        date_string = (
            f"Searching from {s_yyyy}/{s_mm}/{s_dd} 19:00 UTC "
            f"to {e_yyyy}/{e_mm}/{e_dd} 19:00 UTC"
        )
        self.logger.info(date_string)

    def date_error_check(self) -> None:
        """Check for errors with the dates."""

        # Compute how long the search is covering
        prev_run = self.end_date - self.start_date

        # Compute the time that the next list will be posted
        nextlist_time = calc_next_posttime(self.current_time, self.POST_TIME)
        time_until_next = nextlist_time - self.current_time

        t_days = time_until_next.days
        t_hours = time_until_next.seconds // 3600
        t_minutes = (time_until_next.seconds // 60) - t_hours * 60

        next_post_string = (
            "\n          "
            "If looking for the next list, it will be posted at "
            f"{nextlist_time:%Y-%m-%d %H:%M (%Z)},"
            "\n          "
            f"which is {t_days} days, {t_hours} hours, and {t_minutes} minutes from now."
        )

        # Compute number of days between now and the start of the search
        deltadays_now_to_search = (self.current_time.date() - self.start_date).days

        # Count the number of valid search days between start_date and end_date
        valid_search_days = 0
        temp_date = self.end_date
        while temp_date > self.start_date:
            valid_search_days += 1
            temp_date -= datetime.timedelta(days=1)

        # Raise some errors
        # If the search start date is in the future:
        if deltadays_now_to_search < 0:
            self.logger.critical("Search start date is in the future.\n")
            raise ValueError("Search start date is in the future.")

        # If the search end date is in the future:
        if (self.current_time.date() - self.end_date).days < 0:
            self.logger.critical("Search end date is in the future.\n")
            raise ValueError("Search end date is in the future.")

        # If the end date is equal to the start date, tell the user to wait
        if prev_run.days == 0:
            self.logger.critical(
                "Search start/end dates are equal.%s\n", next_post_string
            )
            raise ValueError("Search start/end dates are equal.")

        # If the end date is before the start date
        if prev_run.days < 0:
            self.logger.critical("Search start date is after the end date.\n")
            raise ValueError(
                "Search start date is after the end date. Check for timezone issues."
            )

        # If the search period doesn't cover any searching days, tell the user to wait
        # Typically one of the previous errors will occur before this one if the entire search
        #     period is invalid
        if deltadays_now_to_search < 7 and valid_search_days == 0:
            self.logger.critical(
                "No valid search dates are included.%s\n", next_post_string
            )
            raise ValueError(f"No valid search dates are included.{next_post_string}")

        # If there are no issues, let the user know how many days we are searching over
        self.logger.info("Days since the previous search: %s", prev_run.days)
