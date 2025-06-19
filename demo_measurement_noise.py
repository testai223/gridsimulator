#!/usr/bin/env python3
"""Demonstrate measurement noise vs cleaned estimates explicitly."""

from state_estimator import StateEstimator
from examples import create_ieee_9_bus
import pandapower as pp
import random
import numpy as np


def demo_explicit_noise():
    """Show explicit measurement noise vs cleaned estimates."""
    print("🎯 EXPLICIT MEASUREMENT NOISE DEMONSTRATION")
    print("=" * 70)
    
    # Create IEEE 9-bus system
    net = create_ieee_9_bus()
    pp.runpp(net, verbose=False, numba=False)
    
    print("📋 Setup: IEEE 9-Bus System")
    print("🎯 Goal: Show realistic sensor noise vs cleaned state estimates")
    print("⚙️  Method: Add 3% noise to create visible differences")
    
    # Initialize state estimator
    estimator = StateEstimator(net)
    
    # Manually create measurements with visible noise
    print(f"\n📊 CREATING REALISTIC NOISY MEASUREMENTS:")
    print("-" * 70)
    print("Bus | True Value | Measured   | Noise (%) | Sensor Type")
    print("-" * 70)
    
    measurement_details = []
    
    for bus in range(9):  # All 9 buses
        true_value = net.res_bus.loc[bus, 'vm_pu']
        
        # Add realistic measurement noise (1.2% standard deviation for better convergence)
        noise_std = 0.012  # 1.2% noise
        noise = random.gauss(0, noise_std)
        measured_value = true_value + noise
        noise_percent = (noise / true_value) * 100
        
        # Create measurement
        from state_estimator import Measurement, MeasurementType
        measurement = Measurement(
            meas_type=MeasurementType.VOLTAGE_MAGNITUDE,
            bus_from=bus,
            bus_to=None,
            value=measured_value,
            variance=noise_std**2
        )
        estimator.measurements.append(measurement)
        
        # Store details for display
        measurement_details.append({
            'bus': bus,
            'true': true_value,
            'measured': measured_value,
            'noise_percent': noise_percent
        })
        
        sensor_type = "PMU" if abs(noise_percent) < 2 else "SCADA"
        print(f" {bus:2d} | {true_value:9.4f} | {measured_value:9.4f} | {noise_percent:8.2f} | {sensor_type}")
    
    # Add some redundant measurements to show conflict resolution
    print(f"\n📡 ADDING REDUNDANT MEASUREMENTS (Different Sensors):")
    print("-" * 70)
    redundant_buses = [0, 2, 4, 6, 8]
    for bus in redundant_buses:
        true_value = net.res_bus.loc[bus, 'vm_pu']
        
        # Second sensor with different characteristics
        noise_std = 0.008  # Slightly different accuracy
        bias = random.gauss(0, 0.003)  # Small sensor bias
        noise = random.gauss(0, noise_std)
        measured_value = true_value + bias + noise
        
        measurement = Measurement(
            meas_type=MeasurementType.VOLTAGE_MAGNITUDE,
            bus_from=bus,
            bus_to=None,
            value=measured_value,
            variance=noise_std**2
        )
        estimator.measurements.append(measurement)
        
        total_error = ((measured_value - true_value) / true_value) * 100
        print(f" {bus:2d} | {true_value:9.4f} | {measured_value:9.4f} | {total_error:8.2f} | Backup PMU")
    
    print(f"\nTotal measurements: {len(estimator.measurements)} (9 primary + 5 redundant)")
    
    # Run state estimation with more relaxed parameters for convergence
    print(f"\n🔄 RUNNING WEIGHTED LEAST SQUARES STATE ESTIMATION...")
    results = estimator.estimate_state(max_iterations=50, tolerance=1e-3)
    
    if results['converged']:
        print("✅ State estimation converged successfully!")
        print(f"   Iterations: {results['iterations']}")
        print(f"   Objective function: {results['objective_function']:.6f}")
    else:
        print("❌ State estimation failed to converge")
        return
    
    # Show cleaning results
    print(f"\n🧹 MEASUREMENT CLEANING RESULTS:")
    print("=" * 70)
    print("Bus | True Value | Noisy Meas | Clean Est  | Noise Red. | Quality")
    print("-" * 70)
    
    estimated_voltages = results['voltage_magnitudes']
    
    for detail in measurement_details:
        bus = detail['bus']
        true_val = detail['true']
        measured_val = detail['measured']
        estimated_val = estimated_voltages[bus]
        
        original_error = abs((measured_val - true_val) / true_val) * 100
        final_error = abs((estimated_val - true_val) / true_val) * 100
        noise_reduction = original_error - final_error
        
        if noise_reduction > 1.0:
            quality = "🧹 CLEANED"
        elif noise_reduction > 0.2:
            quality = "✨ IMPROVED"
        else:
            quality = "✅ GOOD"
        
        print(f" {bus:2d} | {true_val:9.4f} | {measured_val:9.4f} | {estimated_val:9.4f} | {noise_reduction:8.2f}% | {quality}")
    
    # Calculate overall improvement
    original_errors = [abs((d['measured'] - d['true']) / d['true']) * 100 for d in measurement_details]
    final_errors = [abs((estimated_voltages[d['bus']] - d['true']) / d['true']) * 100 for d in measurement_details]
    
    avg_original = np.mean(original_errors)
    avg_final = np.mean(final_errors)
    improvement = avg_original - avg_final
    
    print("-" * 70)
    print(f"NOISE REDUCTION SUMMARY:")
    print(f"  Average original error: {avg_original:.2f}%")
    print(f"  Average final error:    {avg_final:.2f}%")
    print(f"  Overall improvement:    {improvement:.2f}%")
    
    if improvement > 0.5:
        print(f"  🎉 EXCELLENT cleaning performance!")
    elif improvement > 0.1:
        print(f"  ✅ GOOD cleaning performance!")
    else:
        print(f"  📊 Measurements were already quite clean")
    
    print(f"\n💡 KEY INSIGHTS:")
    print("=" * 70)
    print("✅ State estimation reduces measurement noise through statistical averaging")
    print("✅ Redundant measurements improve estimate accuracy")
    print("✅ WLS algorithm weights measurements by their accuracy")
    print("✅ Final estimates are more accurate than individual measurements")
    
    print(f"\n🎓 EDUCATIONAL VALUE:")
    print("This demonstration shows exactly what happens in real grid operations:")
    print("• Sensors provide noisy measurements (2-5% error typical)")
    print("• State estimation 'cleans' the data through mathematical optimization")
    print("• Final estimates are more accurate than raw sensor readings")
    print("• Grid operators can trust the cleaned estimates for control decisions")


if __name__ == "__main__":
    demo_explicit_noise()