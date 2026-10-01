"""Tests for the Flask web GUI backend (web/app.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import GridDatabase  # noqa: E402
from examples import create_ieee_9_bus  # noqa: E402
from web.app import create_app  # noqa: E402

IEEE9 = {"source": "example", "id": "ieee9"}


@pytest.fixture(scope="module")
def db_path(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("db") / "test_grid.db")
    db = GridDatabase(path)
    db.save_grid("Test IEEE 9", create_ieee_9_bus(), "saved for web tests")
    db.conn.close()
    return path


@pytest.fixture(scope="module")
def client(db_path):
    app = create_app(db_path)
    app.config["TESTING"] = True
    return app.test_client()


def test_index_and_static_files(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"Grid Simulator" in res.data
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200


def test_health(client):
    data = client.get("/api/health").get_json()
    assert data == {"status": "ok", "database": True}


def test_list_grids_contains_examples_and_db(client):
    grids = client.get("/api/grids").get_json()["grids"]
    example_ids = {g["id"] for g in grids if g["source"] == "example"}
    assert {"simple", "ieee9", "ieee39", "ieee39_standard"} <= example_ids
    assert any(g["source"] == "db" and g["name"] == "Test IEEE 9" for g in grids)


def test_grid_info_returns_topology(client):
    data = client.post("/api/grid", json={"source": "example", "id": "ieee39"}).get_json()
    assert data["success"]
    assert data["stats"]["bus"] == 39
    assert len(data["graph"]["nodes"]) == 39
    assert all(n["x"] is not None and n["y"] is not None for n in data["graph"]["nodes"])
    assert len(data["elements"]["lines"]) == data["stats"]["line"]


def test_loadflow_ieee9(client):
    data = client.post("/api/loadflow", json=IEEE9).get_json()
    assert data["success"]
    assert data["summary"]["converged"] is True
    assert len(data["buses"]) == 9
    assert len(data["lines"]) == 6
    assert len(data["trafos"]) == 3
    for bus in data["buses"]:
        assert 0.8 < bus["vm_pu"] < 1.2
    # generation must cover the load (plus small losses)
    s = data["summary"]
    assert s["total_generation_mw"] >= s["total_load_mw"]
    assert any(e["p_mw"] is not None for e in data["graph"]["edges"])


def test_loadflow_with_line_outage(client):
    base = client.post("/api/loadflow", json=IEEE9).get_json()
    out = client.post("/api/loadflow", json={**IEEE9, "outages": {"line": [0]}}).get_json()
    assert out["success"]
    assert out["outages"] == ["line 0"]
    line0 = next(line for line in out["lines"] if line["id"] == 0)
    assert line0["in_service"] is False
    assert out["summary"]["max_vm_pu"] != base["summary"]["max_vm_pu"] or (
        out["summary"]["max_loading_percent"] != base["summary"]["max_loading_percent"]
    )


def test_loadflow_from_database_grid(client):
    grids = client.get("/api/grids").get_json()["grids"]
    gid = next(g["id"] for g in grids if g["source"] == "db")
    data = client.post("/api/loadflow", json={"source": "db", "id": gid}).get_json()
    assert data["success"]
    assert data["name"] == "Test IEEE 9"
    assert len(data["buses"]) == 9


def test_loadflow_errors(client):
    assert client.post("/api/loadflow", json={"source": "example", "id": "nope"}).status_code == 404
    assert client.post("/api/loadflow", json={"source": "db", "id": 999}).status_code == 404
    assert client.post("/api/loadflow", json={"source": "x", "id": 1}).status_code == 400
    assert client.post("/api/loadflow", json={}).status_code == 400
    res = client.post("/api/loadflow", json={**IEEE9, "outages": {"line": [999]}})
    assert res.status_code == 400
    assert res.get_json()["success"] is False


def test_contingency_analysis(client):
    data = client.post("/api/contingency", json=IEEE9).get_json()
    assert data["success"]
    results = data["results"]
    # base case + 6 lines + 3 trafos + 3 generators... (gens may be skipped for slack)
    assert results[0]["contingency_type"] == "Base Case"
    assert any(r["contingency_type"] == "Line Outage" for r in results)
    assert data["summary"]["total_contingencies"] == len(results)
    assert data["summary"]["security_status"] in ("Secure", "Insecure")
    assert isinstance(data["violations"], list)


def test_state_estimation_voltage_only(client):
    data = client.post("/api/state-estimation", json={**IEEE9, "mode": "voltage_only"}).get_json()
    assert data["success"]
    assert data["converged"] is True
    assert len(data["voltage_magnitudes"]) == 9
    assert len(data["bus_ids"]) == 9
    assert data["measurements_count"] >= 9
    for est, true in zip(data["voltage_magnitudes"], data["true_voltage_magnitudes"]):
        assert abs(est - true) < 0.1


def test_state_estimation_invalid_params(client):
    res = client.post("/api/state-estimation", json={**IEEE9, "max_iterations": "abc"})
    assert res.status_code == 400
    res = client.post("/api/state-estimation", json={**IEEE9, "voltage_noise_percent": 500})
    assert res.status_code == 400


def test_measurement_outage(client):
    data = client.post(
        "/api/measurement-outage", json={**IEEE9, "outage_buses": [4]}
    ).get_json()
    assert data["success"]
    assert data["outage_buses"] == [4]
    assert "scenario_summary" in data
    assert client.post("/api/measurement-outage", json=IEEE9).status_code == 400
    assert (
        client.post("/api/measurement-outage", json={**IEEE9, "outage_buses": [99]}).status_code
        == 400
    )


def test_missing_database_only_lists_examples(tmp_path):
    app = create_app(str(tmp_path / "does_not_exist.db"))
    c = app.test_client()
    grids = c.get("/api/grids").get_json()["grids"]
    assert grids and all(g["source"] == "example" for g in grids)
    assert not (tmp_path / "does_not_exist.db").exists()


def test_upgrade_legacy_load_columns():
    import pandapower as pp

    from web.app import upgrade_legacy_columns

    net = create_ieee_9_bus()
    net.load = net.load.drop(
        columns=[c for c in net.load.columns if c.startswith("const_")]
    )
    net.load["const_z_percent"] = 0.0
    net.load["const_i_percent"] = 0.0
    upgrade_legacy_columns(net)
    for col in ("const_z_p_percent", "const_z_q_percent", "const_i_p_percent", "const_i_q_percent"):
        assert col in net.load.columns
    pp.runpp(net, numba=False)
    assert net.converged
