import networkx as nx
from examples import create_example_grid
from engine import grid_graph


def test_grid_graph_nodes_and_edges():
    net = create_example_grid()
    g = grid_graph(net)
    assert isinstance(g, nx.Graph)
    assert g.number_of_nodes() == len(net.bus)
    assert g.number_of_edges() == len(net.line)
