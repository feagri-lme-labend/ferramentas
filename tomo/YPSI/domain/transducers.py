def build_transducers(selected_nodes):
    """
    Build transducer structure from selected contour nodes.
    """

    return [
        {
            "id": i + 1,
            "contour_node_id": node_id
        }
        for i, node_id in enumerate(selected_nodes)
    ]