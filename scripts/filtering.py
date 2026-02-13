# Import libraries
from scripts.utils import progress_bar, clear_progress_bar

import numpy as np

import re

def author_search(df, entry_count, search_terms, logger):
    """
    All search terms are surrounded by break identifiers (\b).
    """

    author_str = ""
        
    # If there is at least one author of interest
    if search_terms["Authors"] is not None:

        logger.debug("Searching for Authors")

        author_match_str = ""

        # Define a value used to print a string that shows if any authors of interest are found
        if search_terms["Authors"] is not None:

            # Length of the longest name, plus eight characters for ', et al.' incase there are multiple matches
            author_strfill = len(max(search_terms["Authors"], key=len)) + 8

        # Loop over the authors in the search terms
        for author in search_terms["Authors"]:

            # Search the author field in the entry
            author_match = re.search(r"\b"+author+r"\b", df.loc[entry_count, "Authors"])

            # If an author is found:
            if author_match:

                clear_progress_bar(logger, 10)
                logger.debug("Found {:}".format(author))
                    
                # If the paper has an author match, add it to a string
                # If no match has been found yet:
                if not df.loc[entry_count, "Authors Match"]:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author, fill=author_strfill, url=df.loc[entry_count, "url"])
                # If the paper has already had a match, add et at.
                else:
                    author_match_str = "\n    {: >{fill}}:  {url:}".format(author+", et al.", fill=author_strfill, url=df.loc[entry_count, "url"])
                
                # Set the entry in the dataframe for the author match key to True
                # Used for the binary search
                df.loc[entry_count, "Authors Match"] = True

                # Set the score tp 10 points if a match is found
                # Used for the score search
                df.loc[entry_count, "Authors Score"] = 1

        author_str = author_match_str

    return df, author_str

def word_search(df, entry_count, search_terms, key, logger):
    """
    All search terms are surrounded by break identifiers (\b).

    inputs
    ------
    multiplier : float
        Multiplies the score
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
        title_length  = len( re.findall(r'\w+', df.loc[entry_count, "Title"]) )
        title_penalty = 18 / title_length

        # Search the author field in the entry
        title_match = re.search(r"\b"+word+r"\b", df.loc[entry_count, "Title"], re.IGNORECASE)

        # If a match is found in the title:
        if title_match:

            # Count the number of matches
            current_num_title_matches = len( re.findall(r"\b"+word+r"\b", df.loc[entry_count, "Title"], re.IGNORECASE) )

            clear_progress_bar(logger, 10)
            logger.debug("Found {:} {:} time(s) in the title.".format(word, current_num_title_matches))

            # Add to score
            num_title_matches += current_num_title_matches

        # If something exists in the abstract field, search it for matches
        if df.loc[entry_count, "Abstract"] is not None:
            
            abstract_match = re.search(r"\b"+word+r"\b", df.loc[entry_count, "Abstract"], re.IGNORECASE)

            # Compute the number of words in the abstract user to compute a the penalty
            # Abstracts are boosted/penalised for being below/above a word count of 250
            abstract_length  = len( re.findall(r'\w+', df.loc[entry_count, "Abstract"]) )
            abstract_penalty = 250 / abstract_length

            # If a match is found in the abstract:
            if abstract_match:

                # Count the number of matches
                current_num_abstract_matches = len( re.findall(r"\b"+word+r"\b", df.loc[entry_count, "Abstract"], re.IGNORECASE) )

                logger.debug("Found {:} {:} time(s) in the abstract.".format(word, current_num_abstract_matches))

                num_abstract_matches += current_num_abstract_matches
            
        # If a match is found anywhere, set the _ Word Match flag to True
        if title_match or abstract_match:
            
            # logger.debug(key+" Match")
            df.loc[entry_count, key+" Match"] = True

    # Set scores, bound to 0->1.
    # logger.debug("Title penalty: {:} | Title matches: {:}".format(title_penalty, num_title_matches))
    # logger.debug("Abstract penalty: {:} | Abstract matches: {:}".format(abstract_penalty, num_abstract_matches))
    title_score    = min( title_penalty * num_title_matches / 1.0, 1.0 ) # An interesting title has one or two matches
    abstract_score = min( abstract_penalty * num_abstract_matches / 5.0, 1.0 ) # An interesting abstract has ~5 matches
    df.loc[entry_count, key+" Score"] = ( title_score + abstract_score ) / 2.0
    logger.debug("arXiv:{:} - {:} | title {:} | abstract {:} | total {:} |".format(df.loc[entry_count, "arXiv Number"], key, title_score, abstract_score, df.loc[entry_count, key+" Score"]))

    return df

def score_papers(df, search_terms, logger):

    # Loop over all entries
    author_str = "    Found Author(s)"
    for entry_count in range(0, len(df)):

        progress_bar(entry_count, len(df)) # No time estimate as it should always be fast. ~1200 papers take less than a second on a 2023 macbook

        clear_progress_bar(logger, 10)
        logger.debug("Seaching for matches in paper {:}.".format(df.loc[entry_count, "arXiv Number"]))
        
        # Seach for Authors
        df, author_matches_str = author_search(df, entry_count, search_terms, logger)
        author_str            += author_matches_str

        # Search for included words
        df = word_search(df, entry_count, search_terms, "Included Words", logger)

        # Search for excluded words
        df = word_search(df, entry_count, search_terms, "Excluded Words", logger)

    progress_bar(len(df), len(df))

    return df, author_str

def filter_papers_score(df, search_terms, logger):
    """Filters the papers based on some criteria (currently the search terms).
    If a paper is scored above some threshold, it is shown.
    NOTE: 

    inputs
    ------
    df           : pandas.DataFrame
        Contains all papers and their information.
    search_terms : dict
        Contains all search terms used to filter papers.
    logger       : RootLogger
        The logger object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    # Define the threshold
    # 0.50 => quite generous with what papers are opened. 
    # 0.65 => feels like a good limit to ensure the papers are interesting
    # 0.85 => can potentially miss something
    # 1.00 => too strict if there are any 'excluded words'
    threshold = 0.65

    logger.info("Calculating interest score for the papers.")

    # Score the papers
    df, author_str = score_papers(df, search_terms, logger)

    # Loop over all entries
    entries_of_note = []
    scores          = []
    for entry_count in range(0, len(df)):

        # If an Author was found, append it to the entries of note
        # Note that the author score is not actually being utilised in the computation of the papers score. If one author was found, the paper is considered interesting.
        if df.loc[entry_count, "Authors Score"] == 1:

            entries_of_note.append(entry_count)

        # Compute a score. If the score is negative, set it to zero
        # Currently the included/excluded words are being weighted as equal. It may be good to cap the excluded word score?
        df.loc[entry_count, "Score"] = max(df.loc[entry_count, "Included Words Score"] -
                                           df.loc[entry_count, "Excluded Words Score"],
                                           0)

        logger.debug("arXiv:{:} final score: {:}".format(df.loc[entry_count, "arXiv Number"], df.loc[entry_count, "Score"]))

        # If the score is above the threshold, append it to the entries of note
        if df.loc[entry_count, "Score"] >= threshold:

            entries_of_note.append(entry_count)
            scores.append(df.loc[entry_count, "Score"])

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(df["Authors Match"]):
        print(author_str)

    # # Ensure only unique entries
    # # Not required for scores
    # entries_of_note_unique = np.unique(entries_of_note)

    # Sort the entries of note by their score
    logger.info("Sorting papers based on score (descending).")
    entries_of_note_sorted = np.array(entries_of_note)[np.array(scores).argsort()[::-1]]

    return entries_of_note_sorted

