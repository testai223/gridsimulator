"""Tkinter GUI for grid data input and load flow results."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

from database import GridDatabase
from engine import GridCalculator, grid_graph, element_tables
import networkx as nx
import matplotlib.pyplot as plt
from examples import create_example_grid, create_ieee_9_bus, create_ieee_39_bus
from contingency import ContingencyAnalysis

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
        self.edit_frame = ttk.Frame(notebook)
        self.contingency_frame = ttk.Frame(notebook)
        self.result_frame = ttk.Frame(notebook)

        notebook.add(self.bus_frame, text="Buses")
        notebook.add(self.line_frame, text="Lines")
        notebook.add(self.edit_frame, text="Edit Network")
        notebook.add(self.contingency_frame, text="Contingency Analysis")
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

        # Edit Network tab - Editable tables for network parameters
        self._build_edit_widgets()

        # Contingency Analysis tab
        self._build_contingency_widgets()

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
            text="Run IEEE 39-Bus",
            command=self.run_ieee_39_bus,
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

        # Table for transformer power flows
        trafo_columns = ("trafo", "name", "hv_bus", "lv_bus", "p_hv_mw", "q_hv_mvar", "p_lv_mw", "q_lv_mvar", "loading_percent")
        self.trafo_tree = ttk.Treeview(
            self.result_frame, columns=trafo_columns, show="headings", height=8
        )
        self.trafo_tree.heading("trafo", text="Trafo ID")
        self.trafo_tree.heading("name", text="Name")
        self.trafo_tree.heading("hv_bus", text="HV Bus")
        self.trafo_tree.heading("lv_bus", text="LV Bus")
        self.trafo_tree.heading("p_hv_mw", text="P HV (MW)")
        self.trafo_tree.heading("q_hv_mvar", text="Q HV (Mvar)")
        self.trafo_tree.heading("p_lv_mw", text="P LV (MW)")
        self.trafo_tree.heading("q_lv_mvar", text="Q LV (Mvar)")
        self.trafo_tree.heading("loading_percent", text="Loading (%)")
        
        # Configure column widths and alignment
        self.trafo_tree.column("trafo", width=60, anchor="center")
        self.trafo_tree.column("name", width=80, anchor="w")
        self.trafo_tree.column("hv_bus", width=60, anchor="center")
        self.trafo_tree.column("lv_bus", width=60, anchor="center")
        self.trafo_tree.column("p_hv_mw", width=90, anchor="e")
        self.trafo_tree.column("q_hv_mvar", width=90, anchor="e")
        self.trafo_tree.column("p_lv_mw", width=90, anchor="e")
        self.trafo_tree.column("q_lv_mvar", width=90, anchor="e")
        self.trafo_tree.column("loading_percent", width=90, anchor="e")
        
        self.trafo_tree.pack(fill="both", expand=True, pady=5)

        # Table for generator results
        gen_columns = ("gen", "name", "bus", "p_mw", "q_mvar", "vm_pu", "va_degree", "slack")
        self.gen_tree = ttk.Treeview(
            self.result_frame, columns=gen_columns, show="headings", height=8
        )
        self.gen_tree.heading("gen", text="Gen ID")
        self.gen_tree.heading("name", text="Name")
        self.gen_tree.heading("bus", text="Bus")
        self.gen_tree.heading("p_mw", text="P (MW)")
        self.gen_tree.heading("q_mvar", text="Q (Mvar)")
        self.gen_tree.heading("vm_pu", text="V (p.u.)")
        self.gen_tree.heading("va_degree", text="Angle (°)")
        self.gen_tree.heading("slack", text="Slack")
        
        # Configure column widths and alignment
        self.gen_tree.column("gen", width=60, anchor="center")
        self.gen_tree.column("name", width=100, anchor="w")
        self.gen_tree.column("bus", width=60, anchor="center")
        self.gen_tree.column("p_mw", width=80, anchor="e")
        self.gen_tree.column("q_mvar", width=80, anchor="e")
        self.gen_tree.column("vm_pu", width=80, anchor="e")
        self.gen_tree.column("va_degree", width=80, anchor="e")
        self.gen_tree.column("slack", width=60, anchor="center")
        
        self.gen_tree.pack(fill="both", expand=True, pady=5)

        # Raw text output for debugging
        self.text = tk.Text(self.result_frame, height=10, width=50)
        self.text.pack(fill="both", expand=True)

    def _build_edit_widgets(self) -> None:
        """Build the editable network parameter tables."""
        # Create a notebook for different element types
        edit_notebook = ttk.Notebook(self.edit_frame)
        edit_notebook.pack(fill="both", expand=True)

        # Create frames for each element type
        self.edit_bus_frame = ttk.Frame(edit_notebook)
        self.edit_line_frame = ttk.Frame(edit_notebook)
        self.edit_gen_frame = ttk.Frame(edit_notebook)
        self.edit_load_frame = ttk.Frame(edit_notebook)

        edit_notebook.add(self.edit_bus_frame, text="Bus Data")
        edit_notebook.add(self.edit_line_frame, text="Line Data")
        edit_notebook.add(self.edit_gen_frame, text="Generator Data")
        edit_notebook.add(self.edit_load_frame, text="Load Data")

        # Editable Bus Parameters Table
        bus_edit_columns = ("bus", "name", "vn_kv")
        self.edit_bus_tree = ttk.Treeview(
            self.edit_bus_frame, columns=bus_edit_columns, show="headings", height=12
        )
        self.edit_bus_tree.heading("bus", text="Bus ID")
        self.edit_bus_tree.heading("name", text="Name")
        self.edit_bus_tree.heading("vn_kv", text="Vn (kV)")
        
        self.edit_bus_tree.column("bus", width=80, anchor="center")
        self.edit_bus_tree.column("name", width=150, anchor="w")
        self.edit_bus_tree.column("vn_kv", width=100, anchor="e")
        
        self.edit_bus_tree.pack(fill="both", expand=True, pady=5)
        self.edit_bus_tree.bind("<Double-1>", self._on_bus_double_click)

        # Editable Line Parameters Table
        line_edit_columns = ("line", "from_bus", "to_bus", "r_ohm_per_km", "x_ohm_per_km", "c_nf_per_km", "max_i_ka")
        self.edit_line_tree = ttk.Treeview(
            self.edit_line_frame, columns=line_edit_columns, show="headings", height=12
        )
        self.edit_line_tree.heading("line", text="Line ID")
        self.edit_line_tree.heading("from_bus", text="From Bus")
        self.edit_line_tree.heading("to_bus", text="To Bus")
        self.edit_line_tree.heading("r_ohm_per_km", text="R (Ω/km)")
        self.edit_line_tree.heading("x_ohm_per_km", text="X (Ω/km)")
        self.edit_line_tree.heading("c_nf_per_km", text="C (nF/km)")
        self.edit_line_tree.heading("max_i_ka", text="Max I (kA)")
        
        self.edit_line_tree.column("line", width=70, anchor="center")
        self.edit_line_tree.column("from_bus", width=80, anchor="center")
        self.edit_line_tree.column("to_bus", width=80, anchor="center")
        self.edit_line_tree.column("r_ohm_per_km", width=100, anchor="e")
        self.edit_line_tree.column("x_ohm_per_km", width=100, anchor="e")
        self.edit_line_tree.column("c_nf_per_km", width=100, anchor="e")
        self.edit_line_tree.column("max_i_ka", width=100, anchor="e")
        
        self.edit_line_tree.pack(fill="both", expand=True, pady=5)
        self.edit_line_tree.bind("<Double-1>", self._on_line_double_click)

        # Editable Generator Parameters Table
        gen_edit_columns = ("gen", "name", "bus", "p_mw", "vm_pu", "slack")
        self.edit_gen_tree = ttk.Treeview(
            self.edit_gen_frame, columns=gen_edit_columns, show="headings", height=12
        )
        self.edit_gen_tree.heading("gen", text="Gen ID")
        self.edit_gen_tree.heading("name", text="Name")
        self.edit_gen_tree.heading("bus", text="Bus")
        self.edit_gen_tree.heading("p_mw", text="P (MW)")
        self.edit_gen_tree.heading("vm_pu", text="V (p.u.)")
        self.edit_gen_tree.heading("slack", text="Slack")
        
        self.edit_gen_tree.column("gen", width=70, anchor="center")
        self.edit_gen_tree.column("name", width=120, anchor="w")
        self.edit_gen_tree.column("bus", width=70, anchor="center")
        self.edit_gen_tree.column("p_mw", width=100, anchor="e")
        self.edit_gen_tree.column("vm_pu", width=100, anchor="e")
        self.edit_gen_tree.column("slack", width=70, anchor="center")
        
        self.edit_gen_tree.pack(fill="both", expand=True, pady=5)
        self.edit_gen_tree.bind("<Double-1>", self._on_gen_double_click)

        # Editable Load Parameters Table
        load_edit_columns = ("load", "name", "bus", "p_mw", "q_mvar")
        self.edit_load_tree = ttk.Treeview(
            self.edit_load_frame, columns=load_edit_columns, show="headings", height=12
        )
        self.edit_load_tree.heading("load", text="Load ID")
        self.edit_load_tree.heading("name", text="Name")
        self.edit_load_tree.heading("bus", text="Bus")
        self.edit_load_tree.heading("p_mw", text="P (MW)")
        self.edit_load_tree.heading("q_mvar", text="Q (Mvar)")
        
        self.edit_load_tree.column("load", width=70, anchor="center")
        self.edit_load_tree.column("name", width=120, anchor="w")
        self.edit_load_tree.column("bus", width=70, anchor="center")
        self.edit_load_tree.column("p_mw", width=100, anchor="e")
        self.edit_load_tree.column("q_mvar", width=100, anchor="e")
        
        self.edit_load_tree.pack(fill="both", expand=True, pady=5)
        self.edit_load_tree.bind("<Double-1>", self._on_load_double_click)

        # Control buttons
        control_frame = ttk.Frame(self.edit_frame)
        control_frame.pack(fill="x", pady=5)
        
        ttk.Button(control_frame, text="Refresh Tables", command=self._refresh_edit_tables).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Apply Changes & Run", command=self._apply_changes_and_run).pack(side=tk.LEFT, padx=5)

    def _build_contingency_widgets(self) -> None:
        """Build the contingency analysis interface."""
        # Control panel
        control_panel = ttk.Frame(self.contingency_frame)
        control_panel.pack(fill="x", pady=10)
        
        ttk.Label(control_panel, text="N-1 Contingency Analysis", font=("Arial", 12, "bold")).pack(pady=5)
        
        button_frame = ttk.Frame(control_panel)
        button_frame.pack()
        
        ttk.Button(button_frame, text="Run N-1 Analysis", command=self._run_contingency_analysis).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Results", command=self._export_contingency_results).pack(side=tk.LEFT, padx=5)
        
        # Summary panel
        summary_frame = ttk.LabelFrame(self.contingency_frame, text="Analysis Summary")
        summary_frame.pack(fill="x", pady=5, padx=10)
        
        self.contingency_summary = tk.Text(summary_frame, height=6, width=80)
        self.contingency_summary.pack(fill="x", pady=5)
        
        # Color legend
        legend_frame = ttk.LabelFrame(self.contingency_frame, text="Severity Color Legend")
        legend_frame.pack(fill="x", pady=5, padx=10)
        
        legend_text = tk.Text(legend_frame, height=3, width=80, state='disabled')
        legend_text.pack(fill="x", pady=5)
        
        # Configure legend text with colors
        legend_text.config(state='normal')
        legend_text.insert(tk.END, "Critical", "critical_tag")
        legend_text.insert(tk.END, " - Non-convergent cases, system instability  ")
        legend_text.insert(tk.END, "High", "high_tag") 
        legend_text.insert(tk.END, " - Voltage/loading violations  ")
        legend_text.insert(tk.END, "Medium", "medium_tag")
        legend_text.insert(tk.END, " - Near limits\n")
        legend_text.insert(tk.END, "Low", "low_tag")
        legend_text.insert(tk.END, " - Safe operation  ")
        legend_text.insert(tk.END, "Normal", "normal_tag")
        legend_text.insert(tk.END, " - Base case, no outages")
        
        # Configure legend colors
        legend_text.tag_configure("critical_tag", background="#ff9999", foreground="#000000")
        legend_text.tag_configure("high_tag", background="#ffcc99", foreground="#000000")
        legend_text.tag_configure("medium_tag", background="#ffff99", foreground="#000000")
        legend_text.tag_configure("low_tag", background="#99ff99", foreground="#000000")
        legend_text.tag_configure("normal_tag", background="#99ccff", foreground="#000000")
        
        legend_text.config(state='disabled')
        
        # Results table
        results_frame = ttk.LabelFrame(self.contingency_frame, text="Contingency Results")
        results_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        # Create contingency results table
        contingency_columns = ("type", "element", "converged", "max_v", "min_v", "max_line_load", "max_trafo_load", "v_violations", "overloads", "severity")
        self.contingency_tree = ttk.Treeview(
            results_frame, columns=contingency_columns, show="headings", height=15
        )
        
        # Configure headers
        self.contingency_tree.heading("type", text="Type")
        self.contingency_tree.heading("element", text="Element")
        self.contingency_tree.heading("converged", text="Converged")
        self.contingency_tree.heading("max_v", text="Max V (p.u.)")
        self.contingency_tree.heading("min_v", text="Min V (p.u.)")
        self.contingency_tree.heading("max_line_load", text="Max Line (%)")
        self.contingency_tree.heading("max_trafo_load", text="Max Trafo (%)")
        self.contingency_tree.heading("v_violations", text="V Violations")
        self.contingency_tree.heading("overloads", text="Overloads")
        self.contingency_tree.heading("severity", text="Severity")
        
        # Configure column widths
        self.contingency_tree.column("type", width=120, anchor="w")
        self.contingency_tree.column("element", width=150, anchor="w")
        self.contingency_tree.column("converged", width=80, anchor="center")
        self.contingency_tree.column("max_v", width=100, anchor="e")
        self.contingency_tree.column("min_v", width=100, anchor="e")
        self.contingency_tree.column("max_line_load", width=100, anchor="e")
        self.contingency_tree.column("max_trafo_load", width=100, anchor="e")
        self.contingency_tree.column("v_violations", width=100, anchor="center")
        self.contingency_tree.column("overloads", width=100, anchor="center")
        self.contingency_tree.column("severity", width=80, anchor="center")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.contingency_tree.yview)
        self.contingency_tree.configure(yscrollcommand=scrollbar.set)
        
        self.contingency_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Configure row colors based on severity with improved visibility
        self.contingency_tree.tag_configure("Critical", background="#ff9999", foreground="#000000")  # Red
        self.contingency_tree.tag_configure("High", background="#ffcc99", foreground="#000000")      # Orange
        self.contingency_tree.tag_configure("Medium", background="#ffff99", foreground="#000000")    # Yellow
        self.contingency_tree.tag_configure("Low", background="#99ff99", foreground="#000000")       # Green
        self.contingency_tree.tag_configure("Normal", background="#99ccff", foreground="#000000")    # Blue
        
        # Configure alternating row colors for better readability
        self.contingency_tree.tag_configure("oddrow", background="#f0f0f0")
        self.contingency_tree.tag_configure("evenrow", background="#ffffff")

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
        self._refresh_edit_tables()

    def run_ieee_9_bus(self) -> None:
        try:
            net = create_ieee_9_bus()
            pp.runpp(net)
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)
        self._refresh_edit_tables()

    def run_ieee_39_bus(self) -> None:
        try:
            net = create_ieee_39_bus()
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

        # Clear and populate transformer results table
        for item in self.trafo_tree.get_children():
            self.trafo_tree.delete(item)
            
        if hasattr(net, 'res_trafo') and not net.res_trafo.empty:
            for idx, row in net.res_trafo.iterrows():
                try:
                    # Get transformer input data
                    if idx in net.trafo.index:
                        trafo_data = net.trafo.loc[idx]
                        trafo_name = trafo_data.get("name", f"Trafo {idx}")
                        hv_bus = int(trafo_data["hv_bus"])
                        lv_bus = int(trafo_data["lv_bus"])
                    else:
                        trafo_name = f"Trafo {idx}"
                        hv_bus = 0
                        lv_bus = 0
                    
                    # Get result data with safe access
                    p_hv_mw = round(float(row.get("p_hv_mw", 0.0)), 3)
                    q_hv_mvar = round(float(row.get("q_hv_mvar", 0.0)), 3)
                    p_lv_mw = round(float(row.get("p_lv_mw", 0.0)), 3)
                    q_lv_mvar = round(float(row.get("q_lv_mvar", 0.0)), 3)
                    loading_percent = round(float(row.get("loading_percent", 0.0)), 1)
                    
                    self.trafo_tree.insert(
                        "",
                        "end",
                        values=(idx, trafo_name, hv_bus, lv_bus, p_hv_mw, q_hv_mvar, p_lv_mw, q_lv_mvar, loading_percent),
                    )
                except Exception as e:
                    print(f"Error displaying transformer {idx}: {e}")
                    continue

        # Clear and populate generator results table
        for item in self.gen_tree.get_children():
            self.gen_tree.delete(item)
            
        if hasattr(net, 'res_gen') and not net.res_gen.empty:
            for idx, row in net.res_gen.iterrows():
                try:
                    # Get generator input data
                    if idx in net.gen.index:
                        gen_data = net.gen.loc[idx]
                        gen_name = gen_data.get("name", f"Gen {idx}")
                        bus = int(gen_data["bus"])
                        is_slack = gen_data.get("slack", False)
                        slack_text = "Yes" if is_slack else "No"
                    else:
                        gen_name = f"Gen {idx}"
                        bus = 0
                        slack_text = "No"
                    
                    # Get result data with safe access
                    p_mw = round(float(row.get("p_mw", 0.0)), 3)
                    q_mvar = round(float(row.get("q_mvar", 0.0)), 3)
                    vm_pu = round(float(row.get("vm_pu", 0.0)), 3)
                    va_degree = round(float(row.get("va_degree", 0.0)), 1)
                    
                    self.gen_tree.insert(
                        "",
                        "end",
                        values=(idx, gen_name, bus, p_mw, q_mvar, vm_pu, va_degree, slack_text),
                    )
                except Exception as e:
                    print(f"Error displaying generator {idx}: {e}")
                    continue

    def show_graph(self) -> None:
        """Display the current network as a graph using matplotlib."""
        if self.current_net is None:
            messagebox.showinfo("Info", "Run a load flow first")
            return
        
        g = grid_graph(self.current_net)
        pos = nx.spring_layout(g, seed=42)  # Fixed seed for consistent layout
        
        plt.figure(figsize=(12, 8))
        
        # Separate edges by type
        line_edges = [(u, v) for u, v, d in g.edges(data=True) if d.get("type") == "line"]
        transformer_edges = [(u, v) for u, v, d in g.edges(data=True) if d.get("type") == "transformer"]
        
        # Draw nodes
        nx.draw_networkx_nodes(g, pos, node_color="#A0CBE2", node_size=800)
        
        # Draw edges with different styles
        if line_edges:
            nx.draw_networkx_edges(g, pos, edgelist=line_edges, edge_color="black", width=2)
        if transformer_edges:
            nx.draw_networkx_edges(g, pos, edgelist=transformer_edges, edge_color="red", width=3, style="dashed")

        # Node labels with voltage information
        node_labels = {}
        for n, data in g.nodes(data=True):
            name = data.get("name", f"Bus {n}")
            label = f"{name}\n({n})"
            if "vm_pu" in data:
                label += f"\n{data['vm_pu']:.3f} pu"
            node_labels[n] = label
        nx.draw_networkx_labels(g, pos, labels=node_labels, font_size=8)

        # Edge labels with power flow information
        edge_labels = {}
        for u, v, data in g.edges(data=True):
            if data.get("type") == "line" and "p_from_mw" in data:
                edge_labels[(u, v)] = f"{data['p_from_mw']:.1f} MW"
            elif data.get("type") == "transformer" and "p_hv_mw" in data:
                edge_labels[(u, v)] = f"{data['p_hv_mw']:.1f} MW"
        
        if edge_labels:
            nx.draw_networkx_edge_labels(g, pos, edge_labels=edge_labels, font_size=7)

        plt.title("Power System Network Graph\n(Solid lines: Transmission Lines, Dashed red: Transformers)")
        plt.axis('off')
        plt.tight_layout()
        plt.show()

    def _refresh_edit_tables(self) -> None:
        """Refresh all editing tables with current network data."""
        if self.current_net is None:
            messagebox.showinfo("Info", "Load a network first")
            return
        
        net = self.current_net
        
        # Clear all editing tables
        for item in self.edit_bus_tree.get_children():
            self.edit_bus_tree.delete(item)
        for item in self.edit_line_tree.get_children():
            self.edit_line_tree.delete(item)
        for item in self.edit_gen_tree.get_children():
            self.edit_gen_tree.delete(item)
        for item in self.edit_load_tree.get_children():
            self.edit_load_tree.delete(item)
        
        # Populate bus editing table
        for idx, row in net.bus.iterrows():
            name = row.get("name", f"Bus {idx}")
            vn_kv = row["vn_kv"]
            self.edit_bus_tree.insert("", "end", values=(idx, name, vn_kv))
        
        # Populate line editing table
        for idx, row in net.line.iterrows():
            from_bus = row["from_bus"]
            to_bus = row["to_bus"]
            r_ohm_per_km = row.get("r_ohm_per_km", 0.0)
            x_ohm_per_km = row.get("x_ohm_per_km", 0.0)
            c_nf_per_km = row.get("c_nf_per_km", 0.0)
            max_i_ka = row.get("max_i_ka", 0.0)
            self.edit_line_tree.insert("", "end", values=(idx, from_bus, to_bus, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka))
        
        # Populate generator editing table
        if hasattr(net, 'gen') and not net.gen.empty:
            for idx, row in net.gen.iterrows():
                name = row.get("name", f"Gen {idx}")
                bus = row["bus"]
                p_mw = row["p_mw"]
                vm_pu = row["vm_pu"]
                slack = "Yes" if row.get("slack", False) else "No"
                self.edit_gen_tree.insert("", "end", values=(idx, name, bus, p_mw, vm_pu, slack))
        
        # Populate load editing table
        if hasattr(net, 'load') and not net.load.empty:
            for idx, row in net.load.iterrows():
                name = row.get("name", f"Load {idx}")
                bus = row["bus"]
                p_mw = row["p_mw"]
                q_mvar = row["q_mvar"]
                self.edit_load_tree.insert("", "end", values=(idx, name, bus, p_mw, q_mvar))

    def _on_bus_double_click(self, event):
        """Handle double-click on bus table for editing."""
        item = self.edit_bus_tree.selection()[0]
        self._edit_cell(self.edit_bus_tree, item, event)

    def _on_line_double_click(self, event):
        """Handle double-click on line table for editing."""
        item = self.edit_line_tree.selection()[0]
        self._edit_cell(self.edit_line_tree, item, event)

    def _on_gen_double_click(self, event):
        """Handle double-click on generator table for editing."""
        item = self.edit_gen_tree.selection()[0]
        self._edit_cell(self.edit_gen_tree, item, event)

    def _on_load_double_click(self, event):
        """Handle double-click on load table for editing."""
        item = self.edit_load_tree.selection()[0]
        self._edit_cell(self.edit_load_tree, item, event)

    def _edit_cell(self, tree, item, event):
        """Generic cell editing function."""
        # Determine which column was clicked
        column = tree.identify_column(event.x)
        column_index = int(column[1:]) - 1  # Convert #1, #2, etc. to 0, 1, etc.
        
        # Skip editing for ID columns (usually the first column)
        if column_index == 0:
            return
        
        # Get current values
        values = list(tree.item(item, "values"))
        column_name = tree["columns"][column_index]
        current_value = values[column_index]
        
        # Create edit dialog
        self._show_edit_dialog(tree, item, column_name, current_value, column_index)

    def _show_edit_dialog(self, tree, item, column_name, current_value, column_index):
        """Show dialog for editing a cell value."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit {column_name}")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (300 // 2)
        y = (dialog.winfo_screenheight() // 2) - (150 // 2)
        dialog.geometry(f"300x150+{x}+{y}")
        
        ttk.Label(dialog, text=f"Edit {column_name}:").pack(pady=10)
        
        # Special handling for slack column (Yes/No dropdown)
        if column_name == "slack":
            var = tk.StringVar(value=current_value)
            combo = ttk.Combobox(dialog, textvariable=var, values=["Yes", "No"], state="readonly")
            combo.pack(pady=5)
            entry_widget = combo
        else:
            var = tk.StringVar(value=str(current_value))
            entry_widget = ttk.Entry(dialog, textvariable=var)
            entry_widget.pack(pady=5)
        
        def save_value():
            try:
                new_value = var.get()
                # Update the tree display
                values = list(tree.item(item, "values"))
                values[column_index] = new_value
                tree.item(item, values=values)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
        
        def cancel():
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save", command=save_value).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        
        entry_widget.focus()
        if hasattr(entry_widget, 'select_range'):
            entry_widget.select_range(0, tk.END)

    def _apply_changes_and_run(self):
        """Apply all changes from editing tables to the network and run power flow."""
        if self.current_net is None:
            messagebox.showinfo("Info", "Load a network first")
            return
        
        try:
            # Apply bus changes
            for item in self.edit_bus_tree.get_children():
                values = self.edit_bus_tree.item(item, "values")
                bus_id, name, vn_kv = values
                bus_id = int(bus_id)
                vn_kv = float(vn_kv)
                
                if bus_id in self.current_net.bus.index:
                    self.current_net.bus.loc[bus_id, "name"] = name
                    self.current_net.bus.loc[bus_id, "vn_kv"] = vn_kv
            
            # Apply line changes
            for item in self.edit_line_tree.get_children():
                values = self.edit_line_tree.item(item, "values")
                line_id, from_bus, to_bus, r_ohm_per_km, x_ohm_per_km, c_nf_per_km, max_i_ka = values
                line_id = int(line_id)
                
                if line_id in self.current_net.line.index:
                    self.current_net.line.loc[line_id, "from_bus"] = int(from_bus)
                    self.current_net.line.loc[line_id, "to_bus"] = int(to_bus)
                    self.current_net.line.loc[line_id, "r_ohm_per_km"] = float(r_ohm_per_km)
                    self.current_net.line.loc[line_id, "x_ohm_per_km"] = float(x_ohm_per_km)
                    self.current_net.line.loc[line_id, "c_nf_per_km"] = float(c_nf_per_km)
                    self.current_net.line.loc[line_id, "max_i_ka"] = float(max_i_ka)
            
            # Apply generator changes
            if hasattr(self.current_net, 'gen'):
                for item in self.edit_gen_tree.get_children():
                    values = self.edit_gen_tree.item(item, "values")
                    gen_id, name, bus, p_mw, vm_pu, slack = values
                    gen_id = int(gen_id)
                    
                    if gen_id in self.current_net.gen.index:
                        self.current_net.gen.loc[gen_id, "name"] = name
                        self.current_net.gen.loc[gen_id, "bus"] = int(bus)
                        self.current_net.gen.loc[gen_id, "p_mw"] = float(p_mw)
                        self.current_net.gen.loc[gen_id, "vm_pu"] = float(vm_pu)
                        self.current_net.gen.loc[gen_id, "slack"] = (slack == "Yes")
            
            # Apply load changes
            if hasattr(self.current_net, 'load'):
                for item in self.edit_load_tree.get_children():
                    values = self.edit_load_tree.item(item, "values")
                    load_id, name, bus, p_mw, q_mvar = values
                    load_id = int(load_id)
                    
                    if load_id in self.current_net.load.index:
                        self.current_net.load.loc[load_id, "name"] = name
                        self.current_net.load.loc[load_id, "bus"] = int(bus)
                        self.current_net.load.loc[load_id, "p_mw"] = float(p_mw)
                        self.current_net.load.loc[load_id, "q_mvar"] = float(q_mvar)
            
            # Run power flow with updated parameters
            pp.runpp(self.current_net)
            self._display_results(self.current_net)
            messagebox.showinfo("Success", "Changes applied and power flow completed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply changes: {e}")

    def _run_contingency_analysis(self):
        """Run N-1 contingency analysis on the current network."""
        if self.current_net is None:
            messagebox.showinfo("Info", "Load a network first")
            return
        
        try:
            # Show progress dialog
            progress_dialog = tk.Toplevel(self.root)
            progress_dialog.title("Running Contingency Analysis")
            progress_dialog.geometry("400x100")
            progress_dialog.transient(self.root)
            progress_dialog.grab_set()
            
            ttk.Label(progress_dialog, text="Running N-1 contingency analysis...").pack(pady=20)
            progress_bar = ttk.Progressbar(progress_dialog, mode='indeterminate')
            progress_bar.pack(pady=10)
            progress_bar.start()
            
            # Update GUI to show progress
            self.root.update()
            
            # Run contingency analysis
            contingency = ContingencyAnalysis(self.current_net)
            results = contingency.run_n1_analysis()
            
            # Close progress dialog
            progress_dialog.destroy()
            
            # Display results
            self._display_contingency_results(results, contingency)
            
            messagebox.showinfo("Success", f"Contingency analysis completed. Analyzed {len(results)} contingencies.")
            
        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.destroy()
            messagebox.showerror("Error", f"Contingency analysis failed: {e}")

    def _display_contingency_results(self, results, contingency):
        """Display contingency analysis results in the GUI."""
        # Clear previous results
        for item in self.contingency_tree.get_children():
            self.contingency_tree.delete(item)
        
        # Display summary
        summary = contingency.get_contingency_summary()
        summary_text = f"""Analysis Summary:
Total Contingencies: {summary.get('total_contingencies', 0)}
Converged Cases: {summary.get('converged_cases', 0)} ({summary.get('convergence_rate', '0%')})
Security Status: {summary.get('security_status', 'Unknown')}

Severity Breakdown:
  Critical: {summary.get('critical_contingencies', 0)}
  High: {summary.get('high_severity', 0)}
  Medium: {summary.get('medium_severity', 0)}
  Low: {summary.get('low_severity', 0)}
"""
        
        self.contingency_summary.delete("1.0", tk.END)
        self.contingency_summary.insert(tk.END, summary_text)
        
        # Display detailed results with improved formatting and color coding
        for i, result in enumerate(results):
            converged = "Yes" if result['converged'] else "No"
            
            if result['converged']:
                max_v = f"{result.get('max_voltage_pu', 0):.3f}"
                min_v = f"{result.get('min_voltage_pu', 0):.3f}"
                max_line = f"{result.get('max_line_loading', 0):.1f}"
                max_trafo = f"{result.get('max_trafo_loading', 0):.1f}"
                v_violations = str(result.get('voltage_violations', 0))
                overloads = str(result.get('overload_violations', 0))
            else:
                max_v = min_v = max_line = max_trafo = v_violations = overloads = "N/A"
            
            severity = result['severity']
            
            # Determine primary tag for color coding based on severity
            if severity == 'Critical':
                primary_tag = 'Critical'
            elif severity == 'High':
                primary_tag = 'High'
            elif severity == 'Medium':
                primary_tag = 'Medium'
            elif severity == 'Low':
                primary_tag = 'Low'
            else:
                primary_tag = 'Normal'
            
            # Add alternating row colors as secondary tag for non-critical cases
            if severity in ['Normal', 'Low']:
                secondary_tag = 'oddrow' if i % 2 else 'evenrow'
                tags = (secondary_tag, primary_tag)
            else:
                tags = (primary_tag,)
            
            item = self.contingency_tree.insert(
                "", "end",
                values=(
                    result['contingency_type'],
                    result['element_name'],
                    converged,
                    max_v,
                    min_v,
                    max_line,
                    max_trafo,
                    v_violations,
                    overloads,
                    severity
                ),
                tags=tags
            )

    def _export_contingency_results(self):
        """Export contingency results to CSV file."""
        if not hasattr(self, 'contingency_tree') or not self.contingency_tree.get_children():
            messagebox.showinfo("Info", "No contingency results to export")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Export Contingency Results",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                import csv
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    headers = ["Type", "Element", "Converged", "Max V (p.u.)", "Min V (p.u.)", 
                              "Max Line (%)", "Max Trafo (%)", "V Violations", "Overloads", "Severity"]
                    writer.writerow(headers)
                    
                    # Write data
                    for item in self.contingency_tree.get_children():
                        values = self.contingency_tree.item(item, "values")
                        writer.writerow(values)
                
                messagebox.showinfo("Success", f"Results exported to {filename}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export results: {e}")


def main() -> None:
    root = tk.Tk()
    db = GridDatabase()
    app = GridApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    main()
