import engine
from examples import create_example_grid


def test_element_tables_example_grid():
    net = create_example_grid()
    output = engine.element_tables(net)
    assert "Lines" in output
    assert "Loads" in output
    assert "External Grids" in output
