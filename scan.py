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
import datetime
import urllib
import time
import sys
import os
import re

"""
This script will search for all papers on the arXiv since the previous execution, then filter based on personal preferences, and open the abstract pages in the browser.

Usage: run the script
"""

# Note: The 'remaining time" shown in the progress bars are based entirely on the sleep timers, and not how long things actually take.
# This simplification is accurate if the number of papers is ~<100
# If there are more papers then random slowdowns when connecting to the arXiv servers will make any remaining time estimate incorrect.

def load_list(filename, empty_error=True):
    """
    Load search terms from a text file. These are used for regex searches, so word boundaries are added

    If the file is empty, then an error will be raised if empty_error is True, or a warning will be printed if False
    """
    items = []

    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.append(line)

    # Check if any non-commented lines were loaded
    if len(items) == 0:

        if empty_error:

            raise ValueError("No items were loaded from the file {:s}\n            Please check the file and add at least one item".format(filename))

        else:

            print("WARNING: No items were loaded from the file {:s}".format(filename))

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

    # print(f"{(date).year:d}")
    # print(f"{(date).month:d}")
    # print(f"{(date).day:d}")

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

def open_links(df, entries_of_note_unique, sleep_time):

    # Calculate the number of links
    total = len(entries_of_note_unique)

    # Loop through the list and open all in the web browser
    request_count = 0
    time_start = time.time()
    print("Opening the papers. Estimated time: {:.2f} seconds".format(total/4))
    for link_index in entries_of_note_unique:

        progress_bar(request_count, total, ( total - request_count ) / 4)

        # # arXiv asks that you limit opening pages to four requests per second
        # Sleep before the request to prevent an unnecessary sleep at the end
        # # Sleep for 1s every four pages (recommended)
        # if request_count % 4 == 0:
        #     time.sleep(1)
        # Sleep for 0.25s per request (my preferred method when having to watch it open a large number)
        if request_count > 0:
            time.sleep(sleep_time)

        link = df.loc[link_index, "url"]
        # print(link)

        # If args.force_open, start opening links
        # Else, ask for a confirmation that states/warns the user about how many will be opened
        
        # Open in new window if flag is set
        if args.new_window:

            if request_count == 0:

                webbrowser.open(link, new=1)  # new=1: open in a new browser window

            else:

                webbrowser.open(link, new=2)  # new=2: open in a new tab
        else:

            webbrowser.open(link)  # Default behavior, just opens everything in the current window

        request_count += 1

    progress_bar(total, total)
    print("")

    return

def progress_bar(ii, total, time_estimate=None):
    """Print a progress bar that updates
    """

    percent_progress = 100 * ii / total

    width = 50 # Width of the progress bar in characters
    bar_string = "■" * int( np.floor( percent_progress * width/100 ) ) + "□" * int( width - np.floor( percent_progress * width/100 ) )

    if time_estimate is not None:
        if time_estimate <= 60:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.2f} seconds".format( bar_string, int(np.ceil(percent_progress)), time_estimate )
        elif 60 < time_estimate <= 3600:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.1f} minutes".format( bar_string, int(np.ceil(percent_progress)), time_estimate/60 )
        else:
            progress_message = "|{:s}|  {: >3}%  Remaining: {:.1f} hours".format( bar_string, int(np.ceil(percent_progress)), time_estimate/3600 )
    else:
        progress_message = "|{:s}|  {: >3}%".format( bar_string, int(np.ceil(percent_progress)) )

    # Compute the padding to overwrite all text with whitespace
    # Maximum length of the message is width+33+{extra digits before the decimal on the remaining time}
    pad = " " * ( width + 33 + 3 - len(progress_message))

    sys.stdout.write("\r" + progress_message + pad) # Move cursor to the start of the line and print the progress message
    sys.stdout.flush()

    return

def is_posting_day_bool(dt):

    # dt.weekday() = 0 for Monday, ..., 4 for Friday, 5 for Saturday, and 6 for Sunday

    return dt.weekday() <= 4

def calc_search_endtime(now, post_time, search_time):
    """Return the datetime of the most recent arXiv daily list posting.
    """

    # today_post = datetime.datetime.combine(now.date(), post_time)


    # If now is after post_time, search_time will be 19:00 the previous day
    if now.timetz() > post_time:
        temp_date = now - timedelta(days=1)
        while not is_posting_day_bool(temp_date):
            temp_date -= timedelta(days=1)

    # Else, if now is before post_time, search_time will be 19:00 the day before previous
    else:
        temp_date = now - timedelta(days=2)
        while not is_posting_day_bool(temp_date):
            temp_date -= timedelta(days=1)

    search_endtime = datetime.datetime.combine(temp_date.date(), search_time)

    return search_endtime

