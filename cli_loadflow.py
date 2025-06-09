#!/usr/bin/env python3
"""Command-line interface for power system load flow calculations."""

import argparse
import sys
import os
from typing import Optional, List, Dict, Any
import pandas as pd
import pandapower as pp
from tabulate import tabulate

from database import GridDatabase
from examples import create_example_grid, create_ieee_9_bus, create_ieee_39_bus, create_ieee_39_bus_standard
from contingency import ContingencyAnalysis
from convergence_diagnostic import ConvergenceDiagnostic


class TerminalLoadFlow:
    """Terminal-based load flow calculator."""
    
    def __init__(self):
        self.db = GridDatabase()
        self.current_net = None
        self.current_grid_name = None
        
    def load_example_grid(self, grid_type: str) -> bool:
        """Load an example grid."""
        try:
            if grid_type.lower() == "simple":
                self.current_net = create_example_grid()
                self.current_grid_name = "Simple Example Grid"
            elif grid_type.lower() == "ieee9":
                self.current_net = create_ieee_9_bus()
                self.current_grid_name = "IEEE 9-Bus Test System"
            elif grid_type.lower() == "ieee39":
                self.current_net = create_ieee_39_bus()
                self.current_grid_name = "IEEE 39-Bus New England System"
            elif grid_type.lower() == "ieee39std":
                self.current_net = create_ieee_39_bus_standard()
                self.current_grid_name = "IEEE 39-Bus Standard (MATPOWER-based)"
            else:
                print(f"Error: Unknown grid type '{grid_type}'")
                print("Available types: simple, ieee9, ieee39, ieee39std")
                return False
                
            print(f"✓ Loaded {self.current_grid_name}")
            return True
            
        except Exception as e:
            print(f"Error loading grid: {e}")
            return False
    
    def load_database_grid(self, grid_name: str) -> bool:
        """Load a grid from the database by name."""
        try:
            grids = self.db.get_all_grids()
            grid_id = None
            
            for gid, name, desc, created, modified, is_example in grids:
                if name.lower() == grid_name.lower():
                    grid_id = gid
                    break
            
            if grid_id is None:
                print(f"Error: Grid '{grid_name}' not found in database")
                self.list_available_grids()
                return False
            
            self.current_net = self.db.load_grid(grid_id)
            if self.current_net is None:
                print(f"Error: Failed to load grid '{grid_name}' from database")
                return False
                
            self.current_grid_name = grid_name
            print(f"✓ Loaded '{grid_name}' from database")
            return True
            
        except Exception as e:
            print(f"Error loading grid from database: {e}")
            return False
    
    def list_available_grids(self):
        """List all available grids in the database."""
        try:
            grids = self.db.get_all_grids()
            if not grids:
                print("No grids found in database")
                return
                
            print("\nAvailable grids in database:")
            headers = ["ID", "Name", "Type", "Created", "Modified"]
            table_data = []
            
            for grid_id, name, desc, created, modified, is_example in grids:
                grid_type = "Example" if is_example else "User"
                # Format dates
                try:
                    from datetime import datetime
                    created_date = datetime.fromisoformat(created).strftime("%Y-%m-%d")
                    modified_date = datetime.fromisoformat(modified).strftime("%Y-%m-%d")
                except:
                    created_date = created[:10] if len(created) > 10 else created
                    modified_date = modified[:10] if len(modified) > 10 else modified
                
                table_data.append([grid_id, name, grid_type, created_date, modified_date])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
        except Exception as e:
            print(f"Error listing grids: {e}")
    
    def run_load_flow(self) -> bool:
        """Run power flow calculation on the current grid."""
        if self.current_net is None:
            print("Error: No grid loaded. Use --grid or --load-db to load a grid first.")
            return False
        
        try:
            # Ensure there's a slack bus
            has_slack = False
            if hasattr(self.current_net, 'ext_grid') and not self.current_net.ext_grid.empty:
                has_slack = True
            elif hasattr(self.current_net, 'gen') and not self.current_net.gen.empty:
                has_slack = any(self.current_net.gen['slack'])
            
            if not has_slack:
                # Add external grid to first bus as slack
                pp.create_ext_grid(self.current_net, bus=self.current_net.bus.index[0], vm_pu=1.0, name="Auto Slack")
                print(f"ℹ Added automatic external grid to bus {self.current_net.bus.index[0]} for slack reference")
            
            # Run power flow with enhanced settings for better convergence
            try:
                pp.runpp(self.current_net, verbose=False)
                print("✓ Power flow calculation completed successfully")
                return True
            except pp.LoadflowNotConverged:
                # Try with more iterations and relaxed tolerance
                try:
                    pp.runpp(self.current_net, max_iteration=100, tolerance_mva=1e-3, verbose=False)
                    print("✓ Power flow calculation completed successfully (with enhanced solver settings)")
                    return True
                except pp.LoadflowNotConverged:
                    # Try with even more relaxed settings
                    try:
                        pp.runpp(self.current_net, max_iteration=100, tolerance_mva=1e-2, verbose=False)
                        print("✓ Power flow calculation completed successfully (with relaxed tolerance)")
                        return True
                    except:
                        raise pp.LoadflowNotConverged("Failed with all solver configurations")
            
        except pp.LoadflowNotConverged:
            print("✗ Power flow did not converge")
            print("  Check network connectivity and generation/load balance")
            return False
        except Exception as e:
            print(f"✗ Power flow calculation failed: {e}")
            return False
    
    def display_results(self, detailed: bool = False):
        """Display power flow results."""
        if self.current_net is None:
            print("Error: No grid loaded")
            return
        
        if not hasattr(self.current_net, 'res_bus'):
            print("Error: No power flow results available. Run load flow first.")
            return
        
        print(f"\n{'='*60}")
        print(f"POWER FLOW RESULTS: {self.current_grid_name}")
        print(f"{'='*60}")
        
        # System summary
        self._display_system_summary()
        
        # Bus results
        self._display_bus_results(detailed)
        
        # Line results
        if hasattr(self.current_net, 'res_line') and not self.current_net.res_line.empty:
            self._display_line_results(detailed)
        
        # Transformer results
        if hasattr(self.current_net, 'res_trafo') and not self.current_net.res_trafo.empty:
            self._display_transformer_results(detailed)
        
        # Generator results
        if hasattr(self.current_net, 'res_gen') and not self.current_net.res_gen.empty:
            self._display_generator_results(detailed)
    
    def _display_system_summary(self):
        """Display system summary statistics."""
        net = self.current_net
        
        print(f"\nSYSTEM SUMMARY:")
        print(f"  Buses: {len(net.bus)}")
        print(f"  Lines: {len(net.line) if hasattr(net, 'line') else 0}")
        print(f"  Transformers: {len(net.trafo) if hasattr(net, 'trafo') else 0}")
        print(f"  Generators: {len(net.gen) if hasattr(net, 'gen') else 0}")
        print(f"  Loads: {len(net.load) if hasattr(net, 'load') else 0}")
        
        if hasattr(net, 'res_bus'):
            max_v = net.res_bus['vm_pu'].max()
            min_v = net.res_bus['vm_pu'].min()
            print(f"  Voltage range: {min_v:.3f} - {max_v:.3f} p.u.")
        
        if hasattr(net, 'res_gen') and not net.res_gen.empty:
            total_gen = net.res_gen['p_mw'].sum()
            print(f"  Total generation: {total_gen:.1f} MW")
        
        if hasattr(net, 'load') and not net.load.empty:
            total_load = net.load['p_mw'].sum()
            print(f"  Total load: {total_load:.1f} MW")
    
    def _display_bus_results(self, detailed: bool):
        """Display bus voltage results."""
        net = self.current_net
        
        print(f"\nBUS VOLTAGE RESULTS:")
        
        if detailed:
            # Detailed table with all buses
            headers = ["Bus ID", "Name", "Vn (kV)", "V (p.u.)", "Angle (°)", "P (MW)", "Q (Mvar)"]
            table_data = []
            
            for idx, row in net.res_bus.iterrows():
                if idx in net.bus.index:
                    bus_data = net.bus.loc[idx]
                    bus_name = bus_data.get("name", f"Bus {idx}")
                    vn_kv = bus_data["vn_kv"]
                else:
                    bus_name = f"Bus {idx}"
                    vn_kv = 0.0
                
                vm_pu = row["vm_pu"]
                va_degree = row["va_degree"]
                p_mw = row["p_mw"]
                q_mvar = row["q_mvar"]
                
                table_data.append([
                    idx, bus_name, f"{vn_kv:.1f}", f"{vm_pu:.3f}", 
                    f"{va_degree:.1f}", f"{p_mw:.2f}", f"{q_mvar:.2f}"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Summary statistics only
            voltages = net.res_bus['vm_pu']
            print(f"  Buses analyzed: {len(voltages)}")
            print(f"  Max voltage: {voltages.max():.3f} p.u.")
            print(f"  Min voltage: {voltages.min():.3f} p.u.")
            print(f"  Average voltage: {voltages.mean():.3f} p.u.")
            
            # Voltage violations
            low_violations = len(voltages[voltages < 0.97])
            high_violations = len(voltages[voltages > 1.03])
            if low_violations > 0 or high_violations > 0:
                print(f"  ⚠ Voltage violations: {low_violations} low, {high_violations} high")
    
    def _display_line_results(self, detailed: bool):
        """Display line power flow results."""
        net = self.current_net
        
        print(f"\nLINE FLOW RESULTS:")
        
        if detailed:
            headers = ["Line ID", "From", "To", "Vn (kV)", "P from (MW)", "Q from (Mvar)", 
                      "I from (kA)", "Loading (%)"]
            table_data = []
            
            for idx, row in net.res_line.iterrows():
                if idx in net.line.index:
                    line_data = net.line.loc[idx]
                    from_bus = int(line_data["from_bus"])
                    to_bus = int(line_data["to_bus"])
                    # Get voltage level from from_bus
                    if from_bus in net.bus.index:
                        vn_kv = net.bus.loc[from_bus, "vn_kv"]
                    else:
                        vn_kv = 0.0
                else:
                    from_bus = 0
                    to_bus = 0
                    vn_kv = 0.0
                
                p_from_mw = row["p_from_mw"]
                q_from_mvar = row["q_from_mvar"]
                i_from_ka = row["i_from_ka"]
                loading_percent = row["loading_percent"]
                
                table_data.append([
                    idx, from_bus, to_bus, f"{vn_kv:.0f}", f"{p_from_mw:.2f}", 
                    f"{q_from_mvar:.2f}", f"{i_from_ka:.4f}", f"{loading_percent:.1f}"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Summary statistics
            loadings = net.res_line['loading_percent']
            print(f"  Lines analyzed: {len(loadings)}")
            print(f"  Max loading: {loadings.max():.1f}%")
            print(f"  Average loading: {loadings.mean():.1f}%")
            
            # Overload violations
            overloads = len(loadings[loadings > 85])
            if overloads > 0:
                print(f"  ⚠ Overloaded lines (>85%): {overloads}")
    
    def _display_transformer_results(self, detailed: bool):
        """Display transformer results."""
        net = self.current_net
        
        print(f"\nTRANSFORMER RESULTS:")
        
        if detailed:
            headers = ["Trafo ID", "Name", "HV Bus", "LV Bus", "HV kV", "LV kV", 
                      "P HV (MW)", "Loading (%)"]
            table_data = []
            
            for idx, row in net.res_trafo.iterrows():
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
                
                p_hv_mw = row["p_hv_mw"]
                loading_percent = row["loading_percent"]
                
                table_data.append([
                    idx, trafo_name, hv_bus, lv_bus, f"{vn_hv_kv:.0f}", 
                    f"{vn_lv_kv:.0f}", f"{p_hv_mw:.2f}", f"{loading_percent:.1f}"
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Summary statistics
            loadings = net.res_trafo['loading_percent']
            print(f"  Transformers analyzed: {len(loadings)}")
            print(f"  Max loading: {loadings.max():.1f}%")
            print(f"  Average loading: {loadings.mean():.1f}%")
            
            # Overload violations
            overloads = len(loadings[loadings > 85])
            if overloads > 0:
                print(f"  ⚠ Overloaded transformers (>85%): {overloads}")
    
    def _display_generator_results(self, detailed: bool):
        """Display generator results."""
        net = self.current_net
        
        print(f"\nGENERATOR RESULTS:")
        
        if detailed:
            headers = ["Gen ID", "Name", "Bus", "P (MW)", "Q (Mvar)", "V (p.u.)", "Slack"]
            table_data = []
            
            for idx, row in net.res_gen.iterrows():
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
                
                p_mw = row["p_mw"]
                q_mvar = row["q_mvar"]
                vm_pu = row["vm_pu"]
                
                table_data.append([
                    idx, gen_name, bus, f"{p_mw:.2f}", f"{q_mvar:.2f}", 
                    f"{vm_pu:.3f}", slack_text
                ])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            # Summary statistics
            total_p = net.res_gen['p_mw'].sum()
            total_q = net.res_gen['q_mvar'].sum()
            print(f"  Generators: {len(net.res_gen)}")
            print(f"  Total active power: {total_p:.1f} MW")
            print(f"  Total reactive power: {total_q:.1f} Mvar")
    
    def _display_base_case_loading(self, base_case: Dict[str, Any]):
        """Display base case loading information."""
        print(f"\nBASE CASE LOADING:")
        print(f"  Status: {'✓ Converged' if base_case['converged'] else '✗ Failed to converge'}")
        print(f"  Voltage range: {base_case.get('min_voltage_pu', 0):.3f} - {base_case.get('max_voltage_pu', 0):.3f} p.u.")
        print(f"  Max line loading: {base_case.get('max_line_loading', 0):.1f}%")
        print(f"  Max transformer loading: {base_case.get('max_trafo_loading', 0):.1f}%")
        print(f"  Total generation: {base_case.get('total_generation_mw', 0):.1f} MW")
        print(f"  Total load: {base_case.get('total_load_mw', 0):.1f} MW")
        
        # Display any base case violations
        voltage_viol = base_case.get('voltage_violations', 0)
        overload_viol = base_case.get('overload_violations', 0)
        
        if voltage_viol > 0 or overload_viol > 0:
            print(f"  ⚠ Base case violations: {voltage_viol} voltage, {overload_viol} overload")
            print(f"  Base case severity: {base_case.get('severity', 'Unknown')}")
        else:
            print(f"  ✓ No base case violations")
    
    def run_base_case_analysis(self):
        """Run base case analysis only (no contingencies)."""
        if self.current_net is None:
            print("Error: No grid loaded")
            return False
        
        try:
            print(f"\nRunning base case analysis on {self.current_grid_name}...")
            
            contingency = ContingencyAnalysis(self.current_net)
            base_case = contingency._analyze_base_case()
            
            if not base_case:
                print("Failed to analyze base case")
                return False
            
            # Display base case information
            self._display_base_case_loading(base_case)
            
            # Display base case violations in detail if any exist
            if base_case.get('voltage_violations', 0) > 0 or base_case.get('overload_violations', 0) > 0:
                # Collect violations to show details
                if not contingency.violations:  # Only collect if not already collected
                    contingency._collect_detailed_violations(self.current_net, 'Base Case', 'No outages')
                
                if contingency.violations:
                    print(f"\nBASE CASE VIOLATIONS DETAIL:")
                    
                    voltage_violations = [v for v in contingency.violations if 'Voltage' in v['violation_type']]
                    current_violations = [v for v in contingency.violations if 'Overload' in v['violation_type']]
                    
                    if voltage_violations:
                        print(f"\nVOLTAGE VIOLATIONS:")
                        headers = ["Element", "Type", "Value", "Limit", "Severity"]
                        table_data = []
                        for v in voltage_violations:
                            table_data.append([
                                v['element_name'],
                                v['violation_type'],
                                v['violation_value'],
                                v['limit_value'],
                                v['severity']
                            ])
                        print(tabulate(table_data, headers=headers, tablefmt="grid"))
                    
                    if current_violations:
                        print(f"\nOVERLOAD VIOLATIONS:")
                        headers = ["Element", "Type", "Value", "Limit", "Severity"]
                        table_data = []
                        for v in current_violations:
                            table_data.append([
                                v['element_name'],
                                v['violation_type'],
                                v['violation_value'],
                                v['limit_value'],
                                v['severity']
                            ])
                        print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            return True
            
        except Exception as e:
            print(f"Error running base case analysis: {e}")
            return False
    
    def run_diagnostic_analysis(self):
        """Run convergence diagnostic analysis."""
        if self.current_net is None:
            print("Error: No grid loaded")
            return False
        
        try:
            diagnostic = ConvergenceDiagnostic(self.current_net)
            results = diagnostic.run_full_diagnostic()
            return True
            
        except Exception as e:
            print(f"Error running diagnostic analysis: {e}")
            return False
    
    def run_contingency_analysis(self, export_file: Optional[str] = None):
        """Run N-1 contingency analysis."""
        if self.current_net is None:
            print("Error: No grid loaded")
            return False
        
        try:
            print(f"\nRunning N-1 contingency analysis on {self.current_grid_name}...")
            
            contingency = ContingencyAnalysis(self.current_net)
            results = contingency.run_n1_analysis()
            
            if not results:
                print("No contingency results generated")
                return False
            
            # Display base case information first
            base_case = [r for r in results if r['contingency_type'] == 'Base Case']
            if base_case:
                self._display_base_case_loading(base_case[0])
            
            # Display summary
            summary = contingency.get_contingency_summary()
            print(f"\nCONTINGENCY ANALYSIS SUMMARY:")
            print(f"  Total contingencies: {summary.get('total_contingencies', 0)}")
            print(f"  Converged cases: {summary.get('converged_cases', 0)} ({summary.get('convergence_rate', '0%')})")
            print(f"  Security status: {summary.get('security_status', 'Unknown')}")
            print(f"  Critical contingencies: {summary.get('critical_contingencies', 0)}")
            print(f"  High severity: {summary.get('high_severity', 0)}")
            print(f"  Medium severity: {summary.get('medium_severity', 0)}")
            print(f"  Low severity: {summary.get('low_severity', 0)}")
            
            # Display critical contingencies
            critical_contingencies = [r for r in results if r['severity'] in ['Critical', 'High'] and r['contingency_type'] != 'Base Case']
            if critical_contingencies:
                print(f"\nCRITICAL CONTINGENCIES:")
                headers = ["Type", "Element", "Severity", "Max V (p.u.)", "Min V (p.u.)", "Max Loading (%)"]
                table_data = []
                
                for c in critical_contingencies[:10]:  # Show top 10
                    max_loading = max(c.get('max_line_loading', 0), c.get('max_trafo_loading', 0))
                    table_data.append([
                        c['contingency_type'].replace(' Outage', ''),
                        c['element_name'][:20],  # Truncate long names
                        c['severity'],
                        f"{c.get('max_voltage_pu', 0):.3f}",
                        f"{c.get('min_voltage_pu', 0):.3f}",
                        f"{max_loading:.1f}"
                    ])
                
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
            
            # Display violations if any
            if contingency.violations:
                print(f"\nVIOLATIONS DETECTED: {len(contingency.violations)}")
                
                voltage_violations = [v for v in contingency.violations if 'Voltage' in v['violation_type']]
                current_violations = [v for v in contingency.violations if 'Overload' in v['violation_type']]
                
                print(f"  Voltage violations: {len(voltage_violations)}")
                print(f"  Current violations: {len(current_violations)}")
                
                # Show worst violations
                if voltage_violations:
                    print(f"\nWORST VOLTAGE VIOLATIONS:")
                    for v in voltage_violations[:5]:  # Top 5
                        print(f"    {v['violation_type']}: {v['element_name']} = {v['violation_value']} (limit: {v['limit_value']}) [Contingency: {v['contingency_element']}]")
                
                if current_violations:
                    print(f"\nWORST CURRENT VIOLATIONS:")
                    for v in current_violations[:5]:  # Top 5
                        print(f"    {v['violation_type']}: {v['element_name']} = {v['violation_value']} (limit: {v['limit_value']}) [Contingency: {v['contingency_element']}]")
            else:
                print(f"\n✓ No violations detected - System is secure")
            
            # Export if requested
            if export_file:
                self._export_contingency_results(results, contingency.violations, export_file)
            
            return True
            
        except Exception as e:
            print(f"Error running contingency analysis: {e}")
            return False
    
    def export_results(self, filename: str):
        """Export power flow results to CSV."""
        if self.current_net is None or not hasattr(self.current_net, 'res_bus'):
            print("Error: No power flow results available")
            return False
        
        try:
            # Create results dictionary
            results = {
                'bus_results': self.current_net.res_bus.copy(),
                'line_results': self.current_net.res_line.copy() if hasattr(self.current_net, 'res_line') else pd.DataFrame(),
                'trafo_results': self.current_net.res_trafo.copy() if hasattr(self.current_net, 'res_trafo') else pd.DataFrame(),
                'gen_results': self.current_net.res_gen.copy() if hasattr(self.current_net, 'res_gen') else pd.DataFrame()
            }
            
            # Export to Excel with multiple sheets
            base_name = filename.rsplit('.', 1)[0]
            excel_file = f"{base_name}.xlsx"
            
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                results['bus_results'].to_excel(writer, sheet_name='Bus_Results')
                if not results['line_results'].empty:
                    results['line_results'].to_excel(writer, sheet_name='Line_Results')
                if not results['trafo_results'].empty:
                    results['trafo_results'].to_excel(writer, sheet_name='Transformer_Results')
                if not results['gen_results'].empty:
                    results['gen_results'].to_excel(writer, sheet_name='Generator_Results')
            
            print(f"✓ Results exported to {excel_file}")
            return True
            
        except Exception as e:
            print(f"Error exporting results: {e}")
            return False
    
    def _export_contingency_results(self, results: List, violations: List, filename: str):
        """Export contingency analysis results."""
        try:
            base_name = filename.rsplit('.', 1)[0]
            
            # Export contingency results
            contingency_df = pd.DataFrame(results)
            contingency_file = f"{base_name}_contingency.csv"
            contingency_df.to_csv(contingency_file, index=False)
            
            # Export violations if any
            if violations:
                violations_df = pd.DataFrame(violations)
                violations_file = f"{base_name}_violations.csv"
                violations_df.to_csv(violations_file, index=False)
                print(f"✓ Contingency results exported to {contingency_file}")
                print(f"✓ Violations exported to {violations_file}")
            else:
                print(f"✓ Contingency results exported to {contingency_file}")
            
        except Exception as e:
            print(f"Error exporting contingency results: {e}")


def main():
    """Main command-line interface."""
    parser = argparse.ArgumentParser(
        description="Terminal-based power system load flow calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --grid ieee39                           # Load IEEE 39-bus system (custom)
  %(prog)s --grid ieee39std                        # Load IEEE 39-bus system (standard)
  %(prog)s --grid ieee9 --detailed                 # Load IEEE 9-bus with detailed output
  %(prog)s --load-db "My Grid" --export results    # Load from database and export
  %(prog)s --grid simple --contingency             # Run contingency analysis
  %(prog)s --grid ieee9 --base-case-only           # Show base case loading only
  %(prog)s --grid ieee39 --diagnostic              # Run convergence diagnostic
  %(prog)s --list-grids                            # List available database grids
        """
    )
    
    # Grid loading options
    grid_group = parser.add_mutually_exclusive_group()
    grid_group.add_argument('--grid', 
                           choices=['simple', 'ieee9', 'ieee39', 'ieee39std'],
                           help='Load example grid (simple, ieee9, ieee39, or ieee39std)')
    grid_group.add_argument('--load-db', metavar='GRID_NAME',
                           help='Load grid from database by name')
    grid_group.add_argument('--list-grids', action='store_true',
                           help='List available grids in database')
    
    # Analysis options
    parser.add_argument('--contingency', action='store_true',
                       help='Run N-1 contingency analysis')
    parser.add_argument('--base-case-only', action='store_true',
                       help='Show only base case loading (no contingencies)')
    parser.add_argument('--diagnostic', action='store_true',
                       help='Run convergence diagnostic (troubleshoot non-convergence)')
    parser.add_argument('--detailed', action='store_true',
                       help='Show detailed results tables')
    
    # Export options
    parser.add_argument('--export', metavar='FILENAME',
                       help='Export results to file (CSV/Excel)')
    parser.add_argument('--no-loadflow', action='store_true',
                       help='Skip load flow calculation (for grid inspection only)')
    
    args = parser.parse_args()
    
    # Create calculator instance
    calc = TerminalLoadFlow()
    
    # Handle list grids command
    if args.list_grids:
        calc.list_available_grids()
        return 0
    
    # Load grid
    if args.grid:
        if not calc.load_example_grid(args.grid):
            return 1
    elif args.load_db:
        if not calc.load_database_grid(args.load_db):
            return 1
    else:
        print("Error: No grid specified. Use --grid, --load-db, or --list-grids")
        parser.print_help()
        return 1
    
    # Run load flow (unless explicitly skipped)
    if not args.no_loadflow:
        if not calc.run_load_flow():
            return 1
        
        # Display results
        calc.display_results(detailed=args.detailed)
    
    # Run contingency analysis if requested
    if args.contingency:
        export_file = args.export if args.export else None
        if not calc.run_contingency_analysis(export_file):
            return 1
    elif args.base_case_only:
        if not calc.run_base_case_analysis():
            return 1
    elif args.diagnostic:
        if not calc.run_diagnostic_analysis():
            return 1
    
    # Export results if requested (and not already done by contingency analysis)
    if args.export and not args.contingency:
        if not calc.export_results(args.export):
            return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())