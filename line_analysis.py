#!/usr/bin/env python3
"""
Detailed line parameter analysis for IEEE 39-bus system.
"""

from examples import create_ieee_39_bus
import pandapower as pp
import pandas as pd

def analyze_line_parameters():
    """Analyze line parameters for potential issues."""
    print("=" * 60)
    print("IEEE 39-BUS SYSTEM LINE PARAMETER ANALYSIS")
    print("=" * 60)
    
    net = create_ieee_39_bus()
    
    print("\nLINE IMPEDANCE ANALYSIS:")
    print("-" * 50)
    print(f"{'Line':<12} {'R (ohm/km)':<12} {'X (ohm/km)':<12} {'X/R':<8} {'Issue':<20}")
    print("-" * 75)
    
    issues_found = []
    
    for idx, row in net.line.iterrows():
        name = row['name']
        r_ohm = row['r_ohm_per_km']
        x_ohm = row['x_ohm_per_km']
        
        # Calculate X/R ratio
        if r_ohm != 0:
            xr_ratio = x_ohm / r_ohm
        else:
            xr_ratio = float('inf')
        
        # Check for issues
        issue = ""
        if r_ohm <= 0:
            issue = "Zero/Negative R"
            issues_found.append(f"{name}: {issue}")
        elif x_ohm <= 0:
            issue = "Zero/Negative X"
            issues_found.append(f"{name}: {issue}")
        elif xr_ratio > 50:
            issue = "Very high X/R"
            issues_found.append(f"{name}: X/R = {xr_ratio:.1f}")
        elif xr_ratio < 1:
            issue = "Low X/R ratio"
        
        print(f"{name:<12} {r_ohm:<12.4f} {x_ohm:<12.4f} {xr_ratio:<8.1f} {issue:<20}")
    
    print(f"\nISSUES SUMMARY:")
    print("-" * 20)
    if issues_found:
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("  No critical line parameter issues found.")
    
    # Check transformer parameters
    print(f"\nTRANSFORMER ANALYSIS:")
    print("-" * 30)
    print(f"{'Name':<8} {'HV Bus':<8} {'LV Bus':<8} {'Sn (MVA)':<10} {'Vk %':<8}")
    print("-" * 50)
    
    for idx, row in net.trafo.iterrows():
        name = row['name']
        hv_bus = row['hv_bus'] + 1
        lv_bus = row['lv_bus'] + 1
        sn_mva = row['sn_mva']
        vk_percent = row['vk_percent']
        
        print(f"{name:<8} {hv_bus:<8} {lv_bus:<8} {sn_mva:<10} {vk_percent:<8}")

if __name__ == "__main__":
    analyze_line_parameters()