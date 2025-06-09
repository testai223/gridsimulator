"""Standard IEEE 39-bus New England test system based on MATPOWER case39."""

import pandapower as pp
import numpy as np


def create_ieee_39_bus_standard() -> pp.pandapowerNet:
    """
    Create the standard IEEE 39-bus New England test system.
    
    Based on MATPOWER case39.m and official IEEE publications:
    - T. Athay, R. Podmore, and S. Virmani, "A Practical Method for the Direct 
      Analysis of Transient Stability," IEEE Trans. PAS, Vol. PAS-98, No. 2, 1979.
    
    Returns:
        pandapowerNet: Standard IEEE 39-bus system
    """
    # Create empty network
    net = pp.create_empty_network(name="IEEE 39-Bus New England Standard System")
    
    # Bus data - all buses at 345 kV (standard configuration)
    bus_data = [
        # (bus_num, bus_type, name)
        (1, 1, "Bus 1"),    (2, 1, "Bus 2"),    (3, 1, "Bus 3"),    (4, 1, "Bus 4"),
        (5, 1, "Bus 5"),    (6, 1, "Bus 6"),    (7, 1, "Bus 7"),    (8, 1, "Bus 8"),
        (9, 1, "Bus 9"),    (10, 1, "Bus 10"),  (11, 1, "Bus 11"),  (12, 1, "Bus 12"),
        (13, 1, "Bus 13"),  (14, 1, "Bus 14"),  (15, 1, "Bus 15"),  (16, 1, "Bus 16"),
        (17, 1, "Bus 17"),  (18, 1, "Bus 18"),  (19, 1, "Bus 19"),  (20, 1, "Bus 20"),
        (21, 1, "Bus 21"),  (22, 1, "Bus 22"),  (23, 1, "Bus 23"),  (24, 1, "Bus 24"),
        (25, 1, "Bus 25"),  (26, 1, "Bus 26"),  (27, 1, "Bus 27"),  (28, 1, "Bus 28"),
        (29, 1, "Bus 29"),  (30, 2, "Gen 1"),   (31, 3, "Slack"),   (32, 2, "Gen 3"),
        (33, 2, "Gen 4"),   (34, 2, "Gen 5"),   (35, 2, "Gen 6"),   (36, 2, "Gen 7"),
        (37, 2, "Gen 8"),   (38, 2, "Gen 9"),   (39, 2, "Gen 10")
    ]
    
    # Create buses (all at 345 kV)
    buses = []
    for bus_num, bus_type, name in bus_data:
        bus = pp.create_bus(net, vn_kv=345.0, name=name)
        buses.append(bus)
    
    # Generator data (bus_idx, p_mw, vm_pu, q_min, q_max, is_slack)
    gen_data = [
        (29, 250.0, 1.040, -300, 300, False),    # Gen 1 (Bus 30)
        (30, 521.5, 0.982, -300, 300, True),     # Slack (Bus 31) 
        (31, 650.0, 0.983, -300, 300, False),    # Gen 3 (Bus 32)
        (32, 632.0, 0.997, -300, 300, False),    # Gen 4 (Bus 33)
        (33, 508.0, 1.012, -300, 300, False),    # Gen 5 (Bus 34)
        (34, 687.0, 1.050, -300, 300, False),    # Gen 6 (Bus 35)
        (35, 580.0, 1.063, -300, 300, False),    # Gen 7 (Bus 36)
        (36, 564.0, 1.027, -300, 300, False),    # Gen 8 (Bus 37)
        (37, 865.0, 1.026, -300, 300, False),    # Gen 9 (Bus 38)
        (38, 1100.0, 1.030, -300, 300, False),   # Gen 10 (Bus 39)
    ]
    
    # Create generators
    for bus_idx, p_mw, vm_pu, q_min, q_max, is_slack in gen_data:
        gen_name = f"Gen {bus_idx + 1}" + (" (Slack)" if is_slack else "")
        pp.create_gen(net, bus=bus_idx, p_mw=p_mw, vm_pu=vm_pu, 
                     min_q_mvar=q_min, max_q_mvar=q_max, 
                     slack=is_slack, name=gen_name)
    
    # Load data (bus_idx, p_mw, q_mvar) - based on MATPOWER case39
    load_data = [
        (2, 322.0, 2.4),      # Bus 3
        (6, 500.0, 184.0),    # Bus 7 
        (7, 233.8, 84.0),     # Bus 8
        (11, 522.0, 176.6),   # Bus 12
        (14, 8.5, 88.0),      # Bus 15
        (15, 320.0, 153.0),   # Bus 16
        (17, 329.0, 32.3),    # Bus 18
        (19, 158.0, 30.0),    # Bus 20
        (20, 680.0, 103.0),   # Bus 21
        (22, 274.0, 115.0),   # Bus 23
        (24, 247.5, 84.6),    # Bus 25
        (25, 308.6, -92.2),   # Bus 26
        (27, 224.0, 47.2),    # Bus 28
        (28, 139.0, 17.0),    # Bus 29
        (30, 281.0, 75.5),    # Bus 31 - note: slack bus also has load
        (38, 283.5, 26.9),    # Bus 39 - note: generator bus also has load
    ]
    
    # Create loads
    for bus_idx, p_mw, q_mvar in load_data:
        pp.create_load(net, bus=bus_idx, p_mw=p_mw, q_mvar=q_mvar, 
                      name=f"Load {bus_idx + 1}")
    
    # Transmission line data based on MATPOWER case39
    # (from_bus, to_bus, r_pu, x_pu, b_pu, rate_a_mva)
    line_data = [
        (0, 1, 0.0035, 0.0411, 0.6987, 600),     # 1-2
        (0, 38, 0.0010, 0.0250, 0.7500, 1000),   # 1-39
        (1, 2, 0.0013, 0.0151, 0.2572, 500),     # 2-3
        (1, 24, 0.0070, 0.0086, 0.1460, 500),    # 2-25
        (2, 3, 0.0013, 0.0213, 0.2214, 500),     # 3-4
        (2, 17, 0.0007, 0.0142, 0.1234, 600),    # 3-18
        (3, 4, 0.0008, 0.0128, 0.1342, 600),     # 4-5
        (3, 13, 0.0008, 0.0129, 0.1382, 600),    # 4-14
        (4, 5, 0.0002, 0.0026, 0.0434, 1200),    # 5-6
        (4, 7, 0.0008, 0.0112, 0.1476, 900),     # 5-8
        (5, 6, 0.0006, 0.0092, 0.1130, 900),     # 6-7
        (5, 10, 0.0007, 0.0082, 0.1389, 900),    # 6-11
        (6, 7, 0.0004, 0.0046, 0.0780, 900),     # 7-8
        (7, 8, 0.0023, 0.0363, 0.3804, 900),     # 8-9
        (8, 38, 0.0010, 0.0250, 1.2000, 900),    # 9-39
        (9, 10, 0.0004, 0.0043, 0.0729, 600),    # 10-11
        (9, 12, 0.0023, 0.0272, 0.4434, 600),    # 10-13
        (9, 13, 0.0016, 0.0195, 0.3040, 600),    # 10-14
        (10, 11, 0.0007, 0.0089, 0.1342, 600),   # 11-12
        (11, 12, 0.0013, 0.0173, 0.2138, 600),   # 12-13
        (12, 13, 0.0001, 0.0014, 0.0202, 600),   # 13-14
        (13, 14, 0.0008, 0.0108, 0.1404, 600),   # 14-15
        (14, 15, 0.0002, 0.0026, 0.0348, 1200),  # 15-16
        (15, 16, 0.0007, 0.0089, 0.1342, 600),   # 16-17
        (15, 18, 0.0011, 0.0147, 0.2478, 600),   # 16-19
        (15, 20, 0.0022, 0.0284, 0.3944, 600),   # 16-21
        (15, 23, 0.0008, 0.0135, 0.2548, 600),   # 16-24
        (16, 26, 0.0007, 0.0082, 0.1319, 600),   # 17-27
        (17, 26, 0.0013, 0.0173, 0.3216, 600),   # 18-27
        (18, 19, 0.0006, 0.0081, 0.1023, 600),   # 19-20
        (20, 21, 0.0008, 0.0135, 0.2548, 600),   # 21-22
        (21, 22, 0.0006, 0.0087, 0.1073, 600),   # 22-23
        (22, 23, 0.0022, 0.0350, 0.3610, 600),   # 23-24
        (24, 25, 0.0032, 0.0323, 0.5310, 600),   # 25-26
        (25, 27, 0.0013, 0.0141, 0.2132, 600),   # 26-28
        (25, 28, 0.0014, 0.0129, 0.2011, 600),   # 26-29
        (26, 27, 0.0009, 0.0101, 0.1565, 600),   # 27-28
        (26, 28, 0.0016, 0.0195, 0.3040, 600),   # 27-29
        (27, 28, 0.0007, 0.0082, 0.1319, 600),   # 28-29
    ]
    
    # Create transmission lines
    for from_bus, to_bus, r_pu, x_pu, b_pu, rate_mva in line_data:
        # Convert per-unit values to actual ohm/km values for 345 kV system
        # Using 100 MVA base and 345 kV base
        z_base = (345**2) / 100  # Base impedance in ohms
        
        r_ohm_per_km = r_pu * z_base
        x_ohm_per_km = x_pu * z_base
        c_nf_per_km = b_pu * 1000 / (2 * np.pi * 50 * z_base)  # Convert susceptance to capacitance
        max_i_ka = rate_mva / (np.sqrt(3) * 345)  # Convert MVA rating to current rating
        
        pp.create_line_from_parameters(
            net, from_bus=from_bus, to_bus=to_bus, length_km=1.0,
            r_ohm_per_km=r_ohm_per_km, x_ohm_per_km=x_ohm_per_km, 
            c_nf_per_km=c_nf_per_km, max_i_ka=max_i_ka,
            name=f"Line {from_bus+1}-{to_bus+1}"
        )
    
    # Transformer data (from_bus, to_bus, sn_mva, vn_hv_kv, vn_lv_kv, vk_percent, vkr_percent)
    # These connect generators to the 345 kV transmission system
    transformer_data = [
        # Gen step-up transformers (assuming generators at lower voltage levels)
        (29, 1, 300, 345, 22, 10.5, 0.0),     # Gen 1 connection
        (30, 1, 600, 345, 22, 10.5, 0.0),     # Slack gen connection  
        (31, 2, 700, 345, 22, 10.5, 0.0),     # Gen 3 connection
        (32, 19, 700, 345, 22, 10.5, 0.0),    # Gen 4 connection
        (33, 20, 600, 345, 22, 10.5, 0.0),    # Gen 5 connection
        (34, 22, 800, 345, 22, 10.5, 0.0),    # Gen 6 connection
        (35, 23, 700, 345, 22, 10.5, 0.0),    # Gen 7 connection
        (36, 25, 700, 345, 22, 10.5, 0.0),    # Gen 8 connection
        (37, 28, 1000, 345, 22, 10.5, 0.0),   # Gen 9 connection
        (38, 8, 1200, 345, 22, 10.5, 0.0),    # Gen 10 connection
    ]
    
    # Create transformers
    for from_bus, to_bus, sn_mva, vn_hv_kv, vn_lv_kv, vk_percent, vkr_percent in transformer_data:
        pp.create_transformer_from_parameters(
            net, hv_bus=to_bus, lv_bus=from_bus, sn_mva=sn_mva, 
            vn_hv_kv=vn_hv_kv, vn_lv_kv=vn_lv_kv,
            vk_percent=vk_percent, vkr_percent=vkr_percent, 
            pfe_kw=0, i0_percent=0,
            name=f"T{from_bus+1}"
        )
    
    return net


