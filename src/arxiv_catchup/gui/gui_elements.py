"""Functions that create GUI elements"""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

# Import standard libraries
from collections.abc import Callable

# Import non-standard libraries
import customtkinter  # pyright: ignore[reportMissingTypeStubs]


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

    # There are 8 arguments
    # Want this helper function to have the freedom to control these aspects of the button, and to
    #     set them to reasonable default values if the attribute is not passed.
    # Disable pylint for >5 arguments and >5 positional arguments
    # pylint: disable=R0913
    # pylint: disable=R0917

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
    pre_check: bool,
    command: Callable[[], None],
) -> customtkinter.CTkCheckBox:
    """WIP"""

    # There are 6 arguments
    # Want this helper function to have the freedom to control these aspects of the checkbox, and to
    #     set them to the default value.
    # Disable pylint for >5 arguments and >5 positional arguments
    # pylint: disable=R0913
    # pylint: disable=R0917

    checkbox = customtkinter.CTkCheckBox(master=frame, text=text, command=command)
    checkbox.grid(row=row_index, column=col_index, pady=10, padx=10)

    if pre_check:
        checkbox.select()
    else:
        checkbox.deselect()

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
