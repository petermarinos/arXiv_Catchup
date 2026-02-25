"""CLI class, for interactions with the CLI."""

# Import dependency type checking libraries
from __future__ import annotations
from typing import TYPE_CHECKING

# Import libraries
import logging
import pathlib
import sys

# Import functions
from .utils import cli_args
from .ui import open_links

# Import classes for type checking
if TYPE_CHECKING:
    from .storage_manager import Storage
    from .arxiv_client import ArxivClient
    from .corpus import Corpus


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
            self.open_in_browser = False

        # if -w is passed
        if self.args.write_to_file:
            self.write_to_file = True
        else:
            self.write_to_file = False

    def add_logger(self, logger: logging.Logger) -> None:
        """
        Setting up the logger requires knowlegde of the storage manager. Add the logger to this
        class after it has been created.
        """

        self.logger = logger

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
                f"There are {arxiv_client.total_papers:d} papers. "
                f"The search will take {time_to_search_minutes:.1f} minutes."
            )

        # Prompt the user if it is going to take a really long time.
        elif time_to_search_minutes >= 5:

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

                # Delete the .xml file
                storage.delete_file(xml_path)

                # Exit
                sys.exit(
                    "Cancelling the search. Reduce search window to decrease the number of results."
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

                    self.open_in_browser = True

                # If they say no to opening in the browser
                else:

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

                        self.write_to_file = True

                    # If they want the output in the terminal
                    else:

                        self.logger.info("Printing all links to the terminal:\n")
                        for arxiv_id in corpus.papers_of_note:

                            # Show *regardless* of logging level. Critical output.
                            print(corpus.corpus[arxiv_id].paper_info.link_abs)

                        # After printing all the papers, also print a blank space.
                        print("")

    def display(
        self,
        storage: Storage,
        papers_of_note: list[str],
        sleeptimer: float,
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

            # Print a time estimate
            est_time = len(papers_of_note) * sleeptimer
            self.logger.info(
                f"Opening the papers. Estimated time: {est_time:.2f} seconds"
            )

            open_links(papers_of_note, sleeptimer)
