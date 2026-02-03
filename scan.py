# Load packages
from datetime import timedelta
from datetime import timezone
from datetime import datetime

import xml.etree.ElementTree as ET
import pandas                as pd
import numpy                 as np

import urllib.request
import webbrowser
import urllib
import time
import os
import re

"""This script will search for all papers on the arXiv since the previous execution, then filter based on personal preferences, and open the abstract pages in the browser.

To-do:
Make script neater, use functions
"""

# Define categories that I care for
key_categories = [
                 # "astro-ph*", # All astrophysics categories
                 # "astro-ph.CO", # Cosmology and Nongalactic Astrophysics
                 # "astro-ph.EP", # Earth and Planetary Astrophysics
                 "astro-ph.GA", # Astrophysics of Galaxies
                 "astro-ph.HE", # High Energy Astrophysical Phenomena
                 # "astro-ph.IM", # Instrumentation and Methods for Astrophysics
                 # "astro-ph.SR", # Solar and Stellar Astrophysics
                 ]
cat_string = "+OR+".join(f"cat:{c}" for c in key_categories)

# Define keywords to search for
key_words = [
            "diffusion",
            "diffuse",
            "propagation",
            "gamma",
            "ɣ",
            "γ",
            "cosmic",
            "neutrino",
            "Milky Way",
            "Galactic",
            "H.E.S.S.",
            "LHAASO",
            "Tibet",
            "ARGO",
            "IceCube",
            ]

# Define keywords to exclude
exclusion_words = [
                  "extragalactic",
                  "extra-galactic",
                  "high-z",
                  "quasar",
                  "blazar",
                  "GRB",
                  "AGN",
                  "high-redshift",
                  ]

# Define authors to search for
key_authors = [
              "Porter",
              "Rowell",
              "Moskalenko",
              "Einecke",
              "Mertsch",
              "Schwefer",
              "Vecchiotti",
              "Mitchell",
              "Alsulami",
              "Koenig",
              "Collins",
              "Feijen",
              "Capecchiacci",
              "Lopez",
              "Lange",
              ]
fill = len(max(key_authors, key=len)) # Length of the longest name in the key authors array

# Namespaces used by arXiv
ns = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}

# Define filename
filename = "/Users/pmarinos/Documents/PYTHON/arXiv/catchup.txt"

# Obtain the current date
current_time = datetime.now(timezone.utc)
# The list of papers is typically released before 06:00 UTC.
# If executing before 06:00 UTC, set the date to one day prior
if current_time.hour < 6:
    current_time = current_time - timedelta(days=1)
# The lists are published for the previous day. Always go back one day in the search.
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

# The date of the previous execution is saved in a file
# If it does not exist, create it and set the date to the previous day
if not os.path.exists(filename):
    with open(filename, "w") as f:
        f.write(f"{(end_date - timedelta(days=1)).year:d}\n")
        f.write(f"{(end_date - timedelta(days=1)).month:d}\n")
        f.write(f"{(end_date - timedelta(days=1)).day:d}\n")
# Load it and extract the previous runtime
with open(filename, "r", encoding="utf-8") as f:
    text = [next(f).rstrip("\n") for _ in range(3)]
start_date = datetime(year=int(text[0]), month=int(text[1]), day=int(text[2])).astimezone(timezone.utc)

# Raise an error if the end date is before or equal to the start date
if start_date >= end_date:
    raise ValueError(f"Start date must be earlier that today")

prev_run = end_date - start_date
print("Days since the previous search: {:}".format(prev_run.days))

# Define the search url
url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={start_num:d}&max_results={end_num:d}"

# arXiv asks for a courtesy 3-second pause between searches of ten papers, and a 0.25-second pause between opening links
sleep_search    = 3
interval_search = 10
sleep_opening   = 0.25

print("Obtaining arXiv info. Estimated time: 6 seconds") # Always two 3-second sleeps

# Perform a search over all astro-ph categories to find how many papers were posted
formatted_url_allcat = url.format(start_year  = start_date.year,
                                  start_month = start_date.month,
                                  start_day   = start_date.day,
                                  end_year    = end_date.year,
                                  end_month   = end_date.month,
                                  end_day     = end_date.day,
                                  cats        = "astro-ph*",
                                  start_num   = 0,
                                  end_num     = 1)
# First request
with urllib.request.urlopen(formatted_url_allcat) as f:
    xml_data_allcat = f.read()

# Parse the xml
parsed_xml_data_allcat = ET.fromstring(xml_data_allcat)

# Extract the number of papers since the last time the script was executed
total_papers = int(parsed_xml_data_allcat.find("opensearch:totalResults", ns).text)
# Compute the number of digits. Assumes that the number of papers is positive :)
max_digits = len(str(total_papers))

# Perform an initial search to find how many papers there are in the categories of interest
formatted_url_initial = url.format(start_year  = start_date.year,
                                   start_month = start_date.month,
                                   start_day   = start_date.day,
                                   end_year    = end_date.year,
                                   end_month   = end_date.month,
                                   end_day     = end_date.day,
                                   cats        = cat_string,
                                   start_num   = 0,
                                   end_num     = 1)
# Second request. Sleep for 3s
time.sleep(sleep_search)
with urllib.request.urlopen(formatted_url_initial) as f:
    xml_data_initial = f.read()

# Parse the xml
parsed_xml_data_initial = ET.fromstring(xml_data_initial)

# Extract the number of papers since the last time the script was executed
max_num = int(parsed_xml_data_initial.find("opensearch:totalResults", ns).text)

