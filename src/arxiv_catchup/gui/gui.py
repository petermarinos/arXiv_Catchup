"""GUI class."""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable
from dataclasses import dataclass
from itertools import cycle
from tkinter import Event
from typing import Literal
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


ActionName = Literal[
    "on_refresh",
    "on_check_dates",
    "on_search_info",
    "on_download",
    "on_score",
    "on_filter",
    "on_open",
    "on_write",
    "on_toggle_keep_temp",
    "on_toggle_new_window",
]


# Define classes for each type of element. Each GUI element has two classes:
# 1) Small dataclass to define the parameters required to create the element
# 2) Dataclass to define all elements of that type


@dataclass(frozen=True)
class FrameSpec:
    """Defines all the parameters required to create a frame."""

    name: str
    text: str | None
    pos: int


class FrameKind(Enum):
    """Define all frames that will be placed in the GUI."""

    OPTIONS = FrameSpec(name="options", text=None, pos=0)
    DATES = FrameSpec(name="dates", text="Date Setup", pos=1)
    SERVER = FrameSpec(name="server", text="arXiv Server Connections", pos=2)
    ANALYSIS = FrameSpec(name="analysis", text="Corpus Filtering", pos=3)
    RESULTS = FrameSpec(name="results", text="Results", pos=4)


@dataclass(frozen=True)
class ButtonSpec:
    """Defines all parameters required to create and place a button."""

    frame: FrameKind
    name: str
    text: str
    row: int
    col: int | None
    action: ActionName


class ButtonKind(Enum):
    """Define all buttons that will placed in the GUI."""

    REFRESH = ButtonSpec(
        frame=FrameKind.OPTIONS,
        name="refresh_config",
        text="Refresh Search Pars.",
        row=1,
        col=2,
        action="on_refresh",
    )
    CHECKDATES = ButtonSpec(
        frame=FrameKind.DATES,
        name="check_dates",
        text="Check Search Dates",
        row=3,
        col=None,
        action="on_check_dates",
    )
    SEARCHINFO = ButtonSpec(
        frame=FrameKind.SERVER,
        name="search_info",
        text="Obtain Search Info",
        row=2,
        col=0,
        action="on_search_info",
    )
    DOWNLOAD = ButtonSpec(
        frame=FrameKind.SERVER,
        name="download_papers",
        text="Download Papers",
        row=2,
        col=2,
        action="on_download",
    )
    SCORE = ButtonSpec(
        frame=FrameKind.ANALYSIS,
        name="score_papers",
        text="Score Papers",
        row=1,
        col=0,
        action="on_score",
    )
    FILTER = ButtonSpec(
        frame=FrameKind.ANALYSIS,
        name="filter_papers",
        text="Filter Papers",
        row=1,
        col=2,
        action="on_filter",
    )
    OPEN = ButtonSpec(
        frame=FrameKind.RESULTS,
        name="open_papers",
        text="Open Papers",
        row=2,
        col=0,
        action="on_open",
    )
    WRITE = ButtonSpec(
        frame=FrameKind.RESULTS,
        name="write_papers",
        text="Write to File",
        row=2,
        col=2,
        action="on_write",
    )


@dataclass(frozen=True)
class CheckboxSpec:
    """Defines all parameters required to create and place a checkbox."""

    frame: FrameKind
    name: str
    text: str
    row: int
    col: int
    action: ActionName


class CheckboxKind(Enum):
    """Define all checkboxes that will be placed in the GUI."""

    KEEPTEMP = CheckboxSpec(
        frame=FrameKind.OPTIONS,
        name="keep_temp",
        text="Keep Temporary Files",
        row=1,
        col=0,
        action="on_toggle_keep_temp",
    )
    NEWWINDOW = CheckboxSpec(
        frame=FrameKind.RESULTS,
        name="new_window",
        text="Open in New Window",
        row=3,
        col=0,
        action="on_toggle_new_window",
    )


