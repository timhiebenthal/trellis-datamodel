from trellis_datamodel.adapters.lineage import walk_upstream


def _walk(graph, root, leaves=()):
    return walk_upstream(
        root, lambda n: graph.get(n, ()), lambda n: n not in leaves
    )


def test_collects_every_upstream_and_edge():
    nodes, edges = _walk({"c": ["b"], "b": ["a"]}, "c")
    assert nodes == {"a", "b", "c"}
    assert edges == [
        {"source": "b", "target": "c"},
        {"source": "a", "target": "b"},
    ]


def test_leaf_nodes_are_included_but_not_expanded():
    nodes, edges = _walk({"c": ["src"], "src": ["hidden"]}, "c", leaves={"src"})
    assert nodes == {"c", "src"}
    assert edges == [{"source": "src", "target": "c"}]


def test_diamond_keeps_both_edges_but_expands_shared_upstream_once():
    calls = []
    graph = {"d": ["b", "c"], "b": ["a"], "c": ["a"]}

    def upstreams_of(n):
        calls.append(n)
        return graph.get(n, ())

    nodes, edges = walk_upstream("d", upstreams_of, lambda n: True)
    assert nodes == {"a", "b", "c", "d"}
    assert len(edges) == 4
    assert calls.count("a") == 1


def test_cycle_terminates():
    nodes, _ = _walk({"a": ["b"], "b": ["a"]}, "a")
    assert nodes == {"a", "b"}
