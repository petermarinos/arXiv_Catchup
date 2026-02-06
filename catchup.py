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
import yaml
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
# If there are more papers then random slowdowns when connecting to the arXiv servers will make any remaining time estimate inaccurate.

def load_searchterms(filename):

    # Load the .yaml into a dictionary
    with open(filename, 'r') as f:

        search_terms = yaml.safe_load(f)

    # # Check the file

    # At least one category is required
    if search_terms["Categories"] is None:

        raise ValueError("No search terms were found in the 'Categories' entry in the configuration file.\n            Please check the file and add at least one item")

    # If a category with a wildcard (e.g. astro-ph*) is entered with other matching sub-categories (e.g. astro-ph.HE), the API will ignore the sub-categories
    # No need to catch it here

    # At least one search term is required in the "Words" key
    if search_terms["Included Words"] is None:

        raise ValueError("No search terms were found in the 'Included Words' entry in the configuration file.\n            Please check the file and add at least one item")

    # No search terms are required for the "Authors" or "Excluded Words" keys
    # Warn the user if no terms are found
    if search_terms["Authors"] is None:

        print("WARNING: No search terms were found in the 'Authors' entry in the configuration file.")

    if search_terms["Excluded Words"] is None:

        print("WARNING: No search terms were found in the 'Excluded Words' entry in the configuration file.")

    return search_terms

def LaTeX_to_unicode(s):
    """Stip LaTeX-style accents from the string (e.g. {\'a} -> a, and \'a -> a)

    This function only covers common accents.
    To account for all accents and ligatures/special characters, it is best to install an additional package.
    However, that would only be required if one of the Authors has a special character/accent.
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

    with open(filename, "w") as f:
        f.write(date.isoformat())

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
    """Return the datetime of the most recent arXiv daily list posting relative to the input time `now`.
    """

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
    """Return the datetime of the next arXiv daily list posting relative to the input time `now`.
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

def parse_date(date_str, name, search_time):
    try:
        raw_datetime = datetime.datetime.combine(datetime.datetime.strptime(date_str, "%Y-%m-%d"), search_time)
        parsed_date = raw_datetime.date()
        parsed_time = raw_datetime.timetz()
        return parsed_time, parsed_date
    except ValueError:
        raise ValueError(f"{name} must be in YYYY-MM-DD format")

def write_links(filename, df, entries):

    print("Writing all links to the end of the file: {:}".format(filename))

    with open(filename, "a+", encoding="utf-8") as f:

        for link_index in entries:

            link = df.loc[link_index, "url"]
            
            f.write(f"{link}\n")

    return

# Parse command-line arguments
parser = argparse.ArgumentParser(prog='arXiv Catchup',
                                 description='Search arXiv for papers matching your criteria')

parser.add_argument('-f', '--force-open', action='store_true',
                    help='Skip the warning about how many papers will be opened.')
parser.add_argument('-w', '--write-to-file', action='store_true',
                    help='Skip opening links and user prompts, writing all links straight to a file.')
parser.add_argument('-n', '--new-window', action='store_true',
                    help='Open all papers in a single new browser window as tabs.') # Doesn't work on mac with firefox
parser.add_argument('-s', '--start-date', type=str,
                    help='Set the start time for the search, YYYY-MM-DD (19:00 UTC)\nIgnores the date in the `prev_search.txt`.')
parser.add_argument('-e', '--end-date', type=str,
                    help='Set the end time for the search, YYYY-MM-DD (19:00 UTC).')

args = parser.parse_args()

# Find the directory of the script
cdir = os.path.dirname(os.path.realpath(__file__))

# Define filenames of the auxiliary files
filename_prevsearch  = cdir+"/prev_search.txt" # File that stores the date of the previous run
filename_searchterms = cdir+"/search_terms.yaml" # File that stores the search terms
filename_paperlinks  = cdir+"/catchup.txt" # File that stores the links to the papers of interest (if writing to a file)

