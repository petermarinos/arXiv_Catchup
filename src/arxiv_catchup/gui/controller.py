"""The main GUI script, which allows the user to run the search step-by-step."""

from __future__ import annotations

# Import standard libraries
from collections.abc import Callable
from dataclasses import dataclass
import threading
import logging
import copy

# Import non-standard libraries

# Import project classes
from arxiv_catchup.storage_manager import Storage
from arxiv_catchup.arxiv_client import ArxivClient, ArxivError
from arxiv_catchup.xml_handling import XmlReadError
from arxiv_catchup.http_client import HttpClient, TooManyAttempts
from arxiv_catchup.gui.gui import (
    GUI,
    ButtonKind,
    CheckboxKind,
    EntryKind,
    OptionmenuKind,
    OptionsFilterKind,
    OptionsScoreKind,
    OptionsWriteKind,
    ProgressbarKind,
)
from arxiv_catchup.config import Config, InvalidDateError
from arxiv_catchup.corpus import Corpus
from arxiv_catchup.cli import CLI

# Import project functions
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
    """Small dataclass to hold the states of the GUI and obtains button states."""

    dates_checked: bool = False
    info_found: bool = False
    papers_downloaded: bool = False
    papers_scored: bool = False
    papers_filtered: bool = False

    def get_button_states(self) -> dict[ButtonKind, bool]:
        """Return a dict of button states based on current flags.
        NOTE: Use 'and' statements to simplify enabling/disabling all future buttons in the
              pipeline.
        """

        return {
            ButtonKind.REFRESH: True,  # Always available
            ButtonKind.CHECKDATES: True,  # Always available
            ButtonKind.SEARCHINFO: self.dates_checked,
            ButtonKind.DOWNLOAD: (self.dates_checked and self.info_found),
            ButtonKind.SCORE: (
                self.dates_checked and self.info_found and self.papers_downloaded
            ),
            ButtonKind.FILTER: (
                self.dates_checked
                and self.info_found
                and self.papers_downloaded
                and self.papers_scored
            ),
            ButtonKind.OPEN: (
                self.dates_checked
                and self.info_found
                and self.papers_downloaded
                and self.papers_scored
                and self.papers_filtered
            ),
            ButtonKind.WRITE: (
                self.dates_checked
                and self.info_found
                and self.papers_downloaded
                and self.papers_scored
                and self.papers_filtered
            ),
        }


