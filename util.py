def id_map(items):
    """Make a mapping that is the identity over items."""
    return dict((i, i) for i in items)

def ports_of_topo(topo, end_hosts=False):
    """Get all (switch, port)s of a topo as a set."""
    s = set()
    for n, node in topo.node.items():
        ports = node['port'].keys()
        for p in ports:
            # Only include if a switch, or we're including end hosts
            if p != 0 or end_hosts:
                s.add((n, p))
    return s
