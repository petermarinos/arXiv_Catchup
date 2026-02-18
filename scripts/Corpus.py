# Import classes
from .Paper import Paper

# Import function
from .utils import progress_bar

# Import libraries
import xml.etree.ElementTree as ET
import numpy                 as np
import logging

class Corpus:

    # # Initialise the class
    def __init__(self, logger: logging.Logger) -> None:

        self.logger = logger

        self.corpus:dict[str, Paper] = {}

        self.length = 0

    # # Clear the Corpus
    def clear_corpus(self) -> None:

        self.logger.debug("Replacing corpus with an empty dictionary.")

        # Replace the corpus with an empty dictionary
        self.corpus:dict[str, Paper] = {}

        self.length = 0

    # # Add a Paper object to the Corpus
    def add_paper_to_corpus(self, ns: dict[str, str], entry: ET.Element) -> None:

        # Extract the paper from the xml entry
        paper = Paper(self.logger, ns, entry)

        # Add the paper to the corpus dictionary
        key = paper.ID + "v{:d}".format(paper.version) # include version to ensure each key is unique. We will drop revisions later
        value = paper
        self.corpus[key] = value

        # Add one to the length
        self.length += 1

    # # Obtain the number of papers in the Corpus
    def get_corpus_length(self) -> None:

        if len(self.corpus.keys()) is None:
            self.length = 0
        else:
            self.length = len(self.corpus.keys())

    # # Drop revised papers from the Corpus
    def drop_revisions(self) -> None:

        self.logger.debug("Removing revised papers.")

        # Obtain the number of papers before dropping
        N = self.length

        temp_dict:dict[str, Paper] = {}

        for key, value in self.corpus.items():
            if not value.revised:
                temp_dict[key] = value

        self.corpus = temp_dict

        # Update the number of papers
        self.get_corpus_length()
        num_dropped = N - self.length
        self.logger.debug("Dropped {:} revised entries.".format(num_dropped))

    # # Find matches
    def find_matches_corpus(self, search_terms) -> None:

        # Can process ~2,000 papers per second on a macbook

        self.logger.info("Finding keyword matches")

        # Loop over all entries
        count = 0
        for arxiv_ID, paper in self.corpus.items():

            progress_bar(count, self.length) # No time estimate as it should always be fast.

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
    def score_corpus_matches(self) -> None:
        """Scores the papers based on the number of matches found.
        NOTE: This function also counts the number of matches.
        """

        # Can process ~7,000 papers per second on a macbook

        self.logger.info("Scoring papers based on matches")

        # Loop over all entries
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

    # # Filter the Corpus based on the author/word matches
    def filter_corpus_matches(self) -> None:

        self.logger.info("Filtering corpus based on word matching.")

        # Loop over all entries
        self.papers_of_note = np.array([])
        for key, val in self.corpus.items():

            # If an Author was found, append it to the entries of note
            if val.n_author_matches >= 1:

                self.logger.debug("Adding paper: {:} (found author)".format(key))

                # self.papers_of_note.append(key)
                np.append(self.papers_of_note, key)

            # If there were included word matches and *no* excluded word matches, append
            elif ( val.words["Included Words"]["Total Matches"] >= 1 ) and ( val.words["Excluded Words"]["Total Matches"] == 0 ):

                self.logger.debug("Adding paper: {:} (found word)".format(key))

                # self.papers_of_note.append(key)
                np.append(self.papers_of_note, key)

    # # Filter the Corpus based on the score
    def filter_corpus_score(self) -> None:

        # Can process ~1e6 papers per second on a macbook

        self.logger.info("Filtering corpus based on scores.")

        # Define the thresholds
        # Words
        # 0.50 => a bit too generous with what papers are considered interesting
        # 0.65 => feels like a good limit to ensure the papers are interesting
        # 0.85 => can potentially miss something
        # 1.00 => too strict if there are many 'excluded words'
        author_threshold = 0.95 # At least one author in every 25
        word_threshold   = 0.65

        # Loop over all papers
        self.papers_of_note_unsorted: list[str] = []
        self.scores: list[float]                = []
        for key, val in self.corpus.items():

            # If the author score is above the threshold, append the paper to the papers of note
            if val.author_score >= author_threshold:

                self.logger.debug("Adding paper: {:} (Author score = {:})".format(key, val.author_score))

                self.papers_of_note_unsorted.append(key)
                self.scores.append(val.author_score)

            # Otherwise, if the score is above the threshold, append it to the papers of note
            elif val.final_score >= word_threshold:

                self.logger.debug("Adding paper: {:} (Word score = {:})".format(key, val.final_score))

                self.papers_of_note_unsorted.append(key)
                self.scores.append(val.final_score)

        # Sort the papers of note by their score
        self.logger.info("Sorting papers based on score (descending).")
        self.papers_of_note = np.array(self.papers_of_note_unsorted)[np.array(self.scores).argsort()[::-1]]
