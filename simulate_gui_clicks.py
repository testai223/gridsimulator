#!/usr/bin/env python3
"""Simulate exactly what happens when you click GUI buttons for outage simulation."""

def simulate_user_clicks():
    """Simulate the exact sequence of what happens when user clicks GUI buttons."""
    print("🖱️ SIMULATING USER CLICKS IN GUI")
    print("=" * 60)
    
    # Step 1: User selects State Estimation tab (already done)
    print("👆 User clicks: State Estimation tab")
    print("   → Tab becomes active")
    
    # Step 2: User selects grid
    print("\n👆 User selects: IEEE 9-Bus Test System from dropdown")
    selected_grid = "2: IEEE 9-Bus Test System"  # This is what GUI stores
    print(f"   → Grid selected: {selected_grid}")
    
    # Step 3: User clicks Simulate Outage button
    print("\n👆 User clicks: 'Simulate Outage' button")
    print("   → GUI calls: _simulate_measurement_outage()")
    
    # This is what _simulate_measurement_outage() does:
    try:
        from state_estimation_module import StateEstimationModule
        from database import GridDatabase
        
        # Initialize (what GUI has already done)
        db = GridDatabase()
        db.initialize_example_grids()
        module = StateEstimationModule(db)
        
        # Parse selected grid (what GUI does)
        grid_id = int(selected_grid.split(":")[0])  # Extract grid ID
        grid_name = selected_grid.split(":", 1)[1].strip()
        
        # Get available buses (what GUI does for dialog)
        available_buses = module.get_available_buses_for_outage(grid_id=grid_id)
        print(f"   → Found {len(available_buses)} buses for outage selection")
        
        # Step 4: Outage dialog opens
        print("\n📋 Outage Selection Dialog opens:")
        print("   → Shows buses 0-8 with checkboxes")
        print("   → User can select one or more buses")
        
        # Step 5: User selects bus and clicks Run Simulation
        print("\n👆 User checks: Bus 0 checkbox")
        print("👆 User clicks: 'Run Simulation' button")
        selected_buses = [0]  # User's selection
        
        # This triggers _run_outage_simulation()
        print(f"   → GUI calls: _run_outage_simulation({selected_buses}, {grid_id})")
        
        # Step 6: GUI runs the actual simulation
        print("\n🔄 GUI executes outage simulation...")
        
        from state_estimation_module import EstimationConfig, EstimationMode
        
        # Create config (what GUI does)
        config = EstimationConfig(
            mode=EstimationMode.VOLTAGE_ONLY,
            voltage_noise_std=0.025,  # 2.5% from GUI default
            max_iterations=50,
            tolerance=1e-4
        )
        
        # Run simulation (what GUI does)
        results = module.simulate_measurement_outage_scenario(
            grid_id=grid_id,
            outage_buses=selected_buses,
            config=config
        )
        
        print(f"   → Simulation completed: {results.get('success', False)}")
        
        # Step 7: GUI displays results
        print("\n📊 GUI displays results in main text area:")
        print("   → GUI calls: _display_outage_results(results)")
        
        # This is exactly what _display_outage_results does:
        if results.get('success', False):
            # Format results (what GUI does)
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
            
            scenario_summary = results.get('scenario_summary', 'No summary available')
            
            gui_display = f"""Measurement Outage Simulation Results
{'='*50}
Grid: {results.get('grid_name', 'Unknown')}
Outaged Buses: {bus_list}
Impact Status: {impact_status}
Quick Assessment: {quick_impact}
Time: {results.get('timestamp', 'Unknown')}

SCENARIO ANALYSIS:
{'-'*30}
{scenario_summary}

📋 DETAILED ANALYSIS:
Click 'View Results' for comprehensive outage impact analysis
including baseline vs outage comparison, observability analysis,
and operational recommendations.

💡 EDUCATIONAL NOTE:
This simulation demonstrates how measurement failures in real
power grids can affect system observability and state estimation
reliability. Understanding these impacts is crucial for grid
operators and protection engineers.
"""
            
            print("   → Results text cleared")
            print("   → New results inserted:")
            print("   " + "="*50)
            print("   " + gui_display.replace('\n', '\n   '))
            print("   " + "="*50)
            
            # Step 8: Status update
            print(f"\n📱 Status label updated:")
            impact = results.get('comparison_analysis', {}).get('quality_impact', 'Unknown')
            print(f"   → 'Outage simulation completed - Impact: {impact}'")
            
            # Step 9: Results stored for View Results button
            print(f"\n💾 Results stored for 'View Results' button:")
            current_results = module.get_current_results()
            if 'outage_buses' in current_results:
                print("   ✅ Outage results properly stored")
                print("   → 'View Results' button will show detailed analysis")
            else:
                print("   ❌ Results not stored correctly")
            
        else:
            error_msg = results.get('error', 'Unknown error')
            print(f"   → Error displayed: {error_msg}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in simulation: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_results_visibility():
    """Check what makes results visible or invisible."""
    print(f"\n🔍 CHECKING RESULTS VISIBILITY")
    print("=" * 60)
    
    print("Results should appear in:")
    print("✅ Main State Estimation tab")
    print("✅ Large text area at bottom (with scrollbar)")
    print("✅ Below the button row")
    print("✅ Replaces any previous results")
    
    print(f"\nCommon reasons for not seeing results:")
    print("❌ Wrong tab selected (not State Estimation)")
    print("❌ Need to scroll in results area")
    print("❌ Results area too small (resize window)")
    print("❌ Error occurred but not noticed")
    print("❌ Simulation didn't actually run")
    
    print(f"\nTo verify results are working:")
    print("1. Watch status message below buttons")
    print("2. Check if text area content changes")
    print("3. Look for 'Outage simulation completed' status")
    print("4. Try scrolling in results area")
    print("5. Click 'View Results' for popup window")


if __name__ == "__main__":
    print("🚀 SIMULATING COMPLETE GUI WORKFLOW FOR OUTAGE\n")
    
    success = simulate_user_clicks()
    check_results_visibility()
    
    if success:
        print(f"\n🎉 SIMULATION SUCCESSFUL!")
        print("✅ This is exactly what should happen in the GUI")
        print("✅ Results should be clearly visible")
        
        print(f"\n🔧 IF YOU DON'T SEE RESULTS AFTER FOLLOWING THESE STEPS:")
        print("1. Check you're in State Estimation tab")
        print("2. Look in the large text area at the bottom")
        print("3. Watch the status message below buttons")
        print("4. Try resizing the window to see more of results area")
        print("5. Use 'View Results' button for popup window")
    else:
        print(f"\n❌ SIMULATION FAILED - CHECK ERRORS ABOVE")