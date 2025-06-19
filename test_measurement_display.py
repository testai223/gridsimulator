#!/usr/bin/env python3
"""Test the enhanced measurement vs estimate display functionality."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase


def test_measurement_display():
    """Test the measurement vs estimate comparison display."""
    print("🔬 TESTING MEASUREMENT vs ESTIMATE DISPLAY")
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
    
    # Configure state estimation
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.01,  # 1% noise
        max_iterations=20
    )
    
    print("⚙️  Running state estimation...")
    
    # Run state estimation
    results = module.estimate_grid_state(ieee9_grid[0], config)
    
    if not results.get('success', False):
        print(f"❌ State estimation failed: {results.get('error', 'Unknown error')}")
        return
    
    print("✅ State estimation completed successfully!")
    
    # Check if measurement vs estimate data is available
    if 'measurement_vs_estimate' in results:
        meas_vs_est = results['measurement_vs_estimate']
        print(f"\n📊 MEASUREMENT vs ESTIMATE COMPARISON:")
        print(f"Found {len(meas_vs_est)} measurement comparisons")
        print("-" * 80)
        print("Measurement                    | Measured  | Estimated | Diff (%) | Quality")
        print("-" * 80)
        
        for i, data in enumerate(meas_vs_est[:8]):  # Show first 8
            description = data.get('Description', 'Unknown')[:25]
            measured = data.get('Measured Value', 'N/A')
            estimated = data.get('Estimated Value', 'N/A')
            error = data.get('Error (%)', '0')
            unit = data.get('Unit', '')
            
            # Determine quality
            try:
                error_val = float(error)
                abs_error = abs(error_val)
                if abs_error < 1.0:
                    quality = "Excellent ⭐⭐⭐"
                elif abs_error < 3.0:
                    quality = "Good ⭐⭐"
                elif abs_error < 5.0:
                    quality = "Fair ⭐"
                else:
                    quality = "Poor"
            except:
                quality = "Unknown"
            
            print(f"{description:30s} | {measured:8s} | {estimated:8s} | {error:7s} | {quality}")
        
        if len(meas_vs_est) > 8:
            print(f"... and {len(meas_vs_est) - 8} more measurements")
        
        # Summary statistics
        error_values = []
        for data in meas_vs_est:
            try:
                error_val = float(data.get('Error (%)', '0'))
                error_values.append(abs(error_val))
            except:
                pass
        
        if error_values:
            avg_error = sum(error_values) / len(error_values)
            max_error = max(error_values)
            print(f"\n📈 CLEANING PERFORMANCE:")
            print(f"   Average measurement error: {avg_error:.2f}%")
            print(f"   Maximum measurement error: {max_error:.2f}%")
            
            if avg_error < 1.0:
                print("   🌟 EXCELLENT measurement cleaning!")
            elif avg_error < 3.0:
                print("   ⭐ GOOD measurement cleaning!")
            else:
                print("   📊 FAIR measurement cleaning")
        
    else:
        print("❌ No measurement vs estimate data found in results")
    
    # Check other data components
    print(f"\n🔍 AVAILABLE RESULT COMPONENTS:")
    for key in results.keys():
        if key in ['measurement_summary', 'comparison', 'measurement_vs_estimate']:
            data_count = len(results[key]) if isinstance(results[key], list) else 'N/A'
            print(f"   ✅ {key}: {data_count} items")
        else:
            print(f"   📋 {key}: Available")
    
    print(f"\n🎯 CONCLUSION:")
    print("The enhanced GUI will now show:")
    print("• Raw noisy measurements from sensors")
    print("• Clean estimated values from state estimation")
    print("• Side-by-side comparison with quality ratings")
    print("• Clear visualization of the 'cleaning' process")
    print("\nThis makes it easy to understand how state estimation works! 🚀")


if __name__ == "__main__":
    test_measurement_display()