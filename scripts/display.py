# Import functions
from scripts.file_io import write_date
from scripts.utils   import progress_bar

# Import libraries
import webbrowser
import time

def open_links(self):
    """Opens all arXiv links in a webbrowser.

    inputs
    ------
    self : Papers object
    """

    # Calculate the number of links
    total = len(self.papers_of_note)

    # Loop through the list and open all in the web browser
    request_count = 0
    # time_start = time.time()
    self.logger.info("Opening the papers. Estimated time: {:.2f} seconds".format(total * self.arxiv_const.sleeptimer_opening))
    for link_index in self.papers_of_note:

        progress_bar(request_count, total, ( total - request_count ) * self.arxiv_const.sleeptimer_opening)

        # # arXiv asks that you limit opening pages to four requests per second
        # Sleep before the request to prevent an unnecessary sleep at the end
        # # Sleep for 1s every four pages (recommended)
        # if request_count % 4 == 0:
        #     time.sleep(1)
        # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
        if request_count > 0:
            time.sleep(self.arxiv_const.sleeptimer_opening)

        link = self.df_papers.loc[link_index, "url"]

        # Open in new window if flag is set
        if self.args.new_window:

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

def summarise_search(self):
    """Print some information to the terminal that summarises the results of the search
    
    inputs
    ------
    self : Papers object
    """

    # Compute the number of digits. Assumes that the number of papers is positive :)
    max_digits = len(str(self.total_papers))
    
    # Print a summary
    print("")
    self.logger.info("There was a total of {: >{fill}} papers submitted to the categories of interest within the search window.".format(self.total_papers, fill=max_digits))
    self.logger.info("           of these, {: >{fill}} papers were opened/linked.".format(len(self.papers_of_note), fill=max_digits))
    print("")

    return

def display_results(self):
    """Determines the display method, i.e. opening the links in the browser, outputting them to the terminal, or by writing them to a file.
    NOTE: This function doesn't open the links in the browser or write the, to a file, but will print them to the terminal.

    inputs
    ------
    self : Papers object

    outputs
    -------
    browser_flag  : bool
        True if links will be opened in the browser
    file_flag     : bool
        True if links will be written to a file
    """

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(self.df_papers["Authors Matches"]):

        print("\n    Found Author(s):")

        # Compute a fill amount, so that all author lists are right-justified.
        # 8 characters more then the longest name, to account for ', et al.'
        author_strfill = len(max(self.search_terms["Authors"], key=len)) + 8

        # Loop through the papers that survived the filter and print the ones with author matches
        for entry_count in self.papers_of_note:

            author_score       = self.df_papers.loc[entry_count, "Authors Score"]
            num_author_matches = self.df_papers.loc[entry_count, "Authors Matches"]

            # If only one author match
            if ( num_author_matches == 1) and ( author_score > 0.95 ):

                print("{: >{fill}}:  {url:}".format(self.df_papers.loc[entry_count, "Found Authors"][0], fill=author_strfill, url=self.df_papers.loc[entry_count, "url"]))

            # If more than one author match:
            elif ( num_author_matches >= 2) and ( author_score > 0.95 ):

                print("{: >{fill}}:  {url:}".format(self.df_papers.loc[entry_count, "Found Authors"][0]+", et al.", fill=author_strfill, url=self.df_papers.loc[entry_count, "url"]))

    browser_flag = False
    file_flag    = False

    # If there is at least one paper, open/prompt
    if len(self.papers_of_note) > 0:

        # If both -f and -w are passed, both open and write the links
        if self.args.force_open and self.args.write_to_file:

            browser_flag = True
            file_flag    = True

        # If -f is passed and -w is not, only open the links
        elif self.args.force_open and not self.args.write_to_file:

            browser_flag = True

        # If -f is not passed and -w is, only write the links
        elif not self.args.force_open and self.args.write_to_file:

            file_flag = True

        # If neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
        else:

            # Ask the user if they would like to open the links in the browser. Default is no
            print("")
            user_prompt_browser = input(
                                        "There are {:} link(s). Open in the browser? It will take {:} seconds. [y/N]: ".format(len(self.papers_of_note), len(self.papers_of_note) * self.arxiv_const.sleeptimer_opening)
                                       ).strip().lower()

            # If they say yes to opening in the browser
            if user_prompt_browser == "y":

                browser_flag = True

            # If they say no to opening in the browser
            else:

                # Ask if they would like to save the links to a file or print to the terminal. Default is no
                user_prompt_file = input(
                                        "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                                        ).strip().lower()

                # If they want to save the output
                if user_prompt_file == "y":

                    file_flag = True
                
                # If they want the output in the terminal
                else:

                    print("")
                    self.logger.info("Printing all links to the terminal:\n")
                    for link_index in self.papers_of_note:

                        print(self.df_papers.loc[link_index, "url"])
                    print("")

    else:

        self.logger.warning("No papers of interest were found.")

    # Check if any papers were found
    if len(self.df_papers) == 0:

        self.logger.warning("As no papers were found, the date file was not updated")

    # If papers were found, update the date file
    else:

        # Write the end date of the search to a file for the next run
        write_date(self.logger, self.paths["prevsearch"], self.end_date)

    return browser_flag, file_flag