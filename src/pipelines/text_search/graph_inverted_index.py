import pickle
from pprint import pprint
from typing import Any, Dict, Iterable, Union

import graphviz
import matplotlib.pyplot as plt
import networkx as nx
import tqdm


def dict_to_graph_traverse(
    dictionary: Union[Dict, Iterable], g: nx.Graph, prev_node: Any
) -> None:
    for key in dictionary:
        g.add_node(key)
        g.add_edge(prev_node, key)
        if isinstance(dictionary, Dict):
            dict_to_graph_traverse(dictionary=dictionary[key], g=g, prev_node=key)


def dict_to_graph(dictionary: Dict[str, Union[Dict, Iterable]]) -> nx.Graph:
    g = nx.DiGraph()
    g.add_node("root")
    dict_to_graph_traverse(dictionary=dictionary, g=g, prev_node="root")
    return g


inverted_index = pickle.load(file=open(file="inverted_index.pkl", mode="rb"))
stemmed_inverted_index = pickle.load(
    file=open(file="stemmed_inverted_index.pkl", mode="rb")
)

g = dict_to_graph(dictionary=stemmed_inverted_index)
pprint(g)
# nx.draw_circular(G=g, with_labels=True)
# plt.show()
# plt.savefig('graph_inverted_index.png', format='PNG')
nx.drawing.nx_pydot.write_dot(G=g, path="graph_stemmed_inverted_index.dot")
