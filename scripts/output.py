# Import libraries
from scripts.utils import progress_bar, clear_progress_bar
from scripts.dates import write_date

import xml.etree.ElementTree as ET

import webbrowser
import time
import os

def read_catchup(filename, sleep_time, logger):
    """Read the `catchup.txt` file and open all links in the browser.

    inputs
    ------
    filename   : str
        Path_filename of the `catchup.txt` file.
    sleep_time : float
        Wait time between opening links in the browser.
    logger     : RootLogger
        The logger object

    outputs
    -------
    links : list
        Contains all arXiv paper links from the `catchup.txt` file.
    """

    links = []

    with open(filename, "r") as f:

        for line in f:

            link = line.strip()

            if link[:21] != "http://arxiv.org/abs/":

                print("")
                logger.critical("One or more links in the catchup file is malformed.\n          Found    {:}\n          Expected http://arxiv.org/abs/0123.45678v9 format\n".format(link))
                raise

            links.append(link)

    total = len(links)

    request_count = 0
    for link in links:

        progress_bar(request_count, total, ( total - request_count ) * sleep_time)

        if request_count > 0:
            time.sleep(sleep_time)

        if request_count == 0:

            webbrowser.open(link, new=1)  # new=1: open in a new browser window

        else:

            webbrowser.open(link, new=2)  # new=2: open in a new tab

        request_count += 1

    progress_bar(total, total)

    return links

def open_links(args, df, entries, sleep_time, logger):
    """Opens all arXiv links in a webbrowser.

    inputs
    ------
    args       : namespace
        CLI arguments.
    df         : pandas.DataFrame
        Contains all papers and all their information.
    entries    : list
        Contains the indicies of all entries that will be opened. Should pass the post-filtering list.
    sleep_time : float
        Waiting time between opening links.
    logger     : RootLogger
        The logger object
    """

    # Calculate the number of links
    total = len(entries)

    # Loop through the list and open all in the web browser
    request_count = 0
    # time_start = time.time()
    logger.info("Opening the papers. Estimated time: {:.2f} seconds".format(total * sleep_time))
    for link_index in entries:

        progress_bar(request_count, total, ( total - request_count ) * sleep_time)

        # # arXiv asks that you limit opening pages to four requests per second
        # Sleep before the request to prevent an unnecessary sleep at the end
        # # Sleep for 1s every four pages (recommended)
        # if request_count % 4 == 0:
        #     time.sleep(1)
        # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
        if request_count > 0:
            time.sleep(sleep_time)

        link = df.loc[link_index, "url"]

        # Open in new window if flag is set
        if args.new_window:

            if request_count == 0:

                webbrowser.open(link, new=1)  # new=1: open in a new browser window

            else:

                webbrowser.open(link, new=2)  # new=2: open in a new tab

        # Otherwise, open in the current window
        else:

            webbrowser.open(link)  # Default behavior, just opens everything in the current window

        request_count += 1

    progress_bar(total, total)

    return

def write_links(filename, df, entries, logger):
    """Write all links to the `catchup.txt` file.

    inputs
    ------
    filename : str
        Path+filename of the `catchup.txt` file.
    df       : pandas.DataFrame
        Contains all papers and their information.
    entries  : list
        Contains the indicies of all entries that will be opened. Should pass the post-filtering list.
    logger   : RootLogger
        The logger object
    """

    logger.info("Writing all links to the end of the file: {:}".format(filename))

    with open(filename, "a+", encoding="utf-8") as f:

        for link_index in entries:

            link = df.loc[link_index, "url"]
            
            f.write(f"{link}\n")

    return

