import pandapower as pp
from examples import create_example_grid


def test_create_example_grid():
    net = create_example_grid()
    assert isinstance(net, pp.pandapowerNet)
    # 2 buses
    assert len(net.bus) == 2
    # 1 line
    assert len(net.line) == 1
    # 1 load
    assert len(net.load) == 1
    # 1 external grid
    assert len(net.ext_grid) == 1
