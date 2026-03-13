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


###########

# Need to implement:
#     disable all buttons during an operation, then enable ONLY THE APPROPRIATE ONES after
#     if the user goes backwards in the pupeline, disable buttons that may need to be disabled

# Other notes:
#     Put runner attributes into a dataclass
#     Put callables passed into GUI as a dataclass?


class Controller:
    """Controller of the GUI."""

    # This Controller class must hold all attributes as the CLI runner (6),
    #     plus a logger for this class, plus the GUI, plus the GuiState.
    # The runner objects could be put into a dataclass, but that is not seen as required at this
    #     point.
    # Disable the pylint warning for >7 attributes.
    # pylint: disable=R0902

    def __init__(self) -> None:
        """WIP"""

        self.state = GuiState()

        self.cli = CLI()
        self.storage = Storage()

        logger_setup(self.cli.args, self.storage.paths.log)
        self.logger = logging.getLogger(__name__)
        self.cli.add_logger()
        self.storage.add_logger()

        self.search_params = Config()
        self.search_params.get_searchterms(self.storage)
        self.search_params.get_dates(self.storage, self.cli.args)

        self.http_client = HttpClient()
        self.api: ArxivClient

        self.corpus = Corpus()

        # Create GUI and wire callbacks
        self.gui = GUI(
            self.search_params,
            on_keep_temp=self.on_keep_temp,
            on_check_dates=self.on_check_dates,
            on_search_info=self.on_search_info,
            on_download=self.on_download,
            on_score=self.on_score,
            on_filter=self.on_filter,
            on_open=self.on_open,
            on_new_window=self.on_new_window,
            on_write=self.on_write,
        )

    def run(self) -> None:
        """WIP"""

        # Run the GUI
        self.gui.run()

        # Once the GUI has been closed:
        try:
            self.storage.delete_temp_files(self.cli.args.keep_temp)
        except FileNotFoundError:
            self.logger.debug("Attempted to delete temporary files that did not exist.")

        self.storage.write_aux_files(self.search_params.end_date, self.corpus.length)

        # # Print a summary
        self.corpus.summary()

    def on_keep_temp(self) -> None:
        """WIP"""

        self.logger.debug("Toggled keep_temp checkbox.")

        self.cli.args.keep_temp = self.gui.get_bool_from_checkbox("keep_temp")

        self.logger.debug("keep_temp set to %s", self.cli.args.keep_temp)

    def on_new_window(self) -> None:
        """WIP"""

        self.logger.debug("Toggled new_window checkbox.")

        self.cli.args.new_window = self.gui.get_bool_from_checkbox("new_window")

        self.logger.debug("new_window set to %s", self.cli.args.new_window)

    def on_check_dates(self) -> None:
        """Callback for the 'Check Search Dates' button."""

        self.logger.debug("Selected check_dates button.")

        try:

            temp_start_date = self.search_params.start_date
            temp_end_date = self.search_params.end_date

            self.search_params.start_time, self.search_params.start_date = parse_date(
                self.logger,
                self.gui.get_date_from_entry("start_date"),
                "start-date",
                self.search_params.SEARCH_TIME,
                self.search_params.POST_TIME,
            )

            self.search_params.end_time, self.search_params.end_date = parse_date(
                self.logger,
                self.gui.get_date_from_entry("end_date"),
                "end-date",
                self.search_params.SEARCH_TIME,
                self.search_params.POST_TIME,
            )

            self.search_params.date_error_check()

            # If the dates changed since the previous check, disable all GUI buttons other than
            #     'search_info' and continue to after the except
            if (
                temp_start_date != self.search_params.start_date
                or temp_end_date != self.search_params.end_date
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
        s_yyyy, s_mm, s_dd = split_date(self.search_params.start_date)
        e_yyyy, e_mm, e_dd = split_date(self.search_params.end_date)
        date_string = (
            f"Searching from {s_yyyy}-{s_mm}-{s_dd} 19:00 UTC "
            f"to {e_yyyy}-{e_mm}-{e_dd} 19:00 UTC"
        )
        self.logger.info(date_string)

        self.gui.button_set_state("search_info", True)

        # If the search information is good, then the ArXiv client can be created
        self.api = ArxivClient(self.search_params, self.http_client)

        # Ensure the corpus is empty in case the search dates were changed after downloading
        self.corpus.clear_corpus()

        self.state.dates_checked = True

        # If papers were downloaded previously, then the dates were changed, delete the temp file
        if self.state.papers_downloaded:
            self.storage.delete_file(self.storage.paths.papers_xml)

        self.logger.info("Ready to connect to the arXiv servers.")

    def on_search_info(self) -> None:
        """Callback for the 'Obtain Search Info' button."""

        self.logger.debug("Selected search_info button.")

        try:

            self.api.get_search_info(self.storage)

            self.api.arxiv_search_error_check()

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

    def on_download(self) -> None:
        """Callback for the 'Download' button."""

        self.logger.debug("Selected download_papers button.")

        # *always ensure the corpus has been cleared first*
        self.logger.debug("Clearing the corpus.")
        self.corpus.clear_corpus()

        download_cb = self.make_progress_cb("download")

        def worker() -> None:
            """inner function that will download the papers"""

            self.api.get_papers(self.corpus, self.storage, progress_cb=download_cb)

            # Once get_papers finishes on the thread, then run the last few on-finish functions
            self.gui.after(0, self._on_download_finished)

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

    def _on_download_finished(self):

        self.logger.info("Ready to score papers.")
        self.gui.button_set_state("score_papers", True)

        self.state.papers_downloaded = True

    def on_score(self) -> None:
        """Callback for the 'Score Papers' button."""

        self.logger.debug("Selected score_papers button.")

        self.corpus.find_matches(self.search_params.search_terms)

        # Obtain state of the option menu
        score_algo = self.gui.get_state_from_optionmenu("score")
        if score_algo == "Score via Matches":
            self.cli.args.score_on_matches = True
        elif score_algo == "Score via ML":
            self.cli.args.score_on_matches = False
        self.logger.debug("Using the %s scoring algorithm.", score_algo)

        try:
            self.cli.score_papers(self.corpus)
        except NotImplementedError:
            self.logger.error("ML algorithm not yet implemented")
            return

        self.state.papers_scored = True

        self.logger.info("Ready to filter papers.")
        self.gui.button_set_state("filter_papers", True)

    def on_filter(self) -> None:
        """Callback for the 'Filter' button."""

        self.logger.debug("Selected filter_papers button.")

        # Obtain state of the option menu
        filter_algo = self.gui.get_state_from_optionmenu("filter")
        if filter_algo == "Filter via Score":
            self.cli.args.filter_on_matches = False
        elif filter_algo == "Filter via Matches":
            self.cli.args.filter_on_matches = True

        self.cli.filter_papers(self.corpus)

        self.state.papers_filtered = True

        self.logger.info("Ready for output.")
        self.gui.button_set_state("open_papers", True)
        self.gui.button_set_state("write_papers", True)

    def on_open(self) -> None:
        """Callback for the 'Open in Browser' button."""

        self.logger.debug("Selected open_in_browser button.")

        self.cli.open_in_browser = True
        self.cli.write_to_file = False

        results_cb = self.make_progress_cb("results")

        def worker() -> None:
            """inner function that will open the papers"""

            self.cli.display(
                self.storage,
                self.corpus.papers_of_note,
                self.api.SLEEP_OPENING,
                progress_cb=results_cb,
            )

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

    def on_write(self) -> None:
        """Callback for the Write to File button."""

        self.logger.debug("Selected write_to_file button.")

        self.cli.open_in_browser = False
        self.cli.write_to_file = True

        # Obtain state of the option menu
        write_style = self.gui.get_state_from_optionmenu("write")
        if write_style == "Links":
            self.cli.args.only_ids = False
        elif write_style == "ID Numbers":
            self.cli.args.only_ids = True

        self.cli.display(
            self.storage,
            self.corpus.papers_of_note,
            self.api.SLEEP_OPENING,
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
