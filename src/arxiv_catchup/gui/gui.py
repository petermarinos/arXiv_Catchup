"""GUI class"""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable

# Import non-standard libraries
import customtkinter  # pyright: ignore[reportMissingTypeStubs]

# Import project classes
from arxiv_catchup.gui.actions import GuiActions
from arxiv_catchup.config import Config


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

    BUTTON_WIDTH = 180

    def __init__(
        self,
        search_params: Config,
        actions: GuiActions,
    ) -> None:
        """Create the GUI."""

        # There are two popular ways to create the GUI:
        #     1) store each element type (frame, button, etc.) in their own dictionary
        #     2) store each frame and all elements within in a dataclass
        # Currently using (1). While it is not as clean, it simplifies the disabling/enabling of
        #     buttons (which occurs often in this GUI)

        # Input callables
        self._actions = actions

        # GUI Elements
        self._frames: dict[str, customtkinter.CTkFrame] = {}
        self._buttons: dict[str, customtkinter.CTkButton] = {}
        self._checkboxes: dict[str, customtkinter.CTkCheckBox] = {}
        self._entries: dict[str, customtkinter.CTkEntry] = {}
        self._progressbars: dict[str, customtkinter.CTkProgressBar] = {}
        self._optionmenus: dict[str, customtkinter.CTkOptionMenu] = {}

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
        self._frames["options"] = self.create_frame(None, 1)

        self._checkboxes["keep_temp"] = create_checkbox(
            self._frames["options"],
            "Keep Temporary Files",
            1,
            0,
            self._actions.on_toggle_keep_temp,
        )

        # # Dates
        self._frames["dates"] = self.create_frame("Date Setup", 2)

        self._entries["start_date"] = create_entry(
            self._frames["dates"],
            search_params.start_date.isoformat(),
            "Search Start Date (YYYY-mm-dd)",
            1,
            0,
        )

        self._entries["end_date"] = create_entry(
            self._frames["dates"],
            search_params.end_date.isoformat(),
            "Search End Date (YYYY-mm-dd)",
            1,
            2,
        )

        self._buttons["check_dates"] = create_button(
            self._frames["dates"],
            self.BUTTON_WIDTH,
            "Check Search Dates",
            3,
            0,
            self._actions.on_check_dates,
            disabled=False,
            col_span=True,
        )

        # # Server
        self._frames["server"] = self.create_frame("arXiv Server Connections", 3)

        self._progressbars["download"] = create_progressbar(self._frames["server"], 1)

        self._buttons["search_info"] = create_button(
            self._frames["server"],
            self.BUTTON_WIDTH,
            "Obtain Search Info",
            2,
            0,
            self._actions.on_search_info,
        )
        self._buttons["download_papers"] = create_button(
            self._frames["server"],
            self.BUTTON_WIDTH,
            "Download Papers",
            2,
            2,
            self._actions.on_download,
        )

        # # Filter
        self._frames["filter"] = self.create_frame("Corpus Filtering", 4)

        self._buttons["score_papers"] = create_button(
            self._frames["filter"],
            self.BUTTON_WIDTH,
            "Score Papers",
            1,
            0,
            self._actions.on_score,
        )
        self._buttons["filter_papers"] = create_button(
            self._frames["filter"],
            self.BUTTON_WIDTH,
            "Filter Papers",
            1,
            2,
            self._actions.on_filter,
        )

        self._optionmenus["score"] = create_optionmenu(
            self._frames["filter"],
            self.BUTTON_WIDTH,
            ["Score via Matches", "Score via ML"],
            2,
            0,
        )

        self._optionmenus["filter"] = create_optionmenu(
            self._frames["filter"],
            self.BUTTON_WIDTH,
            ["Filter via Score", "Filter via Matches"],
            2,
            2,
        )

        # # Results
        self._frames["results"] = self.create_frame("Results", 5)

        self._buttons["open_papers"] = create_button(
            self._frames["results"],
            self.BUTTON_WIDTH,
            "Open Papers",
            2,
            0,
            self._actions.on_open,
        )
        self._buttons["write_papers"] = create_button(
            self._frames["results"],
            self.BUTTON_WIDTH,
            "Write to File",
            2,
            2,
            self._actions.on_write,
        )

        self._progressbars["results"] = create_progressbar(self._frames["results"], 1)

        self._checkboxes["new_window"] = create_checkbox(
            self._frames["results"],
            "Open in New Window",
            3,
            0,
            self._actions.on_toggle_new_window,
        )

        self._optionmenus["write_style"] = create_optionmenu(
            self._frames["results"],
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

    def get_bool_from_checkbox(self, key: str) -> bool:
        """Extract the date from the entry named 'key'."""

        return bool(self._checkboxes[key].get())

    def get_state_from_optionmenu(self, key: str) -> str:
        """Obtain the state of an option menu element."""

        value = self._optionmenus[key].get()

        return value

    def update_progress_bar(self, key: str, fraction: float) -> None:
        """Update the progress bar named 'key'."""

        self._progressbars[key].set(fraction)

    def get_date_from_entry(self, key: str) -> str:
        """Extract the date from the entry named 'key'."""

        return self._entries[key].get().strip()

    def button_set_state(self, key: str, state: bool) -> None:
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
