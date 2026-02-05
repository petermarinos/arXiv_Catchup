# Load packages
from datetime import timedelta
from datetime import timezone
from datetime import datetime

import xml.etree.ElementTree as ET
import pandas                as pd
import numpy                 as np

import urllib.request
import unicodedata
import webbrowser
import argparse
import urllib
import time
import os
import re

"""
This script will search for all papers on the arXiv since the previous execution, then filter based on personal preferences, and open the abstract pages in the browser.

Usage: run the script
"""

def load_list(filename):
    """
    Load search terms from a text file. These are used for regex searches, so word boundaries are added
    """
    items = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.append(line)

    return items

def LaTeX_to_unicode(s):
    """Stip LaTeX-style accents from the string (e.g. {\'a} -> a, and \'a -> a)

    This function only covers common accents.
    To account for all accents and ligatures/special characters, it is best to install an additional package.
    However, that would only be required if one of the key_authors has a special character/accent.
    As I do not currently have any authors I care about with special characters, and only common accents, I leave this task for later.
    """

    if s is None:
        return ""
    
    # Dictionary of the LaTeX accents
    # Same ordering as on the wikipedia page
    LATEX_ACCENTS = {
                    "`": "\u0300",   # grave,                              e.g. ò
                    "'": "\u0301",   # acute,                              e.g. ó
                    "^": "\u0302",   # circumflex,                         e.g. ô
                    '"': "\u0308",   # umlaut, trema, or dieresis,         e.g. ö
                    # "H": "\u030B",   # long Hungarian umlaut/double acute, e.g. ő # Causes issues with names that have the letter H
                    "~": "\u0303",   # tilde,                              e.g. õ
                    # "c": "\u0327",   # cedilla,                            e.g. ç # Causes issues with names that have the letter c
                    # "k": "\u0328",   # ogonek,                             e.g. ą # Causes issues with names that have the letter k
                                     # barred l,                           e.g. ł
                    "=": "\u0304",   # macron,                             e.g. ō
                                     # under-bar,                          e.g. o
                    # ".": "\u0307",   # dot,                                e.g. ȯ # Causes issues with names that have initials
                                     # under-dot,                          e.g. ụ
                    # "r": "\u030A",   # ring,                               e.g. å # Causes issues with names that have the letter r
                                     # ringed a (special case),            e.g. å
                    # "u": "\u0306",   # breve,                              e.g. ŏ # Causes issues with names that have the letter u
                    # "v": "\u030C",   # caron,                              e.g. š # Causes issues with names that have the letter v
                                     # tie,                                e.g. o͡o
                                     # slashed o,                          e.g. ø
                                     # dotless i,                          e.g. ı
                    }

    # {\'a} style
    for latex, combining in LATEX_ACCENTS.items():
        s = re.sub(
                  rf"\{{{latex}([A-Za-z])\}}",
                  lambda m: m.group(1) + combining,
                  s,
                  )

    # \'a style
    for latex, combining in LATEX_ACCENTS.items():
        s = re.sub(
                  rf"{latex}([A-Za-z])",
                  lambda m: m.group(1) + combining,
                  s,
                  )

    return s

def normalise_string(s):
    """Normalise a string, i.e. remove accents (e.g. ó -> o)
    Also accounts for LaTeX accents
    """

    # Define the form
    form = "NFKD" # "compatibility deecomposition"

    if s is None:
        return ""
    
    s_stripped   = LaTeX_to_unicode(s)
    s_normalised = unicodedata.normalize(form, s_stripped)
    
    return s_normalised.encode("ascii", "ignore").decode("ascii")

def write_date(filename, date):

    print(f"{(date).year:d}")
    print(f"{(date).month:d}")
    print(f"{(date).day:d}")

    with open(filename, "w") as f:
        f.write(f"{(date).year:d}\n")
        f.write(f"{(date).month:d}\n")
        f.write(f"{(date).day:d}\n")

    return

def download_search(url):

    # Query the server
    with urllib.request.urlopen(url) as f:
        xml_data = f.read()

    # Parse the xml
    parsed_xml_data = ET.fromstring(xml_data)

    return parsed_xml_data

