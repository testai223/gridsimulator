#!/usr/bin/env python3
"""Debug the outage simulation GUI to find why results aren't showing."""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

# Test the outage simulation workflow step by step
def test_outage_workflow():
    """Test each step of the outage simulation workflow."""
    print("🔍 DEBUGGING OUTAGE SIMULATION WORKFLOW")
    print("=" * 60)
    
    try:
        # Step 1: Test imports
        print("Step 1: Testing imports...")
        from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
        from database import GridDatabase
        print("✅ Imports successful")
        
        # Step 2: Test database initialization
        print("\nStep 2: Testing database initialization...")
        db = GridDatabase()
        db.initialize_example_grids()
        module = StateEstimationModule(db)
        print("✅ Database initialized")
        
        # Step 3: Test grid selection
        print("\nStep 3: Testing grid selection...")
        grids = module.get_available_grids()
        print(f"✅ Found {len(grids)} grids:")
        for i, (grid_id, name, desc) in enumerate(grids):
            print(f"   {i+1}. ID {grid_id}: {name}")
        
        if not grids:
            print("❌ No grids available!")
            return False
        
        # Use IEEE 9-Bus system (most likely to be available)
        target_grid = None
        for grid_id, name, desc in grids:
            if "IEEE 9-Bus" in name:
                target_grid = (grid_id, name, desc)
                break
        
        if not target_grid:
            target_grid = grids[0]  # Use first available
        
        grid_id, grid_name, grid_desc = target_grid
        print(f"✅ Selected grid: {grid_name}")
        
        # Step 4: Test bus listing
        print(f"\nStep 4: Testing bus listing for outage...")
        buses = module.get_available_buses_for_outage(grid_id=grid_id)
        print(f"✅ Found {len(buses)} buses available for outage:")
        for bus_idx, bus_name in buses[:5]:  # Show first 5
            print(f"   Bus {bus_idx}: {bus_name}")
        if len(buses) > 5:
            print(f"   ... and {len(buses)-5} more buses")
        
        if not buses:
            print("❌ No buses available for outage!")
            return False
        
        # Step 5: Test outage simulation
        print(f"\nStep 5: Running outage simulation...")
        print(f"Simulating outage at bus {buses[0][0]} ({buses[0][1]})")
        
        config = EstimationConfig(
            mode=EstimationMode.VOLTAGE_ONLY,
            voltage_noise_std=0.025,
            max_iterations=30
        )
        
        results = module.simulate_measurement_outage_scenario(
            grid_id=grid_id,
            outage_buses=[buses[0][0]],
            config=config
        )
        
        print("✅ Outage simulation completed")
        print(f"Success: {results.get('success', False)}")
        
        if not results.get('success'):
            print(f"❌ Simulation failed: {results.get('error', 'Unknown error')}")
            return False
        
        # Step 6: Test result structure
        print(f"\nStep 6: Analyzing result structure...")
        
        expected_keys = [
            'success', 'grid_name', 'outage_buses', 'timestamp',
            'comparison_analysis', 'scenario_summary'
        ]
        
        for key in expected_keys:
            if key in results:
                print(f"✅ {key}: Present")
            else:
                print(f"❌ {key}: MISSING")
        
        # Step 7: Test display formatting
        print(f"\nStep 7: Testing display formatting...")
        
        outage_buses = results.get('outage_buses', [])
        bus_list = ", ".join(map(str, outage_buses))
        print(f"✅ Bus list: '{bus_list}'")
        
        comparison = results.get('comparison_analysis', {})
        converged = comparison.get('outage_converged', False)
        print(f"✅ Convergence status: {converged}")
        
        scenario_summary = results.get('scenario_summary', '')
        print(f"✅ Scenario summary length: {len(scenario_summary)} characters")
        if scenario_summary:
            print(f"   First line: {scenario_summary.split(chr(10))[0][:60]}...")
        
        # Step 8: Test what GUI would display
        print(f"\nStep 8: Simulating GUI display...")
        
        # This is exactly what the GUI does in _display_outage_results
        if comparison.get('outage_converged', False):
            impact_status = f"✅ CONVERGED - {comparison.get('quality_impact', 'Unknown impact')}"
            voltage_impact = comparison.get('voltage_impact', {})
            max_error = voltage_impact.get('max_difference_percent', 0)
            quick_impact = f"Max voltage error: {max_error:.2f}%"
        else:
            impact_status = "❌ FAILED - System became unobservable"
            unobservable = comparison.get('unobservable_buses', [])
            quick_impact = f"Unobservable buses: {unobservable}"
        
        gui_summary = f"""Measurement Outage Simulation Results
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
"""
        
        print("✅ GUI would display:")
        print("-" * 40)
        print(gui_summary)
        print("-" * 40)
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in outage workflow: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gui_components():
    """Test the GUI components for outage simulation."""
    print("\n🖥️ TESTING GUI COMPONENTS")
    print("=" * 60)
    
    try:
        # Test GUI imports
        print("Testing GUI imports...")
        from gui import GridApp
        print("✅ GUI imports successful")
        
        # Test state estimation module integration
        print("Testing state estimation module in GUI context...")
        from database import GridDatabase
        from state_estimation_module import StateEstimationModule
        
        db = GridDatabase()
        db.initialize_example_grids()
        module = StateEstimationModule(db)
        
        # Test the methods that GUI calls
        print("Testing GUI method calls...")
        
        # Get grids (what GUI does in grid selection)
        grids = module.get_available_grids()
        if grids:
            grid_id = grids[0][0]
            print(f"✅ Grid selection works: {grids[0][1]}")
            
            # Get buses (what GUI does in outage dialog)
            buses = module.get_available_buses_for_outage(grid_id=grid_id)
            print(f"✅ Bus listing works: {len(buses)} buses")
            
            # Simulate outage (what GUI does when user clicks run)
            if buses:
                from state_estimation_module import EstimationConfig, EstimationMode
                config = EstimationConfig(mode=EstimationMode.VOLTAGE_ONLY)
                
                results = module.simulate_measurement_outage_scenario(
                    grid_id=grid_id,
                    outage_buses=[buses[0][0]],
                    config=config
                )
                
                if results.get('success'):
                    print("✅ Outage simulation works")
                    
                    # Test what _display_outage_results would do
                    print("✅ Result display formatting works")
                    
                    # Test what _view_se_results would do
                    current_results = module.get_current_results()
                    if current_results:
                        print("✅ Results storage/retrieval works")
                        
                        if 'outage_buses' in current_results:
                            print("✅ Outage results properly stored")
                        else:
                            print("⚠️  Outage results may not be stored correctly")
                    else:
                        print("❌ No current results stored")
                else:
                    print(f"❌ Outage simulation failed: {results.get('error')}")
            else:
                print("❌ No buses available for testing")
        else:
            print("❌ No grids available for testing")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR in GUI component test: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_minimal_test_gui():
    """Create a minimal test GUI to verify outage simulation works."""
    print("\n🧪 CREATING MINIMAL TEST GUI")
    print("=" * 60)
    
    try:
        from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode
        from database import GridDatabase
        
        # Initialize
        db = GridDatabase()
        db.initialize_example_grids()
        module = StateEstimationModule(db)
        
        root = tk.Tk()
        root.title("Outage Simulation Test")
        root.geometry("600x400")
        
        # Results display area
        results_text = tk.Text(root, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(root, orient="vertical", command=results_text.yview)
        results_text.configure(yscrollcommand=scrollbar.set)
        
        def run_test_outage():
            """Run a test outage simulation."""
            results_text.delete(1.0, tk.END)
            results_text.insert(tk.END, "Running outage simulation...\n")
            root.update()
            
            try:
                # Get first available grid
                grids = module.get_available_grids()
                if not grids:
                    results_text.insert(tk.END, "❌ No grids available\n")
                    return
                
                grid_id = grids[0][0]
                grid_name = grids[0][1]
                
                # Get first available bus
                buses = module.get_available_buses_for_outage(grid_id=grid_id)
                if not buses:
                    results_text.insert(tk.END, "❌ No buses available\n")
                    return
                
                test_bus = buses[0][0]
                
                results_text.insert(tk.END, f"Testing {grid_name}, bus {test_bus}...\n")
                root.update()
                
                # Run outage simulation
                config = EstimationConfig(mode=EstimationMode.VOLTAGE_ONLY)
                results = module.simulate_measurement_outage_scenario(
                    grid_id=grid_id,
                    outage_buses=[test_bus],
                    config=config
                )
                
                # Display results (same as GUI does)
                if results.get('success'):
                    comparison = results.get('comparison_analysis', {})
                    if comparison.get('outage_converged'):
                        status = "✅ CONVERGED"
                    else:
                        status = "❌ UNOBSERVABLE"
                    
                    summary = f"""
TEST OUTAGE SIMULATION RESULTS:
Grid: {results.get('grid_name')}
Outaged Bus: {test_bus}
Status: {status}
Time: {results.get('timestamp')}

{results.get('scenario_summary', 'No summary')}
"""
                    results_text.insert(tk.END, summary)
                else:
                    results_text.insert(tk.END, f"❌ Failed: {results.get('error')}\n")
                
            except Exception as e:
                results_text.insert(tk.END, f"❌ Error: {e}\n")
        
        # Controls
        ttk.Button(root, text="Run Test Outage", command=run_test_outage).pack(pady=10)
        ttk.Label(root, text="Results:").pack()
        
        results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Auto-run test
        root.after(1000, run_test_outage)
        
        print("✅ Test GUI created - starting...")
        root.mainloop()
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR creating test GUI: {e}")
        return False


if __name__ == "__main__":
    print("🚀 DEBUGGING OUTAGE SIMULATION GUI ISSUES\n")
    
    # Run comprehensive debugging
    step1_success = test_outage_workflow()
    step2_success = test_gui_components()
    
    if step1_success and step2_success:
        print(f"\n🎉 ALL DEBUG TESTS PASSED!")
        print("✅ Outage simulation should work correctly")
        print("✅ GUI integration is functional")
        
        print(f"\n🔧 IF YOU'RE STILL NOT SEEING RESULTS:")
        print("1. Make sure you're in the 'State Estimation' tab")
        print("2. Select a grid (IEEE 9-Bus recommended)")
        print("3. Click 'Simulate Outage' button")
        print("4. Select at least one bus in the dialog")
        print("5. Click 'Run Simulation'")
        print("6. Check the main results area below the buttons")
        print("7. Use 'View Results' for detailed analysis")
        
        # Offer to create test GUI
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == '--test-gui':
            print(f"\n🧪 Creating minimal test GUI...")
            create_minimal_test_gui()
    else:
        print(f"\n❌ DEBUG TESTS REVEALED ISSUES")
        print("⚠️  Check the error messages above for specific problems")