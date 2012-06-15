import nxtopo
import slicing
import netcore as nc
import util

def get_slices():
    p_topo = nxtopo.NXTopo()
    # The triangular core
    p_topo.add_switch("PI1")
    p_topo.add_switch("PI2")
    p_topo.add_switch("PI3")
    p_topo.add_link("PI1","PI2")
    p_topo.add_link("PI1","PI3")
    p_topo.add_link("PI2","PI3")

    # An external-facing switch for each switch in the core
    p_topo.add_switch("PE1")
    p_topo.add_switch("PE2")
    p_topo.add_switch("PE3")
    p_topo.add_link("PI1", "PE1")
    p_topo.add_link("PI2", "PE2")
    p_topo.add_link("PI3", "PE3")

    # For each slice, two endpoints attached appropriately.
    # R    \ /     G
    #       1
    #      / \
    #   --3---2--
    #    /     \
    #       B
    p_topo.add_host("GH1")
    p_topo.add_link("GH1", "PE1")
    p_topo.add_host("GH2")
    p_topo.add_link("GH2", "PE2")
    p_topo.add_host("BH1")
    p_topo.add_link("BH1", "PE2")
    p_topo.add_host("BH2")
    p_topo.add_link("BH2", "PE3")
    p_topo.add_host("RH1")
    p_topo.add_link("RH1", "PE3")
    p_topo.add_host("RH2")
    p_topo.add_link("RH2", "PE1")

    p_topo.finalize()

    green_switches = ("PE1", "PI1", "PI2", "PE2")
    blue_switches  = ("PE2", "PI2", "PI3", "PE3")
    red_switches   = ("PE3", "PI3", "PI1", "PE1")

    green_hosts = ("GH1", "GH2")
    blue_hosts  = ("BH1", "BH2")
    red_hosts   = ("RH1", "RH2")

    green_nodes = green_switches + green_hosts
    blue_nodes  = blue_switches  + blue_hosts
    red_nodes   = red_switches   + red_hosts

    green_topo = p_topo.subgraph(green_nodes)
    blue_topo  = p_topo.subgraph(blue_nodes)
    red_topo   = p_topo.subgraph(red_nodes)

    green_ports = util.ports_of_topo(green_topo)
    blue_ports  = util.ports_of_topo(blue_topo)
    red_ports   = util.ports_of_topo(red_topo)

    g_s_map = util.id_map(green_nodes)
    b_s_map = util.id_map(blue_nodes)
    r_s_map = util.id_map(red_nodes)

    g_p_map = util.id_map(green_ports)
    b_p_map = util.id_map(blue_ports)
    r_p_map = util.id_map(red_ports)

    g_preds = build_external_predicate(green_topo)
    b_preds = build_external_predicate(blue_topo)
    r_preds = build_external_predicate(red_topo)

    green_slice = slicing.Slice(green_topo, p_topo, g_s_map, g_p_map, g_preds)
    blue_slice  = slicing.Slice(blue_topo,  p_topo, b_s_map, b_p_map, b_preds)
    red_slice   = slicing.Slice(red_topo,   p_topo, r_s_map, r_p_map, r_preds)

    return p_topo, (green_slice, blue_slice, red_slice)

def build_external_predicate(l_topo):
    predicates = {}
    for n, node in l_topo.node.items():
        if node['isSwitch']:
            for p, (target, target_port) in node['port'].items():
                if target_port == 0: # that means target is an end host
                    predicates[(n, p)] = nc.Top()
    return predicates
