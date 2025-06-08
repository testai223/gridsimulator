"""Utility functions that generate example power grid models."""

from typing import Any

import pandapower as pp


def create_example_grid() -> pp.pandapowerNet:
    """Return a minimal grid with two buses, a line, an external grid and a load."""
    net = pp.create_empty_network()
    hv_bus = pp.create_bus(net, vn_kv=20.0, name="HV Bus")
    lv_bus = pp.create_bus(net, vn_kv=0.4, name="LV Bus")

    pp.create_ext_grid(net, bus=hv_bus, vm_pu=1.0, name="Grid Connection")

    pp.create_line_from_parameters(
        net,
        hv_bus,
        lv_bus,
        length_km=1.0,
        r_ohm_per_km=0.1,
        x_ohm_per_km=0.1,
        c_nf_per_km=0.0,
        max_i_ka=0.4,
        name="Line",
    )

    pp.create_load(net, bus=lv_bus, p_mw=1.0, q_mvar=0.2, name="Load")
    return net


def create_ieee_9_bus() -> pp.pandapowerNet:
    """Return the IEEE 9-bus test system."""
    net = pp.create_empty_network(name="IEEE 9-bus Test System")

    # Create buses
    bus1 = pp.create_bus(net, vn_kv=16.5, name="Bus 1")
    bus2 = pp.create_bus(net, vn_kv=18.0, name="Bus 2") 
    bus3 = pp.create_bus(net, vn_kv=13.8, name="Bus 3")
    bus4 = pp.create_bus(net, vn_kv=230.0, name="Bus 4")
    bus5 = pp.create_bus(net, vn_kv=230.0, name="Bus 5")
    bus6 = pp.create_bus(net, vn_kv=230.0, name="Bus 6")
    bus7 = pp.create_bus(net, vn_kv=230.0, name="Bus 7")
    bus8 = pp.create_bus(net, vn_kv=230.0, name="Bus 8")
    bus9 = pp.create_bus(net, vn_kv=230.0, name="Bus 9")

    # Create generators (Gen 2 is the slack bus)
    pp.create_gen(net, bus=bus1, p_mw=71.64, vm_pu=1.04, name="Gen 1")
    pp.create_gen(net, bus=bus2, p_mw=163.0, vm_pu=1.025, slack=True, name="Gen 2 (Slack)")
    pp.create_gen(net, bus=bus3, p_mw=85.0, vm_pu=1.025, name="Gen 3")

    # Create transformers (generator step-up transformers)
    pp.create_transformer_from_parameters(
        net, hv_bus=bus4, lv_bus=bus1, sn_mva=100, vn_hv_kv=230, vn_lv_kv=16.5,
        vkr_percent=0.0, vk_percent=5.76, pfe_kw=0, i0_percent=0, name="T1"
    )
    pp.create_transformer_from_parameters(
        net, hv_bus=bus7, lv_bus=bus2, sn_mva=100, vn_hv_kv=230, vn_lv_kv=18.0,
        vkr_percent=0.0, vk_percent=6.25, pfe_kw=0, i0_percent=0, name="T2"
    )
    pp.create_transformer_from_parameters(
        net, hv_bus=bus9, lv_bus=bus3, sn_mva=100, vn_hv_kv=230, vn_lv_kv=13.8,
        vkr_percent=0.0, vk_percent=5.86, pfe_kw=0, i0_percent=0, name="T3"
    )

    # Create transmission lines
    pp.create_line_from_parameters(
        net, from_bus=bus4, to_bus=bus5, length_km=1.0,
        r_ohm_per_km=0.01, x_ohm_per_km=0.085, c_nf_per_km=8800,
        max_i_ka=0.5, name="Line 4-5"
    )
    pp.create_line_from_parameters(
        net, from_bus=bus4, to_bus=bus6, length_km=1.0,
        r_ohm_per_km=0.017, x_ohm_per_km=0.092, c_nf_per_km=7900,
        max_i_ka=0.5, name="Line 4-6"
    )
    pp.create_line_from_parameters(
        net, from_bus=bus5, to_bus=bus7, length_km=1.0,
        r_ohm_per_km=0.032, x_ohm_per_km=0.161, c_nf_per_km=1530,
        max_i_ka=0.5, name="Line 5-7"
    )
    pp.create_line_from_parameters(
        net, from_bus=bus6, to_bus=bus9, length_km=1.0,
        r_ohm_per_km=0.039, x_ohm_per_km=0.170, c_nf_per_km=1790,
        max_i_ka=0.5, name="Line 6-9"
    )
    pp.create_line_from_parameters(
        net, from_bus=bus7, to_bus=bus8, length_km=1.0,
        r_ohm_per_km=0.0085, x_ohm_per_km=0.072, c_nf_per_km=7450,
        max_i_ka=0.5, name="Line 7-8"
    )
    pp.create_line_from_parameters(
        net, from_bus=bus8, to_bus=bus9, length_km=1.0,
        r_ohm_per_km=0.0119, x_ohm_per_km=0.1008, c_nf_per_km=10450,
        max_i_ka=0.5, name="Line 8-9"
    )

    # Create loads
    pp.create_load(net, bus=bus5, p_mw=125.0, q_mvar=50.0, name="Load 5")
    pp.create_load(net, bus=bus6, p_mw=90.0, q_mvar=30.0, name="Load 6")
    pp.create_load(net, bus=bus8, p_mw=100.0, q_mvar=35.0, name="Load 8")

    return net