def calc_next_posttime(now, post_time):
    """Return the datetime of the most recent arXiv daily list posting.
    """

    # If now is after post_time, the next post_time will be 06:00 the following day
    if now.timetz() > post_time:
        temp_date = now + timedelta(days=1)
        while not is_posting_day_bool(temp_date):
            temp_date += timedelta(days=1)

    # Else, if now is before post_time, the next post_time will be 06:00 the next post_day
    else:
        temp_date = now
        while not is_posting_day_bool(temp_date):
            temp_date += timedelta(days=1)

    next_post_time = datetime.datetime.combine(temp_date.date(), post_time)

    return next_post_time


# Parse command-line arguments
parser = argparse.ArgumentParser(prog='arXiv Catchup',
                                 description='Search arXiv for papers matching your criteria')
parser.add_argument('-n', '--new-window', action='store_true',
                    help='Open all papers in a single new browser window as tabs') # Doesn't work on mac with firefox
parser.add_argument('-f', '--force-open', action='store_true',
                    help='Skip the warning about how many papers will be opened') # Not yet implemented
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

# Define filename of the catchup file (where the date of the previous search is stored)
catchup = cdir+"/catchup.txt"

# Load search terms from the auxiliary files
key_words       = load_list(cdir+"/key_words.txt")
key_authors     = load_list(cdir+"/key_authors.txt", False)
exclusion_words = load_list(cdir+"/exclusion_words.txt", False)

# Compute the length of the longest name in the key authors array
fill = len(max(key_authors, key=len))

# xml namespaces used by arXiv
ns = {
     "atom"       : "http://www.w3.org/2005/Atom",
     "opensearch" : "http://a9.com/-/spec/opensearch/1.1/",
     "arxiv"      : "http://arxiv.org/schemas/atom",
     }

# This script is not tied to the daily listings and when they are posted.
# However, as the API is not updated simultaneously, it is best to time the searches around the daily listings.
# The daily list of papers is typically released around 02:00 UTC to 06:00 UTC.
# They are published on Monday, Tuesday, Wednesday, Thursday, and Friday (UTC).
# The lists contain all papers published from 19:00 UTC two posting days ago to 19:00 UTC on the prior posting day
# Our searches here are based on these times

# For example:
#     If searching on Wednesday at 20:00 UTC, we need to search the list posted on Wednesday at 06:00 UTC, which will include papers from Monday 19:00 UTC to Tuesday 19:00 UTC.
#     If searching on Tuesday at 05:00 UTC, we need to search the list posted on Monday day at 06:00 UTC, which will include papers from Thursday 19:00 UTC to Friday 19:00 UTC.

# No lists are released on certain days. These days are chosen ad-hoc, and are days that are important to USAians. It includes Christmas, their Thanksgiving, and others.
# As this script is not tied to the daily listings, and provides a large offset in the search, no papers *should* be missed (not tested)

# Define the posting time of the daily list
list_post_time = datetime.time(6, 0, tzinfo=timezone.utc) # 06:00 UTC

# Define the posting time of the daily list
search_time    = datetime.time(19, 0, tzinfo=timezone.utc) # 19:00 UTC

# Obtain the current time, converted to the UTC timezone
current_time = datetime.datetime.now(timezone.utc)

# Compute the time at the end of the search
end_time = calc_search_endtime(current_time, list_post_time, search_time)
end_date = end_time.date()

# The date of the previous execution is saved in a file
# If the file does not exist, create it and set the date to the listing before the last posting
if not os.path.exists(catchup):

    # Compute the list time before the previous
    # This can be done by passing the end_time found above into the calc_search_endtime() function
    prev_end_time  = calc_search_endtime(end_time, list_post_time, search_time)
    
    write_date(catchup, prev_end_time)

# Load it and extract the previous runtime
with open(catchup, "r", encoding="utf-8") as f:

    start_text = [next(f).rstrip("\n") for _ in range(3)]

# Convert the plain text to a datetime object
start_time = datetime.datetime(year=int(start_text[0]), month=int(start_text[1]), day=int(start_text[2]), hour=19, tzinfo=timezone.utc)
start_date = start_time.date()

# Compute how long the search is covering
prev_run = end_date - start_date