# Parse command-line arguments
parser = argparse.ArgumentParser(prog='arXiv Catchup',
                                 description='Search arXiv for papers matching your criteria')
parser.add_argument('-n', '--new-window', action='store_true',
                    help='Open all papers in a single new browser window as tabs')
# parser.add_argument('-f', '--new-window', action='store_true',
#                     help='Skip the warning about how many papers will be opened') # Not yet implemented
args = parser.parse_args()

# Find the directory of the script
cdir = os.path.dirname(os.path.realpath(__file__))

# Define categories that I care for
key_categories = [
                 # "astro-ph*", # All astrophysics categories. Ensure all other categories are commented out if using this one
                 # "astro-ph.CO", # Cosmology and Nongalactic Astrophysics
                 # "astro-ph.EP", # Earth and Planetary Astrophysics
                 "astro-ph.GA", # Astrophysics of Galaxies
                 "astro-ph.HE", # High Energy Astrophysical Phenomena
                 # "astro-ph.IM", # Instrumentation and Methods for Astrophysics
                 # "astro-ph.SR", # Solar and Stellar Astrophysics
                 ]
# Define string for use in the url search
cat_urlstring = "+OR+".join(f"cat:{c}" for c in key_categories)
# Define string for printing to the terminal
cat_printstring = ", ".join(f"{c}" for c in key_categories)

key_authors     = load_list(cdir+"/key_authors.txt")
key_words       = load_list(cdir+"/key_words.txt")
exclusion_words = load_list(cdir+"/exclusion_words.txt")

fill = len(max(key_authors, key=len)) # Length of the longest name in the key authors array

# Namespaces used by arXiv
ns = {
     "atom": "http://www.w3.org/2005/Atom",
     "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
     "arxiv": "http://arxiv.org/schemas/atom",
     }

# Define filename of the catchup file (where the date of the previous search is stored)
catchup = cdir+"/catchup.txt"

# Obtain the current date
current_time = datetime.now(timezone.utc)
# The list of papers is typically released before 06:00 UTC.
# If executing before 06:00 UTC, set the date to one day prior
if current_time.hour < 6:
    current_time = current_time - timedelta(days=1)
# The lists are published for the previous day, up to 19:00 UTC. Always go back one day in the search.
dt = 1
# No lists are published over the weekend. If it is Sunday, go back one extra day in the search, and two days for Monday.
current_weekday = current_time.weekday()
if current_weekday == 6:
    dt += 1
elif current_weekday == 0:
    dt += 2
# No lists are released on certain days. These days are chosen ad-hoc, and are days that are important to USAians. It includes Christmas, their Thanksgiving, and others.
# The search should return no results on those days (not tested).
# If waiting extra time, there should be no missed papers (not tested).
# Compute the end_date of the search
end_date = current_time - timedelta(days=dt)

print(end_date)

# The date of the previous execution is saved in a file
# If it does not exist, create it and set the date to the previous day
if not os.path.exists(catchup):
    # If it is before the release time of the list, need to subtract an extra day
    if current_time.hour < 6:
        write_date(catchup, end_date - timedelta(days=2))
    else:
        write_date(catchup, end_date - timedelta(days=1))
# Load it and extract the previous runtime
with open(catchup, "r", encoding="utf-8") as f:
    text = [next(f).rstrip("\n") for _ in range(3)]
start_date = datetime(year=int(text[0]), month=int(text[1]), day=int(text[2]), hour=19, tzinfo=timezone.utc)

# prev_run = end_date - start_date

# # Raise an error if the end date is before or equal to the start date
# if prev_run.days == 0:
#     # Add a calculation to compute how long until the next search can be executed, to be included in the error message.
#     # Would need to account for weekdays.
#     raise ValueError(f"Search start/end dates are equal.")
# elif prev_run.days < 0:
#     raise ValueError(f"Search start date is after the end date. Check for timezone issues.")
# else:
#     print("Days since the previous search: {:}".format(prev_run.days))

