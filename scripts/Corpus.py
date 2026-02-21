"""Corpus class."""

# fmt: off
# Import standard libraries
import xml.etree.ElementTree as ET
import logging
import pathlib
import typing
import os

# Import non-standard libraries
import numpy as np

# Import function
from .arxiv_query import arxiv_query
from .file_io     import write_xml
from .utils       import progress_bar, pretty_sleep, delete_file

# Import classes
from .arxiv_client import ArxivClient, ArxivConst
from .paper        import Paper
# fmt: on


class Corpus:
    """Contains the entire corpus downloaded from the arXiv servers."""

    # # Initialise the class
    def __init__(self, logger: logging.Logger) -> None:
        """Create the Corpus object.

        inputs
        ------
        logger : The logger object
        """

        self.logger = logger

        self.corpus: dict[str, Paper] = {}

        self.length = 0

    # # Clear the Corpus
    def clear_corpus(self) -> None:
        """Delete all entries in the Corpus"""

        self.logger.debug("Deleting all entries in the corpus.")

        # Replace the corpus with an empty dictionary
        self.corpus: dict[str, Paper] = {}

        # Set the length back to zero
        self.length = 0

    # # Add a Paper object to the Corpus
    def add_paper_to_corpus(self, ns: dict[str, str], entry: ET.Element) -> None:
        """Add a paper to the Corpus object

        inputs
        ------
        ns    : XML namespace.
        entry : XML data containing a single paper.
        """

        # Extract the paper from the xml entry
        paper = Paper(self.logger, ns, entry)

        # Add the paper to the corpus dictionary
        key = paper.paperInfo.id_num + "v{:d}".format(
            paper.paperInfo.version
        )  # include version to ensure each key is unique. We will drop revisions later
        value = paper
        self.corpus[key] = value

        # Add one to the length
        self.length += 1

    def extract_papers(
        self, ns: dict[str, str], xml_data: ET.ElementTree | ET.Element
    ) -> None:
        """Extracts the papers (and their information) from the results of the API query.

        inputs
        ------
        logger : The logger object.
        corpus : The corpus of all papers currently found.
        ns     : XML namespaces that arXiv uses.
        xml    : XML data from the arXiv query.
        """

        # Loop over the entries (papers) within the current search
        count = 0
        for entry in xml_data.findall("atom:entry", ns):

            self.add_paper_to_corpus(ns, entry)

            count += 1

        self.logger.debug("Found {:} papers in this search block.".format(count))

        return

    # # Loop through the searches and obtain all papers
    def get_papers(
        self, arxiv_const: ArxivConst, api: ArxivClient, xml_path: pathlib.Path
    ) -> None:
        """Obtains all Papers and places them in the Corpus. Will attempt to load the Corpus from an .xml file, and will fall back to querying the arXiv servers in case no file was found, or the file does not match the current search parameters."""

        # Search for xml file. If found, load it
        if os.path.exists(xml_path):

            self.logger.info("Found an .xml file: {:}".format(xml_path))
            self.logger.info("Continuing from the previous failed run.")

            # Load the file
            try:
                xml_tree = typing.cast(ET.ElementTree, ET.parse(xml_path))
            except ET.ParseError as e:
                self.logger.critical("Could not parse XML: %s", e)
                raise

            # Extract the papers from the xml
            self.extract_papers(arxiv_const.ns, xml_tree)

            # Print how many were found
            # Compute the length of the corpus
            n_papers = self.length
            self.logger.info(
                "Found {:} of {:} papers in the .xml file.".format(
                    self.length, api.total_papers
                )
            )

            # Check the url from the loaded xml matches the current search url
            expected_url = api.apiquery.format(
                start_num=0, blocksize=arxiv_const.search_blocksize
            )
            returned_urlblock = xml_tree.find("atom:link", arxiv_const.ns)
            if returned_urlblock is None:
                self.logger.critical(
                    "arXiv data did not include a link. It is corrupted (returned None).\n"
                )
                raise
            returned_url = returned_urlblock.attrib["href"]

            url_missmatch = expected_url != returned_url

            # If the urls do not match, discard and restart the search
            if url_missmatch:

                self.logger.warning(
                    "The .xml file information does not match the current search. Discarding the file and re-connecting."
                )
                self.logger.debug("Expected: {:}".format(expected_url))
                self.logger.debug("Found:    {:}".format(returned_url))

                # # Clear the entries from the list.
                # entries = []
                self.clear_corpus()

                # Clear the .xml file
                delete_file(self.logger, xml_path)

            # If the urls match AND the number of papers was less than the total:
            elif (not url_missmatch) and (n_papers < api.total_papers):
                self.logger.debug(
                    "The .xml file information matches the current search. Continuing."
                )

            # If less than the total, provide info that we are continuing the search
            elif n_papers >= api.total_papers:

                self.logger.info(
                    "All information found in the .xml file. Skipping the search."
                )

        # Compute the length of the corpus
        n_papers = self.length
        # If the number of papers is less that the total, connect to arXiv
        if n_papers < api.total_papers:

            # Set the starting number
            start_num = n_papers

            self.logger.debug(
                "The number of papers found so far is: {:}".format(start_num)
            )

            # # Compute the estimated time for the search
            # The time to complete depends almost entirely on the number of connections to arXiv and the number of sleeps, though there is some slowdown due to connecting to the arXiv servers and waiting for a response
            # It is typically 0.7s per connection, though it varies *wildly*
            # We also add jitter to the timers with random.uniform(0, 0.3) (average slowdown of 0.15 seconds)
            # Because of how wildly it varies, computing the remaining search time accurately during the loop is pointless. Just use the fudge_timer
            fudge_timer = 0.7 + 0.15
            est_time = -(arxiv_const.sleep_search + fudge_timer) * (
                (api.total_papers - start_num) // -arxiv_const.search_blocksize
            )

            # Compute the number of steps it will take
            num_steps = int(
                np.ceil(api.total_papers / arxiv_const.search_blocksize)
                * arxiv_const.search_blocksize
            )

            # Search the arXiv
            self.logger.info(
                "Searching for papers. Estimated time: {:.0f} seconds".format(est_time)
            )
            for ii in range(start_num, api.total_papers, arxiv_const.search_blocksize):

                # Compute the progress of the loop
                if ii + arxiv_const.search_blocksize > api.total_papers:
                    remaining_steps = 1
                    search_interval = api.total_papers - ii
                    search_endnum = api.total_papers
                else:
                    remaining_steps = -(
                        (api.total_papers - ii) // -arxiv_const.search_blocksize
                    )
                    search_interval = arxiv_const.search_blocksize
                    search_endnum = ii + arxiv_const.search_blocksize

                # Print the progress bar
                progress_bar(
                    ii,
                    num_steps,
                    remaining_steps * (arxiv_const.sleep_search + fudge_timer),
                )

                # Debug messages
                self.logger.debug("Remaining steps: {:}".format(remaining_steps))
                self.logger.debug("Starting number: {:}".format(ii))
                self.logger.debug("Ending number:   {:}".format(search_endnum))

                # Sleep before the query so that there is no dead time on the last query. Also need to sleep here as we do not wait after the initial API call
                # Add jitter to the sleep timer
                current_sleep_time = arxiv_const.sleep_search
                progress_bar(ii, num_steps, remaining_steps * current_sleep_time)
                pretty_sleep(self.logger, current_sleep_time)

                # Query the API
                parsed_xml, api.ssl_dict = arxiv_query(
                    self.logger, api.ssl_dict, api.url, ii, search_interval
                )

                # Write the xml to a file
                # logger, filename, xml_data, ns, overwrite=False
                write_xml(self.logger, xml_path, parsed_xml, arxiv_const.ns)

                # Extract the paper from the xml
                self.extract_papers(arxiv_const.ns, parsed_xml)

            # Close the progress bar
            progress_bar(api.total_papers, api.total_papers)

            self.logger.info(
                "All paper information successfully downloaded from the arXiv servers!"
            )

        # Double check that we found the correct number of papers
        self.get_corpus_length()
        n_papers = self.length
        if n_papers != api.total_papers:

            self.logger.error(
                "Found {:} papers (expected {:}).".format(n_papers, api.total_papers)
            )

        else:

            self.logger.debug(
                "Found the expected number of papers ({:}).".format(api.total_papers)
            )

        # Remove revised papers
        self.drop_revisions()

    # # Obtain the number of papers in the Corpus
    def get_corpus_length(self) -> None:
        """Compute the length of the Corpus, i.e. how many papers are contained within."""

        self.length = len(self.corpus)

    # # Drop revised papers from the Corpus
    def drop_revisions(self) -> None:
        """Drop revised papers from the Corpus."""

        self.logger.debug("Removing revised papers.")

        # Obtain the number of papers before dropping revisions
        N = self.length

        # Initialise a temporary dictionary that will hold all papers that are not revisions
        temp_dict: dict[str, Paper] = {}

        # Loop over the Corpus
        for key, paper in self.corpus.items():

            # If the current Paper is not a revision:
            if not paper.paperInfo.revised:

                # Add it to the temp dictionary
                # Use the arXiv ID number without a version number for the new key
                temp_dict[paper.paperInfo.id_num] = paper

        # Replace the Corpus with the temp dictionary
        self.corpus = temp_dict

        # Update the number of papers
        self.get_corpus_length()

        # Compute the number of papers that were dropped
        num_dropped = N - self.length

        self.logger.debug("Dropped {:} revised entries.".format(num_dropped))

    # # Find matches
    def find_matches(self, search_terms: dict[str, list[str]]) -> None:
        """Find search_term matches within each Paper in the Corpus.

        inputs
        ------
        search_terms : All search terms to find matches with.
        """
        # Can process ~2,000 papers per second on a macbook

        self.logger.info("Finding keyword matches")

        # Loop over all papers in the Corpus
        count = 0
        for arxiv_ID, paper in self.corpus.items():

            progress_bar(
                count, self.length
            )  # No time estimate as it should always be fast.

            self.logger.debug("Seaching for matches in arXiv:{:}.".format(arxiv_ID))

            # Seach for Authors
            paper.match_authors(search_terms["Authors"])

            # # Search for included words
            paper.match_words(search_terms, "Included Words")

            # # Search for excluded words
            paper.match_words(search_terms, "Excluded Words")

            count += 1

        progress_bar(self.length, self.length)

    # # Score the papers by author/word matches
    def score_papers_matches(self) -> None:
        """Scores all Papers in the Corpus based on the number of matches found.
        NOTE: This function also counts the number of matches.
        """

        # Can process ~7,000 papers per second on a macbook

        self.logger.info("Scoring papers based on matches")

        # Loop over all Papers
        count = 0
        for arxiv_ID, paper in self.corpus.items():

            progress_bar(count, self.length)

            self.logger.debug("Computing a score for arXiv:{:}.".format(arxiv_ID))

            # Score the authors
            paper.score_authors()

            # Score for included words
            paper.score_words("Included Words")

            # Score for excluded words
            paper.score_words("Excluded Words")

            # Finalise the score
            paper.final_word_score()

            count += 1

        progress_bar(self.length, self.length)

    # # Score the papers via a ML algorithm
    def score_papers_ML(self) -> None:
        """Scores the papers based on a machine-learning algorithm.
        NOTE: This method is not implemented. Current plan is to create a model that can be traied by the user on a directory containing many .pdf files. This function would then use said model to score each paper in the arXiv search.
        """

        self.logger.error(
            "Attempting to use ML model to score papers. This has not been implemented yet. Returning no results.\n"
        )
        raise

    # # Filter the Corpus based on the author/word matches
    def filter_papers_matches(self) -> None:
        """Filter the Corpus such that only Papers with matches to the search terms are kept."""

        self.logger.info("Filtering corpus based on word matching.")

        # Loop over all papers
        self.papers_of_note: list[str] = []
        for key, paper in self.corpus.items():

            # If an Author was found, append it to the entries of note
            if paper.paperScores.n_author_matches >= 1:

                self.logger.debug("Adding paper: {:} (found author)".format(key))

                # self.papers_of_note.append(key)
                self.papers_of_note.append(key)

            # If there were included word matches and *no* excluded word matches, append
            elif (paper.paperScores.matches["Included Words"]["Total"] >= 1) and (
                paper.paperScores.matches["Excluded Words"]["Total"] == 0
            ):

                self.logger.debug("Adding paper: {:} (found word)".format(key))

                # self.papers_of_note.append(key)
                self.papers_of_note.append(key)

    # # Filter the Corpus based on the score
    def filter_papers_score(self) -> None:
        """Filter the Corpus such that only Papers with a score above some threshold are kept."""

        # Can process ~1e6 papers per second on a macbook

        self.logger.info("Filtering corpus based on scores.")

        # Define the thresholds
        # Words
        # 0.50 => a bit too generous with what papers are considered interesting
        # 0.65 => feels like a good limit to ensure the papers are interesting
        # 0.85 => can potentially miss something
        # 1.00 => too strict, especially if there are many 'excluded words'
        author_threshold = 0.95  # At least one author in every 25
        word_threshold = 0.65

        # Loop over all papers
        self.papers_of_note_unsorted: list[str] = []
        self.scores_unsorted: list[float] = []
        for key, paper in self.corpus.items():

            # If the author score is above the threshold, append the paper to the papers of note
            if paper.author_score >= author_threshold:

                self.logger.debug(
                    "Adding paper: {:} (Author score = {:})".format(
                        key, paper.author_score
                    )
                )

                self.papers_of_note_unsorted.append(paper.paperInfo.id_num)
                self.scores_unsorted.append(paper.author_score)

            # Otherwise, if the score is above the threshold, append it to the papers of note
            elif paper.final_score >= word_threshold:

                self.logger.debug(
                    "Adding paper: {:} (Word score = {:})".format(
                        key, paper.final_score
                    )
                )

                self.papers_of_note_unsorted.append(paper.paperInfo.id_num)
                self.scores_unsorted.append(paper.final_score)

        # Sort the papers of note by their score
        self.logger.info("Sorting papers based on score (descending).")
        pairs = sorted(
            zip(self.scores_unsorted, self.papers_of_note_unsorted), reverse=True
        )
        self.papers_of_note = [paper for _, paper in pairs]
        self.scores = [score for score, _ in pairs]

        self.logger.debug("Final Paper scores:")
        for ii in range(0, len(self.papers_of_note)):
            self.logger.debug(
                "arXiv:{:} = {:.2f}".format(self.papers_of_note[ii], self.scores[ii])
            )

    # # Summarise the results
    def summary(self) -> None:
        """Summarise the results."""

        # Compute the number of digits in the number of papers found
        max_digits = len(str(self.length))

        # Print a summary
        print("")
        self.logger.info(
            "There was a total of {: >{fill}} papers submitted to the categories of interest within the search window.".format(
                self.length, fill=max_digits
            )
        )
        self.logger.info(
            "           of these, {: >{fill}} papers were opened/linked.".format(
                len(self.papers_of_note), fill=max_digits
            )
        )
        print("")