@dataclass(frozen=True)
class EntrySpec:
    """Defines all parameters required to create and place a text entry field."""

    frame: FrameKind
    name: str
    vartext: str
    placeholdertext: str
    row: int
    col: int


class EntryKind(Enum):
    """Define all text entry fields that will be placed in the GUI."""

    STARTDATE = EntrySpec(
        frame=FrameKind.DATES,
        name="start_date",
        vartext="start_date",
        placeholdertext="Search Start Date (YYYY-mm-dd)",
        row=1,
        col=0,
    )
    ENDDATE = EntrySpec(
        frame=FrameKind.DATES,
        name="end_date",
        vartext="end_date",
        placeholdertext="Search End Date (YYYY-mm-dd)",
        row=1,
        col=2,
    )


@dataclass(frozen=True)
class OptionmenuSpec:
    """Defines all parameters required to create and place a progress bar."""

    frame: FrameKind
    name: str
    options: list[str]
    row: int
    col: int


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


class OptionmenuKind(Enum):
    """Define all option menus that will be placed in the GUI."""

    SCORE = OptionmenuSpec(
        frame=FrameKind.ANALYSIS,
        name="score_options",
        options=[osk.value for osk in OptionsScoreKind],
        row=2,
        col=0,
    )
    FILTER = OptionmenuSpec(
        frame=FrameKind.ANALYSIS,
        name="filter_options",
        options=[ofk.value for ofk in OptionsFilterKind],
        row=2,
        col=2,
    )
    WRITESTYLE = OptionmenuSpec(
        frame=FrameKind.RESULTS,
        name="write_style",
        options=[owk.value for owk in OptionsWriteKind],
        row=3,
        col=2,
    )


@dataclass(frozen=True)
class ProgressbarSpec:
    """Defines all parameters required to create and place a progress bar."""

    frame: FrameKind
    name: str
    row: int


class ProgressbarKind(Enum):
    """Define all progress bars to be placed in the GUI."""

    DOWNLOAD = ProgressbarSpec(frame=FrameKind.SERVER, name="download", row=1)
    RESULTS = ProgressbarSpec(frame=FrameKind.RESULTS, name="results", row=1)


