"""Functions that create GUI elements."""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable

# Import non-standard libraries
import customtkinter  # pyright: ignore[reportMissingTypeStubs]

# Define constants
APP_HEIGHT = 750
BUTTON_WIDTH = 180
COL_WIDTH = 220
FRAME_WIDTH = 480
N_COLS = 3
PADDING = 10


def create_app(name: str) -> customtkinter.CTk:
    """Helper function to create the main app/window.

    inputs
    ------
    name : Name of the window.

    returns
    ------
    app : The GUI window object.
    """

    # Define the top-level widget
    app = customtkinter.CTk()

    # Name the window
    app.title(name)

    # Set the window size
    # width = column_widths + column_padding + app padding + scroll-bar width
    app_width = 2 * COL_WIDTH + 2 * 2 * PADDING + 2 * 2 * PADDING + 12
    app.geometry(f"{app_width}x{APP_HEIGHT}")

    # Bring the GUI to the font
    app.lift()
    app.attributes("-topmost", True)

    # Create a grid to place the frame in
    app.grid_rowconfigure(0, weight=1)
    app.grid_columnconfigure(0, weight=1)

    return app


def create_scrollable_frame(app: customtkinter.CTk) -> customtkinter.CTkScrollableFrame:
    """Helper function to create a scrollable-frame element.

    inputs
    ------
    app : The GUI window object.

    returns
    ------
    scroll : A scrollable frame that fills the GUI window.
    """

    # Create the scrollable frame
    scroll = customtkinter.CTkScrollableFrame(
        master=app,
        bg_color="transparent",
        fg_color="transparent",
    )

    # Place in the grid
    scroll.grid(row=0, column=0, pady=0, padx=0, sticky="nsew")

    return scroll


def create_frame(
    master_frame: customtkinter.CTkScrollableFrame,
    frame_text: str | None,
    row_count: int,
) -> customtkinter.CTkFrame:
    """Helper function to create a frame element.

    inputs
    ------
    master_frame : The scrollable frame that this frame will be placed into.
    frame_text : Label to be placed at the top of the frame.
    row_count : The row number within master_frame that this frame should be placed at.

    returns
    ------
    frame : A new frame object.
    """

    # Create the frame
    frame = customtkinter.CTkFrame(master=master_frame, width=FRAME_WIDTH)

    # Place in the grid
    frame.grid(row=row_count, column=0, pady=PADDING, padx=2 * PADDING, sticky="ew")

    # Create three columns
    frame.grid_columnconfigure(0, minsize=COL_WIDTH, weight=0)
    frame.grid_columnconfigure(1, minsize=0, weight=1)  # allow to expand
    frame.grid_columnconfigure(2, minsize=COL_WIDTH, weight=0)

    # Create a label that spans all columns at the top of the frame
    if frame_text:

        # Set the label for the frame
        frame_label = customtkinter.CTkLabel(master=frame, text=frame_text)

        # Place the label in the grid
        frame_label.grid(row=0, columnspan=N_COLS, pady=PADDING, padx=0, sticky="")

    return frame


def create_button(
    frame: customtkinter.CTkFrame,
    text: str,
    row_index: int,
    col_index: int | None,
    command: Callable[[], None],
) -> customtkinter.CTkButton:
    """Helper function to create a button element.

    inputs
    ------
    frame : The frame within which this button will be placed.
    text : The button text.
    row_index : The row number that this button should be placed at.
    col_index : The column number that this button should be placed at, or None to centre in the
                frame.
    command : The function that is called when the button is pressed.

    returns
    ------
    button : The button element.
    """

    # Create the button
    button = customtkinter.CTkButton(
        master=frame,
        width=BUTTON_WIDTH,
        text=text,
        command=command,
    )

    # Place in the grid
    if col_index is None:

        button.grid(row=row_index, columnspan=N_COLS, pady=PADDING, padx=PADDING)

    else:

        button.grid(row=row_index, column=col_index, pady=PADDING, padx=PADDING)

    return button


def create_checkbox(
    frame: customtkinter.CTkFrame,
    text: str,
    row_index: int,
    col_index: int,
    command: Callable[[], None],
) -> customtkinter.CTkCheckBox:
    """Helper function to create a check-box element.

    inputs
    ------
    frame : The frame within which this checkbox will be placed.
    text : The checkbbox text.
    row_index : The row number that this checkbox should be placed at.
    col_index : The column number that this checkbox should be placed at.
    command : The function that is called when the checkbox is interacted with.

    returns
    ------
    checkbox : The checkbox element.
    """

    # Create the checkbox
    checkbox = customtkinter.CTkCheckBox(master=frame, text=text, command=command)

    # Place in the grid
    checkbox.grid(row=row_index, column=col_index, pady=PADDING, padx=PADDING)

    return checkbox


def create_entry(
    frame: customtkinter.CTkFrame,
    variable_text: str,
    placeholder_text: str,
    row_index: int,
    col_index: int,
) -> customtkinter.CTkEntry:
    """Helper function to create a text-entry-field element.

    inputs
    ------
    frame : The frame within which this entry will be placed.
    variable_text : The text that is pre-loaded into the entry field.
    placeholder_text : The text to show if the entry is empty.
    row_index : The row number that this entry should be placed at.
    col_index : The column number that this entry should be placed at.

    returns
    ------
    entry : The entry element.
    """

    # Create the entry field
    entry = customtkinter.CTkEntry(
        master=frame,
        width=COL_WIDTH,
        justify=customtkinter.LEFT,
        textvariable=customtkinter.StringVar(value=variable_text),
        placeholder_text=placeholder_text,
    )

    # Place in the grid
    entry.grid(row=row_index, column=col_index, pady=PADDING, padx=PADDING)

    return entry


def create_progressbar(
    frame: customtkinter.CTkFrame, row_index: int
) -> customtkinter.CTkProgressBar:
    """Helper function to create a progress-bar element.

    inputs
    ------
    frame : The frame within which this progressbar will be placed.
    row_index : The row number that this progressbar should be placed at.

    returns
    ------
    progressbar : The progressbar element.
    """

    # Create the progress bar
    progressbar = customtkinter.CTkProgressBar(master=frame)

    # Place in the grid
    progressbar.grid(row=row_index, columnspan=N_COLS, pady=PADDING, padx=PADDING)

    # Initialise the progress bar to be empty
    progressbar.set(0)

    return progressbar


def create_optionmenu(
    frame: customtkinter.CTkFrame,
    values: list[str],
    row_index: int,
    col_index: int,
) -> customtkinter.CTkOptionMenu:
    """Helper function to create an option-menu element.

    inputs
    ------
    frame : The frame within which this optionmenu will be placed.
    values : A list of the potential options.
    row_index : The row number that this optionmenu should be placed at.
    col_index : The column number that this optionmenu should be placed at.

    returns
    ------
    optionmenu : The optionmenu element.
    """

    # Create the option menu
    optionmenu = customtkinter.CTkOptionMenu(
        frame,
        width=BUTTON_WIDTH,
        values=values,
    )

    # Place in the grid
    optionmenu.grid(row=row_index, column=col_index, pady=PADDING, padx=PADDING)

    return optionmenu
