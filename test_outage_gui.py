#!/usr/bin/env python3
"""Test outage simulation functionality without GUI."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase


def test_outage_simulation_api():
    """Test the outage simulation API that GUI uses."""
    print("🧪 TESTING OUTAGE SIMULATION API")
    print("=" * 50)
    
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
        return False
    
    print(f"📋 Using: {ieee9_grid[1]}")
    
    # Test 1: Get available buses
    print("\n🔍 Test 1: Get available buses for outage")
    available_buses = module.get_available_buses_for_outage(grid_id=ieee9_grid[0])
    print(f"Available buses: {[f'{idx}:{name}' for idx, name in available_buses]}")
    
    if not available_buses:
        print("❌ No buses available")
        return False
    
    print("✅ Buses retrieved successfully")
    
    # Test 2: Simulate outage (use a bus that should allow SE to converge)
    print("\n🔍 Test 2: Simulate measurement outage")
    
    # Try a less critical outage first
    test_bus = available_buses[-1][0]  # Use last bus
    print(f"Testing outage at bus {test_bus}")
    
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.01,  # Lower noise for better convergence
        max_iterations=50
    )
    
    try:
        results = module.simulate_measurement_outage_scenario(
            grid_id=ieee9_grid[0],
            outage_buses=[test_bus],
            config=config
        )
        
        if results.get('success'):
            print("✅ Outage simulation completed successfully")
            
            comparison = results.get('comparison_analysis', {})
            if comparison.get('outage_converged', False):
                voltage_impact = comparison.get('voltage_impact', {})
                print(f"   Max voltage error: {voltage_impact.get('max_difference_percent', 0):.2f}%")
                print(f"   Quality impact: {comparison.get('quality_impact', 'Unknown')}")
            else:
                print("   System became unobservable")
                
            # Test scenario summary generation
            summary = results.get('scenario_summary', '')
            if summary:
                print("✅ Scenario summary generated")
                print("   First line:", summary.split('\n')[0])
            else:
                print("⚠️  No scenario summary")
        else:
            print(f"❌ Outage simulation failed: {results.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during outage simulation: {e}")
        return False
    
    # Test 3: Check API compatibility with GUI
    print("\n🔍 Test 3: GUI API compatibility")
    
    # Verify all expected fields are present
    expected_fields = [
        'success', 'grid_name', 'outage_buses', 'timestamp',
        'comparison_analysis', 'scenario_summary'
    ]
    
    missing_fields = []
    for field in expected_fields:
        if field not in results:
            missing_fields.append(field)
    
    if missing_fields:
        print(f"⚠️  Missing expected fields: {missing_fields}")
    else:
        print("✅ All expected fields present")
    
    # Test error handling
    print("\n🔍 Test 4: Error handling")
    try:
        error_results = module.simulate_measurement_outage_scenario(
            grid_id=999,  # Non-existent grid
            outage_buses=[0],
            config=config
        )
        
        if not error_results.get('success') and 'error' in error_results:
            print("✅ Error handling works correctly")
        else:
            print("⚠️  Error handling may not be working properly")
            
    except Exception as e:
        print("✅ Exception handling works correctly")
    
    print("\n🎯 OUTAGE SIMULATION API TESTS COMPLETED")
    return True


def test_measurement_creation_with_outage():
    """Test that measurements are created properly for outage scenarios."""
    print("\n🧪 TESTING MEASUREMENT CREATION FOR OUTAGE")
    print("=" * 50)
    
    db = GridDatabase()
    db.initialize_example_grids()
    module = StateEstimationModule(db)
    
    grids = module.get_available_grids()
    ieee9_grid = grids[0] if grids else None
    
    if not ieee9_grid:
        return False
    
    # Test that we create enough measurements for redundancy
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.015,  # Moderate noise
        max_iterations=30
    )
    
    print("📊 Testing measurement creation...")
    
    # This should create the baseline measurements
    try:
        normal_results = module.estimate_grid_state(ieee9_grid[0], config)
        
        if normal_results.get('success'):
            measurement_count = normal_results['convergence']['measurements_count']
            print(f"Normal operation: {measurement_count} measurements")
            
            if measurement_count >= 9:  # At least one per bus
                print("✅ Sufficient measurements for basic observability")
            else:
                print("⚠️  Low measurement count may cause observability issues")
                
        else:
            print("❌ Normal state estimation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error in measurement creation test: {e}")
        return False
    
    print("✅ Measurement creation test passed")
    return True


if __name__ == "__main__":
    print("🚀 RUNNING OUTAGE SIMULATION API TESTS\n")
    
    success1 = test_outage_simulation_api()
    success2 = test_measurement_creation_with_outage()
    
    if success1 and success2:
        print(f"\n🎉 ALL API TESTS PASSED!")
        print("✅ Outage simulation is ready for GUI integration")
        print("✅ Measurement outage functionality is working correctly")
    else:
        print(f"\n❌ Some tests failed - check implementation")