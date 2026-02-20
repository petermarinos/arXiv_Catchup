# README

Tired of reading all the Titles/Abstracts/Author Lists of every paper posted on the arXiv every single day?

This script searches the [arXiv](https://arxiv.org/) (within the categories of interest) for **all papers since the previous execution**.
It then computes an 'interest' score for every paper based on the search terms you supply, and opens all papers with matches in the web browser, and/or prints the links to a file and/or terminal.

> [!NOTE]
> This project exists to open all unread papers of interest in the browser with minimal user input.
> This behaviour simplifies catching up on the literature after being unable to check the arXiv for one or more weeks due to personal or professional circumstances.
> Similar projects, such as [this one](https://github.com/TideDra/zotero-arxiv-daily), can send you a daily email if you prefer.

> [!IMPORTANT]
> This project is still in development.
> If you encounter any issues or have ideas for improvements, please send me a message or post an issue.

<center>

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![lint: Pylint](https://img.shields.io/badge/lint-pylint-yellowgreen)

</center>

## Usage

### Requirements

Four of the required packages are not part of the default python3 standard library: `numpy`, `pylatexenc`, and `yaml`.
An up-to-date version of `certifi` is also required to connect to the arXiv servers.
Use the included `requirements.txt` file to create an environment.

### Running

The script can be executed from any directory by running:

`$ python3 /path/to/arXiv_Catchup/catchup.py`

For frequent execution, add the following to your bash script:

`alias arxiv='python3 /path/to/arXiv_Catchup/catchup.py'`

The search can then be performed in the CLI from any directory by running:

`$ arxiv`

### CLI Arguments

There are additional arguments that can be used:
- `-h`, `--help` show the help message.
- `-f`, `--force-open` skips all confirmation dialogues and opens all links.
- `-w`, `--write-to-file` skips all confirmation dialogues and writes all links to a file.
- `-n`, `--new-window` opens all links in a new window (does not work on mac).
- `--only-ids` will only write the arXiv ID numbers to a file (instead of the url).
- `-s str`, `--start-date str` manually set the start date for the search.
- `-e str`, `--end-date str` manually set the end date for the search.
- `-v int`, `--verbosity int` set the verbosity level. Default is 3.
    - 0 => Show only critical error messages.
    - 1 => Show the above, and error messages.
    - 2 => Show all the above, and warning messages.
    - 3 => Show all the above, and info messages. Recommended.
    - 4 => Show all the above, and debug messages. Not recommended.

If both `-f` and `-w` are passed, then the script will do both.
If neither are passed, then the script will prompt the user for their preference.
These CLI arguments can be added to the bash alias.

### Auxiliary Files

#### Search Term File

The file `search_terms.yaml` contains all terms that are used in the search.
There are four fields, `Categories`, `Authors`, `Included Words`, and `Excluded Words`.
The `Included Words` and `Excluded Words` are used to compute a score measuring how interesting a paper is.
Examples of the format required for each can be found in the provided file.
- `Categories` defines which arXiv categories are searched over. At least one must be included. The list of possible categories can be found on the [arXiv Category Taxonomy](https://arxiv.org/category_taxonomy) page.
- `Authors` defines which authors to highlight. Most papers with a match will be opened (large author lists slightly reduce the 'interest' score).
- `Included Words` defines which words increase a paper's 'interest' score.
- `Excluded Words` defines which words decrease a paper's 'interest' score.

> [!TIP]
> Lines starting with `#` are ignored.
> Multi-word terms can be used, as can author names with spaces.
> If adding acronyms, include their pluralised forms (e.g. SN and SNe or CR and CRs).
> If including terms that are frequently displayed with a symbol, include all possibilities (e.g. gamma, ɣ, and γ). 

> [!IMPORTANT]
> If cloning the repo, please add this file to the ignored list via the command `$ git update-index --skip-worktree search_terms.yaml` to prevent your personal search terms updating to the main branch.

##### Notes on Author Names

The script will search for all matches between the names found in the `search_terms.yaml` file and the author list for all found papers.
Include as much information as possible for each author, including the surname at a minimum.
Papers with author lists that contain more/less information than the input will still be found.
For example, `Andrew Sydney Withiel Thomas` will work to find papers with exact matches, as well as lower-information representations such as: `Andrew S. W. Thomas`, `A. Thomas`, `Thomas`, etc., while excluding authors such as `A. S. Z. Thomas`, etc..
However, if you include only `A. Thomas` in the `search_terms.yaml` file, you will get true positive matches for `Andrew Thomas`, as well as false positives for `Alexander Thomas`, etc..
Note that periods are not rquired after initials in either the `search_terms.yaml` or the authors field of the papers, and initials with no whitespace will automatically be expanded.

Accented/special characters, ligatures, and LaTeX commands for author names are handled by the script.
Feel free to enter any representation you prefer, e.g. 'Lopez', 'López', 'L{\\'o}pez', or 'L\'opez', in the `search_terms.yaml` file.

Some authors may use a spelling that is different to their preference for submissions to journals that are more restrictive on special characters.
For example, an author may write 'ö' as 'oe'.
For these cases it is recommended to include both representations in the `search_terms.yaml` file.

There is currently no support for name particles or prefixes/suffixes.
Do not include them in the `search_terms.yaml` file.
For example, only include `Ludwig Beethoven` if you want matches for `Ludwig van Beethoven`.

#### Generated Files

The script creates the file `prev_search.txt`, which contains the date of the previous run in ISO format.
This file will be used as the starting point for the next search, and is ignored if manually setting the start-date of the search on the CLI.

If choosing to write links/IDs to a file, they will be placed in `catchup.txt`.
Each arXiv link is written on a new line, and the script will always append the new results to the end of the file.
All links in this file can be opened in a browser by running `python3 /path/to/arXiv_Catchup/open_catchup.py`.

During the run there are two `.xml` files that will be created.
These files contain the results of the queries to the arXiv servers.
If some non-recoverable error occurs, these files can be used to restart the search.
After successfully presenting the results, both `.xml` files will be deleted.

All logs will be written to `catchup.log`.

### Daily Mailings

There are no daily listings posted over the weekend or on some USA public holidays.

Weekends are handled by the script, which will raise an error if being executed before the next listing is posted.
The papers posted on the weekend will be caught when run on Monday.

There are also "deferred mailing" days.
These days are ones that are important to USAians and are chosen ad-hoc.
It includes Christmas, their Thanksgiving, and others.

On these days, the search *should* return zero results, and raise an error.
Hence, no papers *should* be missed from the deferred mailing days, as said papers would appear in the next search (not tested).
The next deferred mailing where this can be tested will be on Friday 2026/06/19.

## Acknowledgements

Thank you to arXiv for use of its open access interoperability.

In addition to the python standard library, we make use of the following packages:
- `pylatexenc` - [homepage](https://github.com/phfaist/pylatexenc)
- `numpy` - [homepage](https://numpy.org/citing-numpy/)
- `yaml` - [homepage](https://pyyaml.org/)

## Future Improvements

Add a machine learning module:
- Look in a directory containing `.pdf` files of all the papers the user has found interesting in the past, and use these to train a model.
- Run the model on the titles/abstracts of each paper and rate them.
- Only open the papers if their rating is above some threshold.
