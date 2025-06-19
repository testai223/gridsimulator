#!/usr/bin/env python3
"""Demonstration of measurement outage impact on state estimation.

This script shows how measurement failures affect:
1. System observability
2. State estimation accuracy
3. Grid operation reliability
4. Recovery strategies
"""

from state_estimator import StateEstimator, MeasurementType
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase
from examples import create_ieee_9_bus
import pandapower as pp
import numpy as np


def demo_single_bus_outage():
    """Demonstrate impact of single bus measurement outage."""
    print("🚨 SINGLE BUS MEASUREMENT OUTAGE DEMONSTRATION")
    print("=" * 70)
    
    # Create IEEE 9-bus system
    net = create_ieee_9_bus()
    print("📋 System: IEEE 9-Bus Test Network")
    print("🎯 Goal: Show impact of losing measurements at one bus")
    
    # Initialize state estimator
    estimator = StateEstimator(net)
    estimator.create_measurement_set_ieee9(simple_mode=True)
    
    print(f"\n📊 BASELINE: {len(estimator.measurements)} measurements")
    
    # Run baseline state estimation
    print("\n🔄 Running baseline state estimation...")
    baseline_results = estimator.estimate_state(max_iterations=50, tolerance=1e-3)
    
    if not baseline_results['converged']:
        print("❌ Baseline state estimation failed")
        return
    
    print("✅ Baseline converged successfully!")
    print(f"   Iterations: {baseline_results['iterations']}")
    print(f"   Objective function: {baseline_results['objective_function']:.6f}")
    
    # Simulate outage at bus 4 (critical bus in IEEE 9-bus system)
    outage_bus = 4
    print(f"\n🚨 SIMULATING OUTAGE: Bus {outage_bus}")
    print("-" * 40)
    
    outage_results = estimator.estimate_state_with_outage_analysis(
        outage_buses=[outage_bus],
        max_iterations=50,
        tolerance=1e-3
    )
    
    # Analyze outage impact
    if outage_results.get('outage_simulation'):
        outage_info = outage_results['outage_simulation']
        observability = outage_info['observability_analysis']
        
        print(f"Measurements before outage: {outage_info['original_measurement_count']}")
        print(f"Measurements after outage:  {outage_info['remaining_measurement_count']}")
        print(f"Measurements lost:          {outage_info['outaged_measurement_count']}")
        print(f"Redundancy before:          {outage_info['measurement_redundancy_before']:.2f}")
        print(f"Redundancy after:           {outage_info['measurement_redundancy_after']:.2f}")
        print(f"Observability status:       {observability['observability_status']}")
        
        if observability['unobservable_buses']:
            print(f"⚠️  Unobservable buses:        {observability['unobservable_buses']}")
        if observability['critically_observable_buses']:
            print(f"⚠️  Critically observable:     {observability['critically_observable_buses']}")
    
    # Check if state estimation still converged
    if outage_results.get('converged', False):
        print(f"\n✅ State estimation still converged with outage!")
        print(f"   Iterations: {outage_results['iterations']}")
        print(f"   Objective function: {outage_results['objective_function']:.6f}")
        
        # Compare voltage estimates
        baseline_vm = np.array(baseline_results['voltage_magnitudes'])
        outage_vm = np.array(outage_results['voltage_magnitudes'])
        
        voltage_diffs = np.abs((outage_vm - baseline_vm) / baseline_vm) * 100
        max_diff = np.max(voltage_diffs)
        mean_diff = np.mean(voltage_diffs)
        
        print(f"\n📊 VOLTAGE ESTIMATE COMPARISON:")
        print(f"   Maximum difference: {max_diff:.2f}%")
        print(f"   Average difference: {mean_diff:.2f}%")
        
        # Show impact assessment
        if 'outage_impact' in outage_results:
            impact = outage_results['outage_impact']
            print(f"\n🔍 OUTAGE IMPACT ASSESSMENT:")
            print(f"   Measurement loss: {impact['measurement_loss_percent']:.1f}%")
            print(f"   Redundancy loss:  {impact['redundancy_loss']:.3f}")
            print(f"   Quality assessment: {impact['quality_assessment']}")
            print(f"   Convergence difficulty: {impact['convergence_difficulty']}")
        
    else:
        print(f"\n❌ State estimation FAILED with outage!")
        if 'unobservable_buses' in outage_results:
            print(f"   Unobservable buses: {outage_results['unobservable_buses']}")
    
    # Show recommendations
    if outage_results.get('outage_simulation'):
        recommendations = outage_results['outage_simulation']['observability_analysis']['recommendations']
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"   • {rec}")
    
    return {
        'baseline_results': baseline_results,
        'outage_results': outage_results,
        'outage_bus': outage_bus
    }


