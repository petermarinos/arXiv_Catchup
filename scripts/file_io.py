# Import functions
from scripts.utils import progress_bar, clear_progress_bar

# Import libraries
import xml.etree.ElementTree as ET
import webbrowser
import time
import yaml
import os

def load_searchterms(self):
    """Loads the user-defined search terms from the `search_terms.yaml` into a dictionary.

    inputs
    ------
    filename : str
        Path+filename of the `search_terms.yaml` file.
    logger   : RootLogger
        The logger object

    outputs
    -------
    search_terms  : dict
        Dictionary of all loaded search terms.
    cat_urlstring : str
        String containing the url used in the arXiv API queries
    """

    self.logger.info("Loading search terms from {:}.".format(self.paths["searchterms"]))

    # Load the .yaml into a dictionary
    with open(self.paths["searchterms"], 'r') as f:

        search_terms = yaml.safe_load(f)

    # # Check the file

    # At least one category is required
    if search_terms["Categories"] is None:

        self.logger.critical("No search terms were found in the 'Categories' entry in the configuration file.\n          Please check the file and add at least one item.\n")
        raise
    
    else:

        # Define category string for the urls/API calls
        cat_urlstring = "+OR+".join(f"cat:{c}" for c in search_terms["Categories"])

        # Define category string to make nice print statements
        if len(search_terms["Categories"]) == 2:

            cat_printstring = " and ".join(f"{c}" for c in search_terms["Categories"])

        elif len(search_terms["Categories"]) > 2:

            catstring_temp = ", ".join(f"{c}" for c in search_terms["Categories"][:-1])
            cat_printstring = ", and ".join([catstring_temp, search_terms["Categories"][-1]])

        else:

            cat_printstring = ", ".join(f"{c}" for c in search_terms["Categories"])

        # Print which categories are being searched over
        self.logger.info("Searching the {:} categories".format(cat_printstring))

    # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
    # No need to catch it here

    # # At least one search term is required in the "Words" key
    # # Depreciated. Now just a warning
    if search_terms["Included Words"] is None:

        self.logger.warning("No search terms were found in the 'Included Words' entry in the configuration file.")
        raise

    # No search terms are required for the "Authors" or "Excluded Words" keys
    # Warn the user if no terms are found
    if search_terms["Authors"] is None:

        self.logger.warning("No search terms were found in the 'Authors' entry in the configuration file.")

    if search_terms["Excluded Words"] is None:

        self.logger.warning("No search terms were found in the 'Excluded Words' entry in the configuration file.")

    return search_terms, cat_urlstring

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

def write_links(logger, filename, df, papers_of_note):
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

        for link_index in papers_of_note:

            link = df.loc[link_index, "url"]
            
            f.write(f"{link}\n")

    return

def write_xml(logger, filename, xml_data, ns, overwrite=False):
    """Writes an XML to a .xml file.

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
        tree = ET.ElementTree(xml_data)
        tree.write(filename, encoding="utf-8")

    else:

        # check if the file exists
        if not os.path.exists(filename):

            # Write the xml
            write_xml(logger, filename, xml_data, ns, overwrite=True)

            return

        else:

            logger.debug("Appending xml to file {:}".format(filename))

            # Load the file
            master_tree = ET.parse(filename)
            master_root = master_tree.getroot()

            new_tree = ET.ElementTree(xml_data)
            new_root = new_tree.getroot()

            # Obtain each entry and append to the file
            for entry in new_root.findall("atom:entry", ns):
                master_root.append(entry)

            # Write the new file
            master_tree.write(filename, encoding="utf-8", )

    return

def write_date(logger, filename, date):
    """Write a datetime.date object to a file.
    While the current implementation only uses this to write Papers.start_date to Papers.paths['prevsearch'], this function is left as-is.

    inputs
    ------
    filename : str
        Path+filename of the `prev_search.txt` file.
    date     : datetime.date
        Date that is being written
    """

    logger.info("Writing the date {:} to the file: {:}.".format(date, filename))

    with open(filename, "w") as f:
        f.write(date.isoformat())

    return

def display_results(self):
    """'Displays' all results, either by opening the links in the browser, outputting them to a file, or by writing them to a file.
    The given display method is chosen by the CLI arguments or user prompts.

    inputs
    ------
    """

    browser_flag = False

    # If there is at least one paper, open/prompt
    if len(self.papers_of_note) > 0:

        # If both -f and -w are passed, both open and write the links
        if self.args.force_open and self.args.write_to_file:

            browser_flag = True
            write_links(self.logger, self.paths["catchup"], self.df_papers, self.papers_of_note)

        # If -f is passed and -w is not, only open the links
        elif self.args.force_open and not self.args.write_to_file:

            browser_flag = True

        # If -f is not passed and -w is, only write the links
        elif not self.args.force_open and self.args.write_to_file:

            write_links(self.logger, self.paths["catchup"], self.df_papers, self.papers_of_note)

        # If neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
        else:

            # Ask the user if they would like to open the links in the browser. Default is no
            user_prompt_browser = input(
                                        "There are {:} link(s). Open in the browser? It will take {:} seconds. [y/N]: ".format(len(self.papers_of_note), len(self.papers_of_note) * self.arxivConst.sleeptimer_opening)
                                       ).strip().lower()

            # If they say no to opening in the browser
            if user_prompt_browser != "y":

                # Ask if they would like to save the links to a file or print to the terminal. Default is no
                user_prompt_file = input(
                                        "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                                        ).strip().lower()
                
                # If they want the output in the terminal
                if user_prompt_file != "y":

                    self.logger.info("Printing all links to the terminal:\n")
                    for link_index in self.papers_of_note:

                        print(self.df_papers.loc[link_index, "url"])
                    print("")

                # If they want to save the output
                else:

                    # If the file doesn't exist, create it. Otherwise, append the links to the end
                    write_links(self.logger, self.paths["catchup"], self.df_papers, self.papers_of_note)

            # If they say yes to opening in the browser
            else:

                # Open all links
                browser_flag = True

    else:

        self.logger.warning("No papers of interest were found.")

    # Check if any papers were found
    if len(self.df_papers) == 0:

        self.logger.warning("As no papers were found, the aux. date file was not updated")

    # If papers were found, update the aux. file
    else:

        # Write the end date of the search to a file for the next run
        write_date(self.logger, self.paths["prevsearch"], self.end_date)

    return browser_flag