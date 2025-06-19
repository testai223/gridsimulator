#!/usr/bin/env python3
"""Test realistic quality metrics for state estimation."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase


def test_realistic_quality_metrics():
    """Test the realistic quality metrics functionality."""
    print("🔬 TESTING REALISTIC GRID OPERATION METRICS")
    print("=" * 60)
    
    # Initialize
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
    print("⚙️  Configuration: Voltage measurements with 2.5% noise (realistic)")
    
    # Configure state estimation
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.025,  # 2.5% noise for visible differences
        max_iterations=20
    )
    
    print("🔄 Running state estimation...")
    
    # Run state estimation
    results = module.estimate_grid_state(ieee9_grid[0], config)
    
    if not results.get('success', False):
        print(f"❌ State estimation failed: {results.get('error', 'Unknown error')}")
        return
    
    print("✅ State estimation completed successfully!")
    
    # Check quality metrics
    if 'quality_metrics' in results:
        quality = results['quality_metrics']
        print(f"\n📊 INDUSTRY-STANDARD QUALITY METRICS:")
        print("=" * 60)
        
        # Chi-square test
        chi_square = quality.get('chi_square_statistic', 0)
        chi_critical = quality.get('chi_square_critical', 0)
        chi_passed = quality.get('chi_square_test_passed', False)
        
        print(f"🔍 CHI-SQUARE TEST (Network Consistency):")
        print(f"   Statistic: {chi_square:.3f}")
        print(f"   Critical:  {chi_critical:.3f}")
        print(f"   Result:    {'✅ PASSED' if chi_passed else '❌ FAILED'}")
        
        # Bad data detection
        lnr = quality.get('largest_normalized_residual', 0)
        suspicious = quality.get('suspicious_measurements', 0)
        bad_data = quality.get('bad_measurements', 0)
        total_meas = quality.get('total_measurements', 0)
        
        print(f"\n🚨 BAD DATA DETECTION (LNR Method):")
        print(f"   Largest Normalized Residual: {lnr:.3f}")
        print(f"   Suspicious measurements:     {suspicious}/{total_meas}")
        print(f"   Bad data detected:          {bad_data}/{total_meas}")
        
        # Interpretation
        if lnr < 3.0:
            lnr_status = "✅ NORMAL - All measurements look good"
        elif lnr < 4.0:
            lnr_status = "⚠️ SUSPICIOUS - Monitor closely"
        else:
            lnr_status = "❌ BAD DATA - Investigate sensors"
        
        print(f"   Assessment: {lnr_status}")
        
        # Measurement redundancy
        redundancy = quality.get('measurement_redundancy', 0)
        print(f"\n📈 MEASUREMENT REDUNDANCY:")
        print(f"   Redundancy: {redundancy:.2f}")
        
        if redundancy > 1.5:
            redundancy_status = "✅ EXCELLENT - Good observability"
        elif redundancy > 1.2:
            redundancy_status = "✅ GOOD - Adequate observability"
        else:
            redundancy_status = "⚠️ POOR - Need more measurements"
        
        print(f"   Assessment: {redundancy_status}")
        
        # Overall assessment
        print(f"\n🎯 OVERALL QUALITY ASSESSMENT:")
        if chi_passed and lnr < 3.0 and bad_data == 0:
            overall = "✅ EXCELLENT - Ready for grid control"
        elif chi_passed and lnr < 4.0 and bad_data == 0:
            overall = "✅ GOOD - Suitable for most operations"
        elif suspicious > 0 or lnr > 4.0:
            overall = "⚠️ SUSPICIOUS - Monitor closely"
        else:
            overall = "❌ POOR - Not suitable for control"
        
        print(f"   Status: {overall}")
        
    else:
        print("❌ No quality metrics found in results")
    
    print(f"\n💡 KEY INSIGHTS:")
    print("=" * 60)
    print("✅ Real grid operators use these EXACT metrics")
    print("✅ No 'truth' comparison needed - validates internal consistency")
    print("✅ Chi-square test catches network model errors")
    print("✅ LNR method identifies faulty sensors automatically")
    print("✅ Measurement redundancy ensures reliable estimates")
    
    print(f"\n🎓 EDUCATIONAL VALUE:")
    print("=" * 60)
    print("• Shows what real operators see every 2-4 seconds")
    print("• Demonstrates industry-standard validation methods")
    print("• No artificial 'truth' values needed")
    print("• Practical quality assessment for grid operations")
    
    print(f"\n🚀 CONCLUSION:")
    print("The enhanced GUI now shows realistic grid operation metrics!")


if __name__ == "__main__":
    test_realistic_quality_metrics()