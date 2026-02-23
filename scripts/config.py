"""Config class."""

# fmt: off
# Import standard libraries
from dataclasses import dataclass
import argparse
import datetime
import logging
import pathlib
import os

# Import non-standard libraries
import yaml

# Import functions
from .string_handling import normalise_string
from .file_io         import write_date
from .dates           import parse_date, calc_search_endtime, calc_next_posttime
from .utils           import delete_file
# fmt: on


@dataclass
class Paths:
    """Holds all paths"""

    prevsearch: pathlib.Path
    searchterms: pathlib.Path
    catchup: pathlib.Path
    searchxml: pathlib.Path
    papersxml: pathlib.Path


class Config:
    """Defines important parameters required for the search"""

    # There are 10 attributes. All of which are required to set up the execution of the script.
    # Disable linting warnings
    # pylint: disable=R0902

    # Define some datetime objects
    # Posting time of the daily list
    POST_TIME = datetime.time(6, 0, tzinfo=datetime.timezone.utc)
    # Time the searches will be bound by
    SEARCH_TIME = datetime.time(19, 0, tzinfo=datetime.timezone.utc)

    def __init__(self, logger: logging.Logger, root_dir: pathlib.Path) -> None:
        """
        Create the CatchupPipeline object, which will store important values used throughout the
        search, scoring, and filtering sections.
        - May want to break apart to separate pipelines in the future

        inputs
        ------
        logger   : The logger object.
        root_dir : Absolute path to the root directory.
        """

        # logger
        self.logger = logger

        # paths
        self.paths = Paths(
            prevsearch=root_dir / "prev_search.txt",
            searchterms=root_dir / "search_terms.yaml",
            catchup=root_dir / "catchup.txt",
            searchxml=root_dir / "search.xml",
            papersxml=root_dir / "papers.xml",
        )

        # Obtain the current time, converted to the UTC timezone
        self.current_time = datetime.datetime.now(datetime.timezone.utc)

        self.start_time: datetime.datetime
        self.start_date: datetime.date
        self.end_time: datetime.datetime
        self.end_date: datetime.date

        self.search_terms: dict[str, list[str] | None]

        self.cat_printstring = ""
        self.cat_urlstring = ""

    def get_searchterms(self) -> None:
        """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary."""

        self.logger.info(f"Loading search terms from {self.paths.searchterms}.")

        # Load the .yaml into a dictionary
        with open(self.paths.searchterms, "r", encoding="utf8") as f:

            self.search_terms = yaml.safe_load(f)

        # Normalise author strings and remove duplicates
        if self.search_terms["Authors"] is not None:

            # Remove duplicates, but preserve order from the config file
            authors = [normalise_string(a) for a in self.search_terms["Authors"]]
            self.search_terms["Authors"] = list(dict.fromkeys(authors))

        # # Check the file
        # At least one category is required
        if self.search_terms["Categories"] is None:

            self.logger.critical(
                "No search terms were found in the 'Categories' entry in the configuration file.\n"
                "          Please check the file and add at least one item.\n"
            )
            raise RuntimeError(
                "No search categories found. Add atleast one to the .yaml."
            )

        # Remove duplicates, but preserve order from the config file
        self.search_terms["Categories"] = list(
            dict.fromkeys(self.search_terms["Categories"])
        )

        # Define category string for the urls/API calls
        self.cat_urlstring = "+OR+".join(
            f"cat:{cat}" for cat in self.search_terms["Categories"]
        )

        # Define category string to make nice print statements
        if len(self.search_terms["Categories"]) == 2:

            self.cat_printstring = " and ".join(
                f"{c}" for c in self.search_terms["Categories"]
            )

        elif len(self.search_terms["Categories"]) > 2:

            catstring_temp = ", ".join(
                f"{c}" for c in self.search_terms["Categories"][:-1]
            )
            self.cat_printstring = ", and ".join(
                [catstring_temp, self.search_terms["Categories"][-1]]
            )

        else:

            self.cat_printstring = ", ".join(
                f"{c}" for c in self.search_terms["Categories"]
            )

        # Print which categories are being searched over
        self.logger.info(f"Searching the {self.cat_printstring} categories")

        # If a category with a wildcard (e.g. astro-ph*) is entered with other matching
        #     sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories.
        #     No need to catch it here

        # # Warn the user if no terms are found
        # If no authors are found, warn the user
        if self.search_terms["Authors"] is None:

            self.logger.warning("No 'Authors' found in the configuration file.")

        # Otherwise, log all authors that were extracted
        else:

            for author in self.search_terms["Authors"]:

                self.logger.debug(f"Found author: {author}")

        # If no included words are found, warn the user
        if self.search_terms["Included Words"] is None:

            self.logger.warning("No 'Included Words' found in the configuration file.")

        # Otherwise, remove duplicates and log all found included words
        else:

            # Remove duplicates and sort
            inc_words = list(self.search_terms["Included Words"])
            self.search_terms["Included Words"] = sorted(set(inc_words))

            for included_word in self.search_terms["Included Words"]:

                self.logger.debug(f"Found included word: {included_word}")

        # If no excluded words are found, warn the user
        if self.search_terms["Excluded Words"] is None:

            self.logger.warning(
                "No 'Excluded Words' were found in the configuration file."
            )

        # Otherwise, remove duplicates and log all found excluded words
        else:

            # Remove duplicates and sort
            exc_words = list(self.search_terms["Excluded Words"])
            self.search_terms["Excluded Words"] = sorted(set(exc_words))

            for excluded_word in self.search_terms["Excluded Words"]:

                self.logger.debug(f"Found excluded word: {excluded_word}")

        # Check to see if any word is in both the 'included' and 'excluded fields
        if (
            self.search_terms["Included Words"] is not None
            and self.search_terms["Excluded Words"] is not None
        ):

            for inc_word in self.search_terms["Included Words"]:

                if inc_word in self.search_terms["Excluded Words"]:

                    self.logger.warning(
                        f"The term '{inc_word}' appears in both the Included and Excluded fields."
                    )

    def get_dates(self, cli_args: argparse.Namespace) -> None:
        """Set up the dates that the script uses for the arXiv API calls.

        inputs
        ------
        cli_args : CLI arguments.
        """

        # If the end_date was passed on the command line, use it
        if cli_args.end_date:

            self.logger.debug(f"Attempting to use the end_date: {cli_args.end_date}")

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
                f"Attempting to use the start_date: {cli_args.start_date}"
            )

            self.start_time, self.start_date = parse_date(
                self.logger,
                cli_args.start_date,
                "start-date",
                self.SEARCH_TIME,
                self.POST_TIME,
            )

        # If the start_date was not passed on the command line, attempt to load it
        if not cli_args.start_date:

            self.logger.debug("No start date was input.")

            # If the file doesn't exist:
            if not os.path.exists(self.paths.prevsearch):

                self.logger.debug(
                    "No previous search file found. Setting to the day prior to the end_date."
                )

                # Compute the list time before the previous by passing the end_time found above
                #     into the calc_search_endtime() function
                prev_end_time = calc_search_endtime(
                    self.end_time, self.SEARCH_TIME, self.POST_TIME
                )

                write_date(self.logger, self.paths.prevsearch, prev_end_time.date())

            # If the file does exist, load it and extract the previous runtime
            with open(self.paths.prevsearch, "r", encoding="utf-8") as f:

                self.start_time, self.start_date = parse_date(
                    self.logger, next(f), "start-date", self.SEARCH_TIME, self.POST_TIME
                )

        # Log the dates
        s_yyyy = self.start_date.year
        s_mm = self.start_date.month
        s_dd = self.start_date.day
        e_yyyy = self.end_date.year
        e_mm = self.end_date.month
        e_dd = self.end_date.day
        self.logger.info(
            f"Searching from {s_yyyy}/{s_mm}/{s_dd} 19:00 UTC to {e_yyyy}/{e_mm}/{e_dd} 19:00 UTC"
        )

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
            self.logger.exception("Search start date is in the future.\n")
            raise ValueError("Search start date is in the future.")

        # If the search end date is in the future:
        if (self.current_time.date() - self.end_date).days < 0:
            self.logger.exception("Search end date is in the future.\n")
            raise ValueError("Search end date is in the future.")

        # If the end date is equal to the start date, tell the user to wait
        if prev_run.days == 0:
            self.logger.exception(
                f"Search start/end dates are equal.{next_post_string}\n"
            )
            raise ValueError("Search start/end dates are equal.")

        # If the end date is before the start date
        if prev_run.days < 0:
            self.logger.exception("Search start date is after the end date.\n")
            raise ValueError(
                "Search start date is after the end date. Check for timezone issues."
            )

        # If the search period doesn't cover any searching days, tell the user to wait
        # Typically one of the previous errors will occur before this one if the entire search
        #     period is invalid
        if deltadays_now_to_search < 7 and valid_search_days == 0:
            self.logger.exception(
                f"No valid search dates are included.{next_post_string}\n"
            )
            raise ValueError(f"No valid search dates are included.{next_post_string}")

        # If there are no issues, let the user know how many days we are searching over
        self.logger.info(f"Days since the previous search: {prev_run.days}")

    def clear_temp_files(self) -> None:
        """Clear the temporary files created by the script."""

        delete_file(self.logger, self.paths.searchxml)
        delete_file(self.logger, self.paths.papersxml)
