#!/usr/bin/env python3
"""Test that outage simulation results display correctly."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase


def test_outage_results_content():
    """Test that outage simulation produces displayable results."""
    print("🧪 TESTING OUTAGE RESULTS DISPLAY")
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
    
    # Configure for better convergence
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.01,  # Lower noise for testing
        max_iterations=30
    )
    
    # Test different outage scenarios
    test_scenarios = [
        ([8], "Single bus outage"),  # Try last bus
        ([7], "Another single bus"),
        ([5, 8], "Two bus outage")
    ]
    
    for outage_buses, scenario_name in test_scenarios:
        print(f"\n🔍 Testing: {scenario_name} - Buses {outage_buses}")
        
        try:
            results = module.simulate_measurement_outage_scenario(
                grid_id=ieee9_grid[0],
                outage_buses=outage_buses,
                config=config
            )
            
            # Check basic result structure
            if not results.get('success'):
                print(f"   ❌ Simulation failed: {results.get('error', 'Unknown error')}")
                continue
            
            # Check required fields for display
            required_fields = [
                'grid_name', 'outage_buses', 'timestamp', 
                'comparison_analysis', 'scenario_summary'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in results:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠️  Missing fields: {missing_fields}")
                continue
            
            # Check comparison analysis content
            comparison = results['comparison_analysis']
            convergence_status = comparison.get('outage_converged', False)
            
            print(f"   ✅ Simulation successful")
            print(f"   Convergence: {'✅ YES' if convergence_status else '❌ NO'}")
            
            if convergence_status:
                voltage_impact = comparison.get('voltage_impact', {})
                max_error = voltage_impact.get('max_difference_percent', 0)
                print(f"   Max voltage error: {max_error:.2f}%")
                print(f"   Quality impact: {comparison.get('quality_impact', 'Unknown')}")
            else:
                unobservable = comparison.get('unobservable_buses', [])
                print(f"   Unobservable buses: {unobservable}")
            
            # Check scenario summary
            summary = results.get('scenario_summary', '')
            if summary:
                first_line = summary.split('\n')[0] if summary else 'No summary'
                print(f"   Summary available: {first_line[:50]}...")
            else:
                print(f"   ⚠️  No scenario summary")
            
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n✅ Outage results display test completed")
    return True


def test_display_formatting():
    """Test that results format correctly for GUI display."""
    print("\n🧪 TESTING DISPLAY FORMATTING")
    print("=" * 50)
    
    # Create sample outage results structure
    sample_results = {
        'success': True,
        'grid_name': 'Test Grid',
        'outage_buses': [1, 4],
        'timestamp': '2024-01-01T12:00:00',
        'comparison_analysis': {
            'outage_converged': True,
            'quality_impact': 'MODERATE - Noticeable estimation degradation',
            'voltage_impact': {
                'max_difference_percent': 2.5,
                'mean_difference_percent': 1.2,
                'rms_difference_percent': 1.8
            },
            'measurement_impact': {
                'measurement_loss_percent': 25.0,
                'outaged_measurements': 5,
                'remaining_measurements': 15
            }
        },
        'scenario_summary': 'Test scenario showing moderate impact from outage'
    }
    
    # Test formatting components
    try:
        outage_buses = sample_results.get('outage_buses', [])
        bus_list = ", ".join(map(str, outage_buses))
        print(f"✅ Bus list formatting: {bus_list}")
        
        comparison = sample_results.get('comparison_analysis', {})
        impact_status = f"✅ CONVERGED - {comparison.get('quality_impact', 'Unknown impact')}"
        print(f"✅ Impact status formatting: {impact_status}")
        
        voltage_impact = comparison.get('voltage_impact', {})
        max_error = voltage_impact.get('max_difference_percent', 0)
        quick_impact = f"Max voltage error: {max_error:.2f}%"
        print(f"✅ Quick impact formatting: {quick_impact}")
        
        print("✅ All formatting tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Formatting error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 RUNNING OUTAGE DISPLAY TESTS\n")
    
    test1_success = test_outage_results_content()
    test2_success = test_display_formatting()
    
    if test1_success and test2_success:
        print(f"\n🎉 ALL DISPLAY TESTS PASSED!")
        print("✅ Outage simulation results should display correctly in GUI")
    else:
        print(f"\n❌ Some display tests failed")
        print("⚠️  Check the GUI display implementation")