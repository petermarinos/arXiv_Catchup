"""Corpus class."""

# Import standard libraries
import xml.etree.ElementTree as ET
import logging

# Import function
from .ui import progress_bar

# Import classes
from .paper import Paper


class Corpus:
    """Contains the entire corpus downloaded from the arXiv servers."""

    # Define the thresholds
    # Authors
    AUTHOR_THRESHOLD = 0.95  # At least one author in every 25
    # Words
    # 0.50 => a bit too generous with what papers are considered interesting
    # 0.65 => feels like a good limit to ensure the papers are interesting
    # 0.85 => can potentially miss something
    # 1.00 => too strict, especially if there are many 'excluded words'
    WORD_THRESHOLD = 0.65

    def __init__(self, logger: logging.Logger) -> None:
        """Create the Corpus object.

        inputs
        ------
        logger : The logger object
        """

        self.logger = logger

        self.corpus: dict[str, Paper] = {}

        self.length = 0

        self.papers_of_note: list[str] = []
        self.scores: list[float] = []

        self.author_summary = "Found Author(s):\n"

    def clear_corpus(self) -> None:
        """Delete all entries in the Corpus"""

        self.logger.debug("Deleting all entries in the corpus.")

        # Clear all entries from the Corpus dictionary
        self.corpus.clear()

        # Set the length back to zero
        self.length = 0

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
        # Include the version number to ensure each key is unique. We will drop revisions later
        key = f"{paper.paper_info.id_num}v{paper.paper_info.version:d}"
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
        ns       : XML namespaces that arXiv uses.
        xml_data : XML data from the arXiv query. Can be a ET tree or root.
        """

        # Loop over the entries (papers) within the current search
        count = 0
        for entry in xml_data.findall("atom:entry", ns):

            self.add_paper_to_corpus(ns, entry)

            count += 1

        self.logger.debug(f"Found {count:d} papers in this search block.")

    def drop_revisions(self) -> None:
        """Drop revised papers from the Corpus."""

        self.logger.debug("Removing revised papers.")

        # Obtain the number of papers before dropping revisions
        n = self.length

        # Initialise a temporary dictionary that will hold all papers that are not revisions
        temp_dict: dict[str, Paper] = {}

        # Loop over the Corpus
        for _, paper in self.corpus.items():

            # If the current Paper is not a revision:
            if not paper.paper_info.revised:

                # Add it to the temp dictionary
                # Use the arXiv ID number without a version number for the new key
                temp_dict[paper.paper_info.id_num] = paper

        # Replace the Corpus with the temp dictionary
        self.corpus = temp_dict

        # Recompute the length
        self.length = len(self.corpus)

        # Compute the number of papers that were dropped
        num_dropped = n - self.length

        self.logger.debug(f"Dropped {num_dropped} revised entries.")

    def find_matches(self, search_terms: dict[str, list[str] | None]) -> None:
        """Find search_term matches within each Paper in the Corpus.

        inputs
        ------
        search_terms : All search terms to find matches with.
        """
        # Can process ~2,000 papers per second on a macbook

        self.logger.info("Finding keyword matches")

        # Loop over all papers in the Corpus
        count = 0
        for arxiv_id, paper in self.corpus.items():

            progress_bar(
                count, self.length
            )  # No time estimate as it should always be fast.

            self.logger.debug(f"Seaching for matches in arXiv:{arxiv_id}.")

            # Seach for Authors
            paper.match_authors(search_terms["Authors"])

            # # Search for included words
            paper.match_words(search_terms, "Included Words")

            # # Search for excluded words
            paper.match_words(search_terms, "Excluded Words")

            count += 1

        progress_bar(self.length, self.length)

    def score_papers_matches(self) -> None:
        """Scores all Papers in the Corpus based on the number of matches found.
        NOTE: This function also counts the number of matches.
        """

        # Can process ~7,000 papers per second on a macbook

        self.logger.info("Scoring papers based on matches")

        # Loop over all Papers
        count = 0
        for arxiv_id, paper in self.corpus.items():

            progress_bar(count, self.length)

            self.logger.debug(f"Computing a score for arXiv:{arxiv_id}.")

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

    def score_papers_ml(self) -> None:
        """Scores the papers based on a machine-learning algorithm.
        NOTE: This method is not implemented.
              Current plan is to create a model that can be traied by the user on a directory
              containing many .pdf files. This function would then use said model to score each
              paper in the arXiv search.
        """

        self.logger.error(
            "Attempting to use ML model to score papers. This has not been implemented yet. "
            "Returning no results.\n"
        )
        raise NotImplementedError("Machine-learning algorithm not yet implemented.")

    def filter_papers_matches(self) -> None:
        """Filter the Corpus such that only Papers with matches to the search terms are kept."""

        self.logger.info("Filtering corpus based on word matching.")

        # Loop over all papers
        for key, paper in self.corpus.items():

            # If an Author was found, append it to the entries of note
            if paper.paper_scores.n_author_matches >= 1:

                self.logger.debug("Adding paper: {key} (found author)")

                self.papers_of_note.append(key)

            # If there were included word matches and *no* excluded word matches, append
            elif (paper.paper_scores.matches["Included Words"]["Total"] >= 1) and (
                paper.paper_scores.matches["Excluded Words"]["Total"] == 0
            ):

                self.logger.debug(f"Adding paper: {key} (found word)")

                self.papers_of_note.append(key)

    def filter_papers_score(self) -> None:
        """Filter the Corpus such that only Papers with a score above some threshold are kept."""

        # Can process ~1e6 papers per second on a macbook

        self.logger.info("Filtering corpus based on scores.")

        # Loop over all papers
        papers_of_note_unsorted: list[str] = []
        scores_unsorted: list[float] = []
        for key, paper in self.corpus.items():

            # If the author score is above the threshold, append the paper to the papers of note
            if paper.paper_scores.author_score >= self.AUTHOR_THRESHOLD:

                self.logger.debug(
                    f"Adding paper: {key} (Author score = {paper.paper_scores.author_score})"
                )

                papers_of_note_unsorted.append(paper.paper_info.id_num)
                scores_unsorted.append(paper.paper_scores.author_score)

            # Otherwise, if the score is above the threshold, append it to the papers of note
            elif paper.paper_scores.final_score >= self.WORD_THRESHOLD:

                self.logger.debug(
                    f"Adding paper: {key} (Word score = {paper.paper_scores.final_score})"
                )

                papers_of_note_unsorted.append(paper.paper_info.id_num)
                scores_unsorted.append(paper.paper_scores.final_score)

        # Sort the papers of note by their score
        self.logger.info("Sorting papers based on score (descending).")
        pairs = sorted(zip(scores_unsorted, papers_of_note_unsorted), reverse=True)
        self.papers_of_note = [paper for _, paper in pairs]
        self.scores = [score for score, _ in pairs]

        self.logger.debug("Final Paper scores:")
        for ii, paper_of_note in enumerate(self.papers_of_note):
            self.logger.debug(f"arXiv:{paper_of_note} = {self.scores[ii]:.2f}")

    def calc_author_summary(self) -> None:
        """Compute a summary string for the found authors.
        NOTE: Currently does not consider the penalties for collaboration papers! Add CLI args as
              an input and only add if the score is above the threshold? Would also require the
              algorithm (matching versus scoring) to be a CLI argument first.
        NOTE: We construct the link with the arXiv ID number instead of taking the abs links. This
              is done because the revision number is never important and it slightly reduces visual
              clutter in the output.
        """

        # Loop through all the papers.
        # Find the longest name in the first position
        found_authors: list[str] = []
        for _, paper in self.corpus.items():

            # If the paper had one match:
            if paper.paper_scores.n_author_matches == 1:

                # Take the name of the author ealiest in the author list
                found_authors.append(paper.paper_scores.found_authors[0])

            # If the paper had more than one match:
            elif paper.paper_scores.n_author_matches > 1:

                # Take the name of the author ealiest in the author list
                found_authors.append(paper.paper_scores.found_authors[0] + ", et al.")

        if len(found_authors) > 0:

            fill = len(max(found_authors, key=len))

            # Loop through the papers again to create the summary text
            for _, paper in self.corpus.items():

                if paper.paper_scores.n_author_matches == 1:
                    self.author_summary += (
                        f"    {paper.paper_scores.found_authors[0]: >{fill}}: "
                        f"https://arxiv.org/abs/{paper.paper_info.id_num}\n"
                        # f"{paper.paper_info.link_abs}\n"
                    )
                # If more than one author, fill with +8 to account for ', et al.'
                elif paper.paper_scores.n_author_matches > 1:
                    self.author_summary += (
                        f"    {paper.paper_scores.found_authors[0]: >{fill-8}}, et al.: "
                        f"https://arxiv.org/abs/{paper.paper_info.id_num}\n"
                        # f"{paper.paper_info.link_abs}\n"
                    )

    def summary(self) -> None:
        """Summarise the results."""

        # Compute the author summary
        self.calc_author_summary()

        # If *any* text has been added to the summary string
        if len(self.author_summary) > len("Found Author(s):\n"):

            # Print the summary. This is integral output, keep out of the logger.
            print(f"\n{self.author_summary}")

        else:

            # Print a blank space to make the output prettier
            print("")

        # Compute the number of digits in the number of papers found
        max_digits = len(str(self.length))

        # Print a summary
        self.logger.info(
            f"There were {self.length:>{max_digits}} papers submitted to the categories of "
            "interest within the search window."
        )
        self.logger.info(
            f" of these, {len(self.papers_of_note):>{max_digits}} papers were interesting.\n"
        )
