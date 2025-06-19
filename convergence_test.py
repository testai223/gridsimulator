#!/usr/bin/env python3
"""
Advanced convergence analysis for IEEE 39-bus system.
"""

from examples import create_ieee_39_bus
import pandapower as pp
import numpy as np

def test_convergence_options():
    """Test different power flow solver options."""
    print("=" * 60)
    print("IEEE 39-BUS CONVERGENCE ANALYSIS")
    print("=" * 60)
    
    net = create_ieee_39_bus()
    
    # Test 1: Basic power flow with different solver options
    print("\n1. TESTING DIFFERENT SOLVER OPTIONS:")
    print("-" * 45)
    
    test_cases = [
        {"name": "Newton-Raphson (default)", "algorithm": "nr", "init": "auto"},
        {"name": "Newton-Raphson (flat start)", "algorithm": "nr", "init": "flat"},
        {"name": "Newton-Raphson (DC)", "algorithm": "nr", "init": "dc"},
        {"name": "Fast-Decoupled", "algorithm": "fdbx", "init": "auto"},
        {"name": "Gauss-Seidel", "algorithm": "gs", "init": "auto"},
    ]
    
    for case in test_cases:
        try:
            net_copy = net.deepcopy()
            pp.runpp(net_copy, algorithm=case["algorithm"], init=case["init"], 
                    max_iteration=50, tolerance_mva=1e-6)
            print(f"✓ {case['name']}: CONVERGED")
            slack_gen = net_copy.res_gen.loc[net_copy.gen[net_copy.gen['slack']].index[0], 'p_mw']
            print(f"  Slack generation: {slack_gen:.1f} MW")
        except Exception as e:
            print(f"✗ {case['name']}: FAILED - {str(e)[:50]}...")
    
    # Test 2: Check for voltage constraint violations
    print("\n2. VOLTAGE CONSTRAINT ANALYSIS:")
    print("-" * 40)
    
    # Check generator voltage setpoints
    print("Generator voltage setpoints:")
    for idx, row in net.gen.iterrows():
        bus_num = row['bus'] + 1
        vm_pu = row['vm_pu']
        status = "OK" if 0.95 <= vm_pu <= 1.05 else "WARNING"
        print(f"  Gen {bus_num}: {vm_pu:.3f} pu ({status})")
    
    # Test 3: Try reduced tolerance and more iterations
    print("\n3. RELAXED CONVERGENCE CRITERIA:")
    print("-" * 40)
    
    relaxed_tests = [
        {"tol": 1e-3, "iter": 100, "name": "Relaxed tolerance (1e-3)"},
        {"tol": 1e-2, "iter": 100, "name": "Very relaxed tolerance (1e-2)"},
        {"tol": 1e-4, "iter": 200, "name": "More iterations (200)"},
    ]
    
    for test in relaxed_tests:
        try:
            net_copy = net.deepcopy()
            pp.runpp(net_copy, tolerance_mva=test["tol"], max_iteration=test["iter"])
            print(f"✓ {test['name']}: CONVERGED")
            slack_gen = net_copy.res_gen.loc[net_copy.gen[net_copy.gen['slack']].index[0], 'p_mw']
            print(f"  Slack generation: {slack_gen:.1f} MW")
        except Exception as e:
            print(f"✗ {test['name']}: FAILED - {str(e)[:50]}...")
    
    # Test 4: Check for network islands or connectivity issues
    print("\n4. NETWORK CONNECTIVITY CHECK:")
    print("-" * 40)
    
    # Create bus adjacency to check connectivity
    n_buses = len(net.bus)
    adjacency = np.zeros((n_buses, n_buses))
    
    # Add line connections
    for _, line in net.line.iterrows():
        from_bus = line['from_bus']
        to_bus = line['to_bus']
        adjacency[from_bus, to_bus] = 1
        adjacency[to_bus, from_bus] = 1
    
    # Add transformer connections
    for _, trafo in net.trafo.iterrows():
        hv_bus = trafo['hv_bus']
        lv_bus = trafo['lv_bus']
        adjacency[hv_bus, lv_bus] = 1
        adjacency[lv_bus, hv_bus] = 1
    
    # Check if network is connected
    visited = np.zeros(n_buses, dtype=bool)
    
    def dfs(bus):
        visited[bus] = True
        for neighbor in range(n_buses):
            if adjacency[bus, neighbor] and not visited[neighbor]:
                dfs(neighbor)
    
    # Start DFS from bus 0
    dfs(0)
    connected_buses = np.sum(visited)
    
    print(f"Connected buses: {connected_buses}/{n_buses}")
    if connected_buses == n_buses:
        print("✓ Network is fully connected")
    else:
        print("✗ Network has isolated buses!")
        isolated = [i for i in range(n_buses) if not visited[i]]
        print(f"  Isolated buses: {[i+1 for i in isolated]}")
    
    # Test 5: Try with a simple modification - remove one problematic generator
    print("\n5. SIMPLIFIED NETWORK TEST:")
    print("-" * 35)
    
    try:
        net_simple = net.deepcopy()
        # Remove the highest power generator (except slack)
        non_slack_gens = net_simple.gen[~net_simple.gen['slack']]
        highest_gen_idx = non_slack_gens['p_mw'].idxmax()
        net_simple.gen.drop(highest_gen_idx, inplace=True)
        
        pp.runpp(net_simple, max_iteration=50)
        print("✓ Simplified network (removed highest non-slack gen): CONVERGED")
        slack_gen = net_simple.res_gen.loc[net_simple.gen[net_simple.gen['slack']].index[0], 'p_mw']
        print(f"  Slack generation: {slack_gen:.1f} MW")
        
        return net_simple
        
    except Exception as e:
        print(f"✗ Simplified network: FAILED - {str(e)[:50]}...")
    
    return None

if __name__ == "__main__":
    working_net = test_convergence_options()