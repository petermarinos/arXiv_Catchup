# README

Tired of reading all the Titles/Abstracts/Author Lists of every paper posted on the arXiv every single day?
Here is the solution!

This script searches the [arXiv](https://arxiv.org/) (within the categories of interest) for **all papers since the previous execution**.
It then performs some basic keyword matching, and opens all papers with matches in the web browser, and/or prints the links to a file and/or terminal.

> [!NOTE]
> Similar projects, such as [this one](https://github.com/TideDra/zotero-arxiv-daily), can send you an email every day. This method can become a chore if missing one or more weeks due to personal or professional circumstances.

## Usage

### Requirements

Four of the required packages are not part of the default python3 standard library: `pylatexenc`, `numpy`, `pandas`, and `yaml`.
Use the included `requirements.txt` file with pip to create an environment.

### Running

The script can be executed from any directory by running:

`$ python3 /path/to/arXiv_Catchup/catchup.py`

For frequent execution, add the following to your bash script:

`alias arxiv='python3 /path/to/arXiv_Catchup/catchup.py'`

The search can then be performed in the CLI from any directory by running:

`$ arxiv`

### CLI Arguments

There are additional arguments that can be used:
- `-f`, `--force-open` skips all confirmation dialogues and opens all links
- `-w`, `--write-to-file` skips all confirmation dialogues and writes all links to a file
- `-n`, `--new-window` opens all links in a new window (does not work on mac)
- `-s`, `--start-date` manually sets the start date for the search
- `-e`, `--end-date` manually sets the end date for the search

If both `-f` and `-w` are passed, then the scipt will do both. If neither are passed, then the script will prompt the user for their preference.
These CLI arguments can be added to the bash alias.

### Auxiliary Files

#### Search Term File

The file `search_terms.yaml` contains all terms that are used in the search.
There are four fields, `Categories`, `Authors`, `Included Words`, and `Excluded Words`.
Examples of the format required for each can be found in the provided file.
- `Categories` defines which arXiv categories are searched over. At least one must be included. The list of possible categories can be found on the [arXiv Category Taxonomy](https://arxiv.org/category_taxonomy) page.
- `Authors` defines which authors to highlight. Use surnames. Every paper with a match will be opened. Do not include accents/special characters/etc..
- `Included Words` defines which words include papers in the results. Every match will be included, unless a word from the exclusion list is also found. At least one must be included.
- `Excluded Words` defines which words exclude papers from the results. Every match blocks a paper from being included, unless one of the authors of interest is found.

Lines starting with `#` are ignored.
Multi-word terms can be used, as can author names with spaces.
If adding acronyms, include their pluralised forms (e.g. SN and SNe or CR and CRs).
If including terms that are frequently displayed with a symbol, include all possibilities (e.g. gamma, ɣ, and γ). 

> [!IMPORTANT]
> If cloning the repo, please add this file to the ignored list via the command `$ git update-index --skip-worktree search_terms.yaml` to prevent your personal search terms updating to the main branch.

##### Notes on Author Names

Accented/special characters and ligatures for author names are handled by the script.
Only include plain ASCII in the `search_terms.yaml` file.

For example, papers with 'López' or 'L{\\'o}pez' written in the author field will have the author name normalised to 'Lopez' by the script, so only the latter should be included in the file.
If unsure on how a special character/LaTeX command is presented in ASCII, run `python3 /path/to/arXiv_Catchup/test_string_norm.py -s "{test}"`, where `{test}` is the author's name with the LaTeX encoding/commands.

For submissions to journals that are more restrictive on special characters, some authors may use a spelling that is different to the ASCII encoding -- for example, an author may choose to write 'ö' as 'oe'.
For these cases it is recommended to include both the normalised ASCII and the alternative spellings in the `search_terms.yaml` file to capture all possibilities.

#### Generated Files

The script creates the file `prev_search.txt`, which contains the date of the previous run in ISO format.
This file is ignored if manually setting the start-date of the search on the CLI.

All links are written to a file `catchup.txt` (if choosing to write to the file). Each arXiv link is written on a new line, and the script will always append the new results to the end of the file.
All links in this file can be opened in a browser by running `python3 /path/to/arXiv_Catchup/open_catchup.py`.

### Daily Mailings

There are no daily listings posted over the weekend or on some USA public holidays.

Weekends are handled by the script, which will raise an error if being executed before the next listing is posted.
The papers posted on the weekend will be caught when run on Monday.

There are also "deferred mailing" days.
These days are chosen ad-hoc, and are days that are important to USAians.
It includes Christmas, their Thanksgiving, and others.

On these days, the search *should* return zero results, and raise an error.
Hence, no papers *should* be missed from the deferred mailing days, as said papers would appear in the next search (not tested).
The next deferred mailing where this can be tested will be on Friday 2026/06/19.

## Acknowledgemeents

Thank you to arXiv for use of its open access interoperability.

We make use of the following packages:
- `pylatexenc` -- [homepage](https://github.com/phfaist/pylatexenc)
- `numpy` -- [homepage](https://numpy.org/citing-numpy/)
- `pandas` -- [homepage](https://pandas.pydata.org)
- `yaml` -- [homepage](https://pyyaml.org/)

## Future Improvements

Using a list of words to exclude can result in some interesting papers not being opened if they include a sentence on their potential application to the wider literature.
However, it reduces the list of papers that need to be checked manually by a significant margin.
Additionally, using a list of key words where there needs to be one match can result in an interesting paper *not* being detected if the authors didn't include one.
Finally, the number of papers that are genuinely interesting each week is very low, but the script still opens on the order of ~100 to be manually checked.

There are two potential solutions.

Ranking system:
- Rate each paper based on what matches were found, the number of matches, etc
- Open papers above some threshold
    - Would need to find appropriate values. Would likely depend on the number of terms in the included/excluded word lists
- Print titles just below the threshold to the terminal for manual checking?

Machine learning module:
- Look in a directory containing `.pdf` files of all the papers the user has found interesting in the past, and use these to train a model
- Run the model on the titles/abstracts of each paper and rate them
- Only open the papers if their rating is above some threshold
