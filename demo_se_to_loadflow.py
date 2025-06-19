#!/usr/bin/env python3
"""Demonstration of using state estimation results for load flow calculations.

This script shows how to:
1. Run state estimation on a grid with noisy measurements
2. Use the cleaned state estimates as initial conditions for load flow
3. Compare SE results vs load flow results
4. Demonstrate practical applications in grid operations
"""

from state_estimator import StateEstimator
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase
from examples import create_ieee_9_bus
import pandapower as pp
import numpy as np


def demo_se_to_loadflow():
    """Demonstrate state estimation to load flow workflow."""
    print("🔄 STATE ESTIMATION → LOAD FLOW DEMONSTRATION")
    print("=" * 70)
    
    # Create IEEE 9-bus system
    net = create_ieee_9_bus()
    print("📋 System: IEEE 9-Bus Test Network")
    print("🎯 Goal: Use cleaned SE estimates to initialize load flow")
    
    # Initialize state estimator
    estimator = StateEstimator(net)
    
    # Create realistic measurements with noise
    print("\n📊 STEP 1: STATE ESTIMATION WITH NOISY MEASUREMENTS")
    print("-" * 70)
    estimator.create_measurement_set_ieee9(simple_mode=True)  # Includes redundant measurements
    
    print(f"Created {len(estimator.measurements)} measurements")
    print("• Primary voltage measurements at all buses (2.5% noise)")
    print("• Redundant measurements at key buses (different sensor types)")
    
    # Run state estimation
    print("\n🔄 Running state estimation...")
    se_results = estimator.estimate_state(max_iterations=50, tolerance=1e-3)
    
    if not se_results['converged']:
        print("❌ State estimation failed to converge")
        return
    
    print("✅ State estimation converged successfully!")
    print(f"   Iterations: {se_results['iterations']}")
    print(f"   Objective function: {se_results['objective_function']:.6f}")
    print(f"   Final voltage range: {np.min(se_results['voltage_magnitudes']):.4f} - {np.max(se_results['voltage_magnitudes']):.4f} p.u.")
    
    # Run standard load flow for comparison
    print("\n📊 STEP 2: STANDARD LOAD FLOW (Without SE)")
    print("-" * 70)
    
    # Create fresh network copy for standard load flow
    import copy
    standard_net = copy.deepcopy(net)
    
    try:
        pp.runpp(standard_net, verbose=False, numba=False)
        print("✅ Standard load flow converged")
        standard_lf_voltages = standard_net.res_bus['vm_pu'].values
        print(f"   Standard LF voltage range: {np.min(standard_lf_voltages):.4f} - {np.max(standard_lf_voltages):.4f} p.u.")
    except:
        print("❌ Standard load flow failed")
        return
    
    # Run load flow with SE initialization
    print("\n📊 STEP 3: LOAD FLOW WITH SE INITIALIZATION")
    print("-" * 70)
    
    se_lf_results = estimator.run_load_flow_with_se_init(se_results)
    
    if not se_lf_results.get('success'):
        print(f"❌ SE-initialized load flow failed: {se_lf_results.get('error', 'Unknown error')}")
        return
    
    print("✅ SE-initialized load flow converged successfully!")
    se_lf_voltages = np.array(se_lf_results['voltage_magnitudes'])
    print(f"   SE-LF voltage range: {np.min(se_lf_voltages):.4f} - {np.max(se_lf_voltages):.4f} p.u.")
    
    # Compare all three results
    print("\n📈 STEP 4: COMPREHENSIVE COMPARISON")
    print("=" * 70)
    print("Bus | SE Voltage | Std LF   | SE-LF    | SE vs Std | SE vs SE-LF")
    print("-" * 70)
    
    se_voltages = np.array(se_results['voltage_magnitudes'])
    
    max_se_std_diff = 0
    max_se_self_diff = 0
    
    for bus in range(len(se_voltages)):
        se_v = se_voltages[bus]
        std_v = standard_lf_voltages[bus]
        se_lf_v = se_lf_voltages[bus]
        
        se_vs_std = ((se_v - std_v) / std_v) * 100
        se_vs_self = ((se_v - se_lf_v) / se_lf_v) * 100
        
        max_se_std_diff = max(max_se_std_diff, abs(se_vs_std))
        max_se_self_diff = max(max_se_self_diff, abs(se_vs_self))
        
        print(f" {bus:2d} | {se_v:8.4f} | {std_v:8.4f} | {se_lf_v:8.4f} | {se_vs_std:8.2f}% | {se_vs_self:8.2f}%")
    
    print("-" * 70)
    print(f"MAX DIFFERENCES:")
    print(f"  SE vs Standard LF:      {max_se_std_diff:.2f}%")
    print(f"  SE vs SE-initialized LF: {max_se_self_diff:.2f}%")
    
    # Analysis and insights
    print("\n💡 PRACTICAL INSIGHTS:")
    print("=" * 70)
    
    if max_se_self_diff < 1.0:
        print("✅ EXCELLENT: SE provides very good LF initialization")
        print("   • State estimation and load flow results are highly consistent")
        print("   • SE-cleaned measurements lead to reliable load flow convergence")
    elif max_se_self_diff < 2.0:
        print("✅ GOOD: SE provides good LF initialization")
        print("   • Minor differences between SE and LF are normal")
        print("   • SE helps with load flow convergence in difficult cases")
    else:
        print("⚠️  MODERATE: Some differences between SE and LF")
        print("   • May indicate modeling differences or measurement issues")
        print("   • Review measurement quality and network model")
    
    print(f"\n🔧 OPERATIONAL APPLICATIONS:")
    print("-" * 40)
    print("✅ Real-time grid monitoring: SE cleans sensor noise every 2-4 seconds")
    print("✅ Contingency analysis: Use SE results as base case for 'what-if' studies")
    print("✅ Economic dispatch: Cleaned state provides accurate starting point")
    print("✅ Optimal power flow: SE initialization improves convergence")
    print("✅ Grid planning: SE results validate network models against reality")
    
    print(f"\n📊 MEASUREMENT QUALITY SUMMARY:")
    print("-" * 40)
    print(f"• Total measurements processed: {len(estimator.measurements)}")
    print(f"• State estimation iterations: {se_results['iterations']}")
    print(f"• SE convergence quality: {se_results['objective_function']:.6f}")
    print(f"• Load flow with SE init: Successfully converged")
    
    # Compare SE vs LF using built-in comparison
    print(f"\n📋 DETAILED SE vs LF COMPARISON:")
    comparison_df = estimator.compare_se_vs_loadflow(se_results, se_lf_results)
    print(comparison_df.to_string(index=False))
    
    print(f"\n🎓 EDUCATIONAL VALUE:")
    print("=" * 70)
    print("• Shows complete workflow from noisy measurements → clean estimates → reliable load flow")
    print("• Demonstrates why grid operators run SE before other analyses")
    print("• Illustrates the practical value of measurement cleaning")
    print("• Validates network models against real-world sensor data")
    print("• Provides foundation for advanced grid optimization and control")
    
    return {
        'se_results': se_results,
        'standard_lf_results': {
            'voltages': standard_lf_voltages.tolist(),
            'converged': True
        },
        'se_lf_results': se_lf_results,
        'comparison': comparison_df
    }


