"""CLI class, for interactions with the CLI."""

# Import dependency type checking libraries
from __future__ import annotations
from typing import TYPE_CHECKING

# Import libraries
from collections.abc import Callable
import logging
import pathlib

# Import functions
from .utils import cli_args
from .ui import open_links

# Import classes for type checking
if TYPE_CHECKING:
    from .storage_manager import Storage
    from .arxiv_client import ArxivClient
    from .corpus import Corpus


class UserCancel(Exception):
    """Exception raised if the user chooses to cancel the search.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class CLI:
    """Deals with all CLI tasks."""

    def __init__(self) -> None:
        """Obtain the CLI arguments"""

        self.logger: logging.Logger

        self.args = cli_args()

        # if -f is passed
        if self.args.force_open:
            self.open_in_browser = True
        else:
            self.open_in_browser = False  # May be mutated later

        # if -w is passed
        if self.args.write_to_file:
            self.write_to_file = True
        else:
            self.write_to_file = False  # May be mutated later

        self.delete_catchup = False  # May be mutated later

    def add_logger(self) -> None:
        """
        Setting up the logger requires knowlegde of the storage manager. Add the logger to this
        class after it has been created.
        """

        # Obtain the logger
        self.logger = logging.getLogger(__name__)

    def check_continue_status(
        self,
        arxiv_client: ArxivClient,
        storage: Storage,
        xml_path: pathlib.Path,
    ) -> None:
        """Warns the user if the search will take a long time, or forces them to confirm.

        inputs
        ------
        logger       : The logger object.
        arxiv_client : The arXiv client object.
        xml_path     : Path+filename to the search .xml file.
        """

        # Compute the time it will take to download all papers
        time_to_search_minutes = (
            arxiv_client.total_papers
            * arxiv_client.SLEEP_SEARCH
            / (arxiv_client.SEARCH_BLOCKSIZE * 60)
        )

        # Print a warning if it is going to take a long time
        if 1 <= time_to_search_minutes < 5:

            self.logger.warning(
                "There are %s papers. The search will take %.1f minutes.",
                arxiv_client.total_papers,
                time_to_search_minutes,
            )

        # Prompt the user if it is going to take a really long time.
        elif time_to_search_minutes >= 5:

            self.logger.debug("Prompting user | Long search time, continue? [y/N]")

            user_prompt = (
                input(
                    f"There are {arxiv_client.total_papers:d} papers. "
                    f"The search will take {time_to_search_minutes:.1f} minutes. "
                    "Continue? [y/N]: "
                )
                .strip()
                .lower()
            )

            # If they want to continue, do nothing.
            # If they do not want to continue, end the search
            if user_prompt != "y":

                self.logger.debug(
                    "User prompt | did not reply with 'y'. Cancelling search."
                )

                # Delete the .xml file
                storage.delete_file(xml_path)

                # Raise the cancellation error
                raise UserCancel(
                    "Cancelling the search. "
                    "Reduce search window to decrease the number of results."
                )

    def score_papers(self, corpus: Corpus) -> None:
        """Wrapper to choose which scoring algorithm is used based on the CLI arguments that were
        passed.
        NOTE: While ML is not implemented, the CLI argument cannot be changed and the score will
              always be used.
        """

        # If argument was passed, score papers based on matches
        if self.args.score_on_matches:

            corpus.score_papers_matches()

        # DEFAULT: Score based on ml algorithm.
        # NOTE: Not yet implemented. Current default is actually to use matches, as the CLI argument
        #       is always True
        else:

            corpus.score_papers_ml()

    def filter_papers(self, corpus: Corpus) -> None:
        """Wrapper to choose with filtering algorithm is used based on the CLI arguments that were
        passed
        """

        # If argument was passed, filter based on matches
        if self.args.filter_on_matches:

            corpus.filter_papers_matches()

        # DEFAULT: filter based on score
        else:

            corpus.filter_papers_score()

    def get_display_method(self, arxiv_client: ArxivClient, corpus: Corpus) -> None:
        """Find the preferred method of displaying the results.

        inputs
        ------
        arxiv_const : All constants related to arXiv connections.
        corpus      : The entire corpus of results.
        """

        # If no papers were found, overwrite output bools with False
        if len(corpus.papers_of_note) == 0:

            self.write_to_file = False
            self.open_in_browser = False

        # If there is at least one paper, open/prompt
        else:

            # If neither -f nor -w were passed, prompt the user for the behaviour they prefer
            if not self.write_to_file and not self.open_in_browser:

                est_time = len(corpus.papers_of_note) * arxiv_client.SLEEP_OPENING

                self.logger.debug("Prompting user | Open in browser? [y/N]")

                # Ask the user if they would like to open the links in the browser
                user_prompt_browser = (
                    input(
                        f"\nThere are {len(corpus.papers_of_note)} link(s). "
                        f"Open in the browser? It will take {est_time} seconds. [y/N]: "
                    )
                    .strip()
                    .lower()
                )

                # If they say yes to opening in the browser
                if user_prompt_browser == "y":

                    self.logger.debug(
                        "User prompt | Replied with 'y'. Will open links."
                    )

                    self.open_in_browser = True

                # If they say no to opening in the browser
                else:

                    self.logger.debug("User prompt | Did not reply with 'y'.")

                    self.logger.debug("Prompting user | Write links to file? [y/N]")

                    # Ask the user if they would like to save the links to a file or the terminal.
                    user_prompt_file = (
                        input(
                            "Save all links to a file? "
                            "Otherwise they will be written to the terminal. [y/N]: "
                        )
                        .strip()
                        .lower()
                    )

                    # If they want to save the output
                    if user_prompt_file == "y":

                        self.logger.debug(
                            "User prompt | Replied with 'y'. Will write links to file."
                        )

                        self.write_to_file = True

                    # If they want the output in the terminal
                    else:

                        self.logger.debug(
                            "User prompt | Did not reply with 'y'. Will write links to the CLI."
                        )

                        print("Printing all links to the terminal:\n")
                        for arxiv_id in corpus.papers_of_note:

                            # Show *regardless* of logging level. Critical output.
                            print(corpus.corpus[arxiv_id].paper_info.link_abs)

                        # After printing all the papers, also print a blank space.
                        print("")

    def get_delete_catchup_bool(self, storage: Storage, links: list[str]) -> None:
        """Prompt the user to ask if the catchup file should be deleted.

        inputs
        ------
        storage : Storage object
        links : List containing all arXiv links in the file.
        """

        # Ask the user if they would like to open the links in the browser. Default is no
        self.logger.warning(
            "There are %s links in %s.", len(links), storage.paths.catchup
        )
        self.logger.debug("Prompting user | Delete all links? [y/N]")

        user_prompt = (
            input(
                "         Delete all links? This action cannot be reversed. "
                "Only do so if the papers have been reviewed. [y/N]: "
            )
            .strip()
            .lower()
        )

        # If the user says yes, set deletion flag to True
        if user_prompt == "y":

            self.logger.debug("User prompt | Replied 'y', will delete file")

            self.delete_catchup = True

        # Else, set deletion flag to False
        else:

            self.logger.debug(
                "User prompt | Did not reply with 'y'. Will not delete file."
            )

            self.delete_catchup = False

    def display(
        self,
        storage: Storage,
        papers_of_note: list[str],
        sleeptimer: float,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> None:
        """Displays the results to the user, based on their preference.

        inputs
        ------
        logger          : The logger object.
        args            : CLI arguments.
        papers_of_note  : arXiv ID numbers for papers that passed filtering.
        open_in_browser : Flag to open in browser (True) or not (False).
        sleeptimer      : Time to sleep between commands to webbrowser.
        write_to_file   : Flag to write results to a file (True) or not (False).
        filename        : Path+filename of the output file.
        """

        if self.write_to_file:

            storage.write_catchup_file(self.args, papers_of_note)

        if self.open_in_browser:

            open_links(papers_of_note, sleeptimer, progress_cb)
