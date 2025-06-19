#!/usr/bin/env python3
"""Analyze measured vs estimated values in state estimation results."""

from database import GridDatabase
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from state_estimator import StateEstimator
import pandas as pd
import numpy as np


def analyze_measurement_comparison(grid_id, grid_name, noise_level=0.03):
    """Analyze measured vs estimated values for a specific grid."""
    print(f"\n🔍 {grid_name} - Measured vs Estimated Analysis")
    print("=" * 70)
    
    db = GridDatabase()
    module = StateEstimationModule(db)
    
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=noise_level,
        max_iterations=50,
        tolerance=1e-4
    )
    
    results = module.estimate_grid_state(grid_id=grid_id, config=config)
    
    if not results.get('success') or not results.get('converged'):
        print(f"❌ State estimation failed: {results.get('error', 'Did not converge')}")
        return
    
    # Basic information
    print(f"Grid: {results.get('grid_info', {}).get('name', 'Unknown')}")
    print(f"Convergence: ✅ {results.get('iterations', 0)} iterations")
    print(f"Measurements: {results.get('measurements_count', 0)}")
    print(f"Noise Level: {noise_level*100:.1f}%")
    print()
    
    # Voltage comparison
    true_voltages = results.get('true_voltage_magnitudes', [])
    estimated_voltages = results.get('voltage_magnitudes', [])
    
    if true_voltages and estimated_voltages:
        print("🔋 Bus Voltage Comparison:")
        print("-" * 70)
        print(f"{'Bus':<5} {'True (p.u.)':<12} {'Estimated (p.u.)':<16} {'Error (%)':<12} {'Status':<10}")
        print("-" * 70)
        
        total_error = 0
        max_error = 0
        
        for i, (true_v, est_v) in enumerate(zip(true_voltages, estimated_voltages)):
            error_pct = ((est_v - true_v) / true_v) * 100 if true_v != 0 else 0
            total_error += abs(error_pct)
            max_error = max(max_error, abs(error_pct))
            
            status = "✅ Good" if abs(error_pct) < 1.0 else "⚠️  High" if abs(error_pct) < 5.0 else "❌ Poor"
            
            print(f"{i:<5} {true_v:<12.4f} {est_v:<16.4f} {error_pct:<12.2f} {status:<10}")
        
        mean_error = total_error / len(true_voltages) if true_voltages else 0
        
        print("-" * 70)
        print(f"📊 Summary: Mean Error = {mean_error:.2f}%, Max Error = {max_error:.2f}%")
    
    print()
    
    # Get detailed measurement comparison if available
    if 'comparison' in results:
        comparison_data = results['comparison']
        print("📋 Detailed Measurement Analysis:")
        print("-" * 90)
        print(f"{'Measurement':<20} {'True Value':<12} {'Measured':<12} {'Estimated':<12} {'Meas Error':<12} {'Est Error':<12}")
        print("-" * 90)
        
        for comp in comparison_data:
            if comp.get('Type') == 'Voltage':
                bus_info = comp.get('Description', 'Unknown')
                true_val = comp.get('True Value', 0)
                measured_val = comp.get('Measured Value', 0)
                estimated_val = comp.get('Estimated Value', 0)
                
                # Convert string values to float if needed
                try:
                    true_val = float(true_val)
                    measured_val = float(measured_val)
                    estimated_val = float(estimated_val)
                    
                    meas_error = ((measured_val - true_val) / true_val * 100) if true_val != 0 else 0
                    est_error = ((estimated_val - true_val) / true_val * 100) if true_val != 0 else 0
                    
                    print(f"{bus_info:<20} {true_val:<12.4f} {measured_val:<12.4f} {estimated_val:<12.4f} {meas_error:<12.2f} {est_error:<12.2f}")
                    
                except (ValueError, TypeError):
                    print(f"{bus_info:<20} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12}")
    
    print()