# Load search terms from the auxiliary file
search_terms = load_searchterms(filename_searchterms)

# Define string for use in the url search
cat_urlstring = "+OR+".join(f"cat:{c}" for c in search_terms["Categories"])
# Define string for printing to the terminal
cat_printstring = ", ".join(f"{c}" for c in search_terms["Categories"])

# Compute the length of the longest name in the authors array
# Makes one of the terminal outputs prettier
if search_terms["Authors"] is not None:
    author_strfill = len(max(search_terms["Authors"], key=len))

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

# If start/end dates were passed on the command line, use them. Otherwise, set to None
start_time, start_date = parse_date(args.start_date, "start-date", search_time) if args.start_date else [None, None]
end_time,   end_date   = parse_date(args.end_date,   "end-date", search_time)   if args.end_date   else [None, None]

# Compute the time at the end of the search
# Only perform if the end_date was not passed in the command line
if end_date is None:
    end_time = calc_search_endtime(current_time, list_post_time, search_time)
    end_date = end_time.date()

# The date of the previous execution is saved in a file
# If the file does not exist, create it and set the date to the listing before the last posting
# Only perform if the start_date was not passed in the command line
if start_date is None:
    if not os.path.exists(filename_prevsearch):

        # Compute the list time before the previous
        # This can be done by passing the end_time found above into the calc_search_endtime() function
        prev_end_time  = calc_search_endtime(end_time, list_post_time, search_time)
        
        write_date(filename_prevsearch, prev_end_time.date())

    # Load it and extract the previous runtime
    with open(filename_prevsearch, "r", encoding="utf-8") as f:

        start_time, start_date = parse_date(next(f), filename_prevsearch, search_time)

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
# The maximum number of papers that can be downloaded per search is 2000
sleep_search    = 3
interval_search = 10
sleep_opening   = 0.25

print("Obtaining arXiv info. Estimated time: {:d} seconds".format(sleep_search)) # Always a single sleep

progress_bar(0, 1, 3)

# Perform a search over all astro-ph categories to find how many papers were posted since the previous search
# This should be the top-category(ies) for the cats. included in the .yaml.
# i.e. astro-ph* for astro-ph.subcats, cs* for sc.subcats
# The only reason to do this is to see how many papers were published within the given subfield.
# As this is not particularly meaningful, it is skipped.
# formatted_url_allcat = url.format(start_year  = start_date.year,
#                                   start_month = start_date.month,
#                                   start_day   = start_date.day,
#                                   end_year    = end_date.year,
#                                   end_month   = end_date.month,
#                                   end_day     = end_date.day,
#                                   cats        = "cat:astro-ph*",
#                                   start_num   = 0,
#                                   end_num     = 1)

# # First request
# parsed_xml_data_allcat = download_search(formatted_url_allcat)

# # Extract the number of papers since the last time the script was executed
# total_papers = int(parsed_xml_data_allcat.find("opensearch:totalResults", ns).text)
# # Compute the number of digits. Assumes that the number of papers is positive :)
# max_digits = len(str(total_papers))

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

# progress_bar(1, 2, 3)
# # Second request. Sleep for 3s
# time.sleep(sleep_search)
parsed_xml_data_initial = download_search(formatted_url_initial)

progress_bar(1, 1)
print("")

# Extract the number of papers since the last time the script was executed
max_num = int(parsed_xml_data_initial.find("opensearch:totalResults", ns).text)

# Compute the number of digits. Assumes that the number of papers is positive :)
max_digits = len(str(max_num))

