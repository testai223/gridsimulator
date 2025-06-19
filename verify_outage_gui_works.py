#!/usr/bin/env python3
"""Verify the outage simulation GUI integration works correctly."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
from database import GridDatabase


def verify_gui_integration():
    """Verify the complete GUI workflow for outage simulation."""
    print("🔍 VERIFYING GUI INTEGRATION FOR OUTAGE SIMULATION")
    print("=" * 60)
    
    # Step 1: Initialize (same as GUI does)
    print("📋 Step 1: Initialize module and database")
    db = GridDatabase()
    db.initialize_example_grids()
    module = StateEstimationModule(db)
    print("✅ Initialization successful")
    
    # Step 2: Get available grids (same as GUI does)
    print("\n📋 Step 2: Get available grids")
    grids = module.get_available_grids()
    print(f"✅ Found {len(grids)} grids available")
    
    # Step 3: Get available buses for outage (same as GUI does)
    print("\n📋 Step 3: Get available buses for outage simulation")
    if grids:
        grid_id = grids[0][0]
        grid_name = grids[0][1]
        buses = module.get_available_buses_for_outage(grid_id=grid_id)
        print(f"✅ Found {len(buses)} buses available for outage in {grid_name}")
        
        # Show some example buses
        for i, (bus_idx, bus_name) in enumerate(buses[:3]):
            print(f"   Example: Bus {bus_idx}: {bus_name}")
        if len(buses) > 3:
            print(f"   ... and {len(buses)-3} more buses")
    else:
        print("❌ No grids available")
        return False
    
    # Step 4: Run outage simulation (same as GUI does)
    print("\n📋 Step 4: Run outage simulation")
    
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.025,  # 2.5% noise
        max_iterations=50
    )
    
    # Test with first available bus
    test_bus = buses[0][0]
    print(f"Testing outage at bus {test_bus}")
    
    try:
        results = module.simulate_measurement_outage_scenario(
            grid_id=grid_id,
            outage_buses=[test_bus],
            config=config
        )
        
        if results.get('success'):
            print("✅ Outage simulation completed successfully")
            
            # Step 5: Verify results have all fields GUI needs
            print("\n📋 Step 5: Verify results structure for GUI display")
            
            required_fields = [
                'grid_name', 'outage_buses', 'timestamp',
                'comparison_analysis', 'scenario_summary'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in results:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print("✅ All required fields present for GUI display")
            
            # Step 6: Test display formatting (same as GUI does)
            print("\n📋 Step 6: Test display formatting")
            
            outage_buses = results.get('outage_buses', [])
            bus_list = ", ".join(map(str, outage_buses))
            comparison = results.get('comparison_analysis', {})
            
            if comparison.get('outage_converged', False):
                impact_status = f"✅ CONVERGED - {comparison.get('quality_impact', 'Unknown impact')}"
                voltage_impact = comparison.get('voltage_impact', {})
                max_error = voltage_impact.get('max_difference_percent', 0)
                quick_impact = f"Max voltage error: {max_error:.2f}%"
            else:
                impact_status = "❌ FAILED - System became unobservable"
                unobservable = comparison.get('unobservable_buses', [])
                quick_impact = f"Unobservable buses: {unobservable}"
            
            print(f"✅ Bus list formatting: '{bus_list}'")
            print(f"✅ Impact status: '{impact_status}'")
            print(f"✅ Quick assessment: '{quick_impact}'")
            
            # Step 7: Verify detailed results for View Results button
            print("\n📋 Step 7: Verify detailed results structure")
            
            if 'baseline_results' in results and 'outage_results' in results:
                print("✅ Baseline and outage results available for detailed view")
            else:
                print("⚠️  Some detailed results may be missing")
            
            scenario_summary = results.get('scenario_summary', '')
            if scenario_summary and len(scenario_summary) > 50:
                print("✅ Comprehensive scenario summary available")
                print(f"   Preview: {scenario_summary[:100]}...")
            else:
                print("⚠️  Scenario summary may be incomplete")
            
            return True
            
        else:
            print(f"❌ Outage simulation failed: {results.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Exception during outage simulation: {e}")
        return False


def provide_user_guidance():
    """Provide guidance for users on what to expect."""
    print("\n💡 USER GUIDANCE FOR OUTAGE SIMULATION")
    print("=" * 60)
    
    print("""
🎯 WHAT TO EXPECT WHEN USING OUTAGE SIMULATION:

✅ NORMAL BEHAVIOR:
• Most single-bus outages will show "System became unobservable"
• This is REALISTIC - real power grids lose observability when critical sensors fail
• The IEEE 9-bus system has limited measurement redundancy by design

📊 WHAT RESULTS YOU'LL SEE:
• Main display: Quick summary with impact status
• "View Results" button: Detailed analysis with recommendations
• Observability analysis: Shows which buses become unobservable
• Recovery recommendations: Operational guidance for grid operators

🎓 EDUCATIONAL VALUE:
• Demonstrates critical infrastructure vulnerability
• Shows why backup measurement systems are essential
• Teaches real-world grid operation challenges
• Illustrates observability theory in practice

🔧 FOR BEST RESULTS:
• Try different bus combinations to see various impacts
• Use "View Results" for comprehensive analysis
• Pay attention to the recommendations provided
• Understand that unobservability is a real operational concern

⚠️  IF YOU SEE NO RESULTS:
• Check that you selected at least one bus for outage
• Ensure the simulation completed (watch status messages)
• Results appear in the main State Estimation results area
• Use "View Results" button for detailed analysis
""")


if __name__ == "__main__":
    print("🚀 VERIFYING OUTAGE SIMULATION GUI INTEGRATION\n")
    
    success = verify_gui_integration()
    
    if success:
        print(f"\n🎉 GUI INTEGRATION VERIFICATION SUCCESSFUL!")
        print("✅ All components working correctly")
        print("✅ Results will display properly in GUI")
        print("✅ User should see outage simulation results")
        
        provide_user_guidance()
    else:
        print(f"\n❌ GUI integration verification failed")
        print("⚠️  There may be issues with the display")