import nxtopo
import slicing
import netcore as nc

def get_slices():
    p_topo = nxtopo.NXTopo()
    p_topo.add_switch("S1")
    p_topo.add_switch("S2")
    p_topo.add_switch("S3")

    p_topo.add_link("S1","S2")
    p_topo.add_link("S1","S3")
    p_topo.add_link("S2","S3")

    for i in range(1,4):
        for j in range(1,4):
            s = "S" + str(i)
            h = s + "_" + str(j)
            p_topo.add_host(h)
            p_topo.add_link(s,h)

    p_topo.finalize()

    return [green_slice(p_topo),blue_slice(p_topo),red_slice(p_topo)]

def blue_slice(p_topo):
    l_topo = nxtopo.NXTopo()
    l_topo.add_switch("B2")
    l_topo.add_switch("B3")
    l_topo.add_link("B2","B3")

    for i in range(2,4):
        for j in range (1,4):
            s = "B" + str(i)
            h = s + "_" + str(j)
            l_topo.add_host(h)
            l_topo.add_link(s,h)
            
    l_topo.finalize()

    s_map = {"B2":"S2","B3":"S3"}

    p_map = {}
    add_to_port_map("B2","B3",p_map,s_map,l_topo,p_topo)
    
    preds = {}

    # Map edge ports and add predicates
    for i in range(2,4):
        for j in range(1,4):
            s = "B" + str(i)
            h_l = s + "_" + str(j)
            h_p = "S" + str(i) + "_" + str(j)
            add_host_port_to_map(s, h_l, h_p, p_map, s_map, l_topo, p_topo)
            
        for ep in l_topo.edge_ports(s):
            if i == 2:
                preds[(s,ep)] = nc.Header("srcport", 80) #TODO define
            else:
                preds[(s,ep)] = nc.Header("dstport", 80)

    return slicing.Slice(l_topo, p_topo, s_map, p_map, preds)

def green_slice(p_topo):
    l_topo = nxtopo.NXTopo()
    l_topo.add_switch("G1")
    l_topo.add_switch("G2")
    l_topo.add_switch("G3")
    l_topo.add_link("G1","G2")
    l_topo.add_link("G1","G3")
    l_topo.add_link("G2","G3")
    l_topo.finalize()

    s_map = {"G1":"S1","G2":"S2","G3":"S3"}

    p_map = {}
    add_to_port_map("G1","G2",p_map,s_map,l_topo,p_topo)
    add_to_port_map("G1","G3",p_map,s_map,l_topo,p_topo)
    add_to_port_map("G2","G3",p_map,s_map,l_topo,p_topo)

    return slicing.Slice(l_topo, p_topo, s_map, p_map, {})
    
def red_slice(p_topo):
    l_topo = nxtopo.NXTopo()
    l_topo.add_switch("R1")
    l_topo.add_switch("R2")
    l_topo.add_link("R1","R2")

    for i in range(1,3):
        for j in range (1,4):
            s = "R" + str(i)
            h = s + "_" + str(j)
            l_topo.add_host(h)
            l_topo.add_link(s,h)

    l_topo.finalize()

    s_map = {"R1":"S1","R2":"S2"}

    p_map = {}
    add_to_port_map("R2","R1",p_map,s_map,l_topo,p_topo)
    preds ={}

    # Map edge ports and add predicates
    for i in range(1,3):
        for j in range(1,4):
            s = "R" + str(i)
            h_l = s + "_" + str(j)
            h_p = "S" + str(i) + "_" + str(j)
            add_host_port_to_map(s, h_l, h_p, p_map, s_map, l_topo, p_topo)
            
        for ep in l_topo.edge_ports(s):
            if i == 1:
                preds[(s,ep)] = nc.Header("srcport", 80)
            else:
                preds[(s,ep)] = nc.Header("dstport", 80)

    return slicing.Slice(l_topo, p_topo, s_map, p_map, preds)

def add_to_port_map(s1, s2, p_map, s_map, l_topo, p_topo):
    s1p = s_map[s1]
    s2p = s_map[s2]
    key = (s1, l_topo.node[s1]['ports'][s2])
    val = (s1p, p_topo.node[s1p]['ports'][s2p])
    p_map[key] = val

    key = (s2, l_topo.node[s2]['ports'][s1])
    val = (s2p, p_topo.node[s2p]['ports'][s1p])
    p_map[key] = val

def add_host_port_to_map(s, h_l, h_p, p_map, s_map, l_topo, p_topo):
    sp = s_map[s]
    key = (s, l_topo.node[s]['ports'][h_l])
    val = (sp, p_topo.node[sp]['ports'][h_p])
    p_map[key] = val

get_slices()
