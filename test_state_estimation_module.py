#!/usr/bin/env python3
"""Test script for the state estimation module."""

from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode, create_default_config
from database import GridDatabase
import pandapower as pp

def test_module_functionality():
    """Test the state estimation module functionality."""
    print("Testing State Estimation Module")
    print("=" * 50)
    
    # Initialize database and module
    db = GridDatabase()
    db.initialize_example_grids()
    
    module = StateEstimationModule(db)
    
    # Get available grids
    grids = module.get_available_grids()
    print(f"Available grids: {len(grids)}")
    for grid in grids:
        print(f"  {grid[0]}: {grid[1]} - {grid[2]}")
    
    if grids:
        # Test with first grid
        grid_id = grids[0][0]
        grid_name = grids[0][1]
        
        print(f"\nTesting state estimation on grid: {grid_name}")
        
        # Create configuration
        config = create_default_config(EstimationMode.VOLTAGE_ONLY)
        
        # Run state estimation
        results = module.estimate_grid_state(grid_id, config)
        
        print(f"Success: {results.get('success', False)}")
        if results.get('success'):
            convergence = results.get('convergence', {})
            print(f"Converged: {convergence.get('converged', False)}")
            print(f"Iterations: {convergence.get('iterations', 'N/A')}")
            print(f"Measurements: {convergence.get('measurements_count', 'N/A')}")
            
            accuracy = results.get('accuracy_metrics', {})
            if accuracy:
                print(f"Max voltage error: {accuracy.get('max_voltage_error_percent', 'N/A'):.2f}%")
        else:
            print(f"Error: {results.get('error', 'Unknown')}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_module_functionality()