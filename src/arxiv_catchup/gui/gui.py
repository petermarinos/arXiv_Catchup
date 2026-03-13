"""GUI class"""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable
from enum import Enum

# Import non-standard libraries
import customtkinter  # pyright: ignore[reportMissingTypeStubs]

# Import project classes
from arxiv_catchup.gui.actions import GuiActions
from arxiv_catchup.config import Config


# Define some small classes. Bounds the expected values and prevents errors within strings.
class ButtonKind(Enum):
    """Define the kinds of frames created for the GUI."""

    CHECKDATES = "check_Dates"
    SEARCHINFO = "search_info"
    DOWNLOAD = "download_papers"
    SCORE = "score_papers"
    FILTER = "filter_papers"
    OPEN = "open_papers"
    WRITE = "write_papers"


class CheckboxKind(Enum):
    """Define the kinds of frames created for the GUI."""

    KEEPTEMP = "keep_temp"
    NEWWINDOW = "new_window"


class EntryKind(Enum):
    """Define the kinds of frames created for the GUI."""

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
    """Define the kinds of frames created for the GUI."""

    SCORE = "score_options"
    FILTER = "filter_options"
    WRITESTYLE = "write_style"


class ProgressbarKind(Enum):
    """Define the kinds of frames created for the GUI."""

    DOWNLOAD = "download"
    RESULTS = "results"


# Helper functions
def create_button(
    frame: customtkinter.CTkFrame,
    width: int,
    text: str,
    row_index: int,
    col_index: int,
    command: Callable[[], None],
    disabled: bool = True,
    col_span: bool = False,
) -> customtkinter.CTkButton:
    """WIP"""

    button = customtkinter.CTkButton(
        master=frame,
        width=width,
        text=text,
        command=command,
    )

    if col_span:
        button.grid(row=row_index, columnspan=3, pady=10, padx=10)
    else:
        button.grid(row=row_index, column=col_index, pady=10, padx=10)

    if disabled:
        button.configure(state="disabled")

    return button


def create_checkbox(
    frame: customtkinter.CTkFrame,
    text: str,
    row_index: int,
    col_index: int,
    command: Callable[[], None],
) -> customtkinter.CTkCheckBox:
    """WIP"""

    checkbox = customtkinter.CTkCheckBox(master=frame, text=text, command=command)
    checkbox.grid(row=row_index, column=col_index, pady=10, padx=10)

    return checkbox


def create_entry(
    frame: customtkinter.CTkFrame,
    variable_text: str,
    placeholder_text: str,
    row_index: int,
    col_index: int,
) -> customtkinter.CTkEntry:
    """WIP"""

    entry = customtkinter.CTkEntry(
        master=frame,
        width=220,
        justify=customtkinter.LEFT,
        textvariable=customtkinter.StringVar(value=variable_text),
        placeholder_text=placeholder_text,
    )
    entry.grid(row=row_index, column=col_index, pady=10, padx=10)

    return entry


def create_progressbar(
    frame: customtkinter.CTkFrame, row_index: int
) -> customtkinter.CTkProgressBar:
    """WIP"""

    progressbar = customtkinter.CTkProgressBar(master=frame)
    progressbar.grid(row=row_index, columnspan=3, pady=10, padx=10)
    progressbar.set(0)

    return progressbar


def create_optionmenu(
    frame: customtkinter.CTkFrame,
    width: int,
    values: list[str],
    row_index: int,
    col_index: int,
) -> customtkinter.CTkOptionMenu:
    """WIP"""

    optionmenu = customtkinter.CTkOptionMenu(
        frame,
        width=width,
        values=values,
    )
    optionmenu.grid(row=row_index, column=col_index, pady=10, padx=10)

    return optionmenu


