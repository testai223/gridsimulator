from database import GridDatabase
from engine import GridCalculator


def setup_simple_db() -> GridDatabase:
    db = GridDatabase(":memory:")
    bus1 = db.add_bus("Bus1", 20.0)
    bus2 = db.add_bus("Bus2", 0.4)
    db.add_line(
        bus1,
        bus2,
        length_km=1.0,
        r_ohm_per_km=0.1,
        x_ohm_per_km=0.1,
        c_nf_per_km=0.0,
        max_i_ka=0.4,
    )
    return db


def test_database_inserts():
    db = setup_simple_db()
    assert len(db.get_buses()) == 2
    assert len(db.get_lines()) == 1


def test_build_network():
    db = setup_simple_db()
    calc = GridCalculator(db)
    calc.build_network()
    assert len(calc.net.bus) == 2
    assert len(calc.net.line) == 1