def create_ieee_39_bus_matpower() -> pp.pandapowerNet:
    """
    Create IEEE 39-bus system using pandapower's built-in MATPOWER case.
    
    This uses the exact data from MATPOWER case39.m file.
    
    Returns:
        pandapowerNet: MATPOWER-based IEEE 39-bus system
    """
    try:
        # Try to use pandapower's built-in case39 if available
        from pandapower.networks.power_system_test_cases import case39
        net = case39()
        net.name = "IEEE 39-Bus MATPOWER Case"
        return net
    except ImportError:
        print("Warning: pandapower.networks.power_system_test_cases not available")
        print("Falling back to standard implementation")
        return create_ieee_39_bus_standard()


def create_ieee_39_bus_simplified() -> pp.pandapowerNet:
    """
    Create a simplified IEEE 39-bus system with all buses at 345 kV.
    
    This version removes the complexity of generator step-up transformers
    and places all generators directly on the 345 kV system for easier analysis.
    
    Returns:
        pandapowerNet: Simplified IEEE 39-bus system
    """
    # Create empty network
    net = pp.create_empty_network(name="IEEE 39-Bus Simplified")
    
    # Create all 39 buses at 345 kV
    for i in range(39):
        if i == 30:  # Bus 31 (slack)
            bus_name = f"Bus {i+1} (Slack)"
        elif i >= 29:  # Generator buses
            bus_name = f"Bus {i+1} (Gen)"
        else:  # Load buses
            bus_name = f"Bus {i+1}"
        
        pp.create_bus(net, vn_kv=345.0, name=bus_name)
    
    # Simplified generator data (all connected directly to 345 kV buses)
    gen_data = [
        (29, 250.0, 1.040, False),    # Gen 1
        (30, 521.5, 0.982, True),     # Slack
        (31, 650.0, 0.983, False),    # Gen 3
        (32, 632.0, 0.997, False),    # Gen 4
        (33, 508.0, 1.012, False),    # Gen 5
        (34, 687.0, 1.050, False),    # Gen 6
        (35, 580.0, 1.063, False),    # Gen 7
        (36, 564.0, 1.027, False),    # Gen 8
        (37, 865.0, 1.026, False),    # Gen 9
        (38, 1100.0, 1.030, False),   # Gen 10
    ]
    
    # Create generators
    for bus_idx, p_mw, vm_pu, is_slack in gen_data:
        gen_name = f"Gen {bus_idx + 1}" + (" (Slack)" if is_slack else "")
        if is_slack:
            # Create external grid for slack bus
            pp.create_ext_grid(net, bus=bus_idx, vm_pu=vm_pu, name=gen_name)
        else:
            # Create PV generator
            pp.create_gen(net, bus=bus_idx, p_mw=p_mw, vm_pu=vm_pu, 
                         slack=False, name=gen_name)
    
    # Standard IEEE 39-bus load data
    load_data = [
        (2, 322.0, 2.4),      # Bus 3
        (6, 500.0, 184.0),    # Bus 7
        (7, 233.8, 84.0),     # Bus 8
        (11, 522.0, 176.6),   # Bus 12
        (14, 8.5, 88.0),      # Bus 15
        (15, 320.0, 153.0),   # Bus 16
        (17, 329.0, 32.3),    # Bus 18
        (19, 158.0, 30.0),    # Bus 20
        (20, 680.0, 103.0),   # Bus 21
        (22, 274.0, 115.0),   # Bus 23
        (24, 247.5, 84.6),    # Bus 25
        (25, 308.6, -92.2),   # Bus 26
        (27, 224.0, 47.2),    # Bus 28
        (28, 139.0, 17.0),    # Bus 29
    ]
    
    # Create loads
    for bus_idx, p_mw, q_mvar in load_data:
        pp.create_load(net, bus=bus_idx, p_mw=p_mw, q_mvar=q_mvar, 
                      name=f"Load {bus_idx + 1}")
    
    # Standard transmission line data with realistic ratings
    line_data = [
        (0, 1, 0.0035, 0.0411, 0.6987, 1000),    # 1-2
        (0, 38, 0.0010, 0.0250, 0.7500, 1500),   # 1-39
        (1, 2, 0.0013, 0.0151, 0.2572, 800),     # 2-3
        (1, 24, 0.0070, 0.0086, 0.1460, 800),    # 2-25
        (2, 3, 0.0013, 0.0213, 0.2214, 800),     # 3-4
        (2, 17, 0.0007, 0.0142, 0.1234, 1000),   # 3-18
        (3, 4, 0.0008, 0.0128, 0.1342, 1000),    # 4-5
        (3, 13, 0.0008, 0.0129, 0.1382, 1000),   # 4-14
        (4, 5, 0.0002, 0.0026, 0.0434, 2000),    # 5-6
        (4, 7, 0.0008, 0.0112, 0.1476, 1500),    # 5-8
        (5, 6, 0.0006, 0.0092, 0.1130, 1500),    # 6-7
        (5, 10, 0.0007, 0.0082, 0.1389, 1500),   # 6-11
        (6, 7, 0.0004, 0.0046, 0.0780, 1500),    # 7-8
        (7, 8, 0.0023, 0.0363, 0.3804, 1500),    # 8-9
        (8, 38, 0.0010, 0.0250, 1.2000, 1500),   # 9-39
        (9, 10, 0.0004, 0.0043, 0.0729, 1000),   # 10-11
        (9, 12, 0.0023, 0.0272, 0.4434, 1000),   # 10-13
        (9, 13, 0.0016, 0.0195, 0.3040, 1000),   # 10-14
        (10, 11, 0.0007, 0.0089, 0.1342, 1000),  # 11-12
        (11, 12, 0.0013, 0.0173, 0.2138, 1000),  # 12-13
        (12, 13, 0.0001, 0.0014, 0.0202, 1000),  # 13-14
        (13, 14, 0.0008, 0.0108, 0.1404, 1000),  # 14-15
        (14, 15, 0.0002, 0.0026, 0.0348, 2000),  # 15-16
        (15, 16, 0.0007, 0.0089, 0.1342, 1000),  # 16-17
        (15, 18, 0.0011, 0.0147, 0.2478, 1000),  # 16-19
        (15, 20, 0.0022, 0.0284, 0.3944, 1000),  # 16-21
        (15, 23, 0.0008, 0.0135, 0.2548, 1000),  # 16-24
        (16, 26, 0.0007, 0.0082, 0.1319, 1000),  # 17-27
        (17, 26, 0.0013, 0.0173, 0.3216, 1000),  # 18-27
        (18, 19, 0.0006, 0.0081, 0.1023, 1000),  # 19-20
        (20, 21, 0.0008, 0.0135, 0.2548, 1000),  # 21-22
        (21, 22, 0.0006, 0.0087, 0.1073, 1000),  # 22-23
        (22, 23, 0.0022, 0.0350, 0.3610, 1000),  # 23-24
        (24, 25, 0.0032, 0.0323, 0.5310, 1000),  # 25-26
        (25, 27, 0.0013, 0.0141, 0.2132, 1000),  # 26-28
        (25, 28, 0.0014, 0.0129, 0.2011, 1000),  # 26-29
        (26, 27, 0.0009, 0.0101, 0.1565, 1000),  # 27-28
        (26, 28, 0.0016, 0.0195, 0.3040, 1000),  # 27-29
        (27, 28, 0.0007, 0.0082, 0.1319, 1000),  # 28-29
    ]
    
    # Create transmission lines
    for from_bus, to_bus, r_pu, x_pu, b_pu, rate_mva in line_data:
        # Convert per-unit values to actual values for 345 kV system
        z_base = (345**2) / 100  # Base impedance in ohms
        
        r_ohm_per_km = r_pu * z_base
        x_ohm_per_km = x_pu * z_base
        c_nf_per_km = b_pu * 1000 / (2 * np.pi * 50 * z_base)
        max_i_ka = rate_mva / (np.sqrt(3) * 345)
        
        pp.create_line_from_parameters(
            net, from_bus=from_bus, to_bus=to_bus, length_km=1.0,
            r_ohm_per_km=r_ohm_per_km, x_ohm_per_km=x_ohm_per_km, 
            c_nf_per_km=c_nf_per_km, max_i_ka=max_i_ka,
            name=f"Line {from_bus+1}-{to_bus+1}"
        )
    
    return net


