import nxtopo
import slicing

def figurin():
    p_topo = nxtopo.NXTopo()
    p_topo.add_switch(1)
    p_topo.add_switch(2)
    p_topo.add_switch(3)
    p_topo.add_link(1,2)
    p_topo.add_link(2,1)
    p_topo.add_link(1,3)
    p_topo.add_link(3,1)
    p_topo.add_link(3,2)
    p_topo.add_link(2,3)
    p_topo.add_host(4)
    p_topo.add_link(1,4)
    p_topo.finalize()
    return p_topo


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
    p_topo.add_link(1,3)
    p_topo.add_link(1,4)
    p_topo.add_link(1,5)
    p_topo.add_link(2,3)
    p_topo.add_link(2,4)
    p_topo.add_link(2,5)
    p_topo.add_link(3,7)
    p_topo.add_link(4,8)
    p_topo.add_link(5,9)
    p_topo.finalize()

    l_topo1 = nxtopo.NXTopo()
    s_map1 = dict()
    p_map1 = dict()

    l_topo1.add_switch(11)
    s_map1[11] = 1
    l_topo1.add_switch(13)
    s_map1[13] = 3
    l_topo1.add_switch(14)
    s_map1[14] = 4
    l_topo1.add_host(17)
    l_topo1.add_host(18)
    
    l_topo1.add_link(11,13)
    l_topo1.add_link(11,14)
    l_topo1.add_link(13,17)
    l_topo1.add_link(14,18)

    l_topo1.finalize()
    
    addToPortMap(11, 13, p_map1, s_map1, l_topo1, p_topo)
    addToPortMap(11, 14, p_map1, s_map1, l_topo1, p_topo)
    
    addHostPortToMap(13, 17, 7, p_map1, s_map1, l_topo1, p_topo)
    addHostPortToMap(14, 18, 8, p_map1, s_map1, l_topo1, p_topo)

    print p_map1 == getSlice(13,11,14,17,18,-10,p_topo)

def getSlice(l_sLeft, l_sMid, l_sRight, l_hLeft, l_hRight, adj,  p_topo):
    l_topo = nxtopo.NXTopo()
    s_map = dict()
    p_map = dict()
    
    l_topo.add_switch(l_sMid)
    s_map[11] = l_sMid + adj
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
    
    return p_map





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