def demonstrate_noise_impact():
    """Demonstrate how different noise levels affect the results."""
    print("\n🎯 Noise Impact Analysis")
    print("=" * 70)
    
    db = GridDatabase()
    module = StateEstimationModule(db)
    
    noise_levels = [0.01, 0.025, 0.05, 0.1]  # 1%, 2.5%, 5%, 10%
    
    for noise in noise_levels:
        config = EstimationConfig(
            mode=EstimationMode.VOLTAGE_ONLY,
            voltage_noise_std=noise,
            max_iterations=50,
            tolerance=1e-4
        )
        
        results = module.estimate_grid_state(grid_id=5, config=config)  # Simple grid
        
        if results.get('success') and results.get('converged'):
            true_voltages = results.get('true_voltage_magnitudes', [])
            estimated_voltages = results.get('voltage_magnitudes', [])
            
            if true_voltages and estimated_voltages:
                errors = [abs((est - true) / true * 100) for true, est in zip(true_voltages, estimated_voltages)]
                mean_error = sum(errors) / len(errors)
                max_error = max(errors)
                
                print(f"Noise {noise*100:4.1f}%: Mean Error = {mean_error:5.2f}%, Max Error = {max_error:5.2f}%")


def show_measurement_noise_characteristics():
    """Show the characteristics of measurement noise."""
    print("\n📊 Measurement Noise Characteristics")
    print("=" * 70)
    
    # Create a simple test to show noise
    db = GridDatabase()
    net = db.load_grid(5)  # Simple grid
    
    from state_estimator import StateEstimator
    import pandapower as pp
    
    pp.runpp(net, verbose=False, numba=False)
    
    estimator = StateEstimator(net)
    
    # Add multiple measurements to the same bus to show noise variation
    print("Adding multiple noisy measurements to Bus 0:")
    print("-" * 50)
    
    true_voltage = net.res_bus.loc[0, 'vm_pu']
    print(f"True voltage at Bus 0: {true_voltage:.4f} p.u.")
    print()
    
    # Add 10 measurements with different noise realizations
    noise_std = 0.03  # 3% noise
    measurements = []
    
    for i in range(10):
        estimator.measurements = []  # Clear previous measurements
        estimator.add_voltage_measurements([0], noise_std=noise_std)
        measured_value = estimator.measurements[0].value
        measurements.append(measured_value)
        
        error = ((measured_value - true_voltage) / true_voltage) * 100
        print(f"Measurement {i+1:2d}: {measured_value:.4f} p.u. (Error: {error:+6.2f}%)")
    
    # Statistics
    mean_measured = sum(measurements) / len(measurements)
    std_measured = np.std(measurements)
    
    print("-" * 50)
    print(f"Statistics over {len(measurements)} measurements:")
    print(f"  Mean measured: {mean_measured:.4f} p.u.")
    print(f"  Std deviation: {std_measured:.4f} p.u. ({std_measured/true_voltage*100:.1f}%)")
    print(f"  Expected std:  {noise_std:.4f} p.u. ({noise_std*100:.1f}%)")
    print(f"  Bias:         {(mean_measured - true_voltage)/true_voltage*100:+.2f}%")


if __name__ == "__main__":
    print("🔬 STATE ESTIMATOR: MEASURED vs ESTIMATED VALUES ANALYSIS")
    print("=" * 70)
    
    # Analyze different grids
    db = GridDatabase()
    module = StateEstimationModule(db)
    grids = module.get_available_grids()
    
    # Analyze first few grids
    for grid_id, name, desc in grids[:2]:  # Just first 2 for brevity
        analyze_measurement_comparison(grid_id, name, noise_level=0.025)
    
    # Show noise impact
    demonstrate_noise_impact()
    
    # Show measurement characteristics
    show_measurement_noise_characteristics()
    
    print("\n🎓 Key Takeaways:")
    print("=" * 70)
    print("1. State estimation 'cleans' noisy measurements using system constraints")
    print("2. Estimated values are typically closer to true values than individual measurements")
    print("3. Higher noise levels result in larger estimation errors")
    print("4. Multiple measurements provide redundancy for better estimates")
    print("5. The state estimator performs statistical filtering of measurement noise")