# Perform the searches in groups of size "interval"
entries = []
print("Searching for papers. Estimated time: {:d} seconds".format(sleep_search*max_num//interval_search + (sleep_search if max_num%interval_search > 0 else 0)))
for ii in range(0, max_num, interval_search):

    # Search over the current interval
    formatted_url = url.format(start_year  = start_date.year,
                               start_month = start_date.month,
                               start_day   = start_date.day,
                               end_year    = end_date.year,
                               end_month   = end_date.month,
                               end_day     = end_date.day,
                               cats        = cat_string,
                               start_num   = ii,
                               end_num     = ii+interval_search)

    # Sleep before the query so that there is no dead time on the last query
    time.sleep(sleep_search)
    with urllib.request.urlopen(formatted_url) as f:
        xml_data = f.read()

    # Parse the xml
    parsed_xml = ET.fromstring(xml_data)
    
    # Loop over the entries (papers) within the current search
    for entry in parsed_xml.findall("atom:entry", ns):

        # Previously, when parsing the emails, there would be 'revised' versions. I would skip them, and they typically had no abstract.
        # The search that is being used now specifically uses "submitted date" as the criteria for being included, so I think there will never be any revised papers or empty abstracts.
        # However, I have kept the relevant columns and error checks in just in case.

        published_date = entry.find("atom:published", ns).text
        updated_date   = entry.find("atom:updated", ns).text

        author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        paper = {
            "arXiv Number"    : entry.find("atom:id", ns).text.split("/")[-1],
            "Title"           : entry.find("atom:title", ns).text.strip(),
            "Authors"         : ", ".join(f"{author}" for author in author_list),
            "Revised?"        : updated_date > published_date,
            "Abstract"        : entry.find("atom:summary", ns).text.strip(),
            "url"             : entry.find("atom:id", ns).text.strip(),
            "KeyAuthor Match" : False,
            "KeyWord Match"   : False,
            "ExcWord Match"   : False,
        }

        entries.append(paper)

# Place into a dataframe
df = pd.DataFrame(entries)

# # Print the entire dataframe
# with pd.option_context('display.max_rows', None,
#                        'display.max_columns', None,
#                        'display.precision', 3,
#                        ):
#     print(df)

# Remove duplicated arXiv numbers
df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)

# Remove revised papers
df.drop(df[df["Revised?"]==True].index, inplace=True)
df.reset_index(drop=True, inplace=True)

entries_of_note = []

# Loop over all entries
author_match_count = 0
for entry_count in range(0, len(df)):
    
    # Search all author lists for the people I care about
    for key_author in key_authors:

        # Search the author field in the entry
        author_match = re.search(key_author, df["Authors"][entry_count])

        if author_match:
            
            # Set the entry in the dataframe for the author match to True
            df.loc[entry_count, "KeyAuthor Match"] = True

            if author_match_count == 0:
                print("    Found Author(s)")
                author_match_count = 1
                
            print("    {: >{fill}}:  ".format(key_author, fill=fill), df["url"][entry_count])
    
    # Search all titles and abstracts for words that I care about
    for key_word in key_words:

        # Search the author field in the entry
        title_match    = re.search(key_word, df["Title"][entry_count], re.IGNORECASE)

        if df["Abstract"][entry_count] is not None: # Skip empty abstract entries
            abstract_match = re.search(key_word, df["Abstract"][entry_count], re.IGNORECASE)
            
        if title_match or abstract_match:
            
            df.loc[entry_count, "KeyWord Match"] = True
    
    # Search all titles and abstracts for words that I want to exclude
    for exclusion_word in exclusion_words:

        # Search the author field in the entry
        title_match    = re.search(exclusion_word, df["Title"][entry_count], re.IGNORECASE)

        if df["Abstract"][entry_count] is not None: # Skip empty abstract entries

            abstract_match = re.search(exclusion_word, df["Abstract"][entry_count], re.IGNORECASE)

        if title_match or abstract_match:

            df.loc[entry_count, "ExcWord Match"] = True

    # If key_authors=True, always keep
    # If there were keyword matches and *no* matches with excluded words, keep
    if df["KeyAuthor Match"][entry_count] == True:
        entries_of_note.append(entry_count)
    elif df["KeyWord Match"][entry_count]==True and df["ExcWord Match"][entry_count]==False:
        entries_of_note.append(entry_count)

# Only keep unique entries
entries_of_note_unique = np.unique(entries_of_note)

# Loop through the list and open all in the web browser
request_count = 0
print("Opening the papers.   Estimated time: {:.2f} seconds".format(len(entries_of_note_unique)/4))
for link_index in entries_of_note_unique:

    # # arXiv asks that you limit opening pages to four requests per second
    # # Sleep for 1s every four pages (recommended)
    # if request_count % 4 == 0:
    #     time.sleep(1)
    # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
    if request_count > 0:
        time.sleep(sleep_opening)
    request_count += 1

    link = df.loc[link_index, "url"]
    # print(link)
    webbrowser.open(link)

print("There were a total of {: >{fill}} papers submitted to the astro-ph list since the previous search".format(total_papers, fill=max_digits))
print("            of these, {: >{fill}} papers were in the categories of interest".format(max_num, fill=max_digits))
print("            of these, {: >{fill}} papers were opened in the web browser".format(len(entries_of_note_unique), fill=max_digits))

# Write the current date to a file so for the next run
with open(filename, "w") as f:
    f.write(f"{end_date.year:d}\n")
    f.write(f"{end_date.month:d}\n")
    f.write(f"{end_date.day:d}\n")
