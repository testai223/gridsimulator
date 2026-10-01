"""Flask backend for the Grid Simulator web GUI.

The backend is a thin JSON layer on top of the existing simulation code:

* ``examples.py``                 - built-in test systems (2-bus, IEEE 9, IEEE 39)
* ``database.py``                 - grids stored in the SQLite database (read-only here)
* ``engine.grid_graph``           - NetworkX graph used for the network visualisation
* ``contingency.ContingencyAnalysis`` - N-1 contingency analysis
* ``state_estimation_module.StateEstimationModule`` - WLS state estimation and
  measurement outage scenarios

No simulation logic is re-implemented here; the endpoints only select a grid,
call the existing code and convert the results into JSON-friendly structures.
"""

from __future__ import annotations

import copy
import dataclasses
import math
import os
import sys
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandapower as pp
from flask import Flask, jsonify, request, send_from_directory

# Make the project root importable when the package is used from elsewhere.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from contingency import ContingencyAnalysis  # noqa: E402
from database import GridDatabase  # noqa: E402
from engine import grid_graph  # noqa: E402
from examples import (  # noqa: E402
    create_example_grid,
    create_ieee_9_bus,
    create_ieee_39_bus,
    create_ieee_39_bus_standard,
)
from state_estimation_module import (  # noqa: E402
    EstimationConfig,
    EstimationMode,
    StateEstimationModule,
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Built-in example grids, created directly from examples.py (no database needed).
EXAMPLES: Dict[str, Dict[str, Any]] = {
    "simple": {
        "name": "Simple Example Grid",
        "description": "Basic 2-bus system with generator and load",
        "factory": create_example_grid,
    },
    "ieee9": {
        "name": "IEEE 9-Bus Test System",
        "description": "Standard IEEE 9-bus test system",
        "factory": create_ieee_9_bus,
    },
    "ieee39": {
        "name": "IEEE 39-Bus New England System",
        "description": "IEEE 39-bus New England test system",
        "factory": create_ieee_39_bus,
    },
    "ieee39_standard": {
        "name": "IEEE 39-Bus Standard (MATPOWER)",
        "description": "Standard IEEE 39-bus system based on MATPOWER case39",
        "factory": create_ieee_39_bus_standard,
    },
}

VOLTAGE_LIMITS = (0.95, 1.05)
LOADING_LIMIT = 85.0  # same threshold as ContingencyAnalysis


class ApiError(Exception):
    """Error that is reported to the client as JSON."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #
def to_jsonable(obj: Any) -> Any:
    """Recursively convert numpy/pandas/enum/dataclass objects to plain JSON types."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(dataclasses.asdict(obj))
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    try:  # pandas NA / NaT and similar
        import pandas as pd

        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return str(obj)


def _num(value: Any, digits: int = 4) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return round(f, digits) if math.isfinite(f) else None


def upgrade_legacy_columns(net: pp.pandapowerNet) -> pp.pandapowerNet:
    """Make grids stored with older pandapower versions loadable by newer ones.

    Grids in ``grid.db`` were serialised with pandapower 3.1, whose load table
    has ``const_z_percent``/``const_i_percent``. Newer pandapower releases split
    these into separate P and Q columns and fail with ``KeyError`` otherwise.
    """
    for element in ("load", "asymmetric_load"):
        table = getattr(net, element, None)
        if table is None:
            continue
        for kind in ("z", "i"):
            old = f"const_{kind}_percent"
            if old in table.columns:
                for new in (f"const_{kind}_p_percent", f"const_{kind}_q_percent"):
                    if new not in table.columns:
                        table[new] = table[old].astype(float)
    return net


def _name(df, idx, prefix: str) -> str:
    if "name" in df.columns:
        value = df.at[idx, "name"]
        if value is not None and str(value) not in ("", "nan", "None"):
            return str(value)
    return f"{prefix} {idx}"


# --------------------------------------------------------------------------- #
# Grid selection
# --------------------------------------------------------------------------- #
def create_app(db_path: Optional[str] = None) -> Flask:
    """Create the Flask application.

    ``db_path`` defaults to the ``GRID_DB`` environment variable or ``grid.db``
    in the project root. The database is only read; if the file does not exist,
    only the built-in example grids are offered.
    """

    app = Flask(__name__, static_folder=None)
    app.config["GRID_DB"] = db_path or os.environ.get(
        "GRID_DB", os.path.join(PROJECT_ROOT, "grid.db")
    )
    example_cache: Dict[str, pp.pandapowerNet] = {}

    def db_available() -> bool:
        path = app.config["GRID_DB"]
        return path == ":memory:" or os.path.exists(path)

    def open_db() -> GridDatabase:
        # A fresh connection per request: sqlite connections are not shareable
        # across the threads used by the Flask development server.
        return GridDatabase(app.config["GRID_DB"])

    def load_net(payload: Dict[str, Any]) -> tuple[pp.pandapowerNet, str]:
        source = payload.get("source", "example")
        grid_id = payload.get("id")
        if grid_id is None or grid_id == "":
            raise ApiError("Missing grid 'id'")
        if source == "example":
            key = str(grid_id)
            if key not in EXAMPLES:
                raise ApiError(f"Unknown example grid '{key}'", 404)
            if key not in example_cache:
                example_cache[key] = EXAMPLES[key]["factory"]()
            return copy.deepcopy(example_cache[key]), EXAMPLES[key]["name"]
        if source == "db":
            if not db_available():
                raise ApiError("Grid database not available", 404)
            try:
                gid = int(grid_id)
            except (TypeError, ValueError):
                raise ApiError("Database grid id must be an integer")
            db = open_db()
            try:
                net = db.load_grid(gid)
                name = next((g[1] for g in db.get_all_grids() if g[0] == gid), f"Grid {gid}")
            finally:
                db.conn.close()
            if net is None:
                raise ApiError(f"Grid {gid} not found in database", 404)
            return upgrade_legacy_columns(net), name
        raise ApiError(f"Unknown grid source '{source}'")

    def apply_outages(net: pp.pandapowerNet, outages: Dict[str, Any]) -> List[str]:
        """Take selected elements out of service (what-if studies)."""
        applied = []
        for element in ("line", "trafo", "gen", "load"):
            ids = outages.get(element) or []
            table = getattr(net, element)
            for raw in ids:
                try:
                    idx = int(raw)
                except (TypeError, ValueError):
                    raise ApiError(f"Invalid {element} id '{raw}'")
                if idx not in table.index:
                    raise ApiError(f"{element} {idx} does not exist")
                table.at[idx, "in_service"] = False
                applied.append(f"{element} {idx}")
        return applied

    def payload() -> Dict[str, Any]:
        if request.method == "GET":
            return request.args.to_dict()
        return request.get_json(silent=True) or {}

    # ------------------------------------------------------------------- #
    # Serialisation of a network
    # ------------------------------------------------------------------- #
    def graph_json(net: pp.pandapowerNet) -> Dict[str, Any]:
        import networkx as nx

        g = grid_graph(net)
        pos: Dict[Any, Any] = {}
        if g.number_of_nodes():
            try:
                pos = nx.kamada_kawai_layout(g)
            except Exception:  # e.g. disconnected graphs on older networkx
                pos = nx.spring_layout(g, seed=42)
        has_res = hasattr(net, "res_bus") and not net.res_bus.empty
        nodes = []
        for n, data in g.nodes(data=True):
            x, y = pos.get(n, (0.0, 0.0))
            nodes.append(
                {
                    "id": int(n),
                    "name": str(data.get("name") or f"Bus {n}"),
                    "x": _num(x),
                    "y": _num(y),
                    "vm_pu": _num(data.get("vm_pu")) if has_res else None,
                    "has_gen": bool(
                        (not net.gen.empty and n in set(net.gen.bus))
                        or (not net.ext_grid.empty and n in set(net.ext_grid.bus))
                    ),
                    "has_load": bool(not net.load.empty and n in set(net.load.bus)),
                }
            )
        edges = []
        for u, v, data in g.edges(data=True):
            edge = {
                "from": int(u),
                "to": int(v),
                "type": data.get("type"),
                "element_id": data.get("id"),
            }
            if data.get("type") == "line" and "p_from_mw" in data:
                edge["p_mw"] = _num(data["p_from_mw"], 2)
                if "res_line" in net and data["id"] in net.res_line.index:
                    edge["loading_percent"] = _num(
                        net.res_line.at[data["id"], "loading_percent"], 1
                    )
            elif data.get("type") == "transformer" and "p_hv_mw" in data:
                edge["p_mw"] = _num(data["p_hv_mw"], 2)
                if "res_trafo" in net and data["id"] in net.res_trafo.index:
                    edge["loading_percent"] = _num(
                        net.res_trafo.at[data["id"], "loading_percent"], 1
                    )
            edges.append(edge)
        return {"nodes": nodes, "edges": edges}

    def elements_json(net: pp.pandapowerNet) -> Dict[str, Any]:
        lines = [
            {
                "id": int(i),
                "name": _name(net.line, i, "Line"),
                "from_bus": int(r.from_bus),
                "to_bus": int(r.to_bus),
                "in_service": bool(r.in_service),
            }
            for i, r in net.line.iterrows()
        ]
        trafos = [
            {
                "id": int(i),
                "name": _name(net.trafo, i, "Trafo"),
                "hv_bus": int(r.hv_bus),
                "lv_bus": int(r.lv_bus),
                "in_service": bool(r.in_service),
            }
            for i, r in net.trafo.iterrows()
        ]
        gens = [
            {"id": int(i), "name": _name(net.gen, i, "Gen"), "bus": int(r.bus)}
            for i, r in net.gen.iterrows()
        ]
        buses = [
            {"id": int(i), "name": _name(net.bus, i, "Bus"), "vn_kv": _num(r.vn_kv, 2)}
            for i, r in net.bus.iterrows()
        ]
        return {"buses": buses, "lines": lines, "trafos": trafos, "gens": gens}

    def stats_json(net: pp.pandapowerNet) -> Dict[str, int]:
        return {
            k: int(len(getattr(net, k)))
            for k in ("bus", "line", "trafo", "gen", "sgen", "load", "ext_grid")
        }

    def loadflow_json(net: pp.pandapowerNet) -> Dict[str, Any]:
        rb = net.res_bus
        buses = []
        for i, r in net.bus.iterrows():
            vm = _num(rb.at[i, "vm_pu"]) if i in rb.index else None
            buses.append(
                {
                    "id": int(i),
                    "name": _name(net.bus, i, "Bus"),
                    "vn_kv": _num(r.vn_kv, 2),
                    "vm_pu": vm,
                    "va_degree": _num(rb.at[i, "va_degree"], 3) if i in rb.index else None,
                    "p_mw": _num(rb.at[i, "p_mw"], 3) if i in rb.index else None,
                    "q_mvar": _num(rb.at[i, "q_mvar"], 3) if i in rb.index else None,
                    "violation": vm is not None
                    and not (VOLTAGE_LIMITS[0] <= vm <= VOLTAGE_LIMITS[1]),
                }
            )

        def branch_rows(table, res, prefix, cols, from_col, to_col, p_from, p_to):
            rows = []
            for i, r in table.iterrows():
                row = {
                    "id": int(i),
                    "name": _name(table, i, prefix),
                    "from_bus": int(r[from_col]),
                    "to_bus": int(r[to_col]),
                    "in_service": bool(r.in_service),
                }
                for out_key, col in cols.items():
                    row[out_key] = _num(res.at[i, col], 3) if i in res.index else None
                loading = row.get("loading_percent")
                row["overloaded"] = loading is not None and loading > LOADING_LIMIT
                rows.append(row)
            return rows

        lines = branch_rows(
            net.line,
            net.res_line,
            "Line",
            {
                "p_from_mw": "p_from_mw",
                "q_from_mvar": "q_from_mvar",
                "p_to_mw": "p_to_mw",
                "q_to_mvar": "q_to_mvar",
                "pl_mw": "pl_mw",
                "i_ka": "i_ka",
                "loading_percent": "loading_percent",
            },
            "from_bus",
            "to_bus",
            "p_from_mw",
            "p_to_mw",
        )
        trafos = branch_rows(
            net.trafo,
            net.res_trafo,
            "Trafo",
            {
                "p_hv_mw": "p_hv_mw",
                "q_hv_mvar": "q_hv_mvar",
                "p_lv_mw": "p_lv_mw",
                "q_lv_mvar": "q_lv_mvar",
                "pl_mw": "pl_mw",
                "loading_percent": "loading_percent",
            },
            "hv_bus",
            "lv_bus",
            "p_hv_mw",
            "p_lv_mw",
        )
        gens = []
        for i, r in net.gen.iterrows():
            res = net.res_gen
            gens.append(
                {
                    "id": int(i),
                    "name": _name(net.gen, i, "Gen"),
                    "bus": int(r.bus),
                    "p_mw": _num(res.at[i, "p_mw"], 3) if i in res.index else None,
                    "q_mvar": _num(res.at[i, "q_mvar"], 3) if i in res.index else None,
                    "vm_pu": _num(res.at[i, "vm_pu"]) if i in res.index else None,
                    "slack": bool(r.get("slack", False)),
                }
            )
        for i, r in net.ext_grid.iterrows():
            res = net.res_ext_grid
            gens.append(
                {
                    "id": f"ext{int(i)}",
                    "name": _name(net.ext_grid, i, "External Grid"),
                    "bus": int(r.bus),
                    "p_mw": _num(res.at[i, "p_mw"], 3) if i in res.index else None,
                    "q_mvar": _num(res.at[i, "q_mvar"], 3) if i in res.index else None,
                    "vm_pu": _num(r.vm_pu),
                    "slack": True,
                }
            )
        loads = [
            {
                "id": int(i),
                "name": _name(net.load, i, "Load"),
                "bus": int(r.bus),
                "p_mw": _num(r.p_mw, 3),
                "q_mvar": _num(r.q_mvar, 3),
                "in_service": bool(r.in_service),
            }
            for i, r in net.load.iterrows()
        ]
        vms = [b["vm_pu"] for b in buses if b["vm_pu"] is not None]
        loadings = [x["loading_percent"] for x in lines + trafos if x.get("loading_percent") is not None]
        total_gen = sum(g["p_mw"] or 0.0 for g in gens)
        total_load = float(net.load.loc[net.load.in_service, "p_mw"].sum()) if not net.load.empty else 0.0
        summary = {
            "converged": bool(net.converged),
            "min_vm_pu": min(vms) if vms else None,
            "max_vm_pu": max(vms) if vms else None,
            "max_loading_percent": max(loadings) if loadings else None,
            "total_generation_mw": _num(total_gen, 2),
            "total_load_mw": _num(total_load, 2),
            "losses_mw": _num(total_gen - total_load, 2),
            "voltage_violations": sum(1 for b in buses if b["violation"]),
            "overloads": sum(1 for x in lines + trafos if x["overloaded"]),
        }
        return {
            "summary": summary,
            "buses": buses,
            "lines": lines,
            "trafos": trafos,
            "gens": gens,
            "loads": loads,
        }

    def se_config(data: Dict[str, Any]) -> EstimationConfig:
        mode_str = str(data.get("mode", "voltage_only"))
        mode = (
            EstimationMode.COMPREHENSIVE
            if mode_str == "comprehensive"
            else EstimationMode.VOLTAGE_ONLY
        )
        try:
            voltage_noise = float(data.get("voltage_noise_percent", 2.5)) / 100.0
            power_noise = float(data.get("power_noise_percent", 3.0)) / 100.0
            max_iter = int(data.get("max_iterations", 20))
        except (TypeError, ValueError):
            raise ApiError("Invalid state estimation parameters")
        if not (0 <= voltage_noise <= 0.5 and 0 <= power_noise <= 0.5 and 1 <= max_iter <= 200):
            raise ApiError("State estimation parameters out of range")
        # Mirrors the configuration built by the desktop GUI (gui.py).
        return EstimationConfig(
            mode=mode,
            voltage_noise_std=voltage_noise,
            power_noise_std=power_noise,
            max_iterations=max_iter,
            tolerance=1e-4,
            include_all_buses=True,
            include_power_injections=(mode == EstimationMode.COMPREHENSIVE),
            include_power_flows=(mode == EstimationMode.COMPREHENSIVE),
        )

    # ------------------------------------------------------------------- #
    # Routes
    # ------------------------------------------------------------------- #
    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        return jsonify({"success": False, "error": err.message}), err.status

    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/static/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(STATIC_DIR, filename)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "database": db_available()})

    @app.get("/api/grids")
    def list_grids():
        grids = [
            {"source": "example", "id": key, "name": e["name"], "description": e["description"]}
            for key, e in EXAMPLES.items()
        ]
        if db_available():
            db = open_db()
            try:
                for gid, name, desc, _created, modified, is_example in db.get_all_grids():
                    grids.append(
                        {
                            "source": "db",
                            "id": int(gid),
                            "name": name,
                            "description": desc or "",
                            "modified": modified,
                            "is_example": bool(is_example),
                        }
                    )
            finally:
                db.conn.close()
        return jsonify({"grids": grids})

    @app.route("/api/grid", methods=["GET", "POST"])
    def grid_info():
        data = payload()
        net, name = load_net(data)
        return jsonify(
            {
                "success": True,
                "name": name,
                "stats": stats_json(net),
                "elements": elements_json(net),
                "graph": graph_json(net),
            }
        )

    @app.post("/api/loadflow")
    def run_loadflow():
        data = payload()
        net, name = load_net(data)
        applied = apply_outages(net, data.get("outages") or {})
        try:
            pp.runpp(net, numba=False)
        except Exception as exc:  # pandapower raises LoadflowNotConverged etc.
            return jsonify(
                {"success": False, "name": name, "outages": applied, "error": f"Load flow failed: {exc}"}
            ), 200
        result = loadflow_json(net)
        result.update(
            {"success": True, "name": name, "outages": applied, "graph": graph_json(net)}
        )
        return jsonify(to_jsonable(result))

    @app.post("/api/contingency")
    def run_contingency():
        data = payload()
        net, name = load_net(data)
        analysis = ContingencyAnalysis(net)
        results = analysis.run_n1_analysis()
        return jsonify(
            to_jsonable(
                {
                    "success": True,
                    "name": name,
                    "summary": analysis.get_contingency_summary(),
                    "results": results,
                    "violations": analysis.violations,
                }
            )
        )

    @app.post("/api/state-estimation")
    def run_state_estimation():
        data = payload()
        net, name = load_net(data)
        config = se_config(data)
        module = StateEstimationModule(GridDatabase(":memory:"))
        results = module.estimate_current_grid_state(net, name, config)
        if results.get("success"):
            # Add bus names / true angles for convenient display.
            pp.runpp(net, numba=False)
            results["bus_ids"] = [int(i) for i in net.bus.index]
            results["bus_names"] = [_name(net.bus, i, "Bus") for i in net.bus.index]
            results["true_voltage_angles_deg"] = net.res_bus["va_degree"].tolist()
            results["voltage_angles_deg"] = np.rad2deg(results["voltage_angles"]).tolist()
        results["name"] = name
        return jsonify(to_jsonable(results))

    @app.post("/api/measurement-outage")
    def run_measurement_outage():
        data = payload()
        net, name = load_net(data)
        raw = data.get("outage_buses") or []
        if isinstance(raw, str):
            raw = [x for x in raw.replace(";", ",").split(",") if x.strip()]
        try:
            outage_buses = [int(x) for x in raw]
        except (TypeError, ValueError):
            raise ApiError("outage_buses must be a list of bus ids")
        if not outage_buses:
            raise ApiError("Select at least one bus for the measurement outage")
        unknown = [b for b in outage_buses if b not in net.bus.index]
        if unknown:
            raise ApiError(f"Unknown bus ids: {unknown}")
        config = se_config(data)
        module = StateEstimationModule(GridDatabase(":memory:"))
        results = module.simulate_measurement_outage_scenario(
            net=net, outage_buses=outage_buses, config=config
        )
        results["name"] = name
        return jsonify(to_jsonable(results))

    return app


def main() -> None:  # pragma: no cover - exercised manually
    import argparse

    parser = argparse.ArgumentParser(description="Grid Simulator web GUI")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "5000")))
    parser.add_argument("--db", default=None, help="Path to the SQLite grid database")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    app = create_app(args.db)
    print(f"Grid Simulator web GUI running on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)
