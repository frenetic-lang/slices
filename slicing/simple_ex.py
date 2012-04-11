import nxtopo
import slicing
import netcore as nc

def get_slice():

    # Create the physical topology
    p_topo = nxtopo.NXTopo()
    p_topo.add_switch(1)
    p_topo.add_switch(2)
    p_topo.add_switch(3)
    p_topo.add_link(1,2)
    p_topo.add_link(1,3)
    p_topo.add_link(2,3)
    p_topo.finalize()

    # Create the logical topology and switch mappings
    l_topo = nxtopo.NXTopo()
    switch_map = dict()
    l_topo.add_switch(12)
    switch_map[12] = 2
    l_topo.add_switch(13)
    switch_map[13] = 3
    l_topo.add_link(12,13)
    l_topo.finalize()
    port_map = dict()
    port_map[get_port(12, 13, l_topo)] = get_port(2, 3, p_topo)
    port_map[get_port(13, 12, l_topo)] = get_port(3, 2, p_topo)

    # Create and return slice
    return slicing.Slice(l_topo, p_topo, switch_map, port_map, dict())

def get_port(src, dest, topo):
    return (src, topo.node[src]['ports'][dest])

get_slice()