# If the end date equal to the start date, raise an error and tell the user to wait
if prev_run.days == 0:

    # Compute the time that the next list will be posted
    nextlist_time   = calc_next_posttime(current_time, list_post_time)
    time_until_next = nextlist_time - current_time

    t_days    = time_until_next.days
    t_hours   = time_until_next.seconds//3600
    t_minutes = (time_until_next.seconds//60) - t_hours * 60

    raise ValueError("Search start/end dates are equal.\n            The next list will be posted in {:} days, {:} hours, and {:} minutes.".format(t_days, t_hours, t_minutes))

# If the end date is before the start date, raise an error
elif prev_run.days < 0:

    raise ValueError(f"Search start date is after the end date. Check for timezone issues.")

# If there are no issues, let the user know how many days we are searching over
else:

    print("Days since the previous search: {:}".format(prev_run.days))

print("Searching the {:} categories from {:}/{:}/{:} 19:00 UTC to {:}/{:}/{:} 19:00 UTC".format(cat_printstring, start_date.year, start_date.month, start_date.day, end_date.year, end_date.month, end_date.day))

# Define the search url
url = "https://export.arxiv.org/api/query?search_query=submittedDate:[{start_year:d}{start_month:02d}{start_day:02d}1900%20TO%20{end_year:d}{end_month:02d}{end_day:02d}1900]+AND+{cats:s}&sortBy=submittedDate&start={start_num:d}&max_results={end_num:d}"

# arXiv asks for a courtesy 3-second pause between searches of ten papers, and a 0.25-second pause between opening links
sleep_search    = 3
interval_search = 10
sleep_opening   = 0.25

print("Obtaining arXiv info. Estimated time: 3 seconds") # Always two 3-second sleeps

# progress_bar(0, 2, 3)

# Perform a search over all astro-ph categories to find how many papers were posted since the previous search
formatted_url_allcat = url.format(start_year  = start_date.year,
                                  start_month = start_date.month,
                                  start_day   = start_date.day,
                                  end_year    = end_date.year,
                                  end_month   = end_date.month,
                                  end_day     = end_date.day,
                                  cats        = "cat:astro-ph*",
                                  start_num   = 0,
                                  end_num     = 1)

# First request
parsed_xml_data_allcat = download_search(formatted_url_allcat)

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
                                   cats        = cat_urlstring,
                                   start_num   = 0,
                                   end_num     = 1)

progress_bar(1, 2, 3)
# Second request. Sleep for 3s
time.sleep(sleep_search)
parsed_xml_data_initial = download_search(formatted_url_initial)

progress_bar(2, 2)
print("")

# Extract the number of papers since the last time the script was executed
max_num = int(parsed_xml_data_initial.find("opensearch:totalResults", ns).text)