def demo_multiple_bus_outage():
    """Demonstrate impact of multiple bus measurement outages."""
    print("\n" + "=" * 70)
    print("🚨 MULTIPLE BUS MEASUREMENT OUTAGE DEMONSTRATION")
    print("=" * 70)
    
    # Initialize module
    db = GridDatabase()
    db.initialize_example_grids()
    module = StateEstimationModule(db)
    
    # Get IEEE 9-bus grid
    grids = module.get_available_grids()
    ieee9_grid = None
    for grid in grids:
        if "IEEE 9-Bus" in grid[1]:
            ieee9_grid = grid
            break
    
    if not ieee9_grid:
        print("❌ IEEE 9-Bus grid not found!")
        return
    
    print(f"📋 Testing on: {ieee9_grid[1]}")
    
    # Test different outage scenarios
    outage_scenarios = [
        ([1], "Single Load Bus"),
        ([2, 6], "Two Adjacent Buses"),
        ([0, 4, 8], "Three Critical Buses"),
        ([1, 3, 5, 7], "Four Buses (High Impact)")
    ]
    
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.025,
        max_iterations=50
    )
    
    for outage_buses, scenario_name in outage_scenarios:
        print(f"\n📊 SCENARIO: {scenario_name}")
        print(f"Outaged buses: {outage_buses}")
        print("-" * 50)
        
        try:
            results = module.simulate_measurement_outage_scenario(
                grid_id=ieee9_grid[0],
                outage_buses=outage_buses,
                config=config
            )
            
            if results.get('success'):
                comparison = results.get('comparison_analysis', {})
                
                # Check convergence status
                if comparison.get('outage_converged', False):
                    voltage_impact = comparison.get('voltage_impact', {})
                    measurement_impact = comparison.get('measurement_impact', {})
                    
                    print(f"✅ State estimation converged")
                    print(f"   Max voltage error: {voltage_impact.get('max_difference_percent', 0):.2f}%")
                    print(f"   Measurements lost: {measurement_impact.get('measurement_loss_percent', 0):.1f}%")
                    print(f"   Quality impact: {comparison.get('quality_impact', 'Unknown')}")
                else:
                    print(f"❌ State estimation FAILED")
                    print(f"   System became unobservable")
                    print(f"   Unobservable buses: {comparison.get('unobservable_buses', [])}")
            else:
                print(f"❌ Simulation failed: {results.get('error', 'Unknown')}")
                
        except Exception as e:
            print(f"❌ Error in scenario: {e}")
    
    return True


def demo_outage_recovery_strategies():
    """Demonstrate strategies for recovering from measurement outages."""
    print("\n" + "=" * 70)
    print("🔧 MEASUREMENT OUTAGE RECOVERY STRATEGIES")
    print("=" * 70)
    
    net = create_ieee_9_bus()
    estimator = StateEstimator(net)
    estimator.create_measurement_set_ieee9(simple_mode=True)
    
    # Create a severe outage scenario
    critical_buses = [2, 4, 6]  # Multiple important buses
    print(f"🚨 Severe outage scenario: Buses {critical_buses}")
    
    # Test the outage
    print("\n📊 STEP 1: Testing severe outage impact")
    outage_results = estimator.estimate_state_with_outage_analysis(
        outage_buses=critical_buses,
        max_iterations=50,
        tolerance=1e-3
    )
    
    if not outage_results.get('converged', False):
        print("❌ System is unobservable with severe outage")
        
        # Strategy 1: Reduce outage scope
        print("\n🔧 STRATEGY 1: Partial recovery")
        partial_outage = critical_buses[:-1]  # Remove one bus from outage
        print(f"   Restoring measurements at bus {critical_buses[-1]}")
        
        partial_results = estimator.estimate_state_with_outage_analysis(
            outage_buses=partial_outage,
            max_iterations=50,
            tolerance=1e-3
        )
        
        if partial_results.get('converged', False):
            print("   ✅ Partial recovery successful!")
            print(f"   System is now observable")
        else:
            print("   ❌ Partial recovery insufficient")
        
        # Strategy 2: Add backup measurements
        print("\n🔧 STRATEGY 2: Deploy backup measurement systems")
        print("   In real operations:")
        print("   • Activate portable PMU units")
        print("   • Use backup SCADA channels")
        print("   • Deploy emergency measurement teams")
        print("   • Utilize state forecast methods")
        
    else:
        print("✅ System remains observable even with severe outage")
        impact = outage_results.get('outage_impact', {})
        print(f"   Quality assessment: {impact.get('quality_assessment', 'Unknown')}")
    
    # General recovery recommendations
    print(f"\n💡 GENERAL RECOVERY STRATEGIES:")
    print("=" * 50)
    print("🔧 IMMEDIATE ACTIONS:")
    print("   • Check communication links")
    print("   • Restart measurement devices")
    print("   • Switch to backup sensors")
    print("   • Verify power supply to RTUs")
    
    print("\n📊 OPERATIONAL PROCEDURES:")
    print("   • Increase SE solution tolerance temporarily")
    print("   • Use pseudo-measurements for critical buses")
    print("   • Apply load forecasting for missing injections")
    print("   • Consider manual state entry for critical states")
    
    print("\n🚨 CONTINGENCY PLANNING:")
    print("   • Identify critical measurement points")
    print("   • Install redundant sensors at key locations")
    print("   • Plan backup communication paths")
    print("   • Train operators for outage scenarios")
    
    return True