# print("Searching the {:} categories with the lists posted from {:}/{:}/{:} to {:}/{:}/{:}".format(cat_printstring, start_date.year, start_date.month, start_date.day, end_date.year, end_date.month, end_date.day))

# # Define the search url
# url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={start_num:d}&max_results={end_num:d}"

# # arXiv asks for a courtesy 3-second pause between searches of ten papers, and a 0.25-second pause between opening links
# sleep_search    = 3
# interval_search = 10
# sleep_opening   = 0.25

# print("Obtaining arXiv info. Estimated time: 6 seconds") # Always two 3-second sleeps

# # Perform a search over all astro-ph categories to find how many papers were posted since the previous search
# formatted_url_allcat = url.format(start_year  = start_date.year,
#                                   start_month = start_date.month,
#                                   start_day   = start_date.day,
#                                   end_year    = end_date.year,
#                                   end_month   = end_date.month,
#                                   end_day     = end_date.day,
#                                   cats        = "astro-ph*",
#                                   start_num   = 0,
#                                   end_num     = 1)

# # First request
# parsed_xml_data_allcat = download_search(formatted_url_allcat)

# # Extract the number of papers since the last time the script was executed
# total_papers = int(parsed_xml_data_allcat.find("opensearch:totalResults", ns).text)
# # Compute the number of digits. Assumes that the number of papers is positive :)
# max_digits = len(str(total_papers))

# # Perform an initial search to find how many papers there are in the categories of interest
# formatted_url_initial = url.format(start_year  = start_date.year,
#                                    start_month = start_date.month,
#                                    start_day   = start_date.day,
#                                    end_year    = end_date.year,
#                                    end_month   = end_date.month,
#                                    end_day     = end_date.day,
#                                    cats        = cat_urlstring,
#                                    start_num   = 0,
#                                    end_num     = 1)
# # Second request. Sleep for 3s
# time.sleep(sleep_search)
# parsed_xml_data_initial = download_search(formatted_url_initial)

# # Extract the number of papers since the last time the script was executed
# max_num = int(parsed_xml_data_initial.find("opensearch:totalResults", ns).text)

# # Perform the searches in groups of size "interval"
# entries = []
# print("Searching for papers. Estimated time: {:d} seconds".format(sleep_search*max_num//interval_search + (sleep_search if max_num%interval_search > 0 else 0)))
# for ii in range(0, max_num, interval_search):

#     # Search over the current interval
#     formatted_url = url.format(start_year  = start_date.year,
#                                start_month = start_date.month,
#                                start_day   = start_date.day,
#                                end_year    = end_date.year,
#                                end_month   = end_date.month,
#                                end_day     = end_date.day,
#                                cats        = cat_urlstring,
#                                start_num   = ii,
#                                end_num     = ii+interval_search)

#     # Sleep before the query so that there is no dead time on the last query
#     time.sleep(sleep_search)
#     parsed_xml = download_search(formatted_url)
    
#     # Loop over the entries (papers) within the current search
#     for entry in parsed_xml.findall("atom:entry", ns):

#         # Previously, when parsing the emails, there would be 'revised' versions. I would skip them, and they typically had no abstract.
#         # The search that is being used now specifically uses "submitted date" as the criteria for being included, so I think there will never be any revised papers or empty abstracts.
#         # However, I have kept the relevant columns and error checks just in case.

#         published_date = entry.find("atom:published", ns).text
#         updated_date   = entry.find("atom:updated", ns).text

#         author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

#         # Place information in a dictionary
#         paper = {
#             "arXiv Number"    : entry.find("atom:id", ns).text.split("/")[-1],
#             "Title"           : entry.find("atom:title", ns).text.strip(),
#             "Authors"         : normalise_string( ", ".join(f"{author}" for author in author_list) ),
#             "Revised?"        : updated_date > published_date,
#             "Abstract"        : entry.find("atom:summary", ns).text.strip(),
#             "url"             : entry.find("atom:id", ns).text.strip(),
#             "KeyAuthor Match" : False,
#             "KeyWord Match"   : False,
#             "ExcWord Match"   : False,
#         }

