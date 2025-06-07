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
