"""Tkinter GUI for grid data input and load flow results."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from database import GridDatabase
from engine import GridCalculator
from examples import create_example_grid

import pandapower as pp


class GridApp:
    """Main application window."""

    def __init__(self, root: tk.Tk, db: GridDatabase) -> None:
        self.root = root
        self.db = db
        self.root.title("Grid Simulator")

        self._build_widgets()

    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.bus_frame = ttk.Frame(notebook)
        self.line_frame = ttk.Frame(notebook)
        self.result_frame = ttk.Frame(notebook)

        notebook.add(self.bus_frame, text="Buses")
        notebook.add(self.line_frame, text="Lines")
        notebook.add(self.result_frame, text="Results")

        # Bus inputs
        ttk.Label(self.bus_frame, text="Name").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(self.bus_frame, text="Voltage (kV)").grid(
            row=1, column=0, sticky=tk.W
        )
        self.bus_name = ttk.Entry(self.bus_frame)
        self.bus_vn_kv = ttk.Entry(self.bus_frame)
        self.bus_name.grid(row=0, column=1)
        self.bus_vn_kv.grid(row=1, column=1)
        ttk.Button(self.bus_frame, text="Add Bus", command=self.add_bus).grid(
            row=2, column=0, columnspan=2
        )

        # Line inputs
        labels = [
            "From Bus ID",
            "To Bus ID",
            "Length (km)",
            "R (ohm/km)",
            "X (ohm/km)",
            "C (nF/km)",
            "Max I (kA)",
        ]
        self.line_entries = []
        for i, lbl in enumerate(labels):
            ttk.Label(self.line_frame, text=lbl).grid(row=i, column=0, sticky=tk.W)
            entry = ttk.Entry(self.line_frame)
            entry.grid(row=i, column=1)
            self.line_entries.append(entry)
        ttk.Button(self.line_frame, text="Add Line", command=self.add_line).grid(
            row=len(labels), column=0, columnspan=2
        )

        ttk.Button(
            self.result_frame, text="Run Load Flow", command=self.run_powerflow
        ).pack()
        ttk.Button(
            self.result_frame,
            text="Run Example Grid",
            command=self.run_example_grid,
        ).pack()

        # Table for bus voltages
        bus_columns = ("bus", "vm_pu", "va_degree")
        self.bus_tree = ttk.Treeview(
            self.result_frame, columns=bus_columns, show="headings", height=5
        )
        self.bus_tree.heading("bus", text="Bus")
        self.bus_tree.heading("vm_pu", text="V (p.u.)")
        self.bus_tree.heading("va_degree", text="Angle (deg)")
        self.bus_tree.pack(fill="both", expand=True, pady=5)

        # Table for line power flows
        line_columns = ("line", "p_from", "p_to")
        self.line_tree = ttk.Treeview(
            self.result_frame, columns=line_columns, show="headings", height=5
        )
        self.line_tree.heading("line", text="Line")
        self.line_tree.heading("p_from", text="P from (MW)")
        self.line_tree.heading("p_to", text="P to (MW)")
        self.line_tree.pack(fill="both", expand=True, pady=5)

        # Raw text output for debugging
        self.text = tk.Text(self.result_frame, height=10, width=50)
        self.text.pack(fill="both", expand=True)

    def add_bus(self) -> None:
        name = self.bus_name.get()
        try:
            vn_kv = float(self.bus_vn_kv.get())
        except ValueError:
            messagebox.showerror("Input Error", "Voltage must be a number")
            return
        self.db.add_bus(name, vn_kv)
        self.bus_name.delete(0, tk.END)
        self.bus_vn_kv.delete(0, tk.END)

    def add_line(self) -> None:
        try:
            values = [float(e.get()) for e in self.line_entries]
        except ValueError:
            messagebox.showerror("Input Error", "All line parameters must be numbers")
            return
        self.db.add_line(*[int(values[0]), int(values[1])], *values[2:])
        for e in self.line_entries:
            e.delete(0, tk.END)

    def run_powerflow(self) -> None:
        calc = GridCalculator(self.db)
        try:
            net = calc.run_powerflow()
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)

    def run_example_grid(self) -> None:
        try:
            net = create_example_grid()
            pp.runpp(net)
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)

    def _display_results(self, net: pp.pandapowerNet) -> None:
        """Show calculation results in the GUI tables and text box."""
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, str(net.res_bus))

        for item in self.bus_tree.get_children():
            self.bus_tree.delete(item)
        for idx, row in net.res_bus.iterrows():
            self.bus_tree.insert(
                "",
                "end",
                values=(idx, round(row["vm_pu"], 3), round(row["va_degree"], 3)),
            )

        for item in self.line_tree.get_children():
            self.line_tree.delete(item)
        if len(net.res_line) > 0:
            for idx, row in net.res_line.iterrows():
                self.line_tree.insert(
                    "",
                    "end",
                    values=(
                        idx,
                        round(row["p_from_mw"], 3),
                        round(row["p_to_mw"], 3),
                    ),
                )


def main() -> None:
    root = tk.Tk()
    db = GridDatabase()
    app = GridApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    main()
