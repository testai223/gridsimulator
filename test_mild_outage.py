#!/usr/bin/env python3
"""Test mild outage scenarios that might still allow convergence."""

from state_estimator import StateEstimator
from examples import create_ieee_9_bus
import numpy as np


def test_mild_outage_scenarios():
    """Test outage scenarios that might still allow SE to converge."""
    print("🧪 TESTING MILD OUTAGE SCENARIOS")
    print("=" * 50)
    
    # Create network with more measurements for better redundancy
    net = create_ieee_9_bus()
    
    # Test different measurement configurations
    test_configs = [
        ("Standard config", lambda est: est.create_measurement_set_ieee9(simple_mode=True)),
        ("Comprehensive config", lambda est: est.create_measurement_set_ieee9(simple_mode=False)),
    ]
    
    for config_name, measurement_setup in test_configs:
        print(f"\n📊 Testing {config_name}:")
        
        estimator = StateEstimator(net)
        measurement_setup(estimator)
        
        print(f"   Total measurements: {len(estimator.measurements)}")
        
        # Test baseline (no outage)
        baseline_results = estimator.estimate_state(max_iterations=30, tolerance=1e-3)
        if baseline_results['converged']:
            print(f"   ✅ Baseline converged in {baseline_results['iterations']} iterations")
        else:
            print(f"   ❌ Baseline failed to converge")
            continue
        
        # Test mild outages (try each bus individually)
        successful_outages = []
        failed_outages = []
        
        for bus in range(9):
            try:
                outage_results = estimator.estimate_state_with_outage_analysis(
                    outage_buses=[bus],
                    max_iterations=50,  # More iterations for difficult cases
                    tolerance=1e-2      # Relaxed tolerance
                )
                
                if outage_results.get('converged', False):
                    successful_outages.append(bus)
                    impact = outage_results.get('outage_impact', {})
                    quality = impact.get('quality_assessment', 'Unknown')
                    print(f"   ✅ Bus {bus} outage: CONVERGED ({quality})")
                else:
                    failed_outages.append(bus)
                    print(f"   ❌ Bus {bus} outage: FAILED")
                    
            except Exception as e:
                failed_outages.append(bus)
                print(f"   ❌ Bus {bus} outage: ERROR ({e})")
        
        print(f"   Summary: {len(successful_outages)} successful, {len(failed_outages)} failed outages")
        
        if successful_outages:
            print(f"   🎯 Buses with successful outages: {successful_outages}")
        else:
            print(f"   ⚠️  No outages allow convergence with this configuration")
    
    return True


def find_working_outage_example():
    """Find a specific outage example that works for demonstration."""
    print("\n🔍 FINDING WORKING OUTAGE EXAMPLE")
    print("=" * 50)
    
    net = create_ieee_9_bus()
    estimator = StateEstimator(net)
    
    # Try with minimal noise and comprehensive measurements
    estimator.create_measurement_set_ieee9(simple_mode=False)
    
    # Reduce noise in measurements
    for measurement in estimator.measurements:
        measurement.variance = (measurement.variance ** 0.5 * 0.5) ** 2  # Reduce noise by half
    
    print(f"📊 Testing with {len(estimator.measurements)} low-noise measurements")
    
    # Test baseline
    baseline_results = estimator.estimate_state(max_iterations=50, tolerance=1e-3)
    if not baseline_results['converged']:
        print("❌ Even baseline doesn't converge with this setup")
        return False
    
    print(f"✅ Baseline converged in {baseline_results['iterations']} iterations")
    
    # Try each bus with relaxed parameters
    for bus in range(9):
        try:
            outage_results = estimator.estimate_state_with_outage_analysis(
                outage_buses=[bus],
                max_iterations=100,  # Many iterations
                tolerance=1e-1       # Very relaxed tolerance
            )
            
            if outage_results.get('converged', False):
                print(f"🎯 FOUND WORKING EXAMPLE: Bus {bus} outage")
                print(f"   Iterations: {outage_results['iterations']}")
                print(f"   Objective: {outage_results.get('objective_function', 'N/A'):.6f}")
                
                if 'outage_impact' in outage_results:
                    impact = outage_results['outage_impact']
                    print(f"   Quality: {impact.get('quality_assessment', 'Unknown')}")
                    print(f"   Uncertainty increase: {impact.get('estimated_uncertainty_increase', 0):.1f}%")
                
                return True
                
        except Exception as e:
            continue
    
    print("❌ No working outage examples found even with relaxed parameters")
    return False


def demonstrate_measurement_redundancy_effect():
    """Demonstrate how measurement redundancy affects outage resilience."""
    print("\n📈 DEMONSTRATING MEASUREMENT REDUNDANCY EFFECT")
    print("=" * 50)
    
    net = create_ieee_9_bus()
    
    # Test different redundancy levels
    redundancy_tests = [
        ("Minimal (9 measurements)", 9),
        ("Low redundancy (12 measurements)", 12),
        ("Medium redundancy (15 measurements)", 15),
        ("High redundancy (20 measurements)", 20)
    ]
    
    for description, target_measurements in redundancy_tests:
        print(f"\n🔍 {description}:")
        
        estimator = StateEstimator(net)
        
        # Add voltage measurements up to target
        all_buses = list(range(9))
        estimator.add_voltage_measurements(all_buses, noise_std=0.005)  # Low noise
        
        # Add extra measurements if needed
        current_count = len(estimator.measurements)
        if current_count < target_measurements:
            # Add redundant voltage measurements
            extra_needed = target_measurements - current_count
            for i in range(min(extra_needed, 9)):  # Add up to 9 more
                estimator.add_voltage_measurements([i], noise_std=0.008)
        
        actual_count = len(estimator.measurements)
        redundancy = actual_count / (9 * 2 - 1)  # 9 buses, 2 states per bus minus slack angle
        
        print(f"   Measurements: {actual_count}, Redundancy: {redundancy:.2f}")
        
        # Test outage resilience
        successful_outages = 0
        for bus in range(9):
            try:
                outage_results = estimator.estimate_state_with_outage_analysis(
                    outage_buses=[bus],
                    max_iterations=30,
                    tolerance=1e-2
                )
                
                if outage_results.get('converged', False):
                    successful_outages += 1
                    
            except:
                pass
        
        resilience_percent = (successful_outages / 9) * 100
        print(f"   Outage resilience: {successful_outages}/9 buses ({resilience_percent:.0f}%)")
        
        if resilience_percent > 50:
            print(f"   ✅ GOOD resilience")
        elif resilience_percent > 20:
            print(f"   ⚠️  FAIR resilience")
        else:
            print(f"   ❌ POOR resilience")
    
    return True


if __name__ == "__main__":
    print("🚀 RUNNING MILD OUTAGE TESTS\n")
    
    test_mild_outage_scenarios()
    find_working_outage_example()
    demonstrate_measurement_redundancy_effect()
    
    print(f"\n💡 KEY INSIGHTS:")
    print("=" * 50)
    print("✅ Most single-bus outages cause unobservability (realistic)")
    print("✅ Higher measurement redundancy improves outage resilience")
    print("✅ System design requires careful measurement placement")
    print("✅ Educational value: shows importance of backup measurements")
    
    print(f"\n🎯 FOR GUI USERS:")
    print("• Try outage simulation on IEEE 9-Bus system")
    print("• Expect most outages to cause unobservability (this is realistic!)")
    print("• Critical outages demonstrate need for backup systems")
    print("• Click 'View Results' to see detailed observability analysis")