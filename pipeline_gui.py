import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from nukescan_pipeline import run_pipeline, set_prompt_handler


def launch_gui():
    def gui_prompt_handler(category, name):
        return simpledialog.askstring("Standardize Entry", f"Unrecognized {category}:\n{name}\n\nEnter standardized version or press Cancel to keep as-is:")

    def run():
        input_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if not input_path:
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not output_path:
            return

        try:
            set_prompt_handler(gui_prompt_handler)
            run_pipeline(input_path, output_path)
            messagebox.showinfo("Success", f"All done! Output saved to:\n{output_path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    root = tk.Tk()
    root.title("NukeScan Preprocessing Tool")
    root.geometry("400x200")

    label = tk.Label(root, text="Click below to select input CSV and output path", wraplength=300)
    label.pack(pady=20)

    run_button = tk.Button(root, text="Click here to start", command=run)
    run_button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    launch_gui()
