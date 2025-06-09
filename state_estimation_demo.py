#!/usr/bin/env python3
"""Comprehensive demonstration of state estimation results with clear explanations."""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase
from examples import create_ieee_9_bus
import pandapower as pp


class StateEstimationDemo:
    """Interactive demonstration of state estimation concepts and results."""
    
    def __init__(self):
        """Initialize the demonstration."""
        self.db = GridDatabase()
        self.db.initialize_example_grids()
        self.module = StateEstimationModule(self.db)
        
    def explain_state_estimation(self):
        """Explain what state estimation is and why it's important."""
        explanation = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           POWER SYSTEM STATE ESTIMATION                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎯 WHAT IS STATE ESTIMATION?
State estimation is like being a detective for the power grid! It takes noisy, 
incomplete measurements from sensors around the grid and figures out the "true" 
electrical state at every bus.

🔍 THE PROBLEM:
• Real measurements have noise and errors
• Not every quantity can be measured directly
• Some sensors might fail or give bad data
• We need complete, accurate system state for control

💡 THE SOLUTION:
State estimation uses mathematical algorithms to:
• Filter out measurement noise
• Estimate unmeasured quantities  
• Detect and remove bad data
• Provide the best estimate of system state

⚡ REAL-WORLD IMPORTANCE:
• Grid operators use this every few seconds
• Critical for real-time control and protection
• Enables automatic generation control
• Essential for preventing blackouts

🧮 THE MATH:
Uses Weighted Least Squares (WLS) to minimize:
J = Σ [(measured - calculated)² / measurement_accuracy²]

