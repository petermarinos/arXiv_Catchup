"""GUI class"""

# customtkinter does not have typing fully implemented.
# Disable all unknown member types for this script
# pyright: reportUnknownMemberType = false

import customtkinter  # pyright: ignore[reportMissingTypeStubs]


# Helper functions


class GUI:
    """Creates and controls the GUI"""

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
        # Set the window size to be smaller than the smallest displays
        # TO-DO: check if this still be visible on large displays. Introduce scaling?
        self.app.geometry("600x760")

        # Bring the GUI to the font
        self.app.lift()
        self.app.attributes("-topmost", True)

        # Create interface

        self.frame_1 = customtkinter.CTkFrame(master=self.app)
        self.frame_1.pack(pady=20, padx=60, fill="both", expand=True)

        self.label_1 = customtkinter.CTkLabel(
            master=self.frame_1, justify=customtkinter.LEFT
        )
        self.label_1.pack(pady=10, padx=10)

        self.progressbar_1 = customtkinter.CTkProgressBar(master=self.frame_1)
        self.progressbar_1.pack(pady=10, padx=10)

        self.button_1 = customtkinter.CTkButton(
            master=self.frame_1, command=self.button_callback
        )
        self.button_1.pack(pady=10, padx=10)

        self.slider_1 = customtkinter.CTkSlider(
            master=self.frame_1, command=self.slider_callback, from_=0, to=1
        )
        self.slider_1.pack(pady=10, padx=10)
        self.slider_1.set(0.5)

        self.entry_1 = customtkinter.CTkEntry(
            master=self.frame_1, placeholder_text="CTkEntry"
        )
        self.entry_1.pack(pady=10, padx=10)

        self.optionmenu_1 = customtkinter.CTkOptionMenu(
            self.frame_1, values=["Option 1", "Option 2", "Option 42 long long long..."]
        )
        self.optionmenu_1.pack(pady=10, padx=10)
        self.optionmenu_1.set("CTkOptionMenu")

        self.combobox_1 = customtkinter.CTkComboBox(
            self.frame_1, values=["Option 1", "Option 2", "Option 42 long long long..."]
        )
        self.combobox_1.pack(pady=10, padx=10)
        self.combobox_1.set("CTkComboBox")

        self.checkbox_1 = customtkinter.CTkCheckBox(master=self.frame_1)
        self.checkbox_1.pack(pady=10, padx=10)

        self.radiobutton_var = customtkinter.IntVar(value=1)

        self.radiobutton_1 = customtkinter.CTkRadioButton(
            master=self.frame_1, variable=self.radiobutton_var, value=1
        )
        self.radiobutton_1.pack(pady=10, padx=10)

        self.radiobutton_2 = customtkinter.CTkRadioButton(
            master=self.frame_1, variable=self.radiobutton_var, value=2
        )
        self.radiobutton_2.pack(pady=10, padx=10)

        self.switch_1 = customtkinter.CTkSwitch(master=self.frame_1)
        self.switch_1.pack(pady=10, padx=10)

        self.text_1 = customtkinter.CTkTextbox(
            master=self.frame_1, width=200, height=70
        )
        self.text_1.pack(pady=10, padx=10)
        self.text_1.insert("0.0", "CTkTextbox\n\n\n\n")  # p

        self.segmented_button_1 = customtkinter.CTkSegmentedButton(
            master=self.frame_1, values=["CTkSegmentedButton", "Value 2"]
        )
        self.segmented_button_1.pack(pady=10, padx=10)

        self.tabview_1 = customtkinter.CTkTabview(master=self.frame_1, width=300)
        self.tabview_1.pack(pady=10, padx=10)
        self.tabview_1.add("CTkTabview")
        self.tabview_1.add("Tab 2")

        self.app.mainloop()

    def button_callback(self) -> None:
        """text"""
        print("Button click", self.combobox_1.get())

    def slider_callback(self, value: float) -> None:
        """text"""
        self.progressbar_1.set(value)
