"""GUI class."""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable
from dataclasses import dataclass
from itertools import cycle
from tkinter import Event
from enum import Enum
import argparse

# Import non-standard libraries
import customtkinter  # pyright: ignore[reportMissingTypeStubs]

# Import project classes
from arxiv_catchup.gui.actions import GuiActions
from arxiv_catchup.config import Config

# Import project functions
from arxiv_catchup.gui.gui_elements import (
    create_app,
    create_button,
    create_checkbox,
    create_entry,
    create_frame,
    create_optionmenu,
    create_progressbar,
    create_scrollable_frame,
)


# Define some small classes. Bounds the expected values and prevents errors within strings.
class ButtonKind(Enum):
    """Define the kinds of buttons created for the GUI."""

    REFRESH = "refresh_config"
    CHECKDATES = "check_dates"
    SEARCHINFO = "search_info"
    DOWNLOAD = "download_papers"
    SCORE = "score_papers"
    FILTER = "filter_papers"
    OPEN = "open_papers"
    WRITE = "write_papers"


class CheckboxKind(Enum):
    """Define the kinds of checkboxes created for the GUI."""

    KEEPTEMP = "keep_temp"
    NEWWINDOW = "new_window"


class EntryKind(Enum):
    """Define the kinds of enties created for the GUI."""

    STARTDATE = "start_date"
    ENDDATE = "end_date"


class FrameKind(Enum):
    """Define the kinds of frames created for the GUI."""

    OPTIONS = "options"
    DATES = "dates"
    SERVER = "server"
    ANALYSIS = "analysis"
    RESULTS = "results"


class OptionmenuKind(Enum):
    """Define the kinds of option menus created for the GUI."""

    SCORE = "score_options"
    FILTER = "filter_options"
    WRITESTYLE = "write_style"


class OptionsScoreKind(Enum):
    """Define the valid options that can be placed in the score-option menus."""

    MATCHES = "Score via Matches"
    ML = "Score via ML"


class OptionsFilterKind(Enum):
    """Define the valid options that can be placed in the filter-option menus."""

    SCORE = "Filter via Score"
    MATCHES = "Filter via Matches"


class OptionsWriteKind(Enum):
    """Define the valid options that can be placed in the write-option menus."""

    LINKS = "Links"
    IDS = "ID Numbers"
    OTHER = "hflksjdfsljdf"


class ProgressbarKind(Enum):
    """Define the kinds of progress bars created for the GUI."""

    DOWNLOAD = "download"
    RESULTS = "results"


@dataclass
class Spinner:
    """Holds the spinner."""

    CYCLER = cycle(["-", "\\", "|", "/"])

    is_spinning: bool = False
    spin_id: str = ""