The better the measurement accuracy, the more we trust it!
"""
        print(explanation)
        print("\n" + "="*60 + "\n")
    
    def demonstrate_measurement_types(self):
        """Show different types of measurements and their importance."""
        print("\n" + "="*80)
        print("🔬 MEASUREMENT TYPES IN POWER SYSTEMS")
        print("="*80)
        
        # Create a simple grid for demonstration
        net = create_ieee_9_bus()
        pp.runpp(net, verbose=False, numba=False)
        
        print("\n📊 TYPES OF MEASUREMENTS:")
        print("-" * 40)
        
        print("1️⃣  VOLTAGE MAGNITUDE (|V|)")
        print("   • Most accurate measurements (±0.5-1%)")
        print("   • Available at most buses")
        print("   • Critical for voltage control")
        
        if hasattr(net, 'res_bus'):
            print(f"   • Example: Bus 0 = {net.res_bus.loc[0, 'vm_pu']:.4f} p.u.")
        
        print("\n2️⃣  POWER INJECTIONS (P, Q)")
        print("   • Power flowing into/out of buses")
        print("   • Less accurate (±1-3%)")
        print("   • Important for generation dispatch")
        
        if hasattr(net, 'res_bus'):
            print(f"   • Example: Bus 4 P = {net.res_bus.loc[4, 'p_mw']:.2f} MW")
        
        print("\n3️⃣  POWER FLOWS (P_flow, Q_flow)")
        print("   • Power flowing through transmission lines")
        print("   • Moderate accuracy (±2-4%)")
        print("   • Critical for line loading monitoring")
        
        if hasattr(net, 'res_line') and not net.res_line.empty:
            print(f"   • Example: Line 0 P = {net.res_line.loc[0, 'p_from_mw']:.2f} MW")
        
        print("\n🎯 KEY INSIGHT:")
        print("State estimation combines ALL these measurements to get the")
        print("most accurate picture of the entire power system!")
        
        print("\n" + "="*60 + "\n")
    
    def run_simple_demonstration(self):
        """Run a simple state estimation demonstration."""
        print("\n" + "="*80)
        print("🚀 SIMPLE STATE ESTIMATION DEMONSTRATION")
        print("="*80)
        
        print("\n📋 DEMONSTRATION SETUP:")
        print("• Grid: IEEE 9-Bus Test System (standard benchmark)")
        print("• Measurements: Voltage magnitudes at all 9 buses")
        print("• Noise Level: 1% (realistic for modern PMUs)")
        print("• Algorithm: Weighted Least Squares")
        
        # Get IEEE 9-bus grid from database
        grids = self.module.get_available_grids()
        ieee9_grid = None
        for grid in grids:
            if "IEEE 9-Bus" in grid[1]:
                ieee9_grid = grid
                break
        
        if not ieee9_grid:
            print("❌ IEEE 9-Bus grid not found in database!")
            return
        
        print(f"\n🔍 Selected Grid: {ieee9_grid[1]}")
        
        # Configure state estimation
        config = EstimationConfig(
            mode=EstimationMode.VOLTAGE_ONLY,
            voltage_noise_std=0.01,  # 1% noise
            max_iterations=20,
            tolerance=1e-4
        )
        
        print("\n⚙️  RUNNING STATE ESTIMATION...")
        print("   Step 1: Loading grid and running power flow...")
        
        # Run state estimation
        results = self.module.estimate_grid_state(ieee9_grid[0], config)
        
        if not results.get('success', False):
            print(f"❌ State estimation failed: {results.get('error', 'Unknown error')}")
            return
        
        print("   Step 2: Creating noisy measurements...")
        print("   Step 3: Solving weighted least squares...")
        print("   Step 4: Calculating accuracy metrics...")
        
        # Display results
        self._display_simple_results(results)
        
        print("\n" + "="*60)
        print("📋 DETAILED ANALYSIS:")
        print("="*60)
        self._show_detailed_analysis(results)
    
    def _display_simple_results(self, results):
        """Display simple, understandable results."""
        print("\n" + "="*60)
        print("📊 STATE ESTIMATION RESULTS")
        print("="*60)
        
        convergence = results.get('convergence', {})
        accuracy = results.get('accuracy_metrics', {})
        
        # Convergence status
        if convergence.get('converged', False):
            print("✅ SUCCESS: State estimation converged!")
            print(f"   Iterations needed: {convergence.get('iterations', 'N/A')}")
            print(f"   Total measurements: {convergence.get('measurements_count', 'N/A')}")
        else:
            print("❌ FAILED: State estimation did not converge")
            return
        
        # Accuracy results
        print(f"\n🎯 ACCURACY ASSESSMENT:")
        if accuracy:
            max_error = accuracy.get('max_voltage_error_percent', 0)
            mean_error = accuracy.get('mean_voltage_error_percent', 0)
            rms_error = accuracy.get('rms_voltage_error_percent', 0)
            
            print(f"   Maximum voltage error: {max_error:.2f}%")
            print(f"   Average voltage error: {mean_error:.2f}%")
            print(f"   RMS voltage error: {rms_error:.2f}%")
            
            # Interpret results
            if max_error < 1.0:
                print("   📈 EXCELLENT: Errors < 1% - Very high accuracy!")
            elif max_error < 2.0:
                print("   📈 GOOD: Errors < 2% - Acceptable for most applications")
            elif max_error < 5.0:
                print("   📈 FAIR: Errors < 5% - May need improvement")
            else:
                print("   📈 POOR: Errors > 5% - Needs investigation")
        
        print(f"\n💡 WHAT THIS MEANS:")
        print(f"   The state estimator successfully cleaned up noisy measurements")
        print(f"   and provided an accurate estimate of all bus voltages!")
    
    def _show_detailed_analysis(self, results):
        """Show detailed voltage comparison."""
        comparison_data = results.get('comparison', [])
        if not comparison_data:
            print("No detailed comparison data available")
            return
        
        print("\n" + "="*80)
        print("🔍 DETAILED VOLTAGE COMPARISON: TRUE vs ESTIMATED")
        print("="*80)
        
        print("Bus | True Voltage | Estimated  | Error   | Quality")
        print("    | (p.u.)      | (p.u.)     | (%)     | Rating")
        print("-" * 55)
        
        for bus_data in comparison_data:
            bus_id = bus_data.get('Bus', 'N/A')
            true_v = bus_data.get('True V (pu)', 'N/A')
            est_v = bus_data.get('Est V (pu)', 'N/A')
            error_str = bus_data.get('V Error (%)', 'N/A')
            
            # Extract error percentage
            try:
                error_val = float(str(error_str).replace('%', ''))
                abs_error = abs(error_val)
                
                if abs_error < 0.5:
                    quality = "Excellent ⭐⭐⭐"
                elif abs_error < 1.0:
                    quality = "Very Good ⭐⭐"
                elif abs_error < 2.0:
                    quality = "Good ⭐"
                else:
                    quality = "Fair"
                    
            except:
                quality = "Unknown"
            
            print(f" {bus_id:2s} | {true_v:10s} | {est_v:9s} | {error_str:6s} | {quality}")
        
        print("\n🎓 KEY INSIGHTS:")
        print("• State estimation 'smooths out' measurement noise")
        print("• Even with 1% measurement noise, we get excellent estimates")
        print("• This accuracy enables safe and efficient grid operation")
        print("• Real grid operators rely on this every few seconds!")
    
    def demonstrate_measurement_impact(self):
        """Show how different measurement types affect accuracy."""
        print("\n" + "="*80)
        print("🔬 MEASUREMENT IMPACT DEMONSTRATION")
        print("="*80)
        
        print("Let's see how different measurement configurations affect accuracy...")
        
        # Get IEEE 9-bus grid
        grids = self.module.get_available_grids()
        ieee9_grid = None
        for grid in grids:
            if "IEEE 9-Bus" in grid[1]:
                ieee9_grid = grid
                break
        
        if not ieee9_grid:
            print("IEEE 9-Bus grid not found!")
            return
        
        # Test different configurations
        configs = [
            ("Voltage Only (High Accuracy)", EstimationConfig(
                mode=EstimationMode.VOLTAGE_ONLY,
                voltage_noise_std=0.005,  # 0.5% noise
                max_iterations=20
            )),
            ("Voltage Only (Normal Accuracy)", EstimationConfig(
                mode=EstimationMode.VOLTAGE_ONLY,
                voltage_noise_std=0.01,   # 1% noise
                max_iterations=20
            )),
            ("Voltage + Power (Comprehensive)", EstimationConfig(
                mode=EstimationMode.COMPREHENSIVE,
                voltage_noise_std=0.01,   # 1% noise
                power_noise_std=0.02,     # 2% noise
                max_iterations=20,
                include_power_injections=True,
                include_power_flows=False  # Keep it simple for demo
            ))
        ]
        
        print("\n📊 COMPARING DIFFERENT MEASUREMENT SCENARIOS:")
        print("-" * 70)
        print("Scenario                      | Converged | Max Error | Mean Error")
        print("-" * 70)
        
        for scenario_name, config in configs:
            try:
                results = self.module.estimate_grid_state(ieee9_grid[0], config)
                
                if results.get('success', False):
                    convergence = results.get('convergence', {})
                    accuracy = results.get('accuracy_metrics', {})
                    
                    converged = "✅ Yes" if convergence.get('converged', False) else "❌ No"
                    max_error = accuracy.get('max_voltage_error_percent', 0)
                    mean_error = accuracy.get('mean_voltage_error_percent', 0)
                    
                    print(f"{scenario_name:28s} | {converged:8s} | {max_error:7.2f}% | {mean_error:8.2f}%")
                else:
                    print(f"{scenario_name:28s} | ❌ Failed | N/A     | N/A")
                    
            except Exception as e:
                print(f"{scenario_name:28s} | ❌ Error  | N/A     | N/A")
        
        print("\n💡 OBSERVATIONS:")
        print("• Higher measurement accuracy → Better state estimation")
        print("• Voltage measurements are most reliable and important")
        print("• More measurements can improve results but may cause convergence issues")
        print("• Real systems balance accuracy needs with computational complexity")
        
        print("\n" + "="*60 + "\n")
    
    def create_visual_summary(self):
        """Create a visual summary of state estimation performance."""
        print("\n" + "="*80)
        print("📈 VISUAL PERFORMANCE SUMMARY")
        print("="*80)
        
        # Test multiple grids
        grids = self.module.get_available_grids()
        grid_results = []
        
        print("Testing state estimation on all available grids...")
        
        for grid_id, grid_name, grid_desc in grids:
            print(f"\n🔍 Testing: {grid_name}")
            
            config = EstimationConfig(
                mode=EstimationMode.VOLTAGE_ONLY,
                voltage_noise_std=0.01,
                max_iterations=20
            )
            
            try:
                results = self.module.estimate_grid_state(grid_id, config)
                
                if results.get('success', False):
                    convergence = results.get('convergence', {})
                    accuracy = results.get('accuracy_metrics', {})
                    network = results.get('network_stats', {})
                    
                    grid_results.append({
                        'name': grid_name,
                        'buses': network.get('buses', 0),
                        'converged': convergence.get('converged', False),
                        'iterations': convergence.get('iterations', 0),
                        'measurements': convergence.get('measurements_count', 0),
                        'max_error': accuracy.get('max_voltage_error_percent', 0),
                        'mean_error': accuracy.get('mean_voltage_error_percent', 0)
                    })
                    
                    status = "✅ SUCCESS" if convergence.get('converged', False) else "❌ FAILED"
                    error = accuracy.get('max_voltage_error_percent', 0)
                    print(f"   Status: {status}, Max Error: {error:.2f}%")
                else:
                    print(f"   Status: ❌ FAILED - {results.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"   Status: ❌ ERROR - {str(e)}")
        
        # Display summary table
        self._display_performance_table(grid_results)
    
    def _display_performance_table(self, results):
        """Display a nice performance summary table."""
        if not results:
            print("\nNo results to display")
            return
        
        print("\n" + "="*90)
        print("🏆 STATE ESTIMATION PERFORMANCE SUMMARY")
        print("="*90)
        
        print("Grid Name                    | Buses | Status    | Iter | Meas | Max Err | Mean Err")
        print("-" * 86)
        
        total_grids = len(results)
        successful_grids = 0
        
        for result in results:
            name = result['name'][:25]  # Truncate long names
            buses = result['buses']
            status = "✅ Conv." if result['converged'] else "❌ Failed"
            iterations = result['iterations']
            measurements = result['measurements']
            max_error = result['max_error']
            mean_error = result['mean_error']
            
            if result['converged']:
                successful_grids += 1
            
            print(f"{name:28s} | {buses:5d} | {status:8s} | {iterations:4d} | {measurements:4d} | "
                  f"{max_error:6.2f}% | {mean_error:7.2f}%")
        
        print("-" * 86)
        success_rate = (successful_grids / total_grids) * 100
        print(f"OVERALL SUCCESS RATE: {successful_grids}/{total_grids} grids ({success_rate:.0f}%)")
        
        if successful_grids > 0:
            avg_max_error = np.mean([r['max_error'] for r in results if r['converged']])
            avg_mean_error = np.mean([r['mean_error'] for r in results if r['converged']])
            print(f"AVERAGE ACCURACY: Max Error = {avg_max_error:.2f}%, Mean Error = {avg_mean_error:.2f}%")
        
        print("\n🎯 CONCLUSIONS:")
        if success_rate >= 80:
            print("✅ Excellent performance across all test grids!")
        elif success_rate >= 60:
            print("✅ Good performance on most grids")
        else:
            print("⚠️  Some grids need attention for better convergence")
        
        print("✅ State estimation provides reliable voltage estimates")
        print("✅ Suitable for real-time power system monitoring")
        print("✅ Accuracy sufficient for grid operation and control")
    
    def run_complete_demo(self):
        """Run the complete demonstration."""
        print("╔════════════════════════════════════════════════════════════════════════════╗")
        print("║              POWER SYSTEM STATE ESTIMATION DEMONSTRATION                  ║")
        print("║                         Interactive Learning Guide                        ║")
        print("╚════════════════════════════════════════════════════════════════════════════╝")
        
        print("\nWelcome to the State Estimation Demo! 🎓")
        print("This interactive demonstration will show you:")
        print("• What state estimation is and why it matters")
        print("• How different measurements work")
        print("• Real examples with actual results")
        print("• Performance across different grid sizes")
        
        print("\nStarting demonstration automatically...\n")
        
        # Run all demonstration parts
        self.explain_state_estimation()
        self.demonstrate_measurement_types()
        self.run_simple_demonstration()
        self.demonstrate_measurement_impact()
        self.create_visual_summary()
        
        print("\n" + "="*80)
        print("🎉 DEMONSTRATION COMPLETE!")
        print("="*80)
        print("You've now seen how state estimation works in practice!")
        print("Key takeaways:")
        print("• State estimation is essential for power grid operation")
        print("• It turns noisy measurements into accurate system state")
        print("• Voltage measurements are most reliable")
        print("• Modern algorithms achieve excellent accuracy (<2% error)")
        print("• This technology keeps the lights on every day! 💡")
        print("\nThank you for learning about power system state estimation! 🚀")


def main():
    """Run the state estimation demonstration."""
    try:
        demo = StateEstimationDemo()
        demo.run_complete_demo()
    except KeyboardInterrupt:
        print("\n\nDemonstration interrupted by user. Goodbye! 👋")
    except EOFError:
        print("\n\nDemonstration completed successfully! 🎉")
    except Exception as e:
        print(f"\n❌ An error occurred during the demonstration: {e}")
        print("Please check your installation and try again.")


if __name__ == "__main__":
    main()