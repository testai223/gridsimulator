import networkx as nx
from examples import create_example_grid
from engine import grid_graph
import pandapower as pp


def test_grid_graph_nodes_and_edges():
    net = create_example_grid()
    g = grid_graph(net)
    assert isinstance(g, nx.Graph)
    assert g.number_of_nodes() == len(net.bus)
    assert g.number_of_edges() == len(net.line)


def test_grid_graph_includes_results():
    net = create_example_grid()
    pp.runpp(net)
    g = grid_graph(net)
    # pick first bus and line
    bus_idx = net.bus.index[0]
    assert "vm_pu" in g.nodes[bus_idx]
    edge_data = list(g.edges(data=True))[0][2]
    assert "p_from_mw" in edge_data
    assert "p_to_mw" in edge_data
