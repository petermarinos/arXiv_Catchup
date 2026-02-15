# Import functions
from scripts.utils import progress_bar

# Import libraries
import numpy as np
import re

def author_search(logger, df_papers, entry_count, authors):
    """Searches a paper for the authors of interest.

    inputs
    ------
    logger      : RootLogger
        The logger object.
    df_papers   : pandas.DataFrame
        Contains all papers.
    entry_count : int
        Index of the paper in the DataFrame.
    authors     : list
        All authors of interest that are being searched for.

    outputs
    -------
    author_str : str
        Contains information on which authors were found
    """

    author_str = ""
        
    # If there is at least one author of interest
    if authors is not None:

        logger.debug("Searching for Authors")

        author_match_str = ""

        # Define a value used to print a string that shows if any authors of interest are found
        if authors is not None:

            # Length of the longest name, plus eight characters for ', et al.' incase there are multiple matches
            author_strfill = len(max(authors, key=len)) + 8

        # Loop over the authors in the search terms
        for author in authors:

            # Search the author field in the entry
            author_match = re.search(r"\b"+author+r"\b", df_papers.loc[entry_count, "Authors"])

            # If an author is found:
            if author_match:

                logger.debug("Found author: {:}".format(author))
                    
                # If the paper has an author match, add it to a string
                # If no match has been found yet:
                if not df_papers.loc[entry_count, "Authors Match"]:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author, fill=author_strfill, url=df_papers.loc[entry_count, "url"])
                # If the paper has already had a match, add et at.
                else:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author+", et al.", fill=author_strfill, url=df_papers.loc[entry_count, "url"])
                
                # Set the entry in the dataframe for the author match key to True
                # Used for the binary search
                df_papers.loc[entry_count, "Authors Match"] = True

                # Set the score tp 10 points if a match is found
                # Used for the score search
                df_papers.loc[entry_count, "Authors Score"] = 1

        author_str += author_match_str

    return author_str

def word_search(logger, df_papers, entry_count, search_terms, key):
    """Searches a paper for keyword matches.

    inputs
    ------
    logger      : RootLogger
        The logger object.
    df_papers   : pandas.DataFrame
        Contains all papers.
    entry_count : int
        Index of the paper in the DataFrame.
    search_terms : dict
        Contains all of the search terms.
    key         : str
        The search_terms dictionary key for which types of words should be searched for.
    """

    logger.debug("Searching for {:}".format(key))

    # # Compute the number of words we are searching for. Used to normalise the score?
    # num_words = len(search_terms[key])

    # Initialise the number of matches found
    num_title_matches    = 0
    num_abstract_matches = 0

    # Search all titles and abstracts for words in the supplied key
    for word in search_terms[key]:

        # Compute the number of words in the title and user to compute a penalty
        # Titles are boosted/penalised for being below/above a word count of 18
        title_length  = len( re.findall(r'\w+', df_papers.loc[entry_count, "Title"]) )
        title_penalty = 18 / title_length

        # Search the author field in the entry
        title_match = re.search(r"\b"+word+r"\b", df_papers.loc[entry_count, "Title"], re.IGNORECASE)

        # If a match is found in the title:
        if title_match:

            # Count the number of matches
            current_num_title_matches = len( re.findall(r"\b"+word+r"\b", df_papers.loc[entry_count, "Title"], re.IGNORECASE) )

            logger.debug("Found {:} {:} time(s) in the title.".format(word, current_num_title_matches))

            # Add to score
            num_title_matches += current_num_title_matches

        # If something exists in the abstract field, search it for matches
        if df_papers.loc[entry_count, "Abstract"] is not None:
            
            abstract_match = re.search(r"\b"+word+r"\b", df_papers.loc[entry_count, "Abstract"], re.IGNORECASE)

            # Compute the number of words in the abstract user to compute a the penalty
            # Abstracts are boosted/penalised for being below/above a word count of 250
            abstract_length  = len( re.findall(r'\w+', df_papers.loc[entry_count, "Abstract"]) )
            abstract_penalty = 250 / abstract_length

            # If a match is found in the abstract:
            if abstract_match:

                # Count the number of matches
                current_num_abstract_matches = len( re.findall(r"\b"+word+r"\b", df_papers.loc[entry_count, "Abstract"], re.IGNORECASE) )

                logger.debug("Found {:} {:} time(s) in the abstract.".format(word, current_num_abstract_matches))

                num_abstract_matches += current_num_abstract_matches
            
        # If a match is found anywhere, set the _ Word Match flag to True
        if title_match or abstract_match:
            
            # logger.debug(key+" Match")
            df_papers.loc[entry_count, key+" Match"] = True

    # Set scores, bound to 0->1.
    # logger.debug("Title penalty: {:} | Title matches: {:}".format(title_penalty, num_title_matches))
    # logger.debug("Abstract penalty: {:} | Abstract matches: {:}".format(abstract_penalty, num_abstract_matches))
    title_score    = min( title_penalty * num_title_matches / 1.0, 1.0 ) # An interesting title has one or two matches
    abstract_score = min( abstract_penalty * num_abstract_matches / 5.0, 1.0 ) # An interesting abstract has ~5 matches
    df_papers.loc[entry_count, key+" Score"] = ( title_score + abstract_score ) / 2.0
    logger.debug("arXiv:{:} - {:} | title {:} | abstract {:} | total {:} |".format(df_papers.loc[entry_count, "arXiv Number"], key, title_score, abstract_score, df_papers.loc[entry_count, key+" Score"]))

    return

