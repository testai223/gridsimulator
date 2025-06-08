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
