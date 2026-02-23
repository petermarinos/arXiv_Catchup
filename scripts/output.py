"""Functions used in creating the outputs."""

# fmt: off
# Import standard libraries
import webbrowser
import argparse
import logging
import pathlib
import time

# Import functions
from .file_io import write_links
from .ui      import progress_bar
# fmt: on


def display(
    logger: logging.Logger,
    args: argparse.Namespace,
    papers_of_note: list[str],
    open_in_browser: bool,
    sleeptimer: float,
    write_to_file: bool,
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

    if write_to_file:

        write_links(logger, args, papers_of_note, filename)

    if open_in_browser:

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
            if args.new_window:

                if request_count == 0:

                    webbrowser.open(link, new=1)  # new=1: open in a new browser window

                else:

                    webbrowser.open(link, new=2)  # new=2: open in a new tab

            # Otherwise, open in the current window
            else:

                webbrowser.open(
                    link
                )  # Default behavior, just opens everything in the current window

            request_count += 1

        progress_bar(total, total)
