"""The main GUI script, which allows the user to run the search step-by-step."""

from __future__ import annotations

# Import standard libraries
from collections.abc import Callable

from dataclasses import dataclass
import logging
import threading

# from typing import Optional

# Import non-standard libraries

# Import project classes
from arxiv_catchup.storage_manager import Storage
from arxiv_catchup.arxiv_client import ArxivClient, ArxivError
from arxiv_catchup.http_client import HttpClient
from arxiv_catchup.config import Config, InvalidDateError
from arxiv_catchup.corpus import Corpus
from arxiv_catchup.cli import CLI

from arxiv_catchup.gui.gui import GUI

# Import project functions
from arxiv_catchup.xml_handling import XmlReadError
from arxiv_catchup.dates import parse_date, split_date
from arxiv_catchup.utils import logger_setup


class ApiNotInitialised(Exception):
    """Exception raised if the API has not been initialised yet.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


@dataclass
class Runner:
    """Dataclass to hold the objects used to run the logic."""

    cli: CLI
    storage: Storage
    search_params: Config
    corpus: Corpus

    http_client: HttpClient
    api: ArxivClient | None = None

    def get_api(self) -> ArxivClient:
        """Basic function to return the API. Ensures the type checker knows what is happening, and
        prevents potential issues if the user is somehow able to call the API before it is
        initalised.
        """

        if self.api is None:
            raise ApiNotInitialised("API has not been initialised.")
        return self.api


@dataclass
class GuiState:
    """Small dataclass to hold the states of the GUI.
    Currently under-utilised, but left in case it is useful later.
    """

    dates_checked: bool = False
    info_found: bool = False
    papers_downloaded: bool = False
    papers_scored: bool = False
    papers_filtered: bool = False


class Controller:
    """Controller of the GUI."""

    def __init__(self) -> None:
        """WIP"""

        self.state = GuiState()

        self.runner = Runner(
            cli=CLI(),
            storage=Storage(),
            search_params=Config(),
            corpus=Corpus(),
            http_client=HttpClient(),
        )

        logger_setup(self.runner.cli.args, self.runner.storage.paths.log)
        self.logger = logging.getLogger(__name__)
        self.runner.cli.add_logger()
        self.runner.storage.add_logger()

        self.runner.search_params.get_searchterms(self.runner.storage)
        self.runner.search_params.get_dates(self.runner.storage, self.runner.cli.args)

        # Create GUI and wire callbacks
        self.gui = GUI(
            self.runner.search_params,
            actions=self,
        )

    def run(self) -> None:
        """WIP"""

        # Run the GUI
        self.gui.run()

        # Once the GUI has been closed:
        try:
            self.runner.storage.delete_temp_files(self.runner.cli.args.keep_temp)
        except FileNotFoundError:
            self.logger.debug("Attempted to delete temporary files that did not exist.")

        self.runner.storage.write_aux_files(
            self.runner.search_params.end_date, self.runner.corpus.length
        )

        # # Print a summary
        self.runner.corpus.summary()

    def on_toggle_keep_temp(self) -> None:
        """WIP"""

        self.logger.debug("Toggled keep_temp checkbox.")

        self.runner.cli.args.keep_temp = self.gui.get_bool_from_checkbox("keep_temp")

        self.logger.debug("keep_temp set to %s", self.runner.cli.args.keep_temp)

    def on_toggle_new_window(self) -> None:
        """WIP"""

        self.logger.debug("Toggled new_window checkbox.")

        self.runner.cli.args.new_window = self.gui.get_bool_from_checkbox("new_window")

        self.logger.debug("new_window set to %s", self.runner.cli.args.new_window)

    def on_check_dates(self) -> None:
        """Callback for the 'Check Search Dates' button."""

        self.logger.debug("Selected check_dates button.")

        try:

            temp_start_date = self.runner.search_params.start_date
            temp_end_date = self.runner.search_params.end_date

            (
                self.runner.search_params.start_time,
                self.runner.search_params.start_date,
            ) = parse_date(
                self.logger,
                self.gui.get_date_from_entry("start_date"),
                "start-date",
                self.runner.search_params.SEARCH_TIME,
                self.runner.search_params.POST_TIME,
            )

            self.runner.search_params.end_time, self.runner.search_params.end_date = (
                parse_date(
                    self.logger,
                    self.gui.get_date_from_entry("end_date"),
                    "end-date",
                    self.runner.search_params.SEARCH_TIME,
                    self.runner.search_params.POST_TIME,
                )
            )

            self.runner.search_params.date_error_check()

            # If the dates changed since the previous check, disable all GUI buttons other than
            #     'search_info' and continue to after the except
            if (
                temp_start_date != self.runner.search_params.start_date
                or temp_end_date != self.runner.search_params.end_date
            ):
                self.gui.button_set_state("download_papers", False)
                self.gui.button_set_state("score_papers", False)
                self.gui.button_set_state("filter_papers", False)
                self.gui.button_set_state("open_papers", False)
                self.gui.button_set_state("write_papers", False)

        except InvalidDateError as exc:

            self.logger.error("Date check failed: %s", exc)

            # Disable all buttons except 'check_dates'
            self.gui.button_set_state("search_info", False)
            self.gui.button_set_state("download_papers", False)
            self.gui.button_set_state("score_papers", False)
            self.gui.button_set_state("filter_papers", False)
            self.gui.button_set_state("open_papers", False)
            self.gui.button_set_state("write_papers", False)

            return

        # self.state.dates_checked = True
        self.logger.info("Dates checked and are valid.")
        s_yyyy, s_mm, s_dd = split_date(self.runner.search_params.start_date)
        e_yyyy, e_mm, e_dd = split_date(self.runner.search_params.end_date)
        date_string = (
            f"Searching from {s_yyyy}-{s_mm}-{s_dd} 19:00 UTC "
            f"to {e_yyyy}-{e_mm}-{e_dd} 19:00 UTC"
        )
        self.logger.info(date_string)

        self.gui.button_set_state("search_info", True)

        # If the search information is good, then the ArXiv client can be created
        self.runner.api = ArxivClient(
            self.runner.search_params, self.runner.http_client
        )

        # Ensure the corpus is empty in case the search dates were changed after downloading
        self.runner.corpus.clear_corpus()

        self.state.dates_checked = True

        # If papers were downloaded previously, then the dates were changed, delete the temp file
        if self.state.papers_downloaded:
            self.runner.storage.delete_file(self.runner.storage.paths.papers_xml)

        self.logger.info("Ready to connect to the arXiv servers.")

    def on_search_info(self) -> None:
        """Callback for the 'Obtain Search Info' button."""

        self.logger.debug("Selected search_info button.")

        try:

            api = self.runner.get_api()

            api.get_search_info(self.runner.storage)

            api.arxiv_search_error_check()

        except ArxivError as exc:

            self.logger.error("search info check failed: %s", exc)

            self.gui.button_set_state("download_papers", False)
            self.gui.button_set_state("score_papers", False)
            self.gui.button_set_state("filter_papers", False)
            self.gui.button_set_state("open_papers", False)
            self.gui.button_set_state("write_papers", False)

            return

        except XmlReadError as exc:

            self.logger.error("search info check failed: %s", exc)

            self.gui.button_set_state("download_papers", False)
            self.gui.button_set_state("score_papers", False)
            self.gui.button_set_state("filter_papers", False)
            self.gui.button_set_state("open_papers", False)
            self.gui.button_set_state("write_papers", False)

            return

        self.state.info_found = True

        self.logger.info("Ready to download papers.")
        self.gui.button_set_state("download_papers", True)
        self.gui.button_set_state("score_papers", False)
        self.gui.button_set_state("filter_papers", False)
        self.gui.button_set_state("open_papers", False)
        self.gui.button_set_state("write_papers", False)

    def on_download(self) -> None:
        """Callback for the 'Download' button."""

        self.logger.debug("Selected download_papers button.")

        # Disable all GUI buttons
        self.gui.all_buttons_set_state(False)

        # *always ensure the corpus has been cleared first*
        self.logger.debug("Clearing the corpus.")
        self.runner.corpus.clear_corpus()

        download_cb = self.make_progress_cb("download")

        api = self.runner.get_api()

        def worker() -> None:
            """inner function that will download the papers"""

            api.get_papers(
                self.runner.corpus, self.runner.storage, progress_cb=download_cb
            )

            # Once get_papers finishes on the thread, then run the last few on-finish functions
            self.gui.after(0, self._on_download_finished)

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

    def _on_download_finished(self):

        self.logger.info("Ready to score papers.")

        # Re-enable previous buttons
        self.gui.button_set_state("check_dates", True)
        self.gui.button_set_state("search_info", True)
        self.gui.button_set_state("download_papers", True)

        # Enable the next button
        self.gui.button_set_state("score_papers", True)

        self.state.papers_downloaded = True

    def on_score(self) -> None:
        """Callback for the 'Score Papers' button."""

        self.logger.debug("Selected score_papers button.")

        self.runner.corpus.find_matches(self.runner.search_params.search_terms)

        # Obtain state of the option menu
        score_algo = self.gui.get_state_from_optionmenu("score")
        if score_algo == "Score via Matches":
            self.runner.cli.args.score_on_matches = True
        elif score_algo == "Score via ML":
            self.runner.cli.args.score_on_matches = False
        self.logger.debug("Using the %s scoring algorithm.", score_algo)

        try:
            self.runner.cli.score_papers(self.runner.corpus)
        except NotImplementedError:
            self.logger.error("ML algorithm not yet implemented")
            return

        self.state.papers_scored = True

        self.logger.info("Ready to filter papers.")
        self.gui.button_set_state("filter_papers", True)
        self.gui.button_set_state("open_papers", False)
        self.gui.button_set_state("write_papers", False)

    def on_filter(self) -> None:
        """Callback for the 'Filter' button."""

        self.logger.debug("Selected filter_papers button.")

        # Obtain state of the option menu
        filter_algo = self.gui.get_state_from_optionmenu("filter")
        if filter_algo == "Filter via Score":
            self.runner.cli.args.filter_on_matches = False
        elif filter_algo == "Filter via Matches":
            self.runner.cli.args.filter_on_matches = True

        self.runner.cli.filter_papers(self.runner.corpus)

        self.state.papers_filtered = True

        self.logger.info("Ready for output.")
        self.gui.button_set_state("open_papers", True)
        self.gui.button_set_state("write_papers", True)

    def on_open(self) -> None:
        """Callback for the 'Open in Browser' button."""

        self.logger.debug("Selected open_in_browser button.")

        # Disable all GUI buttons
        self.gui.all_buttons_set_state(False)

        self.runner.cli.open_in_browser = True
        self.runner.cli.write_to_file = False

        results_cb = self.make_progress_cb("results")

        api = self.runner.get_api()

        def worker() -> None:
            """inner function that will open the papers"""

            self.runner.cli.display(
                self.runner.storage,
                self.runner.corpus.papers_of_note,
                api.SLEEP_OPENING,
                progress_cb=results_cb,
            )

            # Once get_papers finishes on the thread, then run the last few on-finish functions
            self.gui.after(0, self._on_open_finished)

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

    def _on_open_finished(self):

        self.logger.info("Opening papers finished.")

        # Re-enable all buttons buttons
        self.gui.all_buttons_set_state(True)

    def on_write(self) -> None:
        """Callback for the Write to File button."""

        self.logger.debug("Selected write_to_file button.")

        self.runner.cli.open_in_browser = False
        self.runner.cli.write_to_file = True

        # Obtain state of the option menu
        write_style = self.gui.get_state_from_optionmenu("write_style")
        if write_style == "Links":
            self.runner.cli.args.only_ids = False
        elif write_style == "ID Numbers":
            self.runner.cli.args.only_ids = True

        api = self.runner.get_api()

        self.runner.cli.display(
            self.runner.storage,
            self.runner.corpus.papers_of_note,
            api.SLEEP_OPENING,
        )

    def make_progress_cb(self, key: str) -> Callable[[int, int], None]:
        """Create a callback function that will update a progress bar."""

        def _cb(ii: int, total: int) -> None:

            # Compute the progress as a fraction
            frac = 0 if total == 0 else ii / total

            # Update the progress bar named by 'key'
            self.gui.after(0, lambda: self.gui.update_progress_bar(key, frac))

        return _cb


def main() -> None:
    """Pipeline that creates the GUI and runs the analysis."""

    Controller().run()
