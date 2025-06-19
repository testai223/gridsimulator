#!/usr/bin/env python3
"""Simple analysis of measured vs estimated values."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import GridDatabase
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode

def main():
    print("🔬 MEASURED vs ESTIMATED VALUES ANALYSIS")
    print("=" * 50)
    
    # Initialize
    db = GridDatabase()
    db.initialize_example_grids()
    module = StateEstimationModule(db)
    
    # Run state estimation with visible noise
    config = EstimationConfig(
        mode=EstimationMode.VOLTAGE_ONLY,
        voltage_noise_std=0.03,  # 3% noise
        max_iterations=50,
        tolerance=1e-4
    )
    
    print("\n🧪 Testing Simple Example Grid with 3% noise...")
    results = module.estimate_grid_state(grid_id=5, config=config)
    
    if results.get('success') and results.get('converged'):
        print(f"✅ Converged in {results.get('iterations', 0)} iterations")
        print(f"📊 Total measurements: {results.get('measurements_count', 0)}")
        
        # Get voltage data
        true_voltages = results.get('true_voltage_magnitudes', [])
        estimated_voltages = results.get('voltage_magnitudes', [])
        
        print(f"\n📋 Voltage Comparison:")
        print("-" * 50)
        print(f"{'Bus':<5} {'True':<10} {'Estimated':<12} {'Error %':<10}")
        print("-" * 50)
        
        for i, (true_v, est_v) in enumerate(zip(true_voltages, estimated_voltages)):
            error = ((est_v - true_v) / true_v) * 100
            print(f"{i:<5} {true_v:<10.4f} {est_v:<12.4f} {error:<10.2f}")
        
        print("\n💡 Key Points:")
        print("- True values: From power flow solution")
        print("- Estimated values: From state estimator using noisy measurements")  
        print("- State estimator 'cleans' noisy measurements")
        print("- Small errors show the filtering effect working")
        
    else:
        print(f"❌ Failed: {results.get('error', 'Unknown')}")

if __name__ == "__main__":
    main()