class Controller:
    """Controller of the GUI."""

    def __init__(self) -> None:
        """Initialise the controller class"""

        # Create the GuiState object
        self.state = GuiState()

        # Set up the runner
        self.runner = Runner(
            cli=CLI(),
            storage=Storage(),
            search_params=Config(),
            corpus=Corpus(),
            http_client=HttpClient(),
        )

        # Create a logger
        logger_setup(self.runner.cli.args, self.runner.storage.paths.log)
        self.logger = logging.getLogger(__name__)
        self.runner.cli.add_logger()
        self.runner.storage.add_logger()

        # Pre-load search parameters
        self.runner.search_params.get_searchterms(self.runner.storage)
        self.runner.search_params.get_dates(self.runner.storage, self.runner.cli.args)

        # Create GUI and wire callbacks
        self.gui = GUI(
            self.runner.cli.args,
            self.runner.search_params,
            actions=self,
        )

        # Set the GUI state
        self.update_gui_state()

    def run(self) -> None:
        """Method to run the GUI."""

        # Run the GUI
        self.gui.run()

        # Once the GUI has been closed:
        self.runner.storage.delete_temp_files(self.runner.cli.args.keep_temp)

        # Write any auxiliary files
        self.runner.storage.write_aux_files(
            self.runner.search_params.end_date, self.runner.corpus.length
        )

        # Print a summary
        self.runner.corpus.summary()

    def on_toggle_keep_temp(self) -> None:
        """Callback for the 'Keep Temporary Files' checkbox."""

        self.logger.debug("Toggled keep_temp checkbox.")

        # Update the relevant flag
        self.runner.cli.args.keep_temp = self.gui.get_bool_from_checkbox(
            CheckboxKind.KEEPTEMP
        )

        self.logger.debug("keep_temp set to %s", self.runner.cli.args.keep_temp)

    def on_toggle_new_window(self) -> None:
        """Callback for the 'Open in New Window' checkbox."""

        self.logger.debug("Toggled new_window checkbox.")

        # Update the relevant flag
        self.runner.cli.args.new_window = self.gui.get_bool_from_checkbox(
            CheckboxKind.NEWWINDOW
        )

        self.logger.debug("new_window set to %s", self.runner.cli.args.new_window)

    def on_refresh(self) -> None:
        """Callback for the 'Reresh Search Parameters' button."""

        self.logger.debug("Selected refresh_search_terms button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Create a copy of the current search terms to check if they are changed
        temp_search_terms = copy.deepcopy(self.runner.search_params.search_terms)

        # Reload the config file
        self.runner.search_params.get_searchterms(self.runner.storage)

        # Check if the search terms changed. If they did, then disable the relevant buttons
        if temp_search_terms != self.runner.search_params.search_terms:

            self.logger.info("Search parameters updated ...")

            # If search categories changed, will need to re-obtain search info
            if (
                temp_search_terms.categories
                != self.runner.search_params.search_terms.categories
            ):

                self.logger.debug(" ... categories were altered.")
                self.state.info_found = False

            # If only the authors/words changed, will need to re-score
            if (
                (
                    temp_search_terms.authors
                    != self.runner.search_params.search_terms.authors
                )
                or (
                    temp_search_terms.included_words
                    != self.runner.search_params.search_terms.included_words
                )
                or (
                    temp_search_terms.excluded_words
                    != self.runner.search_params.search_terms.excluded_words
                )
            ):

                self.logger.debug(" ... authors and/or key words were altered.")
                self.state.papers_scored = False

        else:

            self.logger.info("Search parameters were unchanged.")

        # Update the GUI state
        self.update_gui_state()

    def on_check_dates(self) -> None:
        """Callback for the 'Check Search Dates' button."""

        self.logger.debug("Selected check_dates button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Obtain the current datetime objects in the search_params
        temp_start_date = self.runner.search_params.start_date
        temp_end_date = self.runner.search_params.end_date

        try:

            # Parse the start date from the start_date Entry
            (
                self.runner.search_params.start_time,
                self.runner.search_params.start_date,
            ) = parse_date(
                self.logger,
                self.gui.get_date_from_entry(EntryKind.STARTDATE),
                "start-date",
                self.runner.search_params.SEARCH_TIME,
                self.runner.search_params.POST_TIME,
            )

            # Parse the end date from the end_date Entry
            self.runner.search_params.end_time, self.runner.search_params.end_date = (
                parse_date(
                    self.logger,
                    self.gui.get_date_from_entry(EntryKind.ENDDATE),
                    "end-date",
                    self.runner.search_params.SEARCH_TIME,
                    self.runner.search_params.POST_TIME,
                )
            )

            # Run some error checks on the dates
            self.runner.search_params.date_error_check()

        except InvalidDateError as exc:

            self.logger.error("Date check failed: %s", exc)

            return

        # If either of the search dates changed since the previous check:
        if (
            temp_start_date != self.runner.search_params.start_date
            or temp_end_date != self.runner.search_params.end_date
        ):

            self.logger.info("Search dates were changed.")

            # Disable all GUI buttons other than 'search_info'
            self.state.info_found = False

            # Delete the search temp file
            self.runner.storage.delete_file(self.runner.storage.paths.search_xml)

        self.logger.info("Dates checked and are valid.")

        # Log the search dates
        s_yyyy, s_mm, s_dd = split_date(self.runner.search_params.start_date)
        e_yyyy, e_mm, e_dd = split_date(self.runner.search_params.end_date)
        date_string = (
            f"Searching from {s_yyyy}-{s_mm}-{s_dd} 19:00 UTC "
            f"to {e_yyyy}-{e_mm}-{e_dd} 19:00 UTC"
        )
        self.logger.info(date_string)

        # If the search information is good, then the ArXiv client can be created
        self.runner.api = ArxivClient(
            self.runner.search_params, self.runner.http_client
        )

        # If any papers have been downloaded, clear the corpus and delete the temp file
        if self.runner.corpus.length > 0:

            self.runner.corpus.clear_corpus()
            self.runner.storage.delete_file(self.runner.storage.paths.papers_xml)

        # Set/update the GUI state
        self.state.dates_checked = True
        self.update_gui_state()

        self.logger.info("Ready to connect to the arXiv servers.")

    def on_search_info(self) -> None:
        """Callback for the 'Obtain Search Info' button."""

        self.logger.debug("Selected search_info button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Disable all buttons/checkboxes
        self.gui.all_buttons_set_state(False)
        self.gui.all_checkboxes_set_state(False)

        def worker() -> None:
            """inner function that will connect to the servers"""

            # Extract the arxiv client
            api = self.runner.get_api()

            try:

                # Obtain the search information
                api.get_search_info(self.runner.storage)

                # Perform some error checks
                api.arxiv_search_error_check()

            except ArxivError as exc:

                self.logger.error("search info check failed: %s", exc)

                # Set/update the GUI state
                self.gui.all_checkboxes_set_state(True)
                self.update_gui_state()

                return

            except XmlReadError as exc:

                self.logger.error("search info check failed: %s", exc)

                # Set/update the GUI state
                self.gui.all_checkboxes_set_state(True)
                self.update_gui_state()

                return

            except TooManyAttempts as exc:

                self.logger.error("Could not connect, servers may be down: %s", exc)

                # Set/update the GUI state
                self.gui.all_checkboxes_set_state(True)
                self.update_gui_state()

                return

            # Once on_search_info finishes on the thread run the last few on-finish functions
            self.gui.after(0, self._on_search_info_finished)

        # Download the papers in a thread so that the GUI remains responsive
        threading.Thread(target=worker, daemon=True).start()

        # Start the spinner
        self.gui.after(0, lambda: self.gui.start_spinner(ButtonKind.SEARCHINFO))

    def _on_search_info_finished(self) -> None:
        """Method to run once the calculations in 'on_search_info' have finished."""

        # Remove the spinner
        self.gui.stop_spinner(ButtonKind.SEARCHINFO)

        # Re-enable the checkboxes
        self.gui.all_checkboxes_set_state(True)

        # Set/update the GUI state
        self.state.info_found = True
        self.state.papers_downloaded = False
        self.update_gui_state()

        self.logger.info("Ready to download papers.")

    def on_download(self) -> None:
        """Callback for the 'Download Papers' button."""

        self.logger.debug("Selected download_papers button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Disable all GUI buttons and checkboxes
        self.gui.all_buttons_set_state(False)
        self.gui.all_checkboxes_set_state(False)

        # *always ensure the corpus has been cleared first*
        self.logger.debug("Clearing the corpus.")
        self.runner.corpus.clear_corpus()

        # Create the downloading progressbar callback function
        download_cb = self.make_progress_cb(ProgressbarKind.DOWNLOAD)

        # Extract the arxiv client
        api = self.runner.get_api()

        def worker() -> None:
            """Inner function that will download the papers."""

            try:

                # Download the papers
                api.get_papers(
                    self.runner.corpus, self.runner.storage, progress_cb=download_cb
                )

            except XmlReadError as exc:

                self.logger.error("Search info check failed: %s", exc)

                # Re-enable checkboxes and update the GUI state
                self.gui.all_checkboxes_set_state(True)
                self.update_gui_state()

                return

            except TooManyAttempts as exc:

                self.logger.error("Could not connect, servers may be down: %s", exc)

                # Re-enable checkboxes and update the GUI state
                self.gui.all_checkboxes_set_state(True)
                self.update_gui_state()

                return

            # Once on_download finishes on the thread run the last few on-finish functions
            self.gui.after(0, self._on_download_finished)

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

        # Start the spinner
        self.gui.after(0, lambda: self.gui.start_spinner(ButtonKind.DOWNLOAD))

    def _on_download_finished(self):
        """Method to run once the calculations in 'on_download' have finished"""

        # Remove the spinner
        self.gui.stop_spinner(ButtonKind.DOWNLOAD)

        # Re-enable the checkboxes
        self.gui.all_checkboxes_set_state(True)

        # Set/update the GUI state
        self.state.papers_downloaded = True
        self.state.papers_scored = False
        self.update_gui_state()

        self.logger.info("Ready to score papers.")

    def on_score(self) -> None:
        """Callback for the 'Score Papers' button."""

        self.logger.debug("Selected score_papers button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Obtain state of the option menu
        score_algo = self.gui.get_state_from_optionmenu(OptionmenuKind.SCORE)

        # The score function uses the CLI arguments to check how to score
        # Overwrite the arguments based on the score option menu
        if score_algo == OptionsScoreKind.MATCHES.value:

            self.runner.cli.args.score_on_matches = True

        elif score_algo == OptionsScoreKind.ML.value:

            self.runner.cli.args.score_on_matches = False

        else:

            raise NotImplementedError(f"{score_algo} has not yet been implemented")

        self.logger.debug("Using the %s scoring algorithm.", score_algo)

        # Find author/word matches
        self.runner.corpus.find_matches(self.runner.search_params.search_terms)

        # Run the scoring algotithm
        # NOTE: ML algorithm is not yet implemented. Place in a try/except for now.
        try:

            self.runner.cli.score_papers(self.runner.corpus)

        except NotImplementedError:

            self.logger.error("ML algorithm not yet implemented.")

            return

        # Set/update the GUI state
        self.state.papers_scored = True
        self.state.papers_filtered = False
        self.update_gui_state()

        self.logger.info("Ready to filter papers.")

    def on_filter(self) -> None:
        """Callback for the 'Filter Papers' button."""

        self.logger.debug("Selected filter_papers button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Obtain state of the filter option menu
        filter_algo = self.gui.get_state_from_optionmenu(OptionmenuKind.FILTER)

        # The filter function uses the CLI arguments to check how to filter
        # Overwrite the arguments based on the filter option menu
        if filter_algo == OptionsFilterKind.SCORE.value:

            self.runner.cli.args.filter_on_matches = False

        elif filter_algo == OptionsFilterKind.MATCHES.value:

            self.runner.cli.args.filter_on_matches = True

        else:

            raise NotImplementedError(f"{filter_algo} has not yet been implemented")

        self.logger.debug("Using the %s filtering algorithm.", filter_algo)

        # Filter the papers
        self.runner.cli.filter_papers(self.runner.corpus)

        # Set/update the GUI state
        self.state.papers_filtered = True
        self.update_gui_state()

        self.logger.info("Ready for output.")

    def on_open(self) -> None:
        """Callback for the 'Open in Browser' button."""

        self.logger.debug("Selected open_in_browser button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Disable all GUI buttons
        self.gui.all_buttons_set_state(False)
        self.gui.all_checkboxes_set_state(False)

        # The display function uses the CLI arguments to check how to display the results
        # Overwrite the arguments to open the links in the browser and *not* write to a file
        self.runner.cli.open_in_browser = True
        self.runner.cli.write_to_file = False

        # Create the progress bar callback
        results_cb = self.make_progress_cb(ProgressbarKind.RESULTS)

        # Extract the arxiv client
        api = self.runner.get_api()

        def worker() -> None:
            """Inner function that will open the papers."""

            self.runner.cli.display(
                self.runner.storage,
                self.runner.corpus.papers_of_note,
                api.SLEEP_OPENING,
                progress_cb=results_cb,
            )

            # Once get_papers finishes on the thread run the last few on-finish functions
            self.gui.after(0, self._on_open_finished)

        # Download the papers in a thread so that the GUI remains responsive and so that the
        #     progress bar will update
        threading.Thread(target=worker, daemon=True).start()

        # Start the spinner
        self.gui.after(0, lambda: self.gui.start_spinner(ButtonKind.OPEN))

    def _on_open_finished(self):
        """Method to run once the calculations in 'on_open' have finished."""

        # Remove the spinner on the button
        self.gui.stop_spinner(ButtonKind.OPEN)

        # Re-enable all buttons and checkboxes
        self.gui.all_buttons_set_state(True)
        self.gui.all_checkboxes_set_state(True)

        self.logger.info("Opening papers finished.")

    def on_write(self) -> None:
        """Callback for the 'Write to File' button."""

        self.logger.debug("Selected write_to_file button.")

        # Change focus to the main window (in case the dates were changed manually)
        self.gui.default_focus()

        # Obtain state of the write-style option menu
        write_style = self.gui.get_state_from_optionmenu(OptionmenuKind.WRITESTYLE)

        # The display function uses the CLI arguments to check how to display the results
        # Overwrite the arguments to write the links and *not* open in the browser
        self.runner.cli.open_in_browser = False
        self.runner.cli.write_to_file = True
        # Overwrite the argument to set the write style
        if write_style == OptionsWriteKind.LINKS.value:

            self.runner.cli.args.only_ids = False

        elif write_style == OptionsWriteKind.IDS.value:

            self.runner.cli.args.only_ids = True

        else:

            raise NotImplementedError(f"{write_style} has not yet been implemented")

        # Extract the arxiv client
        api = self.runner.get_api()

        # Run the display method
        self.runner.cli.display(
            self.runner.storage,
            self.runner.corpus.papers_of_note,
            api.SLEEP_OPENING,
        )

        self.logger.info("Writing papers to file finished.")

    def update_gui_state(self) -> None:
        """UEnable/disable buttons based on the current GuiState."""

        self.logger.debug("Updating GUI button states.")

        # Extract the current state
        states = self.state.get_button_states()

        # Loop over all the buttons
        for button, button_state in states.items():

            self.gui.button_set_state(button, button_state)

    def make_progress_cb(self, key: ProgressbarKind) -> Callable[[int, int], None]:
        """Create a callback function that will update a progress bar.

        inputs
        ------
        key : The key of the progress bar that should be ubdated

        returns
        -------
        _cb : The callback function
        """

        def _cb(ii: int, total: int) -> None:
            """Callback functions to update the progress bar."""

            # Compute the progress as a fraction
            frac = 0 if total == 0 else ii / total

            # Update the progress bar named by 'key'
            self.gui.after(0, lambda: self.gui.update_progress_bar(key, frac))

        return _cb


def main() -> None:
    """Pipeline that creates the GUI and runs the analysis."""

    Controller().run()
