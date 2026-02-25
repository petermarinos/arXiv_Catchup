"""Functions relating to the UI"""

# Import libraries
import webbrowser
import logging
import random
import math
import time
import sys

# # Define constants
# Width of the progress bar (in characters)
WIDTH = 50


def progress_bar(ii: int, total: int, time_estimate: float | None = None) -> None:
    """Prints a progress bar that updates as the loop progresses.

    inputs
    ------
    ii            : Current step in the loop.
    total         : Final step in the loop.
    time_estimate : Estimate of the remaining time of the loop.
    """

    # Compute the percent through the loop
    percent_progress = 100 * ii / total

    # Compute the contents of the bar
    bar_string = ("■" * math.floor(percent_progress * WIDTH / 100)) + (
        "□" * (WIDTH - math.floor(percent_progress * WIDTH / 100))
    )

    # Define the progress message
    progress_message = f"|{bar_string:s}|  {math.ceil(percent_progress):>3}%"

    if time_estimate is not None:
        if time_estimate <= 60:
            progress_message += f"  Remaining: {time_estimate:.2f} seconds"
        elif 60 < time_estimate <= 3600:
            progress_message += f"  Remaining: {time_estimate/60:.1f} minutes"
        else:
            progress_message += f"  Remaining: {time_estimate/3600:.1f} hours"

    # # Compute the padding to overwrite all text with whitespace
    # Maximum time is 2.5 hours.
    # Minutes and seconds can go up to 59.
    # => maximum digits before the decimal = 2
    # Maximum digits after the decimal = 2
    # Additional text is therefore: "||  xxx%  Remaining: xx.xx seconds" => 34 characters
    # Maximum length of the message is width+33
    # Add some padding to ensure the messages are always overwritten on every update
    pad = " " * (WIDTH + 34 - len(progress_message))

    sys.stdout.write(
        f"\r{progress_message}{pad}"
    )  # Move cursor to the start of the line and print the progress message
    sys.stdout.flush()

    # If it is the final call, print a blank line
    if ii == total:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


def pretty_sleep(logger: logging.Logger, sleep_time: float) -> None:
    """Shows a progress bar if sleeping for a long time.
    NOTE: Also adds jitter.

    inputs
    ------
    logger     : The logger object
    sleep_time : Time to sleep for
    """

    # Add jitter
    sleep_time = sleep_time + random.uniform(0, 0.3)
    logger.debug(f"Sleeping for {sleep_time:.3f} seconds ...")

    # If sleeping for a short time (under 5s), do a normal sleep
    if sleep_time <= 5:
        time.sleep(sleep_time)

    # If sleeping for a long time, show a progress bar
    else:

        # Flush any already-existing progress bar
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()

        # Update the bar every 0.1s
        n_steps = math.ceil(sleep_time * 10)
        for ii in range(0, n_steps):

            progress_bar(ii, n_steps, 0.1 * (n_steps - ii))
            time.sleep(0.1)

        progress_bar(n_steps, n_steps)


def open_links(papers_of_note: list[str], sleep_time: float):
    """Open all links in the webbrowser.
    NOTE: While we extract the abs links from the downloaded data, we reconstruct the links here
          using the arXiv ID numbers. This is done to slightly reduce complexity while giving the
          CLI option to only write the ID numbers to files.

    inputs
    ------
    papers_of_note : The arXiv ID numbers of all papers that passed filtering
    sleep_time     : Time to sleep for between opening papers
    """

    total = len(papers_of_note)

    request_count = 0
    for arxiv_id in papers_of_note:

        link = f"https://arxiv.org/abs/{arxiv_id}"

        progress_bar(request_count, total, (total - request_count) * sleep_time)

        if request_count > 0:

            time.sleep(sleep_time)

        if request_count == 0:

            webbrowser.open(link, new=1)  # new=1: open in a new browser window

        else:

            webbrowser.open(link, new=2)  # new=2: open in a new tab

        request_count += 1

    progress_bar(total, total)