class GUI:
    """Creates and controls the GUI."""

    # Most methods/attributes are protected and should not be accessed outside of this class

    # There are two popular ways to create the GUI:
    #     1) store each element type (frame, button, etc.) in their own dictionary
    #     2) store each frame and all elements within in a dataclass
    # Currently using (1). While it is not as clean, it simplifies the disabling/enabling of
    #     buttons (which occurs often in this GUI)
    # Hence, there are six element types
    # Plus actions, app, scroll, and spinner
    # => 10 attributes
    # Disable pylint warning for >7 attributes
    # pylint: disable=R0902

    def __init__(
        self,
        args: argparse.Namespace,
        search_params: Config,
        actions: GuiActions,
    ) -> None:
        """Create the GUI."""

        # Create the spinner
        self._spinner = Spinner()

        # Input callables
        self._actions = actions

        # GUI Elements
        self._frames: dict[FrameKind, customtkinter.CTkFrame] = {}
        self._buttons: dict[ButtonKind, customtkinter.CTkButton] = {}
        self._checkboxes: dict[CheckboxKind, customtkinter.CTkCheckBox] = {}
        self._entries: dict[EntryKind, customtkinter.CTkEntry] = {}
        self._progressbars: dict[ProgressbarKind, customtkinter.CTkProgressBar] = {}
        self._optionmenus: dict[OptionmenuKind, customtkinter.CTkOptionMenu] = {}

        # Set appearance
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")

        # # Create app
        self._app = create_app("arXiv Catchup")

        # # Create scollable frame that all sub-frames will be placed in
        self._scroll = create_scrollable_frame(self._app)

        # # Config
        # self.frame_config = create_frame(self.scroll, "Config", len(self._frames.items()))
        # self.tabview_config = customtkinter.CTkTabview(
        #     master=self.frame_config, width=460
        # )
        # self.tabview_config.grid(row=1, columnspan=3, pady=10, padx=10)
        # self.tabview_config.add("Authors")
        # self.tabview_config.add("Included Words")
        # self.tabview_config.add("Excluded Words")

        # # Options
        self._frames[FrameKind.OPTIONS] = create_frame(
            self._scroll, None, len(self._frames.items())
        )

        self._checkboxes[CheckboxKind.KEEPTEMP] = create_checkbox(
            self._frames[FrameKind.OPTIONS],
            "Keep Temporary Files",
            1,
            0,
            self._actions.on_toggle_keep_temp,
        )
        if args.keep_temp:
            self._checkboxes[CheckboxKind.KEEPTEMP].select()

        self._buttons[ButtonKind.REFRESH] = create_button(
            self._frames[FrameKind.OPTIONS],
            "Refresh Search Pars.",
            1,
            2,
            self._actions.on_refresh,
        )

        # # Dates
        self._frames[FrameKind.DATES] = create_frame(
            self._scroll, "Date Setup", len(self._frames.items())
        )

        self._entries[EntryKind.STARTDATE] = create_entry(
            self._frames[FrameKind.DATES],
            search_params.start_date.isoformat(),
            "Search Start Date (YYYY-mm-dd)",
            1,
            0,
        )

        self._entries[EntryKind.ENDDATE] = create_entry(
            self._frames[FrameKind.DATES],
            search_params.end_date.isoformat(),
            "Search End Date (YYYY-mm-dd)",
            1,
            2,
        )
        # Bind tab to switch between the two entries
        self._bind_tab_to_switch_entries()

        self._buttons[ButtonKind.CHECKDATES] = create_button(
            self._frames[FrameKind.DATES],
            "Check Search Dates",
            3,
            None,
            self._actions.on_check_dates,
        )
        # Bind enter to the check dates button
        self._bind_enter_to_check_dates()

        # # Server
        self._frames[FrameKind.SERVER] = create_frame(
            self._scroll, "arXiv Server Connections", len(self._frames.items())
        )

        self._progressbars[ProgressbarKind.DOWNLOAD] = create_progressbar(
            self._frames[FrameKind.SERVER], 1
        )

        self._buttons[ButtonKind.SEARCHINFO] = create_button(
            self._frames[FrameKind.SERVER],
            "Obtain Search Info",
            2,
            0,
            self._actions.on_search_info,
        )
        self._buttons[ButtonKind.DOWNLOAD] = create_button(
            self._frames[FrameKind.SERVER],
            "Download Papers",
            2,
            2,
            self._actions.on_download,
        )

        # # Filter
        self._frames[FrameKind.ANALYSIS] = create_frame(
            self._scroll, "Corpus Filtering", len(self._frames.items())
        )

        self._buttons[ButtonKind.SCORE] = create_button(
            self._frames[FrameKind.ANALYSIS],
            "Score Papers",
            1,
            0,
            self._actions.on_score,
        )
        self._buttons[ButtonKind.FILTER] = create_button(
            self._frames[FrameKind.ANALYSIS],
            "Filter Papers",
            1,
            2,
            self._actions.on_filter,
        )

        print()
        self._optionmenus[OptionmenuKind.SCORE] = create_optionmenu(
            self._frames[FrameKind.ANALYSIS],
            [sk.value for sk in OptionsScoreKind],
            2,
            0,
        )

        self._optionmenus[OptionmenuKind.FILTER] = create_optionmenu(
            self._frames[FrameKind.ANALYSIS],
            [fk.value for fk in OptionsFilterKind],
            2,
            2,
        )

        # # Results
        self._frames[FrameKind.RESULTS] = create_frame(
            self._scroll, "Results", len(self._frames.items())
        )

        self._buttons[ButtonKind.OPEN] = create_button(
            self._frames[FrameKind.RESULTS],
            "Open Papers",
            2,
            0,
            self._actions.on_open,
        )
        self._buttons[ButtonKind.WRITE] = create_button(
            self._frames[FrameKind.RESULTS],
            "Write to File",
            2,
            2,
            self._actions.on_write,
        )

        self._progressbars[ProgressbarKind.RESULTS] = create_progressbar(
            self._frames[FrameKind.RESULTS], 1
        )

        self._checkboxes[CheckboxKind.NEWWINDOW] = create_checkbox(
            self._frames[FrameKind.RESULTS],
            "Open in New Window",
            3,
            0,
            self._actions.on_toggle_new_window,
        )
        if args.new_window:
            self._checkboxes[CheckboxKind.NEWWINDOW].select()

        self._optionmenus[OptionmenuKind.WRITESTYLE] = create_optionmenu(
            self._frames[FrameKind.RESULTS],
            [wk.value for wk in OptionsWriteKind],
            3,
            2,
        )

    def default_focus(self) -> None:
        """Change focus to the main window."""

        self._app.focus_set()

    def _bind_tab_to_switch_entries(self) -> None:

        def _on_tab_start_to_end(_: Event):

            self._entries[EntryKind.ENDDATE].focus_set()
            self._entries[EntryKind.ENDDATE].selection_clear()
            self._entries[EntryKind.ENDDATE].icursor("end")

            return "break"

        def _on_tab_end_to_start(_: Event):

            self._entries[EntryKind.STARTDATE].focus_set()
            self._entries[EntryKind.STARTDATE].selection_clear()
            self._entries[EntryKind.STARTDATE].icursor("end")

            return "break"

        self._entries[EntryKind.STARTDATE].bind("<Tab>", _on_tab_start_to_end)
        self._entries[EntryKind.ENDDATE].bind("<Tab>", _on_tab_end_to_start)

    def _bind_enter_to_check_dates(self) -> None:

        def _on_enter(_: Event):

            self._actions.on_check_dates()

            return "break"

        self._entries[EntryKind.STARTDATE].bind("<Return>", _on_enter)
        self._entries[EntryKind.ENDDATE].bind("<Return>", _on_enter)

    def get_bool_from_checkbox(self, key: CheckboxKind) -> bool:
        """Extract the date from the entry named 'key'."""

        return bool(self._checkboxes[key].get())

    def get_state_from_optionmenu(self, key: OptionmenuKind) -> str:
        """Obtain the state of an option menu element."""

        value = self._optionmenus[key].get()

        return value

    def update_progress_bar(self, key: ProgressbarKind, fraction: float) -> None:
        """Update the progress bar named 'key'."""

        self._progressbars[key].set(fraction)

    def _tick(self, button: ButtonKind) -> None:
        """Updates the spinner."""

        s = next(self._spinner.CYCLER)

        if button == ButtonKind.SEARCHINFO:
            base_text = "Connecting ... "
        elif button == ButtonKind.DOWNLOAD:
            base_text = "Downloading ... "
        elif button == ButtonKind.OPEN:
            base_text = "Opening ... "
        else:
            base_text = "... "

        self._buttons[button].configure(text=base_text + s)

        if self._spinner.is_spinning:
            self._spinner.spin_id = self.after(500, lambda: self._tick(button))

    def start_spinner(self, button: ButtonKind) -> None:
        """Starts the spinner."""

        self._spinner.is_spinning = True

        self._tick(button)

    def stop_spinner(self, button: ButtonKind) -> None:
        """Clears the spinner."""

        self._spinner.is_spinning = False

        # Cancel the previous call to after() which may be scheduled
        self._app.after_cancel(self._spinner.spin_id)

        # Remove the spinner text
        # If it is the search_info button, the text was completely overwritten
        # Other buttons just had some characters appended
        if button == ButtonKind.SEARCHINFO:
            base_text = "Obtain Search Info"
        elif button == ButtonKind.DOWNLOAD:
            base_text = "Download Papers"
        elif button == ButtonKind.OPEN:
            base_text = "Open Papers"
        else:
            base_text = "..."

        self._buttons[button].configure(text=base_text)

    def get_date_from_entry(self, key: EntryKind) -> str:
        """Extract the date from the entry named 'key'."""

        return self._entries[key].get().strip()

    def checkbox_set_state(self, key: CheckboxKind, state: bool) -> None:
        """Set the state of the checkbox named 'key' to either 'normal' or 'disabled'."""

        if state:
            self._checkboxes[key].configure(state="normal")
        else:
            self._checkboxes[key].configure(state="disabled")

    def all_checkboxes_set_state(self, state: bool) -> None:
        """Set the state of all checkboxes."""

        for key, _ in self._checkboxes.items():

            self.checkbox_set_state(key, state)

    def button_set_state(self, key: ButtonKind, state: bool) -> None:
        """Set the state of the button named 'key' to either 'normal' or 'disabled'."""

        if state:
            self._buttons[key].configure(state="normal")
        else:
            self._buttons[key].configure(state="disabled")

    def all_buttons_set_state(self, state: bool) -> None:
        """Set the state of all buttons."""

        for key, _ in self._buttons.items():

            self.button_set_state(key, state)

    def after(self, ms: int, func: Callable[[], None]) -> str:
        """small wrapper to expose after"""
        return self._app.after(ms, func)

    def run(self) -> None:
        """Run the GUI."""

        self._app.mainloop()
