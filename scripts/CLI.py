"""CLI class, for interactions with the CLI."""

# fmt: off
# Import classes
from .arxiv_client import ArxivConst
from .corpus       import Corpus

# Import functions
from .utils import cli_args
# fmt: on


class CLI:
    """Deals with all CLI tasks."""

    def __init__(self):  # , cdir: str):

        self.args = cli_args()

    # # Determine how to display the results
    def get_display_method(self, arxiv_const: ArxivConst, corpus: Corpus) -> None:
        """Find the preferred method of displaying the results."""

        # If there is at least one paper, open/prompt
        if len(corpus.papers_of_note) > 0:

            # If both -f and -w are passed, both open and write the links
            if self.args.force_open and self.args.write_to_file:

                self.open_in_brower = True
                self.write_to_file = True

            # If -f is passed and -w is not, only open the links
            elif self.args.force_open and not self.args.write_to_file:

                self.open_in_brower = True
                self.write_to_file = False

            # If -f is not passed and -w is, only write the links
            elif not self.args.force_open and self.args.write_to_file:

                self.open_in_brower = False
                self.write_to_file = True

            # If neither -f nor -w were passed, prompt the user to ask for the behaviour they prefer
            else:

                # Ask the user if they would like to open the links in the browser. Default is no
                print("")
                user_prompt_browser = (
                    input(
                        "There are {:} link(s). Open in the browser? It will take {:} seconds. [y/N]: ".format(
                            len(corpus.papers_of_note),
                            len(corpus.papers_of_note) * arxiv_const.sleep_opening,
                        )
                    )
                    .strip()
                    .lower()
                )

                # If they say yes to opening in the browser
                if user_prompt_browser == "y":

                    self.open_in_brower = True
                    self.write_to_file = False

                # If they say no to opening in the browser
                else:

                    self.open_in_brower = False

                    # Ask if they would like to save the links to a file or print to the terminal. Default is no
                    user_prompt_file = (
                        input(
                            "Save all links to a file? Otherwise they will be written to the terminal. [y/N]: "
                        )
                        .strip()
                        .lower()
                    )

                    # If they want to save the output
                    if user_prompt_file == "y":

                        self.write_to_file = True

                    # If they want the output in the terminal
                    else:

                        self.write_to_file = False

                        print("\nPrinting all links to the terminal:\n")
                        for arxiv_id in corpus.papers_of_note:

                            print(corpus.corpus[arxiv_id].paperInfo.link_abs)
                        print("")

        else:

            # self.logger.warning("No papers of interest were found.")
            self.write_to_file = False
            self.open_in_brower = False