class GUI:
    """Creates and controls the GUI"""

    # There are two popular ways to create the GUI:
    #     1) store each element type (frame, button, etc.) in their own dictionary
    #     2) store each frame and all elements within in a dataclass
    # Currently using (1). While it is not as clean, it simplifies the disabling/enabling of
    #     buttons (which occurs often in this GUI)
    # Hence, there are six element types
    # Plus actions, app, scroll
    # => nine attributes
    # Disable pylint warning for >7 attributes
    # pylint: disable=R0902

    BUTTON_WIDTH = 180

    def __init__(
        self,
        search_params: Config,
        actions: GuiActions,
    ) -> None:
        """Create the GUI."""

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

        # Define the top-level widget
        self._app = customtkinter.CTk()

        # Name the window
        self._app.title("arXiv Catchup")

        # Set the window size
        # Cheapest displays as of 2026 have resolutions of 1360 x 768
        # Set the window height to be smaller than the smallest displays
        # TO-DO: check if this still be visible on large displays. Introduce scaling?
        # Current width:
        #     column_widths + column_padding + app padding + scroll_width
        #     2*220         + 2*2*10         + 2*20        + 20
        self._app.geometry("540x760")

        # Bring the GUI to the font
        self._app.lift()
        self._app.attributes("-topmost", True)

        # Create a scollable interface
        self._app.grid_rowconfigure(0, weight=1)
        self._app.grid_columnconfigure(0, weight=1)
        self._scroll = customtkinter.CTkScrollableFrame(
            master=self._app,
            bg_color="transparent",
            fg_color="transparent",
        )
        self._scroll.grid(row=0, column=0, pady=0, padx=0, sticky="nsew")

        # # Create interface

        # # Config
        # self.frame_config = create_frame(self.scroll, "Config", 0)
        # self.tabview_config = customtkinter.CTkTabview(
        #     master=self.frame_config, width=460
        # )
        # self.tabview_config.grid(row=1, columnspan=3, pady=10, padx=10)
        # self.tabview_config.add("Authors")
        # self.tabview_config.add("Included Words")
        # self.tabview_config.add("Excluded Words")

        # # Options
        self._frames[FrameKind.OPTIONS] = self.create_frame(None, 1)

        self._checkboxes[CheckboxKind.KEEPTEMP] = create_checkbox(
            self._frames[FrameKind.OPTIONS],
            "Keep Temporary Files",
            1,
            0,
            self._actions.on_toggle_keep_temp,
        )

        # # Dates
        self._frames[FrameKind.DATES] = self.create_frame("Date Setup", 2)

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

        self._buttons[ButtonKind.CHECKDATES] = create_button(
            self._frames[FrameKind.DATES],
            self.BUTTON_WIDTH,
            "Check Search Dates",
            3,
            0,
            self._actions.on_check_dates,
            disabled=False,
            col_span=True,
        )

        # # Server
        self._frames[FrameKind.SERVER] = self.create_frame(
            "arXiv Server Connections", 3
        )

        self._progressbars[ProgressbarKind.DOWNLOAD] = create_progressbar(
            self._frames[FrameKind.SERVER], 1
        )

        self._buttons[ButtonKind.SEARCHINFO] = create_button(
            self._frames[FrameKind.SERVER],
            self.BUTTON_WIDTH,
            "Obtain Search Info",
            2,
            0,
            self._actions.on_search_info,
        )
        self._buttons[ButtonKind.DOWNLOAD] = create_button(
            self._frames[FrameKind.SERVER],
            self.BUTTON_WIDTH,
            "Download Papers",
            2,
            2,
            self._actions.on_download,
        )

        # # Filter
        self._frames[FrameKind.ANALYSIS] = self.create_frame("Corpus Filtering", 4)

        self._buttons[ButtonKind.SCORE] = create_button(
            self._frames[FrameKind.ANALYSIS],
            self.BUTTON_WIDTH,
            "Score Papers",
            1,
            0,
            self._actions.on_score,
        )
        self._buttons[ButtonKind.FILTER] = create_button(
            self._frames[FrameKind.ANALYSIS],
            self.BUTTON_WIDTH,
            "Filter Papers",
            1,
            2,
            self._actions.on_filter,
        )

        self._optionmenus[OptionmenuKind.SCORE] = create_optionmenu(
            self._frames[FrameKind.ANALYSIS],
            self.BUTTON_WIDTH,
            ["Score via Matches", "Score via ML"],
            2,
            0,
        )

        self._optionmenus[OptionmenuKind.FILTER] = create_optionmenu(
            self._frames[FrameKind.ANALYSIS],
            self.BUTTON_WIDTH,
            ["Filter via Score", "Filter via Matches"],
            2,
            2,
        )

        # # Results
        self._frames[FrameKind.RESULTS] = self.create_frame("Results", 5)

        self._buttons[ButtonKind.OPEN] = create_button(
            self._frames[FrameKind.RESULTS],
            self.BUTTON_WIDTH,
            "Open Papers",
            2,
            0,
            self._actions.on_open,
        )
        self._buttons[ButtonKind.WRITE] = create_button(
            self._frames[FrameKind.RESULTS],
            self.BUTTON_WIDTH,
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

        self._optionmenus[OptionmenuKind.WRITESTYLE] = create_optionmenu(
            self._frames[FrameKind.RESULTS],
            self.BUTTON_WIDTH,
            ["Links", "ID Numbers"],
            3,
            2,
        )

    def create_frame(
        self,
        frame_text: str | None,
        row_count: int,
    ) -> customtkinter.CTkFrame:
        """WIP"""

        # Create the frame
        frame = customtkinter.CTkFrame(master=self._scroll, width=480)
        frame.grid(row=row_count, column=0, pady=10, padx=20, sticky="ew")

        # Set three columns
        frame.grid_columnconfigure(0, minsize=220, weight=0)
        frame.grid_columnconfigure(1, minsize=0, weight=1)
        frame.grid_columnconfigure(2, minsize=220, weight=0)

        # Create a label that spans all columns at the top of the frame
        if frame_text:
            frame_label = customtkinter.CTkLabel(master=frame, text=frame_text)
            frame_label.grid(row=0, columnspan=3, pady=10, padx=0, sticky="")

        return frame

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

    def get_date_from_entry(self, key: EntryKind) -> str:
        """Extract the date from the entry named 'key'."""

        return self._entries[key].get().strip()

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

    def after(self, ms: int, func: Callable[[], None]) -> None:
        """small wrapper to expose after"""
        self._app.after(ms, func)

    def run(self) -> None:
        """Run the GUI."""

        self._app.mainloop()
