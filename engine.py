"""Grid calculation engine using pandapower."""

from typing import Any, List

import pandapower as pp

from database import GridDatabase


class GridCalculator:
    """Build and calculate power flow using pandapower."""

    def __init__(self, db: GridDatabase) -> None:
        self.db = db
        self.net = pp.create_empty_network()

    def build_network(self) -> None:
        """Construct the pandapower network from database entries."""
        for bus_id, name, vn_kv in self.db.get_buses():
            pp.create_bus(self.net, vn_kv=vn_kv, name=name, index=bus_id)

        for (
            line_id,
            from_bus,
            to_bus,
            length_km,
            r_ohm_per_km,
            x_ohm_per_km,
            c_nf_per_km,
            max_i_ka,
        ) in self.db.get_lines():
            pp.create_line_from_parameters(
                self.net,
                from_bus,
                to_bus,
                length_km=length_km,
                r_ohm_per_km=r_ohm_per_km,
                x_ohm_per_km=x_ohm_per_km,
                c_nf_per_km=c_nf_per_km,
                max_i_ka=max_i_ka,
                name=str(line_id),
            )

    def run_powerflow(self) -> Any:
        """Execute a power flow calculation and return results."""
        self.build_network()
        pp.runpp(self.net)
        return self.net.res_bus


def element_tables(net: pp.pandapowerNet) -> str:
    """Return formatted tables of common grid elements in *net*.

    Elements include lines, transformers, generators, static generators,
    loads and external grids. Only non-empty tables are included in the
    returned string.
    """

    element_map = {
        "Lines": "line",
        "Transformers": "trafo",
        "Generators": "gen",
        "Static Generators": "sgen",
        "Loads": "load",
        "External Grids": "ext_grid",
    }

    tables: List[str] = []
    for title, attr in element_map.items():
        df = getattr(net, attr, None)
        if df is not None and not df.empty:
            tables.append(f"{title}\n{df.to_string()}\n")

    return "\n".join(tables)

