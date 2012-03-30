import nxtopo
import slicing
import netcore as nc

def get_slices():
    p_topo = nxtopo.NXTopo()
    p_topo.add_switch(1)
    p_topo.add_switch(2)
    p_topo.add_switch(3)
    p_topo.add_switch(4)
    p_topo.add_switch(5)
    p_topo.add_host(7)
    p_topo.add_host(8)
    p_topo.add_host(9)
    p_topo.add_link(1, 3)
    p_topo.add_link(1, 4)
    p_topo.add_link(1, 5)
    p_topo.add_link(2, 3)
    p_topo.add_link(2, 4)
    p_topo.add_link(2, 5)
    p_topo.add_link(3, 7)
    p_topo.add_link(4, 8)
    p_topo.add_link(5, 9)
    p_topo.finalize()

    slic_list = [# All traffic to one port
                 getSlice(13, 11, 14, 17, 18, -10,
                    nc.Header('dstport', 25565), p_topo),
                 # All IPv6 traffic
                 getSlice(23, 21, 25, 27, 29, -20,
                    nc.Header('ethtype', 0x86DD), p_topo),
                 # IPv4 web traffic, tightly specified
                 getSlice(34, 32, 35, 38, 39, -30,
                          # IPv4
                          nc.nary_intersection([nc.Header('ethtype', 0x0800),
                                               # TCP
                                               nc.Header('protocol', 0x06),
                                               # Port 80
                                               nc.Header('dstport', 80)]),
                          p_topo)]

    return slic_list

def getSlice(l_sLeft, l_sMid, l_sRight, l_hLeft, l_hRight, adj, policy, p_topo):
    # Slice of form
    #         mid
    #        /   \
    #     left   right
    #      |       |
    #    hLeft   hRight
    #
    # Where adj converts it back to a physical number

    l_topo = nxtopo.NXTopo()
    s_map = dict()
    p_map = dict()

    l_topo.add_switch(l_sMid)
    s_map[l_sMid] = l_sMid + adj
    l_topo.add_switch(l_sLeft)
    s_map[l_sLeft] = l_sLeft + adj
    l_topo.add_switch(l_sRight)
    s_map[l_sRight] = l_sRight + adj
    l_topo.add_host(l_hLeft)
    l_topo.add_host(l_hRight)

    l_topo.add_link(l_sMid, l_sLeft)
    l_topo.add_link(l_sMid, l_sRight)
    l_topo.add_link(l_sLeft, l_hLeft)
    l_topo.add_link(l_sRight, l_hRight)

    l_topo.finalize()

    addToPortMap(l_sMid, l_sLeft, p_map, s_map, l_topo, p_topo)
    addToPortMap(l_sMid, l_sRight, p_map, s_map, l_topo, p_topo)

    addHostPortToMap(l_sLeft, l_hLeft, l_hLeft + adj, p_map, s_map,
                     l_topo, p_topo)
    addHostPortToMap(l_sRight, l_hRight, l_hRight + adj, p_map, s_map,
                     l_topo, p_topo)

    ep1 = (l_sLeft, l_topo.edge_ports(l_sLeft)[0])
    ep2 = (l_sRight, l_topo.edge_ports(l_sRight)[0])

    slic = slicing.Slice(l_topo, p_topo, s_map, p_map,
                         {ep1 : policy, ep2 : policy})

    return slic

def addToPortMap(s1, s2, p_map, s_map, l_topo, p_topo):
    s1p = s_map[s1]
    s2p = s_map[s2]
    key = (s1, l_topo.node[s1]['ports'][s2])
    val = (s1p, p_topo.node[s1p]['ports'][s2p])
    p_map[key] = val

    key = (s2, l_topo.node[s2]['ports'][s1])
    val = (s2p, p_topo.node[s2p]['ports'][s1p])
    p_map[key] = val

def addHostPortToMap(s, h_l, h_p, p_map, s_map, l_topo, p_topo):
    sp = s_map[s]
    key = (s, l_topo.node[s]['ports'][h_l])
    val = (sp, p_topo.node[sp]['ports'][h_p])
    p_map[key] = val

get_slices()
