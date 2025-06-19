#!/usr/bin/env python3
"""Demonstrate how to access measured vs estimated values in state estimation results."""

def show_measurement_comparison_access():
    """Show how to access measured vs estimated values from state estimation results."""
    
    print("🔍 HOW TO ACCESS MEASURED vs ESTIMATED VALUES")
    print("=" * 60)
    
    print("""
📋 STEP 1: Run State Estimation
==============================
from database import GridDatabase
from state_estimation_module import StateEstimationModule, EstimationConfig, EstimationMode

db = GridDatabase()
module = StateEstimationModule(db)

config = EstimationConfig(
    mode=EstimationMode.VOLTAGE_ONLY,
    voltage_noise_std=0.03,  # 3% noise to see differences
    max_iterations=50,
    tolerance=1e-4
)

results = module.estimate_grid_state(grid_id=5, config=config)
""")

    print("""
📊 STEP 2: Extract Key Values
=============================
if results.get('success') and results.get('converged'):
    # Basic voltage comparison
    true_voltages = results.get('true_voltage_magnitudes', [])
    estimated_voltages = results.get('voltage_magnitudes', [])
    
    # Detailed measurement comparison (if available)
    measurement_comparison = results.get('measurement_vs_estimate', [])
    detailed_comparison = results.get('comparison', [])
""")

    print("""
🔍 STEP 3: Analyze the Data
===========================
# Bus-by-bus voltage comparison
for i, (true_v, est_v) in enumerate(zip(true_voltages, estimated_voltages)):
    error_pct = ((est_v - true_v) / true_v) * 100
    print(f"Bus {i}: True={true_v:.4f}, Est={est_v:.4f}, Error={error_pct:+.2f}%")

# Detailed measurement analysis
for meas in detailed_comparison:
    if meas.get('Type') == 'Voltage':
        print(f"Measurement: {meas.get('Description')}")
        print(f"  True: {meas.get('True Value')}")
        print(f"  Measured: {meas.get('Measured Value')}")  
        print(f"  Estimated: {meas.get('Estimated Value')}")
        print(f"  Error: {meas.get('Error (%)')}")
""")

    print("""
🎯 WHAT EACH VALUE MEANS:
========================
• True Value:      Ground truth from power flow solution
• Measured Value:  True value + random measurement noise  
• Estimated Value: State estimator's best estimate using all measurements
• Error:           Difference between estimated and true values

🔑 KEY INSIGHT:
===============
The estimated values should be CLOSER to the true values than the individual 
measured values. This demonstrates the noise filtering capability of the 
state estimator.
""")

    print("""
📈 EXAMPLE RESULTS:
==================
Bus 0: True=1.0000, Est=1.0023, Error=+0.23%  ← Very close to true
Bus 1: True=0.9997, Est=0.9989, Error=-0.08%  ← Even closer

Individual measurements might show:
• Measured voltage at Bus 0: 1.0250 (Error: +2.50%)
• Measured voltage at Bus 1: 0.9845 (Error: -1.52%)

The state estimator reduces these errors by 85-95%!
""")

    print("""
🖥️  IN THE GUI:
===============
1. Go to State Estimation tab
2. Select a grid (IEEE 9-Bus recommended)
3. Set noise level to 2.5% or higher
4. Click "Run State Estimation"
5. Click "View Results" for detailed analysis
6. Look for "Measurement vs Estimate" comparison tables

The GUI shows this data in user-friendly tables with:
• Measurement descriptions
• Measured values with noise
• Estimated values from state estimator
• Error percentages and noise characteristics
""")

if __name__ == "__main__":
    show_measurement_comparison_access()