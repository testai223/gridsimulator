#!/usr/bin/env python3
"""Test script for state estimator functionality."""

from state_estimator import StateEstimator
from examples import create_ieee_9_bus
import pandapower as pp

def test_basic_functionality():
    """Test basic state estimator functionality."""
    print("Testing State Estimator Basic Functionality")
    print("=" * 50)
    
    # Create IEEE 9-bus system
    net = create_ieee_9_bus()
    
    # Run power flow to get true state
    pp.runpp(net, verbose=False, numba=False)
    print(f"True system has {len(net.bus)} buses")
    print(f"Network converged: {net.converged}")
    
    # Initialize state estimator
    estimator = StateEstimator(net)
    
    # Add voltage measurements only (simpler case)
    estimator.add_voltage_measurements([0, 1, 2, 3, 4, 5, 6, 7, 8], noise_std=0.01)
    
    print(f"Added {len(estimator.measurements)} voltage measurements")
    
    # Run state estimation
    results = estimator.estimate_state(max_iterations=5, tolerance=1e-3)
    
    print(f"State estimation converged: {results['converged']}")
    print(f"Iterations: {results['iterations']}")
    print(f"Objective function: {results['objective_function']:.6f}")
    
    # Show voltage comparison
    print("\nVoltage Comparison:")
    print("Bus | True V (pu) | Est V (pu) | Error (%)")
    print("-" * 45)
    
    for bus in range(len(net.bus)):
        true_v = net.res_bus.loc[bus, 'vm_pu']
        est_v = results['voltage_magnitudes'][bus]
        error = 100 * (est_v - true_v) / true_v
        print(f"{bus:3d} | {true_v:10.4f} | {est_v:9.4f} | {error:8.2f}")

if __name__ == "__main__":
    test_basic_functionality()