if __name__ == "__main__":
    """Test the different IEEE 39-bus implementations."""
    import pandapower as pp
    
    print("Testing IEEE 39-bus implementations...")
    
    # Test simplified version
    try:
        net_simple = create_ieee_39_bus_simplified()
        pp.runpp(net_simple)
        print("✓ Simplified IEEE 39-bus: Converged")
        print(f"  - Buses: {len(net_simple.bus)}")
        print(f"  - Generators: {len(net_simple.gen)}")
        print(f"  - Lines: {len(net_simple.line)}")
        print(f"  - Loads: {len(net_simple.load)}")
        print(f"  - Total generation: {net_simple.res_gen['p_mw'].sum():.1f} MW")
        print(f"  - Total load: {net_simple.load['p_mw'].sum():.1f} MW")
    except Exception as e:
        print(f"✗ Simplified IEEE 39-bus: Failed - {e}")
    
    # Test MATPOWER version if available
    try:
        net_matpower = create_ieee_39_bus_matpower()
        pp.runpp(net_matpower)
        print("✓ MATPOWER IEEE 39-bus: Converged")
        print(f"  - Buses: {len(net_matpower.bus)}")
        print(f"  - Total generation: {net_matpower.res_gen['p_mw'].sum():.1f} MW")
        print(f"  - Total load: {net_matpower.load['p_mw'].sum():.1f} MW")
    except Exception as e:
        print(f"✗ MATPOWER IEEE 39-bus: Failed - {e}")
    
    print("\nAll implementations tested.")