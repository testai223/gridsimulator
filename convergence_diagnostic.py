#!/usr/bin/env python3
"""Diagnostic tool for power flow convergence issues."""

import sys
import pandas as pd
import pandapower as pp
import numpy as np
from typing import Dict, List, Any, Optional
from examples import create_example_grid, create_ieee_9_bus, create_ieee_39_bus, create_ieee_39_bus_standard


class ConvergenceDiagnostic:
    """Diagnostic tool to identify power flow convergence issues."""
    
    def __init__(self, net: pp.pandapowerNet):
        """Initialize with a pandapower network."""
        self.net = net
        self.issues = []
        self.warnings = []
        self.info = []
    
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run complete diagnostic analysis."""
        print("="*60)
        print("POWER FLOW CONVERGENCE DIAGNOSTIC")
        print("="*60)
        
        # Network topology checks
        self._check_network_topology()
        
        # Power balance checks
        self._check_power_balance()
        
        # Voltage and impedance checks
        self._check_voltage_levels()
        
        # Generator checks
        self._check_generators()
        
        # Load checks
        self._check_loads()
        
        # Connectivity checks
        self._check_connectivity()
        
        # Line parameter checks
        self._check_line_parameters()
        
        # Try different solver settings
        self._test_solver_options()
        
        # Display summary
        self._display_summary()
        
        return {
            'issues': self.issues,
            'warnings': self.warnings,
            'info': self.info
        }
    
    def _check_network_topology(self):
        """Check basic network topology."""
        print("\n1. NETWORK TOPOLOGY CHECK:")
        
        # Basic network statistics
        n_buses = len(self.net.bus)
        n_lines = len(self.net.line) if hasattr(self.net, 'line') else 0
        n_trafos = len(self.net.trafo) if hasattr(self.net, 'trafo') else 0
        n_gens = len(self.net.gen) if hasattr(self.net, 'gen') else 0
        n_ext_grids = len(self.net.ext_grid) if hasattr(self.net, 'ext_grid') else 0
        n_loads = len(self.net.load) if hasattr(self.net, 'load') else 0
        
        print(f"  Buses: {n_buses}")
        print(f"  Lines: {n_lines}")
        print(f"  Transformers: {n_trafos}")
        print(f"  Generators: {n_gens}")
        print(f"  External grids: {n_ext_grids}")
        print(f"  Loads: {n_loads}")
        
        # Check for empty network
        if n_buses == 0:
            self.issues.append("Network has no buses")
        
        if n_lines == 0 and n_trafos == 0:
            self.issues.append("Network has no transmission elements (lines or transformers)")
        
        if n_gens == 0 and n_ext_grids == 0:
            self.issues.append("Network has no generation sources")
        
        self.info.append(f"Network size: {n_buses} buses, {n_lines + n_trafos} transmission elements")
    
    def _check_power_balance(self):
        """Check power balance between generation and load."""
        print("\n2. POWER BALANCE CHECK:")
        
        total_gen_p = 0.0
        total_gen_q = 0.0
        total_load_p = 0.0
        total_load_q = 0.0
        
        # Sum generation
        if hasattr(self.net, 'gen') and not self.net.gen.empty:
            active_gens = self.net.gen[self.net.gen['in_service']]
            total_gen_p += active_gens['p_mw'].sum()
            # Q is not specified for PV generators in input
            
        if hasattr(self.net, 'ext_grid') and not self.net.ext_grid.empty:
            # External grid provides unlimited power
            print("  External grid present (unlimited power source)")
        
        # Sum loads
        if hasattr(self.net, 'load') and not self.net.load.empty:
            active_loads = self.net.load[self.net.load['in_service']]
            total_load_p += active_loads['p_mw'].sum()
            total_load_q += active_loads['q_mvar'].sum()
        
        print(f"  Total generation: {total_gen_p:.1f} MW")
        print(f"  Total load: {total_load_p:.1f} MW")
        print(f"  Power imbalance: {total_gen_p - total_load_p:.1f} MW")
        
        if hasattr(self.net, 'ext_grid') and not self.net.ext_grid.empty:
            print("  Note: External grid will compensate for any imbalance")
        else:
            imbalance = abs(total_gen_p - total_load_p)
            if imbalance > 0.1 * max(total_gen_p, total_load_p):
                self.issues.append(f"Large power imbalance: {total_gen_p - total_load_p:.1f} MW")
            elif imbalance > 10:
                self.warnings.append(f"Moderate power imbalance: {total_gen_p - total_load_p:.1f} MW")
    
    def _check_voltage_levels(self):
        """Check voltage level consistency."""
        print("\n3. VOLTAGE LEVEL CHECK:")
        
        if self.net.bus.empty:
            return
            
        voltage_levels = self.net.bus['vn_kv'].unique()
        print(f"  Voltage levels in network: {sorted(voltage_levels)} kV")
        
        # Check for unrealistic voltage levels
        for vn in voltage_levels:
            if vn <= 0:
                self.issues.append(f"Invalid voltage level: {vn} kV")
            elif vn < 0.1:
                self.warnings.append(f"Very low voltage level: {vn} kV")
            elif vn > 1000:
                self.warnings.append(f"Very high voltage level: {vn} kV")
        
        # Check line voltage level consistency
        if hasattr(self.net, 'line') and not self.net.line.empty:
            for idx, line in self.net.line.iterrows():
                from_bus = line['from_bus']
                to_bus = line['to_bus']
                
                if from_bus in self.net.bus.index and to_bus in self.net.bus.index:
                    from_vn = self.net.bus.loc[from_bus, 'vn_kv']
                    to_vn = self.net.bus.loc[to_bus, 'vn_kv']
                    
                    if from_vn != to_vn:
                        line_name = line.get('name', f'Line {idx}')
                        self.issues.append(f"Line {line_name} connects different voltage levels: {from_vn} kV to {to_vn} kV")
    
    def _check_generators(self):
        """Check generator configuration."""
        print("\n4. GENERATOR CHECK:")
        
        if not hasattr(self.net, 'gen') or self.net.gen.empty:
            if not hasattr(self.net, 'ext_grid') or self.net.ext_grid.empty:
                self.issues.append("No generators or external grids in network")
            return
        
        active_gens = self.net.gen[self.net.gen['in_service']]
        slack_gens = active_gens[active_gens['slack']]
        
        print(f"  Total generators: {len(self.net.gen)}")
        print(f"  Active generators: {len(active_gens)}")
        print(f"  Slack generators: {len(slack_gens)}")
        
        # Check for slack bus
        has_ext_grid = hasattr(self.net, 'ext_grid') and not self.net.ext_grid.empty
        if len(slack_gens) == 0 and not has_ext_grid:
            self.issues.append("No slack generator or external grid found")
        elif len(slack_gens) > 1:
            self.warnings.append(f"Multiple slack generators found: {len(slack_gens)}")
        
        # Check generator parameters
        for idx, gen in active_gens.iterrows():
            gen_name = gen.get('name', f'Gen {idx}')
            
            # Check power output
            if gen['p_mw'] < 0:
                self.warnings.append(f"{gen_name}: Negative power output {gen['p_mw']} MW")
            elif gen['p_mw'] > 2000:
                self.warnings.append(f"{gen_name}: Very large power output {gen['p_mw']} MW")
            
            # Check voltage setpoint
            if gen['vm_pu'] < 0.9 or gen['vm_pu'] > 1.1:
                self.warnings.append(f"{gen_name}: Unusual voltage setpoint {gen['vm_pu']} p.u.")
            
            # Check bus connection
            if gen['bus'] not in self.net.bus.index:
                self.issues.append(f"{gen_name}: Connected to non-existent bus {gen['bus']}")
    
    def _check_loads(self):
        """Check load configuration."""
        print("\n5. LOAD CHECK:")
        
        if not hasattr(self.net, 'load') or self.net.load.empty:
            self.warnings.append("No loads in network")
            return
        
        active_loads = self.net.load[self.net.load['in_service']]
        print(f"  Total loads: {len(self.net.load)}")
        print(f"  Active loads: {len(active_loads)}")
        
        # Check load parameters
        for idx, load in active_loads.iterrows():
            load_name = load.get('name', f'Load {idx}')
            
            # Check power consumption
            if load['p_mw'] < 0:
                self.warnings.append(f"{load_name}: Negative active power {load['p_mw']} MW")
            elif load['p_mw'] > 1000:
                self.warnings.append(f"{load_name}: Very large active power {load['p_mw']} MW")
            
            # Check reactive power
            if abs(load['q_mvar']) > 2 * load['p_mw']:
                self.warnings.append(f"{load_name}: Unusual reactive power {load['q_mvar']} Mvar")
            
            # Check bus connection
            if load['bus'] not in self.net.bus.index:
                self.issues.append(f"{load_name}: Connected to non-existent bus {load['bus']}")
    
    def _check_connectivity(self):
        """Check network connectivity."""
        print("\n6. CONNECTIVITY CHECK:")
        
        try:
            # Use pandapower's topology functions
            mg = pp.topology.create_nxgraph(self.net)
            
            # Check if network is connected
            import networkx as nx
            if not nx.is_connected(mg):
                self.issues.append("Network is not fully connected (has isolated islands)")
                
                # Find connected components
                components = list(nx.connected_components(mg))
                print(f"  Network has {len(components)} separate components")
                for i, comp in enumerate(components):
                    print(f"    Component {i+1}: {len(comp)} buses")
            else:
                print("  Network is fully connected ✓")
                
        except Exception as e:
            self.warnings.append(f"Could not check connectivity: {e}")
    
    def _check_line_parameters(self):
        """Check line and transformer parameters."""
        print("\n7. LINE PARAMETER CHECK:")
        
        # Check lines
        if hasattr(self.net, 'line') and not self.net.line.empty:
            for idx, line in self.net.line.iterrows():
                line_name = line.get('name', f'Line {idx}')
                
                # Check impedance parameters
                if line['r_ohm_per_km'] <= 0:
                    self.issues.append(f"{line_name}: Invalid resistance {line['r_ohm_per_km']}")
                if line['x_ohm_per_km'] <= 0:
                    self.issues.append(f"{line_name}: Invalid reactance {line['x_ohm_per_km']}")
                if line['length_km'] <= 0:
                    self.issues.append(f"{line_name}: Invalid length {line['length_km']}")
                
                # Check for unrealistic values
                if line['r_ohm_per_km'] > 10:
                    self.warnings.append(f"{line_name}: High resistance {line['r_ohm_per_km']} Ω/km")
                if line['x_ohm_per_km'] > 10:
                    self.warnings.append(f"{line_name}: High reactance {line['x_ohm_per_km']} Ω/km")
        
        # Check transformers
        if hasattr(self.net, 'trafo') and not self.net.trafo.empty:
            for idx, trafo in self.net.trafo.iterrows():
                trafo_name = trafo.get('name', f'Trafo {idx}')
                
                # Check basic parameters
                if trafo['sn_mva'] <= 0:
                    self.issues.append(f"{trafo_name}: Invalid rating {trafo['sn_mva']} MVA")
                if trafo['vn_hv_kv'] <= 0 or trafo['vn_lv_kv'] <= 0:
                    self.issues.append(f"{trafo_name}: Invalid voltage ratings")
                if trafo['vk_percent'] <= 0:
                    self.issues.append(f"{trafo_name}: Invalid short-circuit voltage {trafo['vk_percent']}%")
    
    def _test_solver_options(self):
        """Test different solver options to improve convergence."""
        print("\n8. SOLVER TESTING:")
        
        import copy
        test_net = copy.deepcopy(self.net)
        
        # Test different solvers and options
        solver_options = [
            {"algorithm": "nr", "max_iteration": 10},
            {"algorithm": "nr", "max_iteration": 50},
            {"algorithm": "nr", "max_iteration": 100, "tolerance_mva": 1e-3},
            {"algorithm": "nr", "max_iteration": 100, "tolerance_mva": 1e-2},
            {"algorithm": "bfsw"},
            {"algorithm": "gs", "max_iteration": 1000},
        ]
        
        successful_options = []
        
        for i, options in enumerate(solver_options):
            try:
                import copy
                test_net = copy.deepcopy(self.net)
                
                # Ensure there's a slack bus
                if not hasattr(test_net, 'ext_grid') or test_net.ext_grid.empty:
                    if hasattr(test_net, 'gen') and not test_net.gen.empty:
                        # Check if any generator is slack
                        if not any(test_net.gen['slack']):
                            # Make first generator slack
                            test_net.gen.loc[test_net.gen.index[0], 'slack'] = True
                    else:
                        # Add external grid to first bus
                        pp.create_ext_grid(test_net, bus=test_net.bus.index[0], vm_pu=1.0)
                
                pp.runpp(test_net, **options)
                successful_options.append((i, options))
                print(f"  ✓ Option {i+1} converged: {options}")
                
            except Exception as e:
                print(f"  ✗ Option {i+1} failed: {options}")
        
        if successful_options:
            self.info.append(f"Found {len(successful_options)} working solver configurations")
        else:
            self.issues.append("No solver configuration achieved convergence")
    
    def _display_summary(self):
        """Display diagnostic summary."""
        print("\n" + "="*60)
        print("DIAGNOSTIC SUMMARY")
        print("="*60)
        
        print(f"\n🔴 CRITICAL ISSUES ({len(self.issues)}):")
        for issue in self.issues:
            print(f"  • {issue}")
        
        print(f"\n🟡 WARNINGS ({len(self.warnings)}):")
        for warning in self.warnings:
            print(f"  • {warning}")
        
        print(f"\n🔵 INFORMATION ({len(self.info)}):")
        for info in self.info:
            print(f"  • {info}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if self.issues:
            print("  1. Fix critical issues first - these prevent convergence")
        if self.warnings:
            print("  2. Review warnings - these may cause convergence problems")
        if not self.issues and not self.warnings:
            print("  • Network appears well-configured")
            print("  • Try increasing solver iterations or relaxing tolerance")
            print("  • Check for numerical conditioning issues")


def main():
    """Command-line interface for convergence diagnostic."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Power flow convergence diagnostic tool")
    parser.add_argument('--grid', choices=['simple', 'ieee9', 'ieee39', 'ieee39std'], 
                       help='Example grid to diagnose')
    
    args = parser.parse_args()
    
    if not args.grid:
        print("Please specify a grid with --grid option")
        parser.print_help()
        return 1
    
    # Load the specified grid
    if args.grid == 'simple':
        net = create_example_grid()
        grid_name = "Simple Example Grid"
    elif args.grid == 'ieee9':
        net = create_ieee_9_bus()
        grid_name = "IEEE 9-Bus Test System"
    elif args.grid == 'ieee39':
        net = create_ieee_39_bus()
        grid_name = "IEEE 39-Bus New England System"
    elif args.grid == 'ieee39std':
        net = create_ieee_39_bus_standard()
        grid_name = "IEEE 39-Bus Standard (MATPOWER-based)"
    
    print(f"Diagnosing: {grid_name}")
    
    # Run diagnostic
    diagnostic = ConvergenceDiagnostic(net)
    results = diagnostic.run_full_diagnostic()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())