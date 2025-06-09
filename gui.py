"""Tkinter GUI for grid data input and load flow results."""

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from typing import Dict, Any

from database import GridDatabase
from engine import GridCalculator, grid_graph, element_tables
import networkx as nx
import matplotlib.pyplot as plt
from examples import create_example_grid, create_ieee_9_bus, create_ieee_39_bus, create_ieee_39_bus_standard
from contingency import ContingencyAnalysis
from state_estimator import StateEstimator, run_ieee9_state_estimation
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode, create_default_config

import pandapower as pp
from datetime import datetime


class GridApp:
    """Main application window."""

    def __init__(self, root: tk.Tk, db: GridDatabase) -> None:
        self.root = root
        self.db = db
        self.current_net = None
        self.current_grid_id = None
        self.contingency_analysis = None
        self.state_estimation_module = StateEstimationModule(db)
        self.root.title("Grid Simulator")
        
        # Initialize example grids in database
        self.db.initialize_example_grids()

        self._build_widgets()

    def _build_widgets(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.grid_frame = ttk.Frame(notebook)
        self.bus_frame = ttk.Frame(notebook)
        self.line_frame = ttk.Frame(notebook)
        self.edit_frame = ttk.Frame(notebook)
        self.contingency_frame = ttk.Frame(notebook)
        self.state_estimation_frame = ttk.Frame(notebook)
        self.result_frame = ttk.Frame(notebook)

        notebook.add(self.grid_frame, text="Grid Manager")
        notebook.add(self.bus_frame, text="Buses")
        notebook.add(self.line_frame, text="Lines")
        notebook.add(self.edit_frame, text="Edit Network")
        notebook.add(self.contingency_frame, text="Contingency Analysis")
        notebook.add(self.state_estimation_frame, text="State Estimation")
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

        # Grid Manager tab - Save/Load/Manage grids  
        self._build_grid_manager_widgets()

        # Edit Network tab - Editable tables for network parameters
        self._build_edit_widgets()

        # Contingency Analysis tab
        self._build_contingency_widgets()
        
        # State Estimation tab
        self._build_state_estimation_widgets()

        # Create button frame for better organization
        button_frame_results = ttk.Frame(self.result_frame)
        button_frame_results.pack(fill="x", pady=5)
        
        ttk.Button(
            button_frame_results, text="Run Load Flow on Current Grid", command=self.run_powerflow_current
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame_results, text="Show Grid Graph", command=self.show_graph
        ).pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(self.result_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Example grids section
        ttk.Label(self.result_frame, text="Load Example Grids:", font=("Arial", 10, "bold")).pack()
        example_frame = ttk.Frame(self.result_frame)
        example_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            example_frame, text="Simple Example", command=self.run_example_grid
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            example_frame, text="IEEE 9-Bus", command=self.run_ieee_9_bus
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            example_frame, text="IEEE 39-Bus", command=self.run_ieee_39_bus
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            example_frame, text="IEEE 39-Bus Std", command=self.run_ieee_39_bus_standard
        ).pack(side=tk.LEFT, padx=5)

        # Separator
        ttk.Separator(self.result_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # State Estimator section
        ttk.Label(self.result_frame, text="State Estimation:", font=("Arial", 10, "bold")).pack()
        estimator_frame = ttk.Frame(self.result_frame)
        estimator_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            estimator_frame, text="Run State Estimator (IEEE 9-Bus)", command=self.run_state_estimator
        ).pack(side=tk.LEFT, padx=5)

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
        line_columns = ("line", "name", "from_bus", "to_bus", "vn_kv", "p_from_mw", "q_from_mvar", "i_from_ka", "p_to_mw", "q_to_mvar", "i_to_ka", "loading_percent")
        self.line_tree = ttk.Treeview(
            self.result_frame, columns=line_columns, show="headings", height=8
        )
        self.line_tree.heading("line", text="Line ID")
        self.line_tree.heading("name", text="Name")
        self.line_tree.heading("from_bus", text="From")
        self.line_tree.heading("to_bus", text="To")
        self.line_tree.heading("vn_kv", text="Vn (kV)")
        self.line_tree.heading("p_from_mw", text="P from (MW)")
        self.line_tree.heading("q_from_mvar", text="Q from (Mvar)")
        self.line_tree.heading("i_from_ka", text="I from (kA)")
        self.line_tree.heading("p_to_mw", text="P to (MW)")
        self.line_tree.heading("q_to_mvar", text="Q to (Mvar)")
        self.line_tree.heading("i_to_ka", text="I to (kA)")
        self.line_tree.heading("loading_percent", text="Loading (%)")
        
        # Configure column widths and alignment
        self.line_tree.column("line", width=50, anchor="center")
        self.line_tree.column("name", width=90, anchor="w")
        self.line_tree.column("from_bus", width=50, anchor="center")
        self.line_tree.column("to_bus", width=50, anchor="center")
        self.line_tree.column("vn_kv", width=70, anchor="e")
        self.line_tree.column("p_from_mw", width=80, anchor="e")
        self.line_tree.column("q_from_mvar", width=80, anchor="e")
        self.line_tree.column("i_from_ka", width=75, anchor="e")
        self.line_tree.column("p_to_mw", width=80, anchor="e")
        self.line_tree.column("q_to_mvar", width=80, anchor="e")
        self.line_tree.column("i_to_ka", width=75, anchor="e")
        self.line_tree.column("loading_percent", width=85, anchor="e")
        
        self.line_tree.pack(fill="both", expand=True, pady=5)

        # Table for transformer power flows
        trafo_columns = ("trafo", "name", "hv_bus", "lv_bus", "vn_hv_kv", "vn_lv_kv", "p_hv_mw", "q_hv_mvar", "i_hv_ka", "p_lv_mw", "q_lv_mvar", "i_lv_ka", "loading_percent")
        self.trafo_tree = ttk.Treeview(
            self.result_frame, columns=trafo_columns, show="headings", height=8
        )
        self.trafo_tree.heading("trafo", text="Trafo ID")
        self.trafo_tree.heading("name", text="Name")
        self.trafo_tree.heading("hv_bus", text="HV Bus")
        self.trafo_tree.heading("lv_bus", text="LV Bus")
        self.trafo_tree.heading("vn_hv_kv", text="HV kV")
        self.trafo_tree.heading("vn_lv_kv", text="LV kV")
        self.trafo_tree.heading("p_hv_mw", text="P HV (MW)")
        self.trafo_tree.heading("q_hv_mvar", text="Q HV (Mvar)")
        self.trafo_tree.heading("i_hv_ka", text="I HV (kA)")
        self.trafo_tree.heading("p_lv_mw", text="P LV (MW)")
        self.trafo_tree.heading("q_lv_mvar", text="Q LV (Mvar)")
        self.trafo_tree.heading("i_lv_ka", text="I LV (kA)")
        self.trafo_tree.heading("loading_percent", text="Loading (%)")
        
        # Configure column widths and alignment
        self.trafo_tree.column("trafo", width=50, anchor="center")
        self.trafo_tree.column("name", width=60, anchor="w")
        self.trafo_tree.column("hv_bus", width=50, anchor="center")
        self.trafo_tree.column("lv_bus", width=50, anchor="center")
        self.trafo_tree.column("vn_hv_kv", width=60, anchor="e")
        self.trafo_tree.column("vn_lv_kv", width=60, anchor="e")
        self.trafo_tree.column("p_hv_mw", width=75, anchor="e")
        self.trafo_tree.column("q_hv_mvar", width=75, anchor="e")
        self.trafo_tree.column("i_hv_ka", width=70, anchor="e")
        self.trafo_tree.column("p_lv_mw", width=75, anchor="e")
        self.trafo_tree.column("q_lv_mvar", width=75, anchor="e")
        self.trafo_tree.column("i_lv_ka", width=70, anchor="e")
        self.trafo_tree.column("loading_percent", width=85, anchor="e")
        
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
        ttk.Button(button_frame, text="Export Voltage Violations", command=self._export_voltage_violations).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Current Violations", command=self._export_current_violations).pack(side=tk.LEFT, padx=5)
        
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
        
        # Create notebook for separate violation types
        violations_notebook = ttk.Notebook(self.contingency_frame)
        violations_notebook.pack(fill="both", expand=True, pady=5, padx=10)
        
        # Voltage violations tab
        voltage_violations_frame = ttk.Frame(violations_notebook)
        violations_notebook.add(voltage_violations_frame, text="Voltage Violations")
        
        # Current/Overload violations tab
        current_violations_frame = ttk.Frame(violations_notebook)
        violations_notebook.add(current_violations_frame, text="Current/Overload Violations")
        
        # Visual legend for voltage violations
        voltage_legend_frame = ttk.Frame(voltage_violations_frame)
        voltage_legend_frame.pack(fill="x", pady=2)
        
        voltage_legend_text = tk.Text(voltage_legend_frame, height=2, width=120, state='disabled', font=("TkDefaultFont", 8))
        voltage_legend_text.pack(fill="x", pady=2)
        
        voltage_legend_text.config(state='normal')
        voltage_legend_text.insert(tk.END, "Voltage Indicators: ")
        voltage_legend_text.insert(tk.END, "🔺⬆️📈", "high_v_indicators")
        voltage_legend_text.insert(tk.END, " High Voltage  ")
        voltage_legend_text.insert(tk.END, "🔻⬇️📉🔋", "low_v_indicators")
        voltage_legend_text.insert(tk.END, " Low Voltage  ")
        voltage_legend_text.insert(tk.END, "✅", "ok_indicators")
        voltage_legend_text.insert(tk.END, " No Violations")
        voltage_legend_text.insert(tk.END, "\nSeverity: Critical (<0.95 or >1.05 p.u.)  High (<0.97 or >1.03 p.u.)  Medium (<0.98 or >1.02 p.u.)")
        
        voltage_legend_text.tag_configure("high_v_indicators", foreground="#ff4400", font=("TkDefaultFont", 8, "bold"))
        voltage_legend_text.tag_configure("low_v_indicators", foreground="#0066ff", font=("TkDefaultFont", 8, "bold"))
        voltage_legend_text.tag_configure("ok_indicators", foreground="#008000", font=("TkDefaultFont", 8, "bold"))
        voltage_legend_text.config(state='disabled')
        
        # Create voltage violations table
        voltage_columns = ("indicator", "contingency_type", "contingency_element", "bus_name", "voltage_pu", "limit", "severity")
        self.voltage_violations_tree = ttk.Treeview(
            voltage_violations_frame, columns=voltage_columns, show="headings", height=12
        )
        
        # Configure voltage violations headers
        self.voltage_violations_tree.heading("indicator", text="⚡")
        self.voltage_violations_tree.heading("contingency_type", text="Contingency Type")
        self.voltage_violations_tree.heading("contingency_element", text="Contingency Element")
        self.voltage_violations_tree.heading("bus_name", text="Bus Name")
        self.voltage_violations_tree.heading("voltage_pu", text="Voltage (p.u.)")
        self.voltage_violations_tree.heading("limit", text="Limit")
        self.voltage_violations_tree.heading("severity", text="Severity")
        
        # Configure voltage violations column widths
        self.voltage_violations_tree.column("indicator", width=50, anchor="center")
        self.voltage_violations_tree.column("contingency_type", width=140, anchor="w")
        self.voltage_violations_tree.column("contingency_element", width=180, anchor="w")
        self.voltage_violations_tree.column("bus_name", width=120, anchor="w")
        self.voltage_violations_tree.column("voltage_pu", width=120, anchor="e")
        self.voltage_violations_tree.column("limit", width=120, anchor="center")
        self.voltage_violations_tree.column("severity", width=100, anchor="center")
        
        # Add scrollbar for voltage violations
        voltage_scrollbar = ttk.Scrollbar(voltage_violations_frame, orient="vertical", command=self.voltage_violations_tree.yview)
        self.voltage_violations_tree.configure(yscrollcommand=voltage_scrollbar.set)
        
        self.voltage_violations_tree.pack(side="left", fill="both", expand=True)
        voltage_scrollbar.pack(side="right", fill="y")
        
        # Visual legend for current violations
        current_legend_frame = ttk.Frame(current_violations_frame)
        current_legend_frame.pack(fill="x", pady=2)
        
        current_legend_text = tk.Text(current_legend_frame, height=2, width=120, state='disabled', font=("TkDefaultFont", 8))
        current_legend_text.pack(fill="x", pady=2)
        
        current_legend_text.config(state='normal')
        current_legend_text.insert(tk.END, "Current/Overload Indicators: ")
        current_legend_text.insert(tk.END, "⚡🔥", "critical_i_indicators")
        current_legend_text.insert(tk.END, " Critical Overload  ")
        current_legend_text.insert(tk.END, "⚠️🌡️📊", "high_i_indicators")
        current_legend_text.insert(tk.END, " High Loading  ")
        current_legend_text.insert(tk.END, "✅", "ok_indicators")
        current_legend_text.insert(tk.END, " No Violations")
        current_legend_text.insert(tk.END, "\nSeverity: Critical (>120%)  High (>85%)  Medium (>75%)  Lines and Transformers")
        
        current_legend_text.tag_configure("critical_i_indicators", foreground="#ff0000", font=("TkDefaultFont", 8, "bold"))
        current_legend_text.tag_configure("high_i_indicators", foreground="#ff8800", font=("TkDefaultFont", 8, "bold"))
        current_legend_text.tag_configure("ok_indicators", foreground="#008000", font=("TkDefaultFont", 8, "bold"))
        current_legend_text.config(state='disabled')
        
        # Create current violations table
        current_columns = ("indicator", "contingency_type", "contingency_element", "element_type", "element_name", "loading_percent", "limit", "severity")
        self.current_violations_tree = ttk.Treeview(
            current_violations_frame, columns=current_columns, show="headings", height=12
        )
        
        # Configure current violations headers
        self.current_violations_tree.heading("indicator", text="⚡")
        self.current_violations_tree.heading("contingency_type", text="Contingency Type")
        self.current_violations_tree.heading("contingency_element", text="Contingency Element")
        self.current_violations_tree.heading("element_type", text="Element Type")
        self.current_violations_tree.heading("element_name", text="Element Name")
        self.current_violations_tree.heading("loading_percent", text="Loading (%)")
        self.current_violations_tree.heading("limit", text="Limit")
        self.current_violations_tree.heading("severity", text="Severity")
        
        # Configure current violations column widths
        self.current_violations_tree.column("indicator", width=50, anchor="center")
        self.current_violations_tree.column("contingency_type", width=140, anchor="w")
        self.current_violations_tree.column("contingency_element", width=180, anchor="w")
        self.current_violations_tree.column("element_type", width=100, anchor="center")
        self.current_violations_tree.column("element_name", width=140, anchor="w")
        self.current_violations_tree.column("loading_percent", width=120, anchor="e")
        self.current_violations_tree.column("limit", width=100, anchor="center")
        self.current_violations_tree.column("severity", width=100, anchor="center")
        
        # Add scrollbar for current violations
        current_scrollbar = ttk.Scrollbar(current_violations_frame, orient="vertical", command=self.current_violations_tree.yview)
        self.current_violations_tree.configure(yscrollcommand=current_scrollbar.set)
        
        self.current_violations_tree.pack(side="left", fill="both", expand=True)
        current_scrollbar.pack(side="right", fill="y")
        
        # Configure enhanced row colors for both tables
        for tree in [self.voltage_violations_tree, self.current_violations_tree]:
            tree.tag_configure("Critical", background="#ff4d4d", foreground="#ffffff", font=("TkDefaultFont", 9, "bold"))
            tree.tag_configure("High", background="#ff8800", foreground="#ffffff", font=("TkDefaultFont", 9, "bold"))
            tree.tag_configure("Medium", background="#ffcc00", foreground="#000000", font=("TkDefaultFont", 9))
            tree.tag_configure("Critical_stripe", background="#ff6666", foreground="#ffffff", font=("TkDefaultFont", 9, "bold"))
            tree.tag_configure("High_stripe", background="#ffaa33", foreground="#ffffff", font=("TkDefaultFont", 9, "bold"))
            tree.tag_configure("Medium_stripe", background="#ffdd33", foreground="#000000", font=("TkDefaultFont", 9))
            tree.tag_configure("no_violations", background="#d4edda", foreground="#155724", font=("TkDefaultFont", 9, "italic"))

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
    
    def run_powerflow_current(self) -> None:
        """Run power flow on the currently loaded grid."""
        if self.current_net is None:
            messagebox.showwarning("Warning", "No grid is currently loaded")
            return
        
        try:
            # Validate network has required components
            if len(self.current_net.bus) == 0:
                raise Exception("Network has no buses")
            
            # Ensure there's a slack bus
            has_slack = False
            if hasattr(self.current_net, 'ext_grid') and not self.current_net.ext_grid.empty:
                has_slack = True
            elif hasattr(self.current_net, 'gen') and not self.current_net.gen.empty:
                has_slack = any(self.current_net.gen['slack'])
            
            if not has_slack:
                # Add external grid to first bus as slack
                pp.create_ext_grid(self.current_net, bus=self.current_net.bus.index[0], vm_pu=1.0, name="Auto Slack")
                messagebox.showinfo("Info", f"Added automatic external grid to bus {self.current_net.bus.index[0]} for slack reference")
            
            # Run power flow
            pp.runpp(self.current_net, verbose=False)
            
            # Update displays
            self._display_results(self.current_net)
            if hasattr(self, '_refresh_edit_tables'):
                self._refresh_edit_tables()
            
            # Update grid status
            if self.current_grid_id:
                cur = self.db.conn.cursor()
                cur.execute("SELECT name FROM grids WHERE id = ?", (self.current_grid_id,))
                result = cur.fetchone()
                if result:
                    self.current_grid_label.config(text=result[0], foreground="green")
            
            messagebox.showinfo("Success", "Power flow calculation completed successfully")
            
        except pp.LoadflowNotConverged:
            messagebox.showerror("Power Flow Error", "Power flow did not converge.\nCheck network connectivity and generation/load balance.")
        except Exception as exc:
            messagebox.showerror("Error", f"Power flow calculation failed: {str(exc)}")

    def run_example_grid(self) -> None:
        try:
            net = create_example_grid()
            pp.runpp(net)
            self.current_net = net
            self.current_grid_id = None  # Not saved yet
            self.current_grid_label.config(text="Simple Example (unsaved)", foreground="orange")
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)
        self._refresh_edit_tables()

    def run_ieee_9_bus(self) -> None:
        try:
            net = create_ieee_9_bus()
            pp.runpp(net)
            self.current_net = net
            self.current_grid_id = None  # Not saved yet
            self.current_grid_label.config(text="IEEE 9-Bus (unsaved)", foreground="orange")
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)
        self._refresh_edit_tables()

    def run_ieee_39_bus(self) -> None:
        try:
            net = create_ieee_39_bus()
            pp.runpp(net)
            self.current_net = net
            self.current_grid_id = None  # Not saved yet
            self.current_grid_label.config(text="IEEE 39-Bus (unsaved)", foreground="orange")
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)

    def run_ieee_39_bus_standard(self) -> None:
        try:
            net = create_ieee_39_bus_standard()
            pp.runpp(net)
            self.current_net = net
            self.current_grid_id = None  # Not saved yet
            self.current_grid_label.config(text="IEEE 39-Bus Standard (unsaved)", foreground="orange")
        except Exception as exc:  # broad except to show message
            messagebox.showerror("Error", str(exc))
            return
        self._display_results(net)

    def run_state_estimator(self) -> None:
        """Run state estimation on IEEE 9-bus system and display results."""
        try:
            # Create IEEE 9-bus system
            net = create_ieee_9_bus()
            
            # Initialize state estimator
            estimator = StateEstimator(net)
            
            # Create measurement set (simple mode for better convergence)
            estimator.create_measurement_set_ieee9(simple_mode=True)
            
            # Run state estimation
            results = estimator.estimate_state()
            
            # Create results window
            self._show_state_estimation_results(estimator, results)
            
        except Exception as exc:
            messagebox.showerror("State Estimation Error", f"Error running state estimation: {str(exc)}")

    def _show_state_estimation_results(self, estimator: StateEstimator, results: dict) -> None:
        """Display state estimation results in a new window."""
        # Create new window
        results_window = tk.Toplevel(self.root)
        results_window.title("State Estimation Results - IEEE 9-Bus")
        results_window.geometry("900x700")
        
        # Create notebook for different result views
        notebook = ttk.Notebook(results_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary")
        
        summary_text = tk.Text(summary_frame, wrap=tk.WORD, font=("Courier", 10))
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=summary_text.yview)
        summary_text.configure(yscrollcommand=summary_scroll.set)
        
        # Add summary information
        summary_info = f"""State Estimation Results - IEEE 9-Bus System
{'='*60}

Convergence Information:
  Converged: {results['converged']}
  Iterations: {results['iterations']}
  Measurements: {results['measurements_count']}
  Objective Function: {results['objective_function']:.6f}

Algorithm: Weighted Least Squares (WLS)
Measurement Types: Voltage magnitudes, Power injections, Power flows
Noise Level: 0.5-2% of measurement values
"""
        summary_text.insert(tk.END, summary_info)
        summary_text.config(state=tk.DISABLED)
        
        summary_text.pack(side="left", fill="both", expand=True)
        summary_scroll.pack(side="right", fill="y")
        
        # Measurements tab
        measurements_frame = ttk.Frame(notebook)
        notebook.add(measurements_frame, text="Measurements")
        
        # Get measurement summary
        meas_df = estimator.get_measurement_summary()
        
        # Create treeview for measurements
        meas_columns = list(meas_df.columns)
        meas_tree = ttk.Treeview(measurements_frame, columns=meas_columns, show="headings", height=15)
        
        for col in meas_columns:
            meas_tree.heading(col, text=col)
            meas_tree.column(col, width=80 if col != "Type" else 120, anchor="center")
        
        # Add measurement data
        for _, row in meas_df.iterrows():
            meas_tree.insert("", "end", values=list(row))
        
        meas_scroll = ttk.Scrollbar(measurements_frame, orient="vertical", command=meas_tree.yview)
        meas_tree.configure(yscrollcommand=meas_scroll.set)
        
        meas_tree.pack(side="left", fill="both", expand=True)
        meas_scroll.pack(side="right", fill="y")
        
        # Comparison tab
        comparison_frame = ttk.Frame(notebook)
        notebook.add(comparison_frame, text="True vs Estimated")
        
        # Get comparison data
        comp_df = estimator.compare_with_true_state(results)
        
        if not comp_df.empty:
            # Create treeview for comparison
            comp_columns = list(comp_df.columns)
            comp_tree = ttk.Treeview(comparison_frame, columns=comp_columns, show="headings", height=15)
            
            for col in comp_columns:
                comp_tree.heading(col, text=col)
                comp_tree.column(col, width=100, anchor="center")
            
            # Add comparison data
            for _, row in comp_df.iterrows():
                comp_tree.insert("", "end", values=list(row))
            
            comp_scroll = ttk.Scrollbar(comparison_frame, orient="vertical", command=comp_tree.yview)
            comp_tree.configure(yscrollcommand=comp_scroll.set)
            
            comp_tree.pack(side="left", fill="both", expand=True)
            comp_scroll.pack(side="right", fill="y")

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
                        line_name = line_data.get("name", f"Line {idx}")
                        from_bus = int(line_data["from_bus"])
                        to_bus = int(line_data["to_bus"])
                        # Get voltage level from the from_bus
                        if from_bus in net.bus.index:
                            vn_kv = net.bus.loc[from_bus, "vn_kv"]
                        else:
                            vn_kv = 0.0
                    else:
                        line_name = f"Line {idx}"
                        from_bus = 0
                        to_bus = 0
                        vn_kv = 0.0
                    
                    # Get result data with safe access
                    p_from_mw = round(float(row.get("p_from_mw", 0.0)), 3)
                    q_from_mvar = round(float(row.get("q_from_mvar", 0.0)), 3)
                    i_from_ka = round(float(row.get("i_from_ka", 0.0)), 4)
                    p_to_mw = round(float(row.get("p_to_mw", 0.0)), 3)
                    q_to_mvar = round(float(row.get("q_to_mvar", 0.0)), 3)
                    i_to_ka = round(float(row.get("i_to_ka", 0.0)), 4)
                    loading_percent = round(float(row.get("loading_percent", 0.0)), 1)
                    
                    self.line_tree.insert(
                        "",
                        "end",
                        values=(idx, line_name, from_bus, to_bus, vn_kv, p_from_mw, q_from_mvar, i_from_ka, p_to_mw, q_to_mvar, i_to_ka, loading_percent),
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
                        vn_hv_kv = trafo_data.get("vn_hv_kv", 0.0)
                        vn_lv_kv = trafo_data.get("vn_lv_kv", 0.0)
                    else:
                        trafo_name = f"Trafo {idx}"
                        hv_bus = 0
                        lv_bus = 0
                        vn_hv_kv = 0.0
                        vn_lv_kv = 0.0
                    
                    # Get result data with safe access
                    p_hv_mw = round(float(row.get("p_hv_mw", 0.0)), 3)
                    q_hv_mvar = round(float(row.get("q_hv_mvar", 0.0)), 3)
                    i_hv_ka = round(float(row.get("i_hv_ka", 0.0)), 4)
                    p_lv_mw = round(float(row.get("p_lv_mw", 0.0)), 3)
                    q_lv_mvar = round(float(row.get("q_lv_mvar", 0.0)), 3)
                    i_lv_ka = round(float(row.get("i_lv_ka", 0.0)), 4)
                    loading_percent = round(float(row.get("loading_percent", 0.0)), 1)
                    
                    self.trafo_tree.insert(
                        "",
                        "end",
                        values=(idx, trafo_name, hv_bus, lv_bus, vn_hv_kv, vn_lv_kv, p_hv_mw, q_hv_mvar, i_hv_ka, p_lv_mw, q_lv_mvar, i_lv_ka, loading_percent),
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
            self._display_separate_violations(contingency.violations)
            
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
    
    def _display_separate_violations(self, violations):
        """Display detailed violations in separate voltage and current tables."""
        # Clear previous violations
        for item in self.voltage_violations_tree.get_children():
            self.voltage_violations_tree.delete(item)
        for item in self.current_violations_tree.get_children():
            self.current_violations_tree.delete(item)
        
        if not violations:
            # Add messages if no violations found
            self.voltage_violations_tree.insert(
                "", "end",
                values=("✅", "No voltage violations detected", "", "", "", "0.97-1.03 p.u.", "System OK"),
                tags=("no_violations",)
            )
            self.current_violations_tree.insert(
                "", "end",
                values=("✅", "No current violations detected", "", "", "", "", "85%", "System OK"),
                tags=("no_violations",)
            )
            return
        
        # Sort violations by severity (Critical first, then High, then Medium)
        severity_order = {'Critical': 0, 'High': 1, 'Medium': 2}
        sorted_violations = sorted(violations, key=lambda x: severity_order.get(x['severity'], 3))
        
        # Separate violations by type
        voltage_violations = [v for v in sorted_violations if 'Voltage' in v['violation_type']]
        current_violations = [v for v in sorted_violations if 'Overload' in v['violation_type']]
        
        # Display voltage violations
        if not voltage_violations:
            self.voltage_violations_tree.insert(
                "", "end",
                values=("✅", "No voltage violations detected", "", "", "", "0.95-1.05 p.u.", "System OK"),
                tags=("no_violations",)
            )
        else:
            for i, violation in enumerate(voltage_violations):
                severity = violation['severity']
                violation_type = violation['violation_type']
                
                # Visual indicators for voltage violations
                if severity == 'Critical':
                    if violation_type == 'Low Voltage':
                        indicator = "🔻"  # Down arrow for low voltage
                    else:  # High Voltage
                        indicator = "🔺"  # Up arrow for high voltage  
                    tag = 'Critical' if i % 2 == 0 else 'Critical_stripe'
                elif severity == 'High':
                    if violation_type == 'Low Voltage':
                        indicator = "⬇️"   # Down arrow for low voltage
                    else:  # High Voltage
                        indicator = "⬆️"   # Up arrow for high voltage
                    tag = 'High' if i % 2 == 0 else 'High_stripe'
                else:  # Medium
                    if violation_type == 'Low Voltage':
                        indicator = "📉"  # Chart down for medium low voltage
                    else:  # High Voltage
                        indicator = "📈"  # Chart up for medium high voltage
                    tag = 'Medium' if i % 2 == 0 else 'Medium_stripe'
                
                # Format voltage value with indicators
                voltage_value = violation['violation_value']
                if 'p.u.' in voltage_value:
                    try:
                        current_val = float(voltage_value.replace(' p.u.', ''))
                        if current_val < 0.90:
                            voltage_value += " 🔋"  # Battery low for very low voltage
                        elif current_val > 1.10:
                            voltage_value += " ⚡"  # Lightning for very high voltage
                    except:
                        pass
                
                self.voltage_violations_tree.insert(
                    "", "end",
                    values=(
                        indicator,
                        violation['contingency_type'],
                        violation['contingency_element'],
                        violation['element_name'],
                        voltage_value,
                        violation['limit_value'],
                        violation['severity']
                    ),
                    tags=(tag,)
                )
        
        # Display current violations
        if not current_violations:
            self.current_violations_tree.insert(
                "", "end",
                values=("✅", "No current violations detected", "", "", "", "", "100%", "System OK"),
                tags=("no_violations",)
            )
        else:
            for i, violation in enumerate(current_violations):
                severity = violation['severity']
                
                # Visual indicators for current violations
                if severity == 'Critical':
                    indicator = "⚡"  # Lightning for critical overload
                    tag = 'Critical' if i % 2 == 0 else 'Critical_stripe'
                elif severity == 'High':
                    indicator = "⚠️"   # Warning for high overload
                    tag = 'High' if i % 2 == 0 else 'High_stripe'
                else:  # Medium
                    indicator = "📊"  # Chart for medium overload
                    tag = 'Medium' if i % 2 == 0 else 'Medium_stripe'
                
                # Format loading value with indicators
                loading_value = violation['violation_value']
                if '%' in loading_value:
                    try:
                        current_val = float(loading_value.replace('%', ''))
                        if current_val > 150:
                            loading_value += " 🔥"  # Fire for severe overload
                        elif current_val > 120:
                            loading_value += " 🌡️"   # Thermometer for high overload
                    except:
                        pass
                
                self.current_violations_tree.insert(
                    "", "end",
                    values=(
                        indicator,
                        violation['contingency_type'],
                        violation['contingency_element'],
                        violation['element_type'],
                        violation['element_name'],
                        loading_value,
                        violation['limit_value'],
                        violation['severity']
                    ),
                    tags=(tag,)
                )
    
    def _export_voltage_violations(self):
        """Export voltage violations to CSV file."""
        if not hasattr(self, 'voltage_violations_tree') or not self.voltage_violations_tree.get_children():
            messagebox.showinfo("Info", "No voltage violations to export")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Export Voltage Violations",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                import csv
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    headers = ["Indicator", "Contingency Type", "Contingency Element", "Bus Name", 
                              "Voltage (p.u.)", "Limit", "Severity"]
                    writer.writerow(headers)
                    
                    # Write data
                    for item in self.voltage_violations_tree.get_children():
                        values = self.voltage_violations_tree.item(item, "values")
                        writer.writerow(values)
                
                messagebox.showinfo("Success", f"Voltage violations exported to {filename}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export voltage violations: {e}")

    def _export_current_violations(self):
        """Export current/overload violations to CSV file."""
        if not hasattr(self, 'current_violations_tree') or not self.current_violations_tree.get_children():
            messagebox.showinfo("Info", "No current violations to export")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                title="Export Current Violations",
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
            )
            
            if filename:
                import csv
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    headers = ["Indicator", "Contingency Type", "Contingency Element", "Element Type", 
                              "Element Name", "Loading (%)", "Limit", "Severity"]
                    writer.writerow(headers)
                    
                    # Write data
                    for item in self.current_violations_tree.get_children():
                        values = self.current_violations_tree.item(item, "values")
                        writer.writerow(values)
                
                messagebox.showinfo("Success", f"Current violations exported to {filename}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export current violations: {e}")
    
    def _build_state_estimation_widgets(self) -> None:
        """Build the state estimation interface."""
        # Title
        title_frame = ttk.Frame(self.state_estimation_frame)
        title_frame.pack(fill="x", pady=10)
        ttk.Label(title_frame, text="Power System State Estimation", font=("Arial", 14, "bold")).pack()
        
        # Grid selection frame
        grid_frame = ttk.LabelFrame(self.state_estimation_frame, text="Grid Selection")
        grid_frame.pack(fill="x", pady=5, padx=10)
        
        # Grid selection
        selection_frame = ttk.Frame(grid_frame)
        selection_frame.pack(fill="x", pady=5)
        
        ttk.Label(selection_frame, text="Select Grid:").pack(side=tk.LEFT)
        self.se_grid_var = tk.StringVar()
        self.se_grid_combo = ttk.Combobox(selection_frame, textvariable=self.se_grid_var, state="readonly", width=40)
        self.se_grid_combo.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(selection_frame, text="Use Current Grid", command=self._se_use_current_grid).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_frame, text="Refresh Grid List", command=self._se_refresh_grids).pack(side=tk.LEFT, padx=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(self.state_estimation_frame, text="Estimation Configuration")
        config_frame.pack(fill="x", pady=5, padx=10)
        
        # Mode selection
        mode_frame = ttk.Frame(config_frame)
        mode_frame.pack(fill="x", pady=5)
        
        ttk.Label(mode_frame, text="Mode:").pack(side=tk.LEFT)
        self.se_mode_var = tk.StringVar(value="voltage_only")
        ttk.Radiobutton(mode_frame, text="Voltage Only", variable=self.se_mode_var, value="voltage_only").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Comprehensive", variable=self.se_mode_var, value="comprehensive").pack(side=tk.LEFT, padx=10)
        
        # Parameters frame
        params_frame = ttk.Frame(config_frame)
        params_frame.pack(fill="x", pady=5)
        
        ttk.Label(params_frame, text="Voltage Noise (%):").pack(side=tk.LEFT)
        self.se_voltage_noise_var = tk.StringVar(value="1.0")
        ttk.Entry(params_frame, textvariable=self.se_voltage_noise_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(params_frame, text="Power Noise (%):").pack(side=tk.LEFT, padx=10)
        self.se_power_noise_var = tk.StringVar(value="2.0")
        ttk.Entry(params_frame, textvariable=self.se_power_noise_var, width=8).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(params_frame, text="Max Iterations:").pack(side=tk.LEFT, padx=10)
        self.se_max_iter_var = tk.StringVar(value="20")
        ttk.Entry(params_frame, textvariable=self.se_max_iter_var, width=8).pack(side=tk.LEFT, padx=5)
        
        # Run estimation frame
        run_frame = ttk.Frame(self.state_estimation_frame)
        run_frame.pack(fill="x", pady=10, padx=10)
        
        ttk.Button(run_frame, text="Run State Estimation", command=self._run_state_estimation, 
                  style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(run_frame, text="View Results", command=self._view_se_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(run_frame, text="Export Results", command=self._export_se_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(run_frame, text="Clear History", command=self._clear_se_history).pack(side=tk.LEFT, padx=5)
        
        # Status frame
        status_frame = ttk.LabelFrame(self.state_estimation_frame, text="Status")
        status_frame.pack(fill="x", pady=5, padx=10)
        
        self.se_status_label = ttk.Label(status_frame, text="Ready to run state estimation")
        self.se_status_label.pack(pady=5)
        
        # Results summary frame
        summary_frame = ttk.LabelFrame(self.state_estimation_frame, text="Latest Results Summary")
        summary_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        # Results text area
        self.se_results_text = tk.Text(summary_frame, height=8, wrap=tk.WORD, font=("Courier", 9))
        se_scrollbar = ttk.Scrollbar(summary_frame, orient="vertical", command=self.se_results_text.yview)
        self.se_results_text.configure(yscrollcommand=se_scrollbar.set)
        
        self.se_results_text.pack(side="left", fill="both", expand=True)
        se_scrollbar.pack(side="right", fill="y")
        
        # Initialize grid list
        self._se_refresh_grids()

    def _build_grid_manager_widgets(self) -> None:
        """Build the grid management interface."""
        # Title
        title_frame = ttk.Frame(self.grid_frame)
        title_frame.pack(fill="x", pady=10)
        ttk.Label(title_frame, text="Grid Database Manager", font=("Arial", 14, "bold")).pack()
        
        # Control panel
        control_frame = ttk.LabelFrame(self.grid_frame, text="Grid Operations")
        control_frame.pack(fill="x", pady=5, padx=10)
        
        # Current grid info
        current_frame = ttk.Frame(control_frame)
        current_frame.pack(fill="x", pady=5)
        
        ttk.Label(current_frame, text="Current Grid:").pack(side=tk.LEFT)
        self.current_grid_label = ttk.Label(current_frame, text="None loaded", foreground="red")
        self.current_grid_label.pack(side=tk.LEFT, padx=10)
        
        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill="x", pady=5)
        
        ttk.Button(button_frame, text="Save Current Grid", command=self._save_current_grid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Selected Grid", command=self._load_selected_grid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected Grid", command=self._delete_selected_grid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Refresh List", command=self._refresh_grid_list).pack(side=tk.LEFT, padx=5)
        
        # Grid list
        list_frame = ttk.LabelFrame(self.grid_frame, text="Saved Grids")
        list_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        # Create grid list table
        grid_columns = ("id", "name", "description", "type", "created", "modified")
        self.grid_tree = ttk.Treeview(
            list_frame, columns=grid_columns, show="headings", height=15
        )
        
        # Configure headers
        self.grid_tree.heading("id", text="ID")
        self.grid_tree.heading("name", text="Grid Name")
        self.grid_tree.heading("description", text="Description")
        self.grid_tree.heading("type", text="Type")
        self.grid_tree.heading("created", text="Created")
        self.grid_tree.heading("modified", text="Modified")
        
        # Configure column widths
        self.grid_tree.column("id", width=50, anchor="center")
        self.grid_tree.column("name", width=200, anchor="w")
        self.grid_tree.column("description", width=300, anchor="w")
        self.grid_tree.column("type", width=80, anchor="center")
        self.grid_tree.column("created", width=150, anchor="center")
        self.grid_tree.column("modified", width=150, anchor="center")
        
        # Add scrollbar
        grid_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.grid_tree.yview)
        self.grid_tree.configure(yscrollcommand=grid_scrollbar.set)
        
        self.grid_tree.pack(side="left", fill="both", expand=True)
        grid_scrollbar.pack(side="right", fill="y")
        
        # Configure row colors
        self.grid_tree.tag_configure("example", background="#e6f3ff", foreground="#000000")
        self.grid_tree.tag_configure("user", background="#ffffff", foreground="#000000")
        self.grid_tree.tag_configure("current", background="#90EE90", foreground="#000000", font=("TkDefaultFont", 9, "bold"))
        
        # Bind double-click to load grid
        self.grid_tree.bind("<Double-1>", self._on_grid_double_click)
        
        # Initial refresh
        self._refresh_grid_list()

    def _refresh_grid_list(self):
        """Refresh the grid list from database."""
        # Clear existing items
        for item in self.grid_tree.get_children():
            self.grid_tree.delete(item)
        
        # Get all grids from database
        grids = self.db.get_all_grids()
        
        for grid_id, name, description, created, modified, is_example in grids:
            # Format dates
            try:
                created_date = datetime.fromisoformat(created).strftime("%Y-%m-%d %H:%M")
                modified_date = datetime.fromisoformat(modified).strftime("%Y-%m-%d %H:%M")
            except:
                created_date = created
                modified_date = modified
            
            grid_type = "Example" if is_example else "User"
            tag = "example" if is_example else "user"
            
            # Check if this is the current grid
            if self.current_grid_id == grid_id:
                tag = "current"
            
            self.grid_tree.insert(
                "", "end",
                values=(grid_id, name, description, grid_type, created_date, modified_date),
                tags=(tag,)
            )

    def _save_current_grid(self):
        """Save the current grid to database."""
        if self.current_net is None:
            messagebox.showwarning("Warning", "No grid loaded to save")
            return
        
        # Create save dialog
        save_dialog = tk.Toplevel(self.root)
        save_dialog.title("Save Grid")
        save_dialog.geometry("400x200")
        save_dialog.transient(self.root)
        save_dialog.grab_set()
        
        # Center the dialog
        save_dialog.update_idletasks()
        x = (save_dialog.winfo_screenwidth() // 2) - (400 // 2)
        y = (save_dialog.winfo_screenheight() // 2) - (200 // 2)
        save_dialog.geometry(f"400x200+{x}+{y}")
        
        ttk.Label(save_dialog, text="Grid Name:").pack(pady=5)
        name_var = tk.StringVar()
        name_entry = ttk.Entry(save_dialog, textvariable=name_var, width=40)
        name_entry.pack(pady=5)
        
        ttk.Label(save_dialog, text="Description:").pack(pady=5)
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(save_dialog, textvariable=desc_var, width=40)
        desc_entry.pack(pady=5)
        
        def save_grid():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Grid name is required")
                return
            
            description = desc_var.get().strip()
            
            try:
                grid_id = self.db.save_grid(name, self.current_net, description, False)
                self.current_grid_id = grid_id
                self.current_grid_label.config(text=name, foreground="green")
                save_dialog.destroy()
                self._refresh_grid_list()
                messagebox.showinfo("Success", f"Grid '{name}' saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save grid: {e}")
        
        def cancel():
            save_dialog.destroy()
        
        button_frame = ttk.Frame(save_dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Save", command=save_grid).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5)
        
        name_entry.focus()

    def _load_selected_grid(self):
        """Load the selected grid from database."""
        selection = self.grid_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a grid to load")
            return
        
        # Get selected grid ID
        item = selection[0]
        values = self.grid_tree.item(item, "values")
        grid_id = int(values[0])
        grid_name = values[1]
        
        try:
            net = self.db.load_grid(grid_id)
            if net is not None:
                # Validate and prepare network for power flow
                try:
                    # Check for basic network validity
                    if len(net.bus) == 0:
                        raise Exception("Network has no buses")
                    
                    # Ensure there's at least one slack bus or external grid
                    has_slack = False
                    if hasattr(net, 'ext_grid') and not net.ext_grid.empty:
                        has_slack = True
                    elif hasattr(net, 'gen') and not net.gen.empty:
                        has_slack = any(net.gen['slack'])
                    
                    if not has_slack:
                        # Add external grid to first bus as slack
                        pp.create_ext_grid(net, bus=net.bus.index[0], vm_pu=1.0, name="Auto Slack")
                        print(f"Added automatic external grid to bus {net.bus.index[0]} for slack reference")
                    
                    # Run power flow
                    pp.runpp(net, verbose=False)
                    
                    # Store the network
                    self.current_net = net
                    self.current_grid_id = grid_id
                    self.current_grid_label.config(text=grid_name, foreground="green")
                    
                    # Display results
                    self._display_results(net)
                    if hasattr(self, '_refresh_edit_tables'):
                        self._refresh_edit_tables()
                    self._refresh_grid_list()  # Refresh to highlight current grid
                    
                    messagebox.showinfo("Success", f"Grid '{grid_name}' loaded and analyzed successfully")
                    
                except pp.LoadflowNotConverged:
                    # Power flow didn't converge, but still load the network
                    self.current_net = net
                    self.current_grid_id = grid_id
                    self.current_grid_label.config(text=f"{grid_name} (No Conv.)", foreground="orange")
                    
                    # Display basic network info without results
                    self._display_network_info_only(net)
                    if hasattr(self, '_refresh_edit_tables'):
                        self._refresh_edit_tables()
                    self._refresh_grid_list()
                    
                    messagebox.showwarning("Warning", f"Grid '{grid_name}' loaded but power flow did not converge.\nCheck network connectivity and generation/load balance.")
                    
                except Exception as pf_error:
                    # Other power flow errors
                    self.current_net = net
                    self.current_grid_id = grid_id
                    self.current_grid_label.config(text=f"{grid_name} (Error)", foreground="red")
                    
                    # Display basic network info
                    self._display_network_info_only(net)
                    if hasattr(self, '_refresh_edit_tables'):
                        self._refresh_edit_tables()
                    self._refresh_grid_list()
                    
                    messagebox.showerror("Power Flow Error", f"Grid '{grid_name}' loaded but power flow failed:\n{str(pf_error)}")
                    
            else:
                messagebox.showerror("Error", "Failed to load grid from database")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load grid: {e}")

    def _delete_selected_grid(self):
        """Delete the selected grid from database."""
        selection = self.grid_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a grid to delete")
            return
        
        # Get selected grid info
        item = selection[0]
        values = self.grid_tree.item(item, "values")
        grid_id = int(values[0])
        grid_name = values[1]
        grid_type = values[3]
        
        # Prevent deletion of example grids
        if grid_type == "Example":
            messagebox.showwarning("Warning", "Cannot delete example grids")
            return
        
        # Confirm deletion
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete grid '{grid_name}'?\n\nThis action cannot be undone."):
            try:
                if self.db.delete_grid(grid_id):
                    if self.current_grid_id == grid_id:
                        self.current_grid_id = None
                        self.current_grid_label.config(text="None loaded", foreground="red")
                    self._refresh_grid_list()
                    messagebox.showinfo("Success", f"Grid '{grid_name}' deleted successfully")
                else:
                    messagebox.showerror("Error", "Failed to delete grid")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete grid: {e}")

    def _display_network_info_only(self, net: pp.pandapowerNet) -> None:
        """Display basic network information without power flow results."""
        # Clear results tables
        for item in self.bus_tree.get_children():
            self.bus_tree.delete(item)
        for item in self.line_tree.get_children():
            self.line_tree.delete(item)
        for item in self.trafo_tree.get_children():
            self.trafo_tree.delete(item)
        for item in self.gen_tree.get_children():
            self.gen_tree.delete(item)
        
        # Display bus information without results
        for idx, row in net.bus.iterrows():
            bus_name = row.get("name", f"Bus {idx}")
            vn_kv = row["vn_kv"]
            self.bus_tree.insert(
                "", "end",
                values=(idx, bus_name, vn_kv, "N/A", "N/A", "N/A", "N/A")
            )
        
        # Display line information without results
        for idx, row in net.line.iterrows():
            line_name = row.get("name", f"Line {idx}")
            from_bus = int(row["from_bus"])
            to_bus = int(row["to_bus"])
            # Get voltage level from the from_bus
            if from_bus in net.bus.index:
                vn_kv = net.bus.loc[from_bus, "vn_kv"]
            else:
                vn_kv = 0.0
            self.line_tree.insert(
                "", "end",
                values=(idx, line_name, from_bus, to_bus, vn_kv, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
            )
        
        # Display transformer information without results
        if hasattr(net, 'trafo') and not net.trafo.empty:
            for idx, row in net.trafo.iterrows():
                trafo_name = row.get("name", f"Trafo {idx}")
                hv_bus = int(row["hv_bus"])
                lv_bus = int(row["lv_bus"])
                vn_hv_kv = row.get("vn_hv_kv", 0.0)
                vn_lv_kv = row.get("vn_lv_kv", 0.0)
                self.trafo_tree.insert(
                    "", "end",
                    values=(idx, trafo_name, hv_bus, lv_bus, vn_hv_kv, vn_lv_kv, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A")
                )
        
        # Display generator information without results
        if hasattr(net, 'gen') and not net.gen.empty:
            for idx, row in net.gen.iterrows():
                gen_name = row.get("name", f"Gen {idx}")
                bus = int(row["bus"])
                p_mw = row["p_mw"]
                vm_pu = row.get("vm_pu", "N/A")
                is_slack = row.get("slack", False)
                slack_text = "Yes" if is_slack else "No"
                self.gen_tree.insert(
                    "", "end",
                    values=(idx, gen_name, bus, p_mw, "N/A", vm_pu, "N/A", slack_text)
                )
        
        # Update text output
        self.text.delete("1.0", tk.END)
        network_info = f"Network loaded but power flow not calculated\n"
        network_info += f"Buses: {len(net.bus)}\n"
        network_info += f"Lines: {len(net.line)}\n"
        if hasattr(net, 'trafo'):
            network_info += f"Transformers: {len(net.trafo)}\n"
        if hasattr(net, 'gen'):
            network_info += f"Generators: {len(net.gen)}\n"
        if hasattr(net, 'load'):
            network_info += f"Loads: {len(net.load)}\n"
        network_info += "\nNote: Run power flow to see electrical results"
        self.text.insert(tk.END, network_info)

    # State Estimation Methods
    def _se_refresh_grids(self):
        """Refresh the grid list for state estimation."""
        try:
            grids = self.state_estimation_module.get_available_grids()
            grid_names = [f"{grid[0]}: {grid[1]}" for grid in grids]
            self.se_grid_combo['values'] = grid_names
            
            if grid_names:
                self.se_grid_combo.set(grid_names[0])
        except Exception as e:
            self.se_status_label.config(text=f"Error loading grids: {e}")
    
    def _se_use_current_grid(self):
        """Use the currently loaded grid for state estimation."""
        if self.current_net is None:
            messagebox.showwarning("Warning", "No grid is currently loaded")
            return
        
        grid_name = "Current Grid"
        if hasattr(self, 'current_grid_label'):
            grid_name = self.current_grid_label.cget("text")
        
        self.se_grid_var.set(f"Current: {grid_name}")
        self.se_status_label.config(text="Ready to estimate current grid")
    
    def _run_state_estimation(self):
        """Run state estimation with current configuration."""
        try:
            # Update status
            self.se_status_label.config(text="Running state estimation...")
            self.root.update()
            
            # Create configuration
            mode_str = self.se_mode_var.get()
            mode = EstimationMode.VOLTAGE_ONLY if mode_str == "voltage_only" else EstimationMode.COMPREHENSIVE
            
            config = EstimationConfig(
                mode=mode,
                voltage_noise_std=float(self.se_voltage_noise_var.get()) / 100.0,
                power_noise_std=float(self.se_power_noise_var.get()) / 100.0,
                max_iterations=int(self.se_max_iter_var.get()),
                tolerance=1e-4,
                include_all_buses=True,
                include_power_injections=(mode == EstimationMode.COMPREHENSIVE),
                include_power_flows=(mode == EstimationMode.COMPREHENSIVE)
            )
            
            # Determine which grid to use
            selected_grid = self.se_grid_var.get()
            
            if selected_grid.startswith("Current:"):
                # Use current grid
                if self.current_net is None:
                    messagebox.showerror("Error", "No grid is currently loaded")
                    return
                
                grid_name = selected_grid.replace("Current: ", "")
                results = self.state_estimation_module.estimate_current_grid_state(
                    self.current_net, grid_name, config
                )
            else:
                # Use database grid
                grid_id = int(selected_grid.split(":")[0])
                results = self.state_estimation_module.estimate_grid_state(grid_id, config)
            
            # Display results
            self._display_se_results(results)
            
            if results.get('success', False):
                self.se_status_label.config(text="State estimation completed successfully")
            else:
                self.se_status_label.config(text=f"State estimation failed: {results.get('error', 'Unknown error')}")
                
        except Exception as e:
            self.se_status_label.config(text=f"Error: {e}")
            messagebox.showerror("State Estimation Error", str(e))
    
    def _display_se_results(self, results: Dict[str, Any]):
        """Display state estimation results in the summary area."""
        self.se_results_text.delete(1.0, tk.END)
        
        if not results.get('success', False):
            error_text = f"State Estimation Failed\n{'='*50}\nError: {results.get('error', 'Unknown error')}\n"
            self.se_results_text.insert(tk.END, error_text)
            return
        
        # Format results summary
        grid_info = results.get('grid_info', {})
        convergence = results.get('convergence', {})
        accuracy = results.get('accuracy_metrics', {})
        
        summary = f"""State Estimation Results
{'='*50}
Grid: {grid_info.get('name', 'Unknown')}
Time: {results.get('timestamp', 'Unknown')}

Convergence:
  Status: {'✓ Converged' if convergence.get('converged', False) else '✗ Failed'}
  Iterations: {convergence.get('iterations', 'N/A')}
  Measurements: {convergence.get('measurements_count', 'N/A')}
  Objective Function: {convergence.get('objective_function', 'N/A'):.6f}

Accuracy Metrics:
  Max Voltage Error: {accuracy.get('max_voltage_error_percent', 'N/A'):.2f}%
  Mean Voltage Error: {accuracy.get('mean_voltage_error_percent', 'N/A'):.2f}%
  RMS Voltage Error: {accuracy.get('rms_voltage_error_percent', 'N/A'):.2f}%

Configuration:
  Mode: {results.get('config', {}).mode.value if hasattr(results.get('config', {}), 'mode') else 'N/A'}
  Voltage Noise: {results.get('config', {}).voltage_noise_std * 100 if hasattr(results.get('config', {}), 'voltage_noise_std') else 'N/A'}%
  Max Iterations: {results.get('config', {}).max_iterations if hasattr(results.get('config', {}), 'max_iterations') else 'N/A'}
"""
        
        self.se_results_text.insert(tk.END, summary)
    
    def _view_se_results(self):
        """View detailed state estimation results in a new window."""
        current_results = self.state_estimation_module.get_current_results()
        
        if not current_results or not current_results.get('success', False):
            messagebox.showwarning("Warning", "No successful state estimation results available")
            return
        
        # Create detailed results window
        results_window = tk.Toplevel(self.root)
        results_window.title("State Estimation Results - Detailed View")
        results_window.geometry("1000x700")
        
        # Create notebook for different views
        notebook = ttk.Notebook(results_window)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_frame = ttk.Frame(notebook)
        notebook.add(summary_frame, text="Summary")
        
        summary_text = tk.Text(summary_frame, wrap=tk.WORD, font=("Courier", 10))
        summary_scroll = ttk.Scrollbar(summary_frame, orient="vertical", command=summary_text.yview)
        summary_text.configure(yscrollcommand=summary_scroll.set)
        
        # Add detailed summary
        self._format_detailed_summary(summary_text, current_results)
        summary_text.config(state=tk.DISABLED)
        
        summary_text.pack(side="left", fill="both", expand=True)
        summary_scroll.pack(side="right", fill="y")
        
        # Comparison tab
        if 'comparison' in current_results:
            comparison_frame = ttk.Frame(notebook)
            notebook.add(comparison_frame, text="True vs Estimated")
            
            # Create treeview for comparison data
            comp_data = current_results['comparison']
            if comp_data:
                comp_columns = list(comp_data[0].keys())
                comp_tree = ttk.Treeview(comparison_frame, columns=comp_columns, show="headings", height=20)
                
                for col in comp_columns:
                    comp_tree.heading(col, text=col)
                    comp_tree.column(col, width=100, anchor="center")
                
                for row in comp_data:
                    comp_tree.insert("", "end", values=list(row.values()))
                
                comp_scroll = ttk.Scrollbar(comparison_frame, orient="vertical", command=comp_tree.yview)
                comp_tree.configure(yscrollcommand=comp_scroll.set)
                
                comp_tree.pack(side="left", fill="both", expand=True)
                comp_scroll.pack(side="right", fill="y")
    
    def _format_detailed_summary(self, text_widget, results):
        """Format detailed summary for results viewing."""
        grid_info = results.get('grid_info', {})
        convergence = results.get('convergence', {})
        network_stats = results.get('network_stats', {})
        measurements = results.get('measurement_summary', [])
        
        detailed_text = f"""State Estimation Detailed Results
{'='*60}

Grid Information:
  Name: {grid_info.get('name', 'Unknown')}
  Description: {grid_info.get('description', 'N/A')}
  Analysis Time: {results.get('timestamp', 'Unknown')}

Network Statistics:
  Buses: {network_stats.get('buses', 'N/A')}
  Lines: {network_stats.get('lines', 'N/A')}
  Generators: {network_stats.get('generators', 'N/A')}
  Loads: {network_stats.get('loads', 'N/A')}
  Transformers: {network_stats.get('transformers', 'N/A')}

Convergence Details:
  Converged: {convergence.get('converged', False)}
  Iterations: {convergence.get('iterations', 'N/A')}
  Total Measurements: {convergence.get('measurements_count', 'N/A')}
  Objective Function: {convergence.get('objective_function', 'N/A'):.8f}

Measurement Breakdown:
"""
        
        # Add measurement type counts
        if measurements:
            measurement_types = {}
            for meas in measurements:
                mtype = meas.get('Type', 'Unknown')
                measurement_types[mtype] = measurement_types.get(mtype, 0) + 1
            
            for mtype, count in measurement_types.items():
                detailed_text += f"  {mtype}: {count} measurements\n"
        
        text_widget.insert(tk.END, detailed_text)
    
    def _export_se_results(self):
        """Export state estimation results to file."""
        try:
            current_results = self.state_estimation_module.get_current_results()
            
            if not current_results or not current_results.get('success', False):
                messagebox.showwarning("Warning", "No successful results to export")
                return
            
            # Export as CSV
            filename = self.state_estimation_module.export_results(current_results, 'csv')
            messagebox.showinfo("Success", f"Results exported to {filename}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export results: {e}")
    
    def _clear_se_history(self):
        """Clear state estimation history."""
        self.state_estimation_module.clear_history()
        self.se_results_text.delete(1.0, tk.END)
        self.se_status_label.config(text="History cleared - ready for new estimation")

    def _on_grid_double_click(self, event):
        """Handle double-click on grid list to load grid."""
        self._load_selected_grid()


def main() -> None:
    root = tk.Tk()
    db = GridDatabase()
    app = GridApp(root, db)
    root.mainloop()


if __name__ == "__main__":
    main()