#         entries.append(paper)

# # Place into a dataframe
# df = pd.DataFrame(entries)

# # # Print the entire dataframe
# # with pd.option_context('display.max_rows', None,
# #                        'display.max_columns', None,
# #                        'display.precision', 3,
# #                        ):
# #     print(df)

# # Remove duplicated arXiv numbers
# df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)

# # Remove revised papers
# df.drop(df[df["Revised?"]==True].index, inplace=True)
# df.reset_index(drop=True, inplace=True)

# entries_of_note = []

# # Loop over all entries
# author_match_count = 0
# for entry_count in range(0, len(df)):
    
#     # Search all author lists for the people I care about
#     for key_author in key_authors:

#         # Search the author field in the entry
#         author_match = re.search(r"\b"+key_author+r"\b", df["Authors"][entry_count])

#         if author_match:
            
#             # Set the entry in the dataframe for the author match to True
#             df.loc[entry_count, "KeyAuthor Match"] = True

#             # If one author is found, output an extra line to the terminal
#             if author_match_count == 0:
#                 print("    Found Author(s)")
#                 author_match_count = 1
                
#             print("    {: >{fill}}:  ".format(key_author, fill=fill), df["url"][entry_count])
    
#     # Search all titles and abstracts for words that I care about
#     for key_word in key_words:

#         # Search the author field in the entry
#         title_match    = re.search(r"\b"+key_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

#         if df["Abstract"][entry_count] is not None: # Skip empty abstract entries
#             abstract_match = re.search(r"\b"+key_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)
            
#         if title_match or abstract_match:
            
#             df.loc[entry_count, "KeyWord Match"] = True
    
#     # Search all titles and abstracts for words that I want to exclude
#     for exclusion_word in exclusion_words:

#         # Search the author field in the entry
#         title_match    = re.search(r"\b"+exclusion_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

#         if df["Abstract"][entry_count] is not None: # Skip empty abstract entries

#             abstract_match = re.search(r"\b"+exclusion_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)

#         if title_match or abstract_match:

#             df.loc[entry_count, "ExcWord Match"] = True

#     # If key_authors=True, always keep
#     # If there were keyword matches and *no* matches with excluded words, keep
#     if df["KeyAuthor Match"][entry_count] == True:
#         entries_of_note.append(entry_count)
#     elif df["KeyWord Match"][entry_count]==True and df["ExcWord Match"][entry_count]==False:
#         entries_of_note.append(entry_count)

# # Only keep unique entries (should only matter if there are revised versions)
# entries_of_note_unique = np.unique(entries_of_note)

# # Loop through the list and open all in the web browser
# request_count = 0
# print("Opening the papers.   Estimated time: {:.2f} seconds".format(len(entries_of_note_unique)/4))
# for link_index in entries_of_note_unique:

#     # # arXiv asks that you limit opening pages to four requests per second
#     # Sleep before the request to prevent an unnecessary sleep at the end
#     # # Sleep for 1s every four pages (recommended)
#     # if request_count % 4 == 0:
#     #     time.sleep(1)
#     # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
#     if request_count > 0:
#         time.sleep(sleep_opening)

#     link = df.loc[link_index, "url"]
#     # print(link)
    
#     # Open in new window if flag is set
#     if args.new_window:
#         if request_count == 0:
#             webbrowser.open(link, new=1)  # new=1: open in a new browser window
#         else:
#             webbrowser.open(link, new=2)  # new=2: open in a new tab
#     else:
#         webbrowser.open(link)  # Default behavior, just opens everything in the current window

#     request_count += 1

# print("There were a total of {: >{fill}} papers submitted to the astro-ph list since the previous search".format(total_papers, fill=max_digits))
# print("            of these, {: >{fill}} papers were in the categories of interest".format(max_num, fill=max_digits))
# print("            of these, {: >{fill}} papers were opened in the web browser".format(len(entries_of_note_unique), fill=max_digits))

# # print("currently not updating the start date for the search")
# # Write the current date to a file so for the next run
# write_date(catchup, end_date)
