"""CLI class, for interactions with the CLI."""

# fmt: off
# Import libraries
import logging
import pathlib
import sys

# Import classes
from .arxiv_client import ArxivClient
from .corpus       import Corpus

# Import functions
from .utils import cli_args, delete_file
# fmt: on


class CLI:
    """Deals with all CLI tasks."""

    def __init__(self):
        """Obtain the CLI arguments"""

        self.args = cli_args()

        # if -f is passed
        if self.args.force_open:
            self.open_in_brower = True
        else:
            self.open_in_brower = False

        # if -w is passed
        if self.args.write_to_file:
            self.write_to_file = True
        else:
            self.write_to_file = False

    def check_continue_status(
        self,
        logger: logging.Logger,
        arxiv_client: ArxivClient,
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

            logger.warning(
                "There are {total_papers:d} papers. "
                + f"The search will take {time_to_search_minutes:.1f} minutes."
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
                delete_file(logger, xml_path)

                # Exit
                sys.exit(
                    "Cancelling the search. Reduce search window to decrease the number of results."
                )

    def get_display_method(self, arxiv_client: ArxivClient, corpus: Corpus) -> None:
        """Find the preferred method of displaying the results.

        inputs
        ------
        arxiv_const : All constants related to arXiv connections.
        corpus      : The entire corpus of results.
        """

        # If no papers were found, overwrite output bools with False
        if len(corpus.papers_of_note) == 0:

            # self.logger.warning("No papers of interest were found.")
            self.write_to_file = False
            self.open_in_brower = False

        # If there is at least one paper, open/prompt
        else:

            # If neither -f nor -w were passed, prompt the user for the behaviour they prefer
            if not self.write_to_file and not self.open_in_brower:

                est_time = len(corpus.papers_of_note) * arxiv_client.SLEEP_OPENING

                # Ask the user if they would like to open the links in the browser
                print("")
                user_prompt_browser = (
                    input(
                        f"There are {len(corpus.papers_of_note)} link(s). "
                        + f"Open in the browser? It will take {est_time} seconds. [y/N]: "
                    )
                    .strip()
                    .lower()
                )

                # If they say yes to opening in the browser
                if user_prompt_browser == "y":

                    self.open_in_brower = True

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

                        print("\nPrinting all links to the terminal:\n")
                        for arxiv_id in corpus.papers_of_note:

                            print(corpus.corpus[arxiv_id].paper_info.link_abs)
                        print("")