def demo_observability_analysis():
    """Demonstrate detailed observability analysis during outages."""
    print("\n" + "=" * 70)
    print("🔍 OBSERVABILITY ANALYSIS DEMONSTRATION")
    print("=" * 70)
    
    net = create_ieee_9_bus()
    estimator = StateEstimator(net)
    estimator.create_measurement_set_ieee9(simple_mode=True)
    
    print("📊 Analyzing observability for different outage scenarios:")
    
    # Test different combinations
    test_scenarios = [
        ([], "No Outage (Baseline)"),
        ([1], "Single Load Bus"),
        ([0], "Slack Bus"),
        ([3], "Generator Bus"),
        ([1, 7], "Two Load Buses"),
        ([0, 1], "Slack + Load Bus"),
        ([3, 6], "Two Generator Buses"),
        ([1, 4, 7], "Three Load Buses"),
        ([0, 3, 6], "All Generator Buses")
    ]
    
    print("\nBus | Scenario Description    | Observable | Redundancy | Quality")
    print("-" * 70)
    
    for outage_buses, description in test_scenarios:
        try:
            # Store original measurements
            original_measurements = estimator.measurements.copy()
            
            if outage_buses:
                outage_info = estimator.simulate_measurement_outage(outage_buses)
                observability = outage_info['observability_analysis']
                redundancy = outage_info['measurement_redundancy_after']
                
                if observability['unobservable_buses']:
                    observable_status = "❌ NO"
                    quality = "CRITICAL"
                elif observability['critically_observable_buses']:
                    observable_status = "⚠️ POOR"
                    quality = "WARNING"
                elif redundancy < 1.2:
                    observable_status = "✅ YES"
                    quality = "POOR"
                elif redundancy < 1.5:
                    observable_status = "✅ YES"
                    quality = "FAIR"
                else:
                    observable_status = "✅ YES"
                    quality = "GOOD"
                
                # Restore measurements
                estimator.measurements = original_measurements
            else:
                # Baseline case
                observable_status = "✅ YES"
                redundancy = len(estimator.measurements) / (len(net.bus) * 2 - 1)
                quality = "EXCELLENT"
            
            bus_str = str(outage_buses) if outage_buses else "None"
            print(f"{bus_str:3s} | {description:23s} | {observable_status:10s} | {redundancy:8.2f} | {quality}")
            
        except Exception as e:
            print(f"{outage_buses} | {description:23s} | ERROR     | N/A      | N/A")
    
    print("\n💡 OBSERVABILITY INSIGHTS:")
    print("=" * 40)
    print("✅ System remains observable in most single-bus outages")
    print("⚠️  Generator bus outages have higher impact due to power injections")
    print("❌ Multiple bus outages can cause critical observability loss")
    print("📊 Measurement redundancy is key to outage resilience")
    
    return True


if __name__ == "__main__":
    print("🚀 RUNNING MEASUREMENT OUTAGE DEMONSTRATIONS\n")
    
    # Run all demonstrations
    print("=" * 70)
    demo_single_bus_outage()
    
    demo_multiple_bus_outage()
    
    demo_outage_recovery_strategies()
    
    demo_observability_analysis()
    
    print(f"\n🎉 ALL OUTAGE DEMONSTRATIONS COMPLETED!")
    print("=" * 70)
    print("Key takeaways:")
    print("✅ Measurement outages are a critical operational concern")
    print("✅ System observability depends on measurement redundancy")
    print("✅ Strategic backup systems can maintain grid visibility")
    print("✅ Recovery strategies are essential for reliable operations")
    print("✅ Operators must understand outage impact scenarios")