@dataclass
class Spinner:
    """Holds the spinner state and values."""

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
        """Initialise the GUI and place all elements within.

        inputs
        ------
        args : CLI arguments.
        search_params : Search configuration.
        action : All functions to be performed when elements in the GUI are interacted with.
        """

        # Create the spinner
        self._spinner = Spinner()

        # Extract actions and place in a map
        self._actions = actions
        action_map = {
            "on_refresh": self._actions.on_refresh,
            "on_check_dates": self._actions.on_check_dates,
            "on_search_info": self._actions.on_search_info,
            "on_download": self._actions.on_download,
            "on_score": self._actions.on_score,
            "on_filter": self._actions.on_filter,
            "on_open": self._actions.on_open,
            "on_write": self._actions.on_write,
            "on_toggle_keep_temp": self._actions.on_toggle_keep_temp,
            "on_toggle_new_window": self._actions.on_toggle_new_window,
        }

        # Create a map for the search parameters
        search_param_map = {
            "start_date": search_params.start_date.isoformat(),
            "end_date": search_params.end_date.isoformat(),
        }

        # Define dictionaries to hold each type of element
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

        # Create frames
        for fk in FrameKind:
            self._frames[fk] = create_frame(self._scroll, fk.value.text, fk.value.pos)

        # Create buttons
        for bk in ButtonKind:
            self._buttons[bk] = create_button(
                self._frames[bk.value.frame],
                bk.value.text,
                bk.value.row,
                bk.value.col,
                action_map[bk.value.action],
            )

        # Create checkboxes
        for cbk in CheckboxKind:
            self._checkboxes[cbk] = create_checkbox(
                self._frames[cbk.value.frame],
                cbk.value.text,
                cbk.value.row,
                cbk.value.col,
                action_map[cbk.value.action],
            )

        # Create entries
        for ek in EntryKind:
            self._entries[ek] = create_entry(
                self._frames[ek.value.frame],
                search_param_map[ek.value.vartext],
                ek.value.placeholdertext,
                ek.value.row,
                ek.value.col,
            )

        # Create progressbars
        for pbk in ProgressbarKind:
            self._progressbars[pbk] = create_progressbar(
                self._frames[pbk.value.frame], pbk.value.row
            )

        # Create optionmenus
        for omk in OptionmenuKind:
            self._optionmenus[omk] = create_optionmenu(
                self._frames[omk.value.frame],
                omk.value.options,
                omk.value.row,
                omk.value.col,
            )

        # Check the checkboxes if certain flags were passed
        if args.keep_temp:
            self._checkboxes[CheckboxKind.KEEPTEMP].select()
        if args.new_window:
            self._checkboxes[CheckboxKind.NEWWINDOW].select()

        # Bind keyboard presses to actions
        self._bind_tab_to_switch_entries()
        self._bind_enter_to_check_dates()

    def default_focus(self) -> None:
        """Change focus to the main window."""

        self._app.focus_set()

    def _bind_tab_to_switch_entries(self) -> None:
        """Bind the tab key to switch between the two date entry fields (if either one is in focus),
        placing the cursor at the end."""

        def _on_tab_start_to_end(_: Event):
            """Inner function to switch the focus and place the cursor to the end of the ENDDATE
            Entry.
            """

            self._entries[EntryKind.ENDDATE].focus_set()
            self._entries[EntryKind.ENDDATE].selection_clear()
            self._entries[EntryKind.ENDDATE].icursor("end")

            return "break"

        def _on_tab_end_to_start(_: Event):
            """Inner function to switch the focus and place the cursor to the end of the STARTDATE
            Entry.
            """

            self._entries[EntryKind.STARTDATE].focus_set()
            self._entries[EntryKind.STARTDATE].selection_clear()
            self._entries[EntryKind.STARTDATE].icursor("end")

            return "break"

        # Bind the tab key to switch entry fiels. STARTDATE -> ENDDATE -> STARTDATE
        self._entries[EntryKind.STARTDATE].bind("<Tab>", _on_tab_start_to_end)
        self._entries[EntryKind.ENDDATE].bind("<Tab>", _on_tab_end_to_start)

    def _bind_enter_to_check_dates(self) -> None:
        """Bind the enter/return key to run the 'on_check_dates' button if either date entry fields
        are in focus.
        """

        def _on_enter(_: Event):
            """Inner function to define what should occur if enter is pressed."""

            self._actions.on_check_dates()

            return "break"

        # Bind the enter/return key to run if either of the entries are in focus.
        self._entries[EntryKind.STARTDATE].bind("<Return>", _on_enter)
        self._entries[EntryKind.ENDDATE].bind("<Return>", _on_enter)

    def get_bool_from_checkbox(self, checkbox: CheckboxKind) -> bool:
        """Extract state of the checkbox.

        inputs
        ------
        checkbox : The checkbox to find the state of.

        returns
        -------
        : True if checkbox is checked, otherwise False.
        """

        return bool(self._checkboxes[checkbox].get())

    def get_state_from_optionmenu(self, optionmenu: OptionmenuKind) -> str:
        """Obtain the state of an option menu element.

        inputs
        ------
        optionmenu : The option menu to obtain the state from.

        returns
        -------
        : The option that is currently selected in the menu
        """

        return self._optionmenus[optionmenu].get()

    def update_progress_bar(
        self, progressbar: ProgressbarKind, fraction: float
    ) -> None:
        """Update the progress bar.

        inputs
        ------
        progressbar : The progress bar to update.
        fraction : The fraction the progress bar should be filled to
        """

        self._progressbars[progressbar].set(fraction)

    def _tick(self, button: ButtonKind) -> None:
        """Updates the spinner.

        inputs
        ------
        button : The button that the spinner is being placed on.
        """

        # Obtain the next spinner character from the cycler
        s = next(self._spinner.CYCLER)

        # Obtain the base text for the spinner based on the button
        if button == ButtonKind.SEARCHINFO:

            base_text = "Connecting ... "

        elif button == ButtonKind.DOWNLOAD:

            base_text = "Downloading ... "

        elif button == ButtonKind.OPEN:

            base_text = "Opening ... "

        else:

            raise NotImplementedError(
                "Atempted to add a spinner to a button that shouldn't have one."
            )

        # Update the text to include the spinner
        self._buttons[button].configure(text=base_text + s)

        # If the state of the spinner is True, schedule the next tick.
        if self._spinner.is_spinning:

            self._spinner.spin_id = self.after(500, lambda: self._tick(button))

    def start_spinner(self, button: ButtonKind) -> None:
        """Starts the spinner on the button.

        inputs
        ------
        button : The button to add the spinner to.
        """

        # Set the state of the spinner to True
        self._spinner.is_spinning = True

        # Begin ticking the spinner
        self._tick(button)

    def stop_spinner(self, button: ButtonKind) -> None:
        """Clears the spinner from the button.

        inputs
        ------
        button : The button to remove the spinner from.
        """

        # Set the state of the spinner to False
        self._spinner.is_spinning = False

        # Cancel the previous call to after() which may be scheduled
        self._app.after_cancel(self._spinner.spin_id)

        # Remove the spinner text
        # Replace the text with something new
        if button == ButtonKind.SEARCHINFO:

            base_text = "Obtain Search Info"

        elif button == ButtonKind.DOWNLOAD:

            base_text = "Download Papers"

        elif button == ButtonKind.OPEN:

            base_text = "Open Papers"

        else:

            raise NotImplementedError(
                "Atempted to clear spinner from a button that shouldn't have one."
            )

        self._buttons[button].configure(text=base_text)

    def get_date_from_entry(self, entry: EntryKind) -> str:
        """Extract the date from the entry named.

        inputs
        ------
        entry : The entry to extract the text from.

        returns
        -------
        : The text that was in the entry field.
        """

        return self._entries[entry].get().strip()

    def checkbox_set_state(self, checkbox: CheckboxKind, state: bool) -> None:
        """Set the state of the checkbox named 'key' to either 'normal' or 'disabled'.

        inputs
        ------
        checkbox : The checkbox to set the state of.
        state : True => set state of the checkbox to normal, False => Disable the checkbox.
        """

        if state:
            self._checkboxes[checkbox].configure(state="normal")
        else:
            self._checkboxes[checkbox].configure(state="disabled")

    def all_checkboxes_set_state(self, state: bool) -> None:
        """Set the state of all checkboxes.

        inputs
        ------
        state : True => set state of all checkboxes to normal, False => Disable all checkboxes.
        """

        for key, _ in self._checkboxes.items():

            self.checkbox_set_state(key, state)

    def button_set_state(self, button: ButtonKind, state: bool) -> None:
        """Set the state of the button to either 'normal' or 'disabled'.

        inputs
        ------
        button : The button to set the state of.
        state : True => set state of the button to normal, False => Disable the button.
        """

        if state:
            self._buttons[button].configure(state="normal")
        else:
            self._buttons[button].configure(state="disabled")

    def all_buttons_set_state(self, state: bool) -> None:
        """Set the state of all buttons.

        inputs
        ------
        state : True => set state of all buttons to normal, False => Disable all buttons.
        """

        for key, _ in self._buttons.items():

            self.button_set_state(key, state)

    def after(self, ms: int, func: Callable[[], None]) -> str:
        """Small wrapper to expose after().

        inputs
        ------
        ms : Time to wait before running (in ms)
        func : Function that will be called

        returns
        -------
        : Process ID
        """

        return self._app.after(ms, func)

    def run(self) -> None:
        """Run the GUI."""

        self._app.mainloop()