def create_ieee_39_bus() -> pp.pandapowerNet:
    """Return the IEEE 39-bus New England test system."""
    net = pp.create_empty_network(name="IEEE 39-bus New England Test System")

    # Create buses (39 buses total)
    bus_data = [
        (0, 345.0, "Bus 01"), (1, 345.0, "Bus 02"), (2, 345.0, "Bus 03"), (3, 345.0, "Bus 04"),
        (4, 345.0, "Bus 05"), (5, 345.0, "Bus 06"), (6, 345.0, "Bus 07"), (7, 345.0, "Bus 08"),
        (8, 345.0, "Bus 09"), (9, 345.0, "Bus 10"), (10, 345.0, "Bus 11"), (11, 345.0, "Bus 12"),
        (12, 345.0, "Bus 13"), (13, 345.0, "Bus 14"), (14, 345.0, "Bus 15"), (15, 345.0, "Bus 16"),
        (16, 345.0, "Bus 17"), (17, 345.0, "Bus 18"), (18, 345.0, "Bus 19"), (19, 345.0, "Bus 20"),
        (20, 345.0, "Bus 21"), (21, 345.0, "Bus 22"), (22, 345.0, "Bus 23"), (23, 345.0, "Bus 24"),
        (24, 345.0, "Bus 25"), (25, 345.0, "Bus 26"), (26, 345.0, "Bus 27"), (27, 345.0, "Bus 28"),
        (28, 345.0, "Bus 29"), (29, 16.5, "Gen 30"), (30, 18.0, "Gen 31"), (31, 20.7, "Gen 32"),
        (32, 18.0, "Gen 33"), (33, 20.7, "Gen 34"), (34, 18.0, "Gen 35"), (35, 20.7, "Gen 36"),
        (36, 18.0, "Gen 37"), (37, 20.7, "Gen 38"), (38, 345.0, "Bus 39 (Slack)")
    ]
    
    buses = []
    for idx, vn_kv, name in bus_data:
        bus = pp.create_bus(net, vn_kv=vn_kv, name=name)
        buses.append(bus)

    # Create generators
    gen_data = [
        (29, 250.0, 1.04, False),   # Gen 30
        (30, 677.87, 1.025, False), # Gen 31
        (31, 650.0, 0.982, False),  # Gen 32
        (32, 632.0, 0.983, False),  # Gen 33
        (33, 508.0, 0.997, False),  # Gen 34
        (34, 687.0, 1.013, False),  # Gen 35
        (35, 580.0, 1.025, False),  # Gen 36
        (36, 564.0, 1.026, False),  # Gen 37
        (37, 865.0, 1.03, False),   # Gen 38
        (38, 1000.0, 1.03, True),   # Gen 39 (Slack)
    ]
    
    for bus_idx, p_mw, vm_pu, is_slack in gen_data:
        gen_name = f"Gen {bus_idx + 1}" + (" (Slack)" if is_slack else "")
        pp.create_gen(net, bus=bus_idx, p_mw=p_mw, vm_pu=vm_pu, slack=is_slack, name=gen_name)

    # Create transmission lines
    line_data = [
        (0, 1, 0.0035, 0.0411, 0.6987, 600),    # 1-2
        (0, 38, 0.001, 0.025, 0.75, 1000),       # 1-39
        (1, 2, 0.0013, 0.0151, 0.2572, 500),    # 2-3
        (1, 24, 0.007, 0.0086, 0.146, 500),     # 2-25
        (2, 3, 0.0013, 0.0213, 0.2214, 500),    # 3-4
        (2, 17, 0.0007, 0.0142, 0.1234, 600),   # 3-18
        (3, 4, 0.0008, 0.0128, 0.1342, 600),    # 4-5
        (3, 13, 0.0008, 0.0129, 0.1382, 600),   # 4-14
        (4, 5, 0.0002, 0.0026, 0.0434, 1200),   # 5-6
        (4, 7, 0.0008, 0.0112, 0.1476, 900),    # 5-8
        (5, 6, 0.0006, 0.0092, 0.113, 900),     # 6-7
        (5, 10, 0.0007, 0.0082, 0.1389, 900),   # 6-11
        (6, 7, 0.0004, 0.0046, 0.078, 900),     # 7-8
        (7, 8, 0.0023, 0.0363, 0.3804, 900),    # 8-9
        (8, 38, 0.001, 0.025, 1.2, 900),        # 9-39
        (9, 10, 0.0004, 0.0043, 0.0729, 600),   # 10-11
        (9, 12, 0.0023, 0.0272, 0.4434, 600),   # 10-13
        (9, 13, 0.0016, 0.0195, 0.304, 600),    # 10-14
        (10, 11, 0.0007, 0.0089, 0.1342, 600),  # 11-12
        (11, 12, 0.0013, 0.0173, 0.2138, 600),  # 12-13
        (12, 13, 0.0001, 0.0014, 0.0202, 600),  # 13-14
        (13, 14, 0.0008, 0.0108, 0.1404, 600),  # 14-15
        (14, 15, 0.0002, 0.0026, 0.0348, 1200), # 15-16
        (15, 16, 0.0007, 0.0089, 0.1342, 600),  # 16-17
        (15, 18, 0.0011, 0.0147, 0.2478, 600),  # 16-19
        (15, 20, 0.0022, 0.0284, 0.3944, 600),  # 16-21
        (15, 23, 0.0008, 0.0135, 0.2548, 600),  # 16-24
        (16, 26, 0.0007, 0.0082, 0.1319, 600),  # 17-27
        (17, 26, 0.0013, 0.0173, 0.3216, 600),  # 18-27
        (18, 19, 0.0006, 0.0081, 0.1023, 600),  # 19-20
        (18, 32, 0.0007, 0.0143, 0.2565, 600),  # 19-33
        (19, 32, 0.0009, 0.018, 0.358, 600),    # 20-34
        (20, 21, 0.0008, 0.0135, 0.2548, 600),  # 21-22
        (20, 32, 0.0018, 0.0217, 0.366, 600),   # 21-34
        (21, 22, 0.0006, 0.0087, 0.1073, 600),  # 22-23
        (21, 34, 0.0009, 0.0101, 0.1565, 600),  # 22-35
        (22, 23, 0.0022, 0.035, 0.361, 600),    # 23-24
        (22, 35, 0.0025, 0.0298, 0.5984, 600),  # 23-36
        (23, 35, 0.0043, 0.0504, 0.514, 600),   # 24-36
        (24, 25, 0.0032, 0.0323, 0.531, 600),   # 25-26
        (24, 25, 0.0014, 0.0147, 0.2396, 600),  # 25-26 (parallel)
        (25, 27, 0.0013, 0.0141, 0.2132, 600),  # 26-28
        (25, 28, 0.0014, 0.0129, 0.2011, 600),  # 26-29
        (26, 27, 0.0009, 0.0101, 0.1565, 600),  # 27-28
        (26, 28, 0.0016, 0.0195, 0.304, 600),   # 27-29
        (27, 28, 0.0007, 0.0082, 0.1319, 600),  # 28-29
        (28, 37, 0.0016, 0.0195, 0.304, 600),   # 29-38
    ]
    
    for from_bus, to_bus, r_pu, x_pu, b_pu, max_i_ka in line_data:
        pp.create_line_from_parameters(
            net, from_bus=from_bus, to_bus=to_bus, length_km=1.0,
            r_ohm_per_km=r_pu*345**2/100, x_ohm_per_km=x_pu*345**2/100, 
            c_nf_per_km=b_pu*100/(2*3.14159*50*345**2)*1e9, max_i_ka=max_i_ka/1000,
            name=f"Line {from_bus+1}-{to_bus+1}"
        )

    # Create transformers (generator step-up transformers)
    trafo_data = [
        (29, 38, 100, 16.5, 345.0, "T30"),  # Gen 30
        (30, 16, 100, 18.0, 345.0, "T31"),  # Gen 31
        (31, 20, 100, 20.7, 345.0, "T32"),  # Gen 32
        (32, 18, 100, 18.0, 345.0, "T33"),  # Gen 33
        (33, 23, 100, 20.7, 345.0, "T34"),  # Gen 34
        (34, 21, 100, 18.0, 345.0, "T35"),  # Gen 35
        (35, 22, 100, 20.7, 345.0, "T36"),  # Gen 36
        (36, 22, 100, 18.0, 345.0, "T37"),  # Gen 37
        (37, 28, 100, 20.7, 345.0, "T38"),  # Gen 38
    ]
    
    for lv_bus, hv_bus, sn_mva, vn_lv_kv, vn_hv_kv, name in trafo_data:
        pp.create_transformer_from_parameters(
            net, hv_bus=hv_bus, lv_bus=lv_bus, sn_mva=sn_mva, vn_hv_kv=vn_hv_kv, vn_lv_kv=vn_lv_kv,
            vkr_percent=0.0, vk_percent=10.0, pfe_kw=0, i0_percent=0, name=name
        )

    # Create loads (major load centers)
    load_data = [
        (2, 322.0, 2.4),    # Bus 3
        (6, 233.8, 84.0),   # Bus 7
        (7, 522.0, 176.6),  # Bus 8
        (11, 8.5, 88.0),    # Bus 12
        (14, 320.0, 153.0), # Bus 15
        (15, 329.0, 32.3),  # Bus 16
        (17, 158.0, 30.0),  # Bus 18
        (19, 680.0, 103.0), # Bus 20
        (20, 274.0, 115.0), # Bus 21
        (22, 247.5, 84.6),  # Bus 23
        (23, 308.6, -92.2), # Bus 24
        (24, 224.0, 47.2),  # Bus 25
        (25, 139.0, 17.0),  # Bus 26
        (26, 281.0, 75.5),  # Bus 27
        (27, 206.0, 27.6),  # Bus 28
        (28, 283.5, 26.9),  # Bus 29
    ]
    
    for bus_idx, p_mw, q_mvar in load_data:
        pp.create_load(net, bus=bus_idx, p_mw=p_mw, q_mvar=q_mvar, name=f"Load {bus_idx+1}")

    return net
