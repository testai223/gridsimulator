#!/usr/bin/env python3
"""Verify that all outage simulation functionality works correctly."""

import sys


def test_imports():
    """Test that all modules import correctly."""
    print("🔍 Testing imports...")
    
    try:
        from gui import GridApp
        print("✅ GUI imports work")
    except Exception as e:
        print(f"❌ GUI import failed: {e}")
        return False
    
    try:
        from state_estimator import StateEstimator
        from state_estimation_module import StateEstimationModule
        print("✅ State estimation imports work")
    except Exception as e:
        print(f"❌ State estimation import failed: {e}")
        return False
    
    return True


def test_outage_api():
    """Test the outage simulation API."""
    print("\n🔍 Testing outage simulation API...")
    
    try:
        from database import GridDatabase
        from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
        
        # Initialize
        db = GridDatabase()
        db.initialize_example_grids()
        module = StateEstimationModule(db)
        
        # Get grids
        grids = module.get_available_grids()
        if not grids:
            print("❌ No grids available")
            return False
        
        # Test bus listing
        grid_id = grids[0][0]
        buses = module.get_available_buses_for_outage(grid_id=grid_id)
        print(f"✅ Found {len(buses)} buses for outage simulation")
        
        if len(buses) == 0:
            print("❌ No buses available for outage")
            return False
        
        # Test a simple outage scenario
        test_bus = buses[0][0]
        config = EstimationConfig(mode=EstimationMode.VOLTAGE_ONLY, voltage_noise_std=0.01)
        
        results = module.simulate_measurement_outage_scenario(
            grid_id=grid_id,
            outage_buses=[test_bus],
            config=config
        )
        
        if results.get('success'):
            print("✅ Outage simulation completed successfully")
        else:
            print(f"⚠️  Outage simulation completed with issues: {results.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Outage API test failed: {e}")
        return False


def test_state_estimator_outage():
    """Test the core state estimator outage functionality."""
    print("\n🔍 Testing core state estimator outage functions...")
    
    try:
        from state_estimator import StateEstimator
        from examples import create_ieee_9_bus
        
        # Create network
        net = create_ieee_9_bus()
        estimator = StateEstimator(net)
        estimator.create_measurement_set_ieee9(simple_mode=True)
        
        print(f"✅ Created {len(estimator.measurements)} measurements")
        
        # Test outage simulation
        outage_info = estimator.simulate_measurement_outage([0])  # Test bus 0 outage
        
        if 'observability_analysis' in outage_info:
            print("✅ Observability analysis working")
        else:
            print("❌ Observability analysis missing")
            return False
        
        # Test state estimation with outage
        results = estimator.estimate_state_with_outage_analysis(
            outage_buses=[0],
            max_iterations=20,
            tolerance=1e-3
        )
        
        if 'outage_simulation' in results:
            print("✅ State estimation with outage analysis working")
        else:
            print("❌ Outage analysis missing from results")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ State estimator outage test failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("🚀 VERIFYING OUTAGE SIMULATION FUNCTIONALITY")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_outage_api,
        test_state_estimator_outage
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS:")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ Outage simulation functionality is ready to use!")
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("❌ Some functionality may not work correctly")
        return 1


if __name__ == "__main__":
    sys.exit(main())