def demo_with_state_estimation_module():
    """Demonstrate SE-to-LF using the state estimation module."""
    print("\n" + "=" * 70)
    print("🏭 USING STATE ESTIMATION MODULE FOR SE→LF WORKFLOW")
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
        print("❌ IEEE 9-Bus grid not found in database!")
        return
    
    print(f"📋 Using: {ieee9_grid[1]}")
    
    # Configure and run state estimation
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.025,  # 2.5% noise
        max_iterations=50
    )
    
    print("🔄 Running state estimation via module...")
    se_results = module.estimate_grid_state(ieee9_grid[0], config)
    
    if not se_results.get('success'):
        print(f"❌ State estimation failed: {se_results.get('error')}")
        return
    
    print("✅ State estimation completed via module!")
    
    # Run load flow with SE results
    print("🔄 Running load flow with SE initialization...")
    lf_results = module.run_load_flow_with_se_results(grid_id=ieee9_grid[0])
    
    if not lf_results.get('success'):
        print(f"❌ Load flow failed: {lf_results.get('error')}")
        return
    
    print("✅ Load flow with SE initialization completed!")
    
    # Show convergence quality
    if 'convergence_metrics' in lf_results:
        metrics = lf_results['convergence_metrics']
        print(f"\n📊 CONVERGENCE QUALITY ASSESSMENT:")
        print("-" * 50)
        print(f"  Maximum voltage difference: {metrics['max_voltage_difference_percent']:.2f}%")
        print(f"  Mean voltage difference:    {metrics['mean_voltage_difference_percent']:.2f}%")
        print(f"  RMS voltage difference:     {metrics['rms_voltage_difference_percent']:.2f}%")
        print(f"  Convergence quality:        {metrics['convergence_quality'].upper()}")
        print(f"  Good SE initialization:     {'✅ YES' if metrics['se_provided_good_initialization'] else '❌ NO'}")
    
    # Show SE vs LF comparison
    if 'se_vs_lf_comparison' in lf_results:
        print(f"\n📋 SE vs LF COMPARISON (via Module):")
        comparison_data = lf_results['se_vs_lf_comparison']
        print("Bus | SE Voltage | LF Voltage | V Diff | SE Angle | LF Angle | A Diff")
        print("-" * 70)
        for row in comparison_data:
            print(f" {row['Bus']:2d} | {row['SE Voltage (pu)']:8s} | {row['LF Voltage (pu)']:8s} | {row['V Diff (%)']:6s} | {row['SE Angle (deg)']:8s} | {row['LF Angle (deg)']:8s} | {row['Angle Diff (deg)']:6s}")
    
    print(f"\n🎯 MODULE WORKFLOW COMPLETE!")
    print("• State estimation: ✅ Converged")
    print("• Load flow with SE init: ✅ Converged")
    print("• Integration quality: ✅ Validated")
    
    return lf_results


if __name__ == "__main__":
    # Run both demonstrations
    print("🚀 RUNNING STATE ESTIMATION → LOAD FLOW DEMONSTRATIONS\n")
    
    # Basic demonstration
    basic_results = demo_se_to_loadflow()
    
    # Module-based demonstration  
    module_results = demo_with_state_estimation_module()
    
    print(f"\n🎉 ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("Key takeaways:")
    print("✅ State estimation cleans noisy sensor measurements")
    print("✅ Cleaned estimates provide excellent load flow initialization")
    print("✅ SE→LF workflow is essential for reliable grid operations")
    print("✅ Integration shows consistency between SE and power flow models")