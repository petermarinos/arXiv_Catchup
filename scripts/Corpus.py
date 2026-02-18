# Import classes
from .Paper import Paper

# Import libraries
import xml.etree.ElementTree as ET
import numpy                 as np
import logging

class Corpus:

    # # Initialise the class
    def __init__(self) -> None:

        self.corpus:dict[str, Paper] = {}

    # # Add a Paper object to the Corpus
    def addPaperToCorpus(self, logger: logging.Logger, ns: dict[str, str], entry: ET.Element) -> None:

        # Extract the paper from the xml entry
        paper = Paper(logger, ns, entry)

        # Add the paper to the corpus dictionary
        key = paper.ID + "v{:d}".format(paper.version) # include version to ensure each key is unique. We will drop revisions later
        value = paper
        self.corpus[key] = value

    # # Clear the Corpus
    def clearCorpus(self,  logger: logging.Logger) -> None:

        logger.debug("Replacing corpus with an empty dictionary.")

        # Replace the corpus with an empty dictionary
        self.corpus:dict[str, Paper] = {}

    # # Obtain the number of papers in the Corpus
    def getCorpusLength(self) -> None:

        self.length = len(self.corpus.keys())

    # # Drop revised papers from the Corpus
    def dropRevisions(self, logger: logging.Logger) -> None:

        logger.debug("Removing revised papers.")

        # Obtain the number of papers before dropping
        N = self.length

        temp_dict:dict[str, Paper] = {}

        for key, value in self.corpus.items():
            if not value.revised:
                temp_dict[key] = value

        self.corpus = temp_dict

        # Update the number of papers
        self.getCorpusLength()
        num_dropped = N - self.length
        logger.debug("Dropped {:} revised entries.".format(num_dropped))

    # # Filter the Corpus based on the author/word matches
    def filterCorpusMatches(self, logger: logging.Logger) -> None:

        logger.info("Filtering corpus based on word matching.")

        # Loop over all entries
        self.papers_of_note = np.array([])
        for key, val in self.corpus.items():

            # If an Author was found, append it to the entries of note
            if val.n_author_matches >= 1:

                logger.debug("Adding paper: {:} (found author)".format(key))

                # self.papers_of_note.append(key)
                np.append(self.papers_of_note, key)

            # If there were included word matches and *no* excluded word matches, append
            elif ( val.words["Included Words"]["Total Matches"] >= 1 ) and ( val.words["Excluded Words"]["Total Matches"] == 0 ):

                logger.debug("Adding paper: {:} (found word)".format(key))

                # self.papers_of_note.append(key)
                np.append(self.papers_of_note, key)

    # # Filter the Corpus based on the score
    def filterCorpusScore(self, logger: logging.Logger) -> None:

        logger.info("Filtering corpus based on scores.")

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

                logger.debug("Adding paper: {:} (Author score = {:})".format(key, val.author_score))

                self.papers_of_note_unsorted.append(key)
                self.scores.append(val.author_score)

            # Otherwise, if the score is above the threshold, append it to the papers of note
            elif val.final_score >= word_threshold:

                logger.debug("Adding paper: {:} (Word score = {:})".format(key, val.final_score))

                self.papers_of_note_unsorted.append(key)
                self.scores.append(val.final_score)

        # Sort the papers of note by their score
        logger.info("Sorting papers based on score (descending).")
        self.papers_of_note = np.array(self.papers_of_note_unsorted)[np.array(self.scores).argsort()[::-1]]