# Perform the searches in groups of size "interval"
entries = []
print("Searching for papers. Estimated time: {:d} seconds".format(-sleep_search*(max_num//-interval_search)))
for ii in range(0, max_num, interval_search):

    # Compute the progress of the loop
    if ii+interval_search > max_num:
        remaining_steps = 1
    else:
        # remaining_steps = ( max_num - ii + 1 ) // interval_search
        remaining_steps = -((max_num-ii)//-interval_search)

    # Print the progress bar
    progress_bar(ii, max_num, remaining_steps * sleep_search)

    # Search over the current interval
    formatted_url = url.format(start_year  = start_date.year,
                               start_month = start_date.month,
                               start_day   = start_date.day,
                               end_year    = end_date.year,
                               end_month   = end_date.month,
                               end_day     = end_date.day,
                               cats        = cat_urlstring,
                               start_num   = ii,
                               end_num     = ii+interval_search)

    # Sleep before the query so that there is no dead time on the last query
    time.sleep(sleep_search)
    parsed_xml = download_search(formatted_url)
    
    # Loop over the entries (papers) within the current search
    for entry in parsed_xml.findall("atom:entry", ns):

        # Previously, when parsing the emails, there would be 'revised' versions. I would skip them, and they typically had no abstract.
        # The search that is being used now specifically uses "submitted date" as the criteria for being included, so I think there will never be any revised papers or empty abstracts.
        # However, I have kept the relevant columns and error checks just in case.

        published_date = entry.find("atom:published", ns).text
        updated_date   = entry.find("atom:updated", ns).text

        author_list = [author.find("atom:name", ns).text for author in entry.findall("atom:author", ns)]

        # Place information in a dictionary
        paper = {
            "arXiv Number"    : entry.find("atom:id", ns).text.split("/")[-1],
            "Title"           : entry.find("atom:title", ns).text.strip(),
            "Authors"         : normalise_string( ", ".join(f"{author}" for author in author_list) ),
            "Revised?"        : updated_date > published_date,
            "Abstract"        : entry.find("atom:summary", ns).text.strip(),
            "url"             : entry.find("atom:id", ns).text.strip(),
            "KeyAuthor Match" : False,
            "KeyWord Match"   : False,
            "ExcWord Match"   : False,
        }

        entries.append(paper)

progress_bar(max_num, max_num)
print("")

# Place into a dataframe
df = pd.DataFrame(entries)

# Remove duplicated arXiv numbers
df.drop_duplicates(subset="arXiv Number", inplace=True, ignore_index=True)

# Remove revised papers
df.drop(df[df["Revised?"]==True].index, inplace=True)
df.reset_index(drop=True, inplace=True)

# Loop over all entries
author_match_count = 0
entries_of_note = []
author_str = ""
print("Finding papers of interest.")
for entry_count in range(0, len(df)):

    progress_bar(entry_count, len(df)) # No time estimate as it should always be fast. ~1200 papers take less than a second on a 2023 macbook
    
    # Search all author lists for the people I care about
    for key_author in key_authors:

        # Search the author field in the entry
        author_match = re.search(r"\b"+key_author+r"\b", df["Authors"][entry_count])

        if author_match:
            
            # Set the entry in the dataframe for the author match to True
            df.loc[entry_count, "KeyAuthor Match"] = True

            # If one author is found, output an extra line to the terminal
            if author_match_count == 0:
                # print("    Found Author(s)")
                author_str += "\n    Found Author(s)"
                author_match_count = 1
                
            # print("    {: >{fill}}:  ".format(key_author, fill=fill), df["url"][entry_count])
            author_str += "\n    {: >{fill}}:  {url:}".format(key_author, fill=fill, url=df["url"][entry_count])
    
    # Search all titles and abstracts for words that I care about
    for key_word in key_words:

        # Search the author field in the entry
        title_match    = re.search(r"\b"+key_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

        if df["Abstract"][entry_count] is not None: # Skip empty abstract entries
            abstract_match = re.search(r"\b"+key_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)
            
        if title_match or abstract_match:
            
            df.loc[entry_count, "KeyWord Match"] = True
    
    # Search all titles and abstracts for words that I want to exclude
    for exclusion_word in exclusion_words:

        # Search the author field in the entry
        title_match    = re.search(r"\b"+exclusion_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

        if df["Abstract"][entry_count] is not None: # Skip empty abstract entries

            abstract_match = re.search(r"\b"+exclusion_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)

        if title_match or abstract_match:

            df.loc[entry_count, "ExcWord Match"] = True

    # If key_authors=True, always keep
    # If there were keyword matches and *no* matches with excluded words, keep
    if df["KeyAuthor Match"][entry_count] == True:
        entries_of_note.append(entry_count)
    elif df["KeyWord Match"][entry_count]==True and df["ExcWord Match"][entry_count]==False:
        entries_of_note.append(entry_count)


progress_bar(len(df), len(df))
print(author_str)
# print("")

# Only keep unique entries (should only matter if there are revised versions)
entries_of_note_unique = np.unique(entries_of_note)

# Open all links if the force-open flag is True
if args.force_open:

    open_links(df, entries_of_note_unique, sleep_opening)

# Else, prompt the user
else:

    # Ask the user if they would like to open the links in the browser
    user_prompt_browser = input(
                               "There are {:} links. Open in the browser? It will take {:} seconds. [y/N]: ".format(len(entries_of_note_unique), len(entries_of_note_unique)/4)
                               ).strip().lower()

    # If they say no to opening in the browser
    if user_prompt_browser != "y":

        # Ask if they would like to save the links to a file or print to the terminal
        user_prompt_output = input(
                                  "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                                  ).strip().lower()
        
        # If they want the output in the terminal
        if user_prompt_output != "y":

            print("Printing all links to the terminal")
            for link_index in entries_of_note_unique:

                print(df.loc[link_index, "url"])

        # If they want to save the output
        else:

            print("Writing all links to the end of the file: {:}".format(cdir+"/all_links.txt"))
            # If the file doesn't exist, create it. Otherwise, append the links to the end
            with open(cdir+"/all_links.txt", "a+", encoding="utf-8") as f:

                for link_index in entries_of_note_unique:

                    link = df.loc[link_index, "url"]
                    
                    f.write(f"{link}\n")

    # If they say yes to opening in the browser
    else:

        # Open all links
        open_links(df, entries_of_note_unique, sleep_opening)

# Print a summary
print("\nThere were a total of {: >{fill}} papers submitted to the astro-ph list since the previous search".format(total_papers, fill=max_digits))
print("            of these, {: >{fill}} papers were in the categories of interest".format(max_num, fill=max_digits))
print("            of these, {: >{fill}} papers were opened/linked".format(len(entries_of_note_unique), fill=max_digits))

# print("currently not updating the start date for the search")
# Write the current date to a file so for the next run
write_date(catchup, end_date)
