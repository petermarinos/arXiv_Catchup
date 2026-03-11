"""docstring"""

import customtkinter  # type: ignore[reportMissingTypeStubs]

customtkinter.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
customtkinter.set_default_color_theme(
    "dark-blue"
)  # Themes: "blue" (standard), "green", "dark-blue"

app = customtkinter.CTk()
app.geometry("400x780")
app.title("CustomTkinter simple_example.py")


def button_callback() -> None:
    """text"""
    print("Button click", combobox_1.get())


def slider_callback(value: float) -> None:
    """text"""
    progressbar_1.set(value)  # type: ignore[reportUnknownMemberType]


frame_1 = customtkinter.CTkFrame(master=app)
frame_1.pack(pady=20, padx=60, fill="both", expand=True)  # type: ignore[reportUnknownMemberType]

label_1 = customtkinter.CTkLabel(master=frame_1, justify=customtkinter.LEFT)
label_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

progressbar_1 = customtkinter.CTkProgressBar(master=frame_1)
progressbar_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

button_1 = customtkinter.CTkButton(master=frame_1, command=button_callback)
button_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

slider_1 = customtkinter.CTkSlider(
    master=frame_1, command=slider_callback, from_=0, to=1
)
slider_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]
slider_1.set(0.5)  # type: ignore[reportUnknownMemberType]

entry_1 = customtkinter.CTkEntry(master=frame_1, placeholder_text="CTkEntry")
entry_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

optionmenu_1 = customtkinter.CTkOptionMenu(
    frame_1, values=["Option 1", "Option 2", "Option 42 long long long..."]
)
optionmenu_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]
optionmenu_1.set("CTkOptionMenu")  # type: ignore[reportUnknownMemberType]

combobox_1 = customtkinter.CTkComboBox(
    frame_1, values=["Option 1", "Option 2", "Option 42 long long long..."]
)
combobox_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]
combobox_1.set("CTkComboBox")  # type: ignore[reportUnknownMemberType]

checkbox_1 = customtkinter.CTkCheckBox(master=frame_1)
checkbox_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

radiobutton_var = customtkinter.IntVar(value=1)

radiobutton_1 = customtkinter.CTkRadioButton(
    master=frame_1, variable=radiobutton_var, value=1
)
radiobutton_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

radiobutton_2 = customtkinter.CTkRadioButton(
    master=frame_1, variable=radiobutton_var, value=2
)
radiobutton_2.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

switch_1 = customtkinter.CTkSwitch(master=frame_1)
switch_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

text_1 = customtkinter.CTkTextbox(master=frame_1, width=200, height=70)
text_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]
text_1.insert("0.0", "CTkTextbox\n\n\n\n")  # pyright: ignore[reportUnknownMemberType]

segmented_button_1 = customtkinter.CTkSegmentedButton(
    master=frame_1, values=["CTkSegmentedButton", "Value 2"]
)
segmented_button_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]

tabview_1 = customtkinter.CTkTabview(master=frame_1, width=300)
tabview_1.pack(pady=10, padx=10)  # type: ignore[reportUnknownMemberType]
tabview_1.add("CTkTabview")
tabview_1.add("Tab 2")

app.mainloop()  # type: ignore[reportUnknownMemberType]