def filter_papers_binary(df, search_terms, logger):
    """Filters the papers based on some criteria (currently the search terms).
    If a paper matches the criteria, is is shown.
    NOTE: This method is not favoured. Papers that are not interesting to the user can be shown based on the inclusion of certain key words, leading to a large list that needs to be manually gone through. Meanwhile, papers that would be considered interesting can be excluded based on other key words, leading to interesting papers not being shown at all.

    inputs
    ------
    df           : pandas.DataFrame
        Contains all papers and their information.
    search_terms : dict
        Contains all search terms used to filter papers.
    logger       : RootLogger
        The logger object

    outputs
    -------
    entries_of_note_unique : list
        Contains the indices of all papers that pass the filter.
    """

    logger.info("Finding keyword matches in the titles/abstracts.")

    # Score the papers
    df, author_str = score_papers(df, search_terms, logger)

    # Loop over all entries
    entries_of_note = []
    for entry_count in range(0, len(df)):

        # If an Author was found, append it to the entries of note
        if df.loc[entry_count, "Authors Match"] == True:

            logger.debug("Adding paper: {:}".format(df.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

        # If there were included word matches and *no* excluded word matches, append
        elif ( df.loc[entry_count, "Included Words Match"] == True ) and ( df.loc[entry_count, "Excluded Words Match"] == False ):

            logger.debug("Adding paper: {:}".format(df.loc[entry_count, "arXiv Number"]))

            entries_of_note.append(entry_count)

    # Print the list of the found authors and their papers
    # Do not pass this through the logger -- it should always be shown (if at least one was found)
    if any(df["Authors Match"]):
        print(author_str)

    entries_of_note_unique = np.unique(entries_of_note)

    return entries_of_note_unique

# Current method to filter papers.
def filter_papers(df, search_terms, logger):
    """Filter papers"""

    # # Binary search. Filter based on terms found.
    # entries_or_note_unique = filter_papers_binary(df, search_terms, logger)

    # Score search. Filter based on score.
    entries_or_note_unique = filter_papers_score(df, search_terms, logger)

    # # Machine-laerning search. Filter based on score from the ML algorithm
    # # Not yet implemented
    # entries_or_note_unique = filter_papers_ML(df, search_terms, logger)

    return entries_or_note_unique