def score_papers_matches(self):
    """Scores the papers based on the number of matches found.
    NOTE: This function also applies a simple binary True/False if matches are found.

    inputs
    ------
    self : Papers object

    outputs
    -------
    author_str : str
        Information on all authors that were found, which will be printed later.
    """

    self.logger.info("Finding keyword matches")

    # Loop over all entries
    author_str = "    Found Author(s)"
    for entry_count in range(0, len(self.df_papers)):

        progress_bar(entry_count, len(self.df_papers)) # No time estimate as it should always be fast. ~1200 papers take less than a second on a 2023 macbook

        self.logger.debug("Seaching for matches in arXiv:{:}.".format(self.df_papers.loc[entry_count, "arXiv Number"]))
        
        # Seach for Authors
        author_matches_str = author_search(self.logger,
                                           self.df_papers,
                                           entry_count,
                                           self.search_terms["Authors"])
        author_str        += author_matches_str

        # Search for included words
        word_search(self.logger,
                    self.df_papers,
                    entry_count,
                    self.search_terms,
                    "Included Words")

        # Search for excluded words
        word_search(self.logger,
                    self.df_papers,
                    entry_count,
                    self.search_terms,
                    "Excluded Words")

        self.logger.debug("Computing a score for arXiv:{:}.".format(self.df_papers.loc[entry_count, "arXiv Number"]))
        # Compute a score. If the score is negative, set it to zero
        # Currently the included/excluded words are being weighted as equal. It may be good to cap the excluded word score?
        self.df_papers.loc[entry_count, "Score"] = max(self.df_papers.loc[entry_count, "Included Words Score"] -
                                           self.df_papers.loc[entry_count, "Excluded Words Score"],
                                           0)

        self.logger.debug("arXiv:{:} final score: {:}".format(self.df_papers.loc[entry_count, "arXiv Number"], self.df_papers.loc[entry_count, "Score"]))

    progress_bar(len(self.df_papers), len(self.df_papers))

    return author_str

def score_papers_ML(self):
    """Scores the papers based on a machine-learning algorithm.
    NOTE: This method is not implemented. Current plan is to create a model that can be traied by the user on a directory containing many .pdf files. This function would then use said model to score each paper in the arXiv search.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    self.logger.error("Attempting to use ML model to filter papers. This has not been implemented yet. Returning no results.\n")
    raise

def filter_papers_score(self):
    """Filters the papers based on the number and type of matches with the search terms.
    If a paper is scored above some threshold, it is shown.
    NOTE: May need some more optimisation.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_sorted : list
        Contains the indices of all papers that pass the filter, in order of their score.
    """

    # Define the threshold
    # 0.50 => quite generous with what papers are opened. 
    # 0.65 => feels like a good limit to ensure the papers are interesting
    # 0.85 => can potentially miss something
    # 1.00 => too strict if there are any 'excluded words'
    threshold = 0.65

    self.logger.info("Filtering papers based on scores")

    # Loop over all entries
    entries_of_note = []
    scores          = []
    for entry_count in range(0, len(self.df_papers)):

        # If an Author was found, append it to the entries of note
        # Note that the author score is not actually being utilised in the computation of the papers score. If one author was found, the paper is considered interesting.
        if self.df_papers.loc[entry_count, "Authors Score"] == 1:

            entries_of_note.append(entry_count)
            scores.append(1.0)

        # If the score is above the threshold, append it to the entries of note
        if self.df_papers.loc[entry_count, "Score"] >= threshold:

            entries_of_note.append(entry_count)
            scores.append(self.df_papers.loc[entry_count, "Score"])

    # Sort the entries of note by their score
    self.logger.info("Sorting papers based on score (descending).")
    entries_of_note_sorted = np.array(entries_of_note)[np.array(scores).argsort()[::-1]]

    return entries_of_note_sorted

def filter_papers_matches(self):
    """Filters the papers based on matches with the search terms.
    NOTE: This method is not favoured. Papers that are not interesting to the user can be shown based on the inclusion of certain key words, leading to a large list that needs to be manually checked. Meanwhile, papers that would be considered interesting can be excluded based on other key words, leading to interesting papers not being shown at all.

    inputs
    ------
    self : Papers object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    self.logger.info("Filtering papers based on word matching")

    # Loop over all entries
    entries_of_note = []
    for entry_count in range(0, len(self.df_papers)):

        # If an Author was found, append it to the entries of note
        if self.df_papers.loc[entry_count, "Authors Match"] == True:

            self.logger.debug("Adding paper: {:}".format(self.df_papers.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

        # If there were included word matches and *no* excluded word matches, append
        elif ( self.df_papers.loc[entry_count, "Included Words Match"] == True ) and ( self.df_papers.loc[entry_count, "Excluded Words Match"] == False ):

            self.logger.debug("Adding paper: {:}".format(self.df_papers.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(self.df_papers["Authors Match"]):
        print(self.author_str)

    return entries_of_note