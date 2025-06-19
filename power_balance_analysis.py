#!/usr/bin/env python3
"""
Power balance analysis for IEEE 39-bus system to identify convergence issues.
"""

from examples import create_ieee_39_bus
import pandapower as pp

def analyze_power_balance():
    """Analyze power balance in the IEEE 39-bus system."""
    print("=" * 60)
    print("IEEE 39-BUS SYSTEM POWER BALANCE ANALYSIS")
    print("=" * 60)
    
    # Create the network
    net = create_ieee_39_bus()
    
    # 1. Calculate total generation
    print("\n1. GENERATOR ANALYSIS:")
    print("-" * 30)
    total_gen_p = 0
    total_gen_q = 0
    
    print(f"{'Bus':<5} {'Name':<15} {'P (MW)':<10} {'VM (pu)':<10} {'Slack':<8}")
    print("-" * 60)
    
    for idx, row in net.gen.iterrows():
        bus_num = row['bus'] + 1  # Convert to 1-based indexing
        name = row['name']
        p_mw = row['p_mw']
        vm_pu = row['vm_pu']
        is_slack = row['slack']
        total_gen_p += p_mw
        
        print(f"{bus_num:<5} {name:<15} {p_mw:<10.1f} {vm_pu:<10.3f} {'YES' if is_slack else 'NO':<8}")
    
    print("-" * 60)
    print(f"TOTAL GENERATION: {total_gen_p:.1f} MW")
    
    # 2. Calculate total load
    print("\n2. LOAD ANALYSIS:")
    print("-" * 30)
    total_load_p = 0
    total_load_q = 0
    
    print(f"{'Bus':<5} {'Name':<15} {'P (MW)':<10} {'Q (Mvar)':<12}")
    print("-" * 50)
    
    for idx, row in net.load.iterrows():
        bus_num = row['bus'] + 1  # Convert to 1-based indexing
        name = row['name']
        p_mw = row['p_mw']
        q_mvar = row['q_mvar']
        total_load_p += p_mw
        total_load_q += q_mvar
        
        print(f"{bus_num:<5} {name:<15} {p_mw:<10.1f} {q_mvar:<12.1f}")
    
    print("-" * 50)
    print(f"TOTAL LOAD: {total_load_p:.1f} MW, {total_load_q:.1f} Mvar")
    
    # 3. Power balance analysis
    print("\n3. POWER BALANCE ANALYSIS:")
    print("-" * 40)
    power_imbalance = total_gen_p - total_load_p
    print(f"Total Generation:     {total_gen_p:.1f} MW")
    print(f"Total Load:          {total_load_p:.1f} MW")
    print(f"Power Imbalance:     {power_imbalance:.1f} MW")
    print(f"Imbalance Ratio:     {(power_imbalance/total_load_p)*100:.2f}%")
    
    # 4. Check for unrealistic values
    print("\n4. UNREALISTIC VALUE CHECK:")
    print("-" * 35)
    
    # Check generators
    gen_issues = []
    for idx, row in net.gen.iterrows():
        bus_num = row['bus'] + 1
        p_mw = row['p_mw']
        vm_pu = row['vm_pu']
        
        if p_mw > 1200:  # Very high generation
            gen_issues.append(f"Gen {bus_num}: Very high power output ({p_mw} MW)")
        if vm_pu < 0.9 or vm_pu > 1.1:  # Voltage outside typical range
            gen_issues.append(f"Gen {bus_num}: Voltage setpoint outside normal range ({vm_pu} pu)")
    
    # Check loads
    load_issues = []
    for idx, row in net.load.iterrows():
        bus_num = row['bus'] + 1
        p_mw = row['p_mw']
        q_mvar = row['q_mvar']
        
        if p_mw > 800:  # Very high load
            load_issues.append(f"Load {bus_num}: Very high power consumption ({p_mw} MW)")
        if q_mvar < -100:  # Large capacitive load
            load_issues.append(f"Load {bus_num}: Large capacitive reactive power ({q_mvar} Mvar)")
    
    if gen_issues:
        print("Generator Issues Found:")
        for issue in gen_issues:
            print(f"  - {issue}")
    else:
        print("No obvious generator issues found.")
        
    if load_issues:
        print("Load Issues Found:")
        for issue in load_issues:
            print(f"  - {issue}")
    else:
        print("No obvious load issues found.")
    
    # 5. Slack generator analysis
    print("\n5. SLACK GENERATOR ANALYSIS:")
    print("-" * 40)
    slack_gen = net.gen[net.gen['slack'] == True]
    if len(slack_gen) == 1:
        slack_row = slack_gen.iloc[0]
        slack_bus = slack_row['bus'] + 1
        slack_p = slack_row['p_mw']
        slack_vm = slack_row['vm_pu']
        print(f"Slack Generator: Gen {slack_bus}")
        print(f"Initial P setting: {slack_p} MW")
        print(f"Voltage setpoint: {slack_vm} pu")
        
        # Calculate expected slack generation
        expected_slack = total_load_p - (total_gen_p - slack_p)
        print(f"Expected generation after load flow: ~{expected_slack:.1f} MW")
        
        if abs(expected_slack - slack_p) > 100:
            print("WARNING: Large difference between initial and expected slack generation!")
    else:
        print(f"ERROR: Found {len(slack_gen)} slack generators (should be exactly 1)")
    
    # 6. Network connectivity check
    print("\n6. NETWORK CONNECTIVITY:")
    print("-" * 30)
    print(f"Total buses: {len(net.bus)}")
    print(f"Total lines: {len(net.line)}")
    print(f"Total transformers: {len(net.trafo)}")
    print(f"Generators: {len(net.gen)}")
    print(f"Loads: {len(net.load)}")
    
    # Try to run power flow to see specific error
    print("\n7. POWER FLOW TEST:")
    print("-" * 25)
    try:
        pp.runpp(net, verbose=True, numba=False)
        print("Power flow converged successfully!")
        print(f"Slack generation: {net.res_gen.loc[net.gen[net.gen['slack']].index[0], 'p_mw']:.1f} MW")
    except Exception as e:
        print(f"Power flow failed with error: {e}")
        print("This confirms convergence issues exist.")
    
    return net

if __name__ == "__main__":
    net = analyze_power_balance()