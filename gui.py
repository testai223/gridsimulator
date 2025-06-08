"""Tkinter GUI for grid data input and load flow results."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from database import GridDatabase
from engine import GridCalculator, grid_graph, element_tables
import networkx as nx
import matplotlib.pyplot as plt
from examples import create_example_grid, create_ieee_9_bus

import pandapower as pp


class GridApp:
    """Main application window."""

    def __init__(self, root: tk.Tk, db: GridDatabase) -> None:
        self.root = root
        self.db = db
        self.current_net = None
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
        ttk.Button(
            self.result_frame,
            text="Run IEEE 9-Bus",
            command=self.run_ieee_9_bus,
        ).pack()
        ttk.Button(
            self.result_frame,
            text="Show Grid Graph",
            command=self.show_graph,
        ).pack()

        # Table for bus voltages
        bus_columns = ("bus", "name", "vn_kv", "vm_pu", "va_degree", "p_mw", "q_mvar")
        self.bus_tree = ttk.Treeview(
            self.result_frame, columns=bus_columns, show="headings", height=8
        )
        self.bus_tree.heading("bus", text="Bus ID")
        self.bus_tree.heading("name", text="Name")
        self.bus_tree.heading("vn_kv", text="Vn (kV)")
        self.bus_tree.heading("vm_pu", text="V (p.u.)")
        self.bus_tree.heading("va_degree", text="Angle (°)")
        self.bus_tree.heading("p_mw", text="P (MW)")
        self.bus_tree.heading("q_mvar", text="Q (Mvar)")
        
        # Configure column widths and alignment
        self.bus_tree.column("bus", width=60, anchor="center")
        self.bus_tree.column("name", width=100, anchor="w")
        self.bus_tree.column("vn_kv", width=80, anchor="e")
        self.bus_tree.column("vm_pu", width=80, anchor="e")
        self.bus_tree.column("va_degree", width=80, anchor="e")
        self.bus_tree.column("p_mw", width=80, anchor="e")
        self.bus_tree.column("q_mvar", width=80, anchor="e")
        
        self.bus_tree.pack(fill="both", expand=True, pady=5)

        # Table for line power flows
        line_columns = ("line", "from_bus", "to_bus", "p_from_mw", "q_from_mvar", "p_to_mw", "q_to_mvar", "loading_percent")
        self.line_tree = ttk.Treeview(
            self.result_frame, columns=line_columns, show="headings", height=8
        )
        self.line_tree.heading("line", text="Line ID")
        self.line_tree.heading("from_bus", text="From")
        self.line_tree.heading("to_bus", text="To")
        self.line_tree.heading("p_from_mw", text="P from (MW)")
        self.line_tree.heading("q_from_mvar", text="Q from (Mvar)")
        self.line_tree.heading("p_to_mw", text="P to (MW)")
        self.line_tree.heading("q_to_mvar", text="Q to (Mvar)")
        self.line_tree.heading("loading_percent", text="Loading (%)")
        
        # Configure column widths and alignment
        self.line_tree.column("line", width=60, anchor="center")
        self.line_tree.column("from_bus", width=60, anchor="center")
        self.line_tree.column("to_bus", width=60, anchor="center")
        self.line_tree.column("p_from_mw", width=90, anchor="e")
        self.line_tree.column("q_from_mvar", width=90, anchor="e")
        self.line_tree.column("p_to_mw", width=90, anchor="e")
        self.line_tree.column("q_to_mvar", width=90, anchor="e")
        self.line_tree.column("loading_percent", width=90, anchor="e")
        
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

    def run_ieee_9_bus(self) -> None:
        try:
            net = create_ieee_9_bus()
            pp.runpp(net)
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)

    def _display_results(self, net: pp.pandapowerNet) -> None:
        """Show calculation results in the GUI tables and text box."""
        self.current_net = net
        
        # Update text output with comprehensive results
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, element_tables(net))

        # Clear and populate bus results table
        for item in self.bus_tree.get_children():
            self.bus_tree.delete(item)
        
        if hasattr(net, 'res_bus') and not net.res_bus.empty:
            for idx, row in net.res_bus.iterrows():
                try:
                    # Get bus input data
                    if idx in net.bus.index:
                        bus_data = net.bus.loc[idx]
                        bus_name = bus_data.get("name", f"Bus {idx}")
                        vn_kv = bus_data["vn_kv"]
                    else:
                        bus_name = f"Bus {idx}"
                        vn_kv = 0.0
                    
                    # Get result data with safe access
                    vm_pu = round(float(row.get("vm_pu", 0.0)), 3)
                    va_degree = round(float(row.get("va_degree", 0.0)), 1)
                    p_mw = round(float(row.get("p_mw", 0.0)), 3)
                    q_mvar = round(float(row.get("q_mvar", 0.0)), 3)
                    
                    self.bus_tree.insert(
                        "",
                        "end",
                        values=(idx, bus_name, vn_kv, vm_pu, va_degree, p_mw, q_mvar),
                    )
                except Exception as e:
                    print(f"Error displaying bus {idx}: {e}")
                    continue

        # Clear and populate line results table
        for item in self.line_tree.get_children():
            self.line_tree.delete(item)
            
        if hasattr(net, 'res_line') and not net.res_line.empty:
            for idx, row in net.res_line.iterrows():
                try:
                    # Get line input data
                    if idx in net.line.index:
                        line_data = net.line.loc[idx]
                        from_bus = int(line_data["from_bus"])
                        to_bus = int(line_data["to_bus"])
                    else:
                        from_bus = 0
                        to_bus = 0
                    
                    # Get result data with safe access
                    p_from_mw = round(float(row.get("p_from_mw", 0.0)), 3)
                    q_from_mvar = round(float(row.get("q_from_mvar", 0.0)), 3)
                    p_to_mw = round(float(row.get("p_to_mw", 0.0)), 3)
                    q_to_mvar = round(float(row.get("q_to_mvar", 0.0)), 3)
                    loading_percent = round(float(row.get("loading_percent", 0.0)), 1)
                    
                    self.line_tree.insert(
                        "",
                        "end",
                        values=(idx, from_bus, to_bus, p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, loading_percent),
                    )
                except Exception as e:
                    print(f"Error displaying line {idx}: {e}")
                    continue

    def show_graph(self) -> None:
        """Display the current network as a graph using matplotlib."""
        if self.current_net is None:
            messagebox.showinfo("Info", "Run a load flow first")
            return
        g = grid_graph(self.current_net)
        pos = nx.spring_layout(g)
        plt.figure()
        nx.draw(g, pos, with_labels=False, node_color="#A0CBE2")

        node_labels = {}
        for n, data in g.nodes(data=True):
            label = str(n)
            if "vm_pu" in data:
                label += f"\n{data['vm_pu']:.2f} pu"
            node_labels[n] = label
        nx.draw_networkx_labels(g, pos, labels=node_labels)

        edge_labels = {}
        for u, v, data in g.edges(data=True):
            if "p_from_mw" in data:
                edge_labels[(u, v)] = f"{data['p_from_mw']:.2f} MW"
        if edge_labels:
            nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels)

        plt.show()


def main() -> None:
    root = tk.Tk()
    db = GridDatabase()
    app = GridApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    main()
