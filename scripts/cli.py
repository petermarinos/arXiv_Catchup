"""CLI class, for interactions with the CLI."""

# fmt: off
# Import libraries
import webbrowser
import logging
import pathlib
import time
import sys

# Import classes
from .arxiv_client import ArxivClient
from .corpus       import Corpus

# Import functions
from .file_io import write_links
from .utils   import cli_args, delete_file
from .ui      import progress_bar
# fmt: on


# Import functions


class CLI:
    """Deals with all CLI tasks."""

    def __init__(self):
        """Obtain the CLI arguments"""

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
            self.open_in_browser = False

        # If there is at least one paper, open/prompt
        else:

            # If neither -f nor -w were passed, prompt the user for the behaviour they prefer
            if not self.write_to_file and not self.open_in_browser:

                est_time = len(corpus.papers_of_note) * arxiv_client.SLEEP_OPENING

                # Ask the user if they would like to open the links in the browser
                print("")
                user_prompt_browser = (
                    input(
                        f"There are {len(corpus.papers_of_note)} link(s). "
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

                        print("\nPrinting all links to the terminal:\n")
                        for arxiv_id in corpus.papers_of_note:

                            print(corpus.corpus[arxiv_id].paper_info.link_abs)
                        print("")

    def display(
        self,
        logger: logging.Logger,
        papers_of_note: list[str],
        sleeptimer: float,
        filename: pathlib.Path,
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

            write_links(logger, self.args, papers_of_note, filename)

        if self.open_in_browser:

            # Calculate the number of links
            total = len(papers_of_note)

            # Loop through the list and open all in the web browser
            request_count = 0
            est_time = total * sleeptimer
            logger.info(f"Opening the papers. Estimated time: {est_time:.2f} seconds")
            for arxiv_id in papers_of_note:

                progress_bar(request_count, total, (total - request_count) * sleeptimer)

                # # arXiv asks that you limit opening pages to four requests per second.
                # They recommend burst of four papers, but I prefer one per every quarter second.
                if request_count > 0:

                    time.sleep(sleeptimer)

                link = f"https://arxiv.org/abs/{arxiv_id}"

                # Open in new window if flag is set
                if self.args.new_window:

                    if request_count == 0:

                        webbrowser.open(
                            link, new=1
                        )  # new=1: open in a new browser window

                    else:

                        webbrowser.open(link, new=2)  # new=2: open in a new tab

                # Otherwise, open in the current window
                else:

                    webbrowser.open(
                        link
                    )  # Default behavior, just opens everything in the current window

                request_count += 1

            progress_bar(total, total)
