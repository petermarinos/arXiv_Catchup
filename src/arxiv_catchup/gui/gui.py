"""GUI class"""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

import customtkinter  # pyright: ignore[reportMissingTypeStubs]


# Helper functions
def create_frame(
    app: customtkinter.CTk | customtkinter.CTkScrollableFrame,
    frame_text: str,
    row_count: int,
) -> customtkinter.CTkFrame:
    """WIP"""

    # Create the frame
    frame = customtkinter.CTkFrame(master=app, width=480)
    frame.grid(row=row_count, column=0, pady=10, padx=20, sticky="ew")

    # Set three columns
    frame.grid_columnconfigure(0, minsize=220, weight=0)
    frame.grid_columnconfigure(1, minsize=0, weight=1)
    frame.grid_columnconfigure(2, minsize=220, weight=0)

    # Create a label that spans all columns at the top of the frame
    frame_label = customtkinter.CTkLabel(master=frame, text=frame_text)
    frame_label.grid(row=0, columnspan=3, pady=10, padx=0, sticky="")

    return frame


class GUI:
    """Creates and controls the GUI"""

    BUTTON_WIDTH = 180

    def __init__(self) -> None:
        """Create the GUI."""

        # Set appearance
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("dark-blue")

        # Define the top-level widget
        self.app = customtkinter.CTk()

        # Name the window
        self.app.title("arXiv Catchup")

        # Set the window size
        # Cheapest displays as of 2026 have resolutions of 1360 x 768
        # Set the window height to be smaller than the smallest displays
        # TO-DO: check if this still be visible on large displays. Introduce scaling?
        # Current width:
        #     column_widths + column_padding + app padding + scroll_width
        #     2*220         + 2*2*10         + 2*20        + 20
        self.app.geometry("540x760")

        # Bring the GUI to the font
        self.app.lift()
        self.app.attributes("-topmost", True)

        # Create a scollable interface
        self.app.grid_rowconfigure(0, weight=1)
        self.app.grid_columnconfigure(0, weight=1)
        self.scroll = customtkinter.CTkScrollableFrame(
            master=self.app,
            bg_color="transparent",
            fg_color="transparent",
        )
        self.scroll.grid(row=0, column=0, pady=0, padx=0, sticky="nsew")

        # # Create interface

        # Create the frames
        # self.frame_config = create_frame(self.scroll, "Config", 0)
        self.frame_options = create_frame(self.scroll, "Options", 1)
        self.frame_dates = create_frame(self.scroll, "Date Setup", 2)
        self.frame_server = create_frame(self.scroll, "arXiv Server Connections", 3)
        self.frame_filter = create_frame(self.scroll, "Corpus Filtering", 4)
        self.frame_results = create_frame(self.scroll, "Results", 5)

        # # Add elements to config
        # self.tabview_config = customtkinter.CTkTabview(
        #     master=self.frame_config, width=460
        # )
        # self.tabview_config.grid(row=1, columnspan=3, pady=10, padx=10)
        # self.tabview_config.add("Authors")
        # self.tabview_config.add("Included Words")
        # self.tabview_config.add("Excluded Words")

        # Add elements to options
        self.checkbox_tempfiles = customtkinter.CTkCheckBox(
            master=self.frame_options, text="Keep Temporary Files"
        )
        self.checkbox_tempfiles.grid(row=1, column=0, pady=10, padx=10)

        # Add elements to dates
        self.entry_start_date = customtkinter.CTkEntry(
            master=self.frame_dates,
            width=220,
            justify=customtkinter.LEFT,
            placeholder_text="Search Start Date (YYYY-mm-dd)",
        )
        self.entry_start_date.grid(row=1, column=0, pady=10, padx=10)

        self.entry_end_date = customtkinter.CTkEntry(
            master=self.frame_dates,
            width=220,
            justify=customtkinter.LEFT,
            placeholder_text="Search End Date (YYYY-mm-dd)",
        )
        self.entry_end_date.grid(row=1, column=2, pady=10, padx=10)

        # Add elements to server
        self.progressbar_download = customtkinter.CTkProgressBar(
            master=self.frame_server
        )
        self.progressbar_download.grid(row=1, columnspan=3, pady=10, padx=10)
        self.progressbar_download.set(0)

        self.button_search_info = customtkinter.CTkButton(
            master=self.frame_server,
            width=self.BUTTON_WIDTH,
            text="Obtain Search Info",
        )
        self.button_search_info.grid(row=2, column=0, pady=10, padx=10)

        self.button_download_papers = customtkinter.CTkButton(
            master=self.frame_server,
            width=self.BUTTON_WIDTH,
            text="Download Papers",
        )
        self.button_download_papers.grid(row=2, column=2, pady=10, padx=10)

        # Add elements to filter
        self.button_score = customtkinter.CTkButton(
            master=self.frame_filter,
            width=self.BUTTON_WIDTH,
            text="Score Papers",
        )
        self.button_score.grid(row=1, column=0, pady=10, padx=10)

        self.optionmenu_score = customtkinter.CTkOptionMenu(
            self.frame_filter,
            width=self.BUTTON_WIDTH,
            values=["Score via Matches", "Score via ML"],
        )
        self.optionmenu_score.grid(row=2, column=0, pady=10, padx=10)

        self.button_filter = customtkinter.CTkButton(
            master=self.frame_filter,
            width=self.BUTTON_WIDTH,
            text="Filter papers",
        )
        self.button_filter.grid(row=1, column=2, pady=10, padx=10)

        self.optionmenu_filter = customtkinter.CTkOptionMenu(
            self.frame_filter,
            width=self.BUTTON_WIDTH,
            values=["Filter via Score", "Filter via Matches"],
        )
        self.optionmenu_filter.grid(row=2, column=2, pady=10, padx=10)

        # Add elements to results
        self.progressbar_results = customtkinter.CTkProgressBar(
            master=self.frame_results
        )
        self.progressbar_results.grid(row=1, columnspan=3, pady=10, padx=10)
        self.progressbar_results.set(0)

        self.button_open = customtkinter.CTkButton(
            master=self.frame_results,
            width=self.BUTTON_WIDTH,
            text="Open Papers",
        )
        self.button_open.grid(row=2, column=0, pady=10, padx=10)

        self.checkbox_newwindow = customtkinter.CTkCheckBox(
            master=self.frame_results,
            width=self.BUTTON_WIDTH,
            text="Open in New Window",
        )
        self.checkbox_newwindow.grid(row=3, column=0, pady=10, padx=10)

        self.button_write = customtkinter.CTkButton(
            master=self.frame_results,
            width=self.BUTTON_WIDTH,
            text="Write to File",
        )
        self.button_write.grid(row=2, column=2, pady=10, padx=10)

        self.optionmenu_write = customtkinter.CTkOptionMenu(
            self.frame_results,
            width=self.BUTTON_WIDTH,
            values=["Links", "ID Numbers"],
        )
        self.optionmenu_write.grid(row=3, column=2, pady=10, padx=10)

        self.app.mainloop()
