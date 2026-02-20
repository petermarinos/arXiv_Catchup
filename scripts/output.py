# Import functions
from .file_io import write_links
from .utils   import progress_bar

# Import libraries
import webbrowser
import argparse
import logging
import time


def display(logger: logging.Logger, args: argparse.Namespace, papers_of_note, open_in_browser, sleeptimer, write_to_file, filename) -> None:
    """Displays the results to the user, based on their preference.
    """

    if write_to_file:

        write_links(logger, args, papers_of_note, filename)

    if open_in_browser:
        
        # Calculate the number of links
        total = len(papers_of_note)

        # Loop through the list and open all in the web browser
        request_count = 0
        # time_start = time.time()
        logger.info("Opening the papers. Estimated time: {:.2f} seconds".format(total * sleeptimer))
        for arxiv_id in papers_of_note:

            progress_bar(request_count, total, ( total - request_count ) * sleeptimer)

            # # arXiv asks that you limit opening pages to four requests per second. They recommend burst of four papers, but I prefer one per every quarter second.
            if request_count > 0:

                time.sleep(sleeptimer)

            link = "https://arxiv.org/abs/"+arxiv_id

            # Open in new window if flag is set
            if args.new_window:

                if request_count == 0:

                    webbrowser.open(link, new=1) # new=1: open in a new browser window

                else:

                    webbrowser.open(link, new=2) # new=2: open in a new tab

            # Otherwise, open in the current window
            else:

                webbrowser.open(link) # Default behavior, just opens everything in the current window

            request_count += 1

        progress_bar(total, total)