def write_xml(filename, ns, xml, logger, overwrite=False):
    """

    inputs
    ------
    filename : str
        Path+filename of the `.xml` file.
    xml      : 
    logger   : RootLogger
        The logger object
    """

    # Clear the progress bar in preparation for the info messages later
    clear_progress_bar(logger, 20)

    # As these files are not meant to be touched by the user, and are deleted at the end, logging messages are set to debug

    if overwrite:

        logger.debug("Saving xml to file: {:}".format(filename))
        tree = ET.ElementTree(xml)
        tree.write(filename, encoding="utf-8")

    else:

        # check if the file exists
        if not os.path.exists(filename):

            # Write the xml
            write_xml(filename, ns, xml, logger, overwrite=True)

            return

        else:

            logger.debug("Appending xml to file {:}".format(filename))

            # Load the file
            master_tree = ET.parse(filename)
            master_root = master_tree.getroot()

            new_tree = ET.ElementTree(xml)
            new_root = new_tree.getroot()

            # Obtain each entry and append to the file
            for entry in new_root.findall("atom:entry", ns):
                master_root.append(entry)

            # Write the new file
            master_tree.write(filename, encoding="utf-8", )

    return

def display_results(args, df, entries_of_note, sleep_time, outfile, prev_outfile, end_date, max_num, logger):
    """'Displays' all results, either by opening the links in the browser, outputting them to a file, or by writing them to a file.
    The given display method is chosen by the CLI arguments or user prompts.

    inputs
    ------
    args            : namespace
        CLI arguments
    df              : pandas.DataFrame
        Contains all papers and their information
    entries_of_note : list
        Contains the indices of all papers that were found to be interesting in the filtering.
    sleep_time      : float
        Wait time between opening links in the browser.
    outfile         : str
        Path+filename of the `catchup.txt` file.
    prev_outfile    : str
        Path+filename of the `prev_search.txt` file.
    end_date        : datetime.date
        End date of the arXiv search period.
    max_num         : int
        Number of papers found in the categories of interest.
    logger          : RootLogger
        The logger object
    """

    # If there is at least one paper, open/prompt
    if len(entries_of_note) > 0:

        # If both -f and -w are passed, both open and write the links
        if args.force_open and args.write_to_file:

            open_links(args, df, entries_of_note, sleep_time, logger)
            write_links(outfile, df, entries_of_note, logger)

        # If -f is passed and -w is not, only open the links
        elif args.force_open and not args.write_to_file:

            open_links(args, df, entries_of_note, sleep_time, logger)

        # If -f is not passed and -w is, only write the links
        elif not args.force_open and args.write_to_file:

            write_links(outfile, df, entries_of_note, logger)

        # If neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
        else:

            # Ask the user if they would like to open the links in the browser. Default is no
            user_prompt_browser = input(
                                    "There are {:} link(s). Open in the browser? It will take {:} seconds. [y/N]: ".format(len(entries_of_note), len(entries_of_note)/4)
                                    ).strip().lower()

            # If they say no to opening in the browser
            if user_prompt_browser != "y":

                # Ask if they would like to save the links to a file or print to the terminal. Default is no
                user_prompt_output = input(
                                        "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                                        ).strip().lower()
                
                # If they want the output in the terminal
                if user_prompt_output != "y":

                    logger.info("Printing all links to the terminal:\n")
                    for link_index in entries_of_note:

                        print(df.loc[link_index, "url"])

                # If they want to save the output
                else:

                    # If the file doesn't exist, create it. Otherwise, append the links to the end
                    write_links(outfile, df, entries_of_note, logger)

            # If they say yes to opening in the browser
            else:

                # Open all links
                open_links(args, df, entries_of_note, sleep_time, logger)

    else:

        logger.warning("No papers of interest were found.")

    # Compute the number of digits. Assumes that the number of papers is positive :)
    max_digits = len(str(max_num))

    # Print a summary
    print("")
    logger.info("There was a total of {: >{fill}} papers submitted to the categories of interest since the previous search".format(max_num, fill=max_digits))
    logger.info("           of these, {: >{fill}} papers were opened/linked".format(len(entries_of_note), fill=max_digits))
    print("")

    # Check if any papers were found
    if len(df) == 0:

        logger.warning("As no papers were found, the aux. date file was not updated")

    # If papers were found, update the aux. file
    else:

        # Write the end date of the search to a file for the next run
        write_date(prev_outfile, end_date)

    return