# The arXiv API will likely return an error in the first search
if max_num >= 30000:
    raise ValueError("Number of papers is too large. Refine search dates and/or categories.")

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
            "Author Match"    : False,
            "IncWord Match"   : False,
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
    
    # Search all author lists for the key authors
    if search_terms["Authors"] is not None:
        for author in search_terms["Authors"]:

            # Search the author field in the entry
            author_match = re.search(r"\b"+author+r"\b", df["Authors"][entry_count])

            if author_match:
                
                # Set the entry in the dataframe for the author match to True
                df.loc[entry_count, "Author Match"] = True

                # If one author is found, output an extra line to the terminal
                if author_match_count == 0:
                    # print("    Found Author(s)")
                    author_str += "\n    Found Author(s)"
                    author_match_count = 1
                    
                # print("    {: >{fill}}:  ".format(key_author, fill=author_strfill), df["url"][entry_count])
                author_str += "\n    {: >{fill}}:  {url:}".format(author, fill=author_strfill, url=df["url"][entry_count])
    
    # Search all titles and abstracts for words that I care about
    for inc_word in search_terms["Included Words"]:

        # Search the author field in the entry
        title_match    = re.search(r"\b"+inc_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

        if df["Abstract"][entry_count] is not None: # Skip empty abstract entries
            abstract_match = re.search(r"\b"+inc_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)
            
        if title_match or abstract_match:
            
            df.loc[entry_count, "IncWord Match"] = True
    
    # Search all titles and abstracts for words that I want to exclude
    if search_terms["Excluded Words"] is not None:
        for exc_word in search_terms["Excluded Words"]:

            # Search the author field in the entry
            title_match    = re.search(r"\b"+exc_word+r"\b", df["Title"][entry_count], re.IGNORECASE)

            if df["Abstract"][entry_count] is not None: # Skip empty abstract entries

                abstract_match = re.search(r"\b"+exc_word+r"\b", df["Abstract"][entry_count], re.IGNORECASE)

            if title_match or abstract_match:

                df.loc[entry_count, "ExcWord Match"] = True

    # If key_authors=True, always keep
    # If there were keyword matches and *no* matches with excluded words, keep
    if df["Author Match"][entry_count] == True:
        entries_of_note.append(entry_count)
    elif df["IncWord Match"][entry_count]==True and df["ExcWord Match"][entry_count]==False:
        entries_of_note.append(entry_count)

progress_bar(len(df), len(df))
print(author_str)
# print("")

# Only keep unique entries (should only matter if there are revised versions)
entries_of_note_unique = np.unique(entries_of_note)

# If there is at least one paper, open/prompt
if len(entries_of_note_unique) > 0:

    # If -f and -w are passed, both open and write the links
    if args.force_open and args.write_to_file:

        open_links(df, entries_of_note_unique, sleep_opening)
        write_links(filename_paperlinks, df, entries_of_note_unique)

    # If -f is passed and -w is not, only open the links
    elif args.force_open and not args.write_to_file:

        open_links(df, entries_of_note_unique, sleep_opening)

    # If if is not passed and -w is, only write the links
    elif not args.force_open and args.write_to_file:

        write_links(filename_paperlinks, df, entries_of_note_unique)

    # Else, if neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
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

                # If the file doesn't exist, create it. Otherwise, append the links to the end
                write_links(filename_paperlinks, df, entries_of_note_unique)

        # If they say yes to opening in the browser
        else:

            # Open all links
            open_links(df, entries_of_note_unique, sleep_opening)

else:

    print("No papers of interest were found.")

# Print a summary
# print("\nThere were a total of {: >{fill}} papers submitted to the astro-ph list since the previous search".format(total_papers, fill=max_digits))
# print("            of these, {: >{fill}} papers were in the categories of interest ".format(max_num, fill=max_digits))
print("\nThere was a total of {: >{fill}} papers submitted to the categories of interest since the previous search".format(max_num, fill=max_digits))
print("             of these, {: >{fill}} papers were opened/linked".format(len(entries_of_note_unique), fill=max_digits))

# print("TESTING so not updating the start date for the search")

# Check if any papers were found
if len(df) == 0:

    print("As no papers were found, the aux. date file was not updated")

# If papers were found, update the aux. file
else:

    # Write the end date of the search to a file for the next run
    write_date(filename_prevsearch, end_date)
