import nxtopo
import slicing
import netcore

def get_slices():
    p_topo = nxtopo.NXTopo()
    for i in range(1,6):
        p_topo.add_switch(i)
        for j in range(1,i):
            p_topo.add_link(i,j)

    for i in range(6,11):
        p_topo.add_host(i)
        p_topo.add_link(i-5, i)

    p_topo.finalize()

    slices = []
    for i in range(1,3):
        l_topo = nxtopo.NXTopo()
        s_map = dict()
        s1p = i
        s2p = s1p + 2
        
        s1l = s1p + (i * 10) 
        l_topo.add_switch(s1l)
        s_map[s1l] = s1p
        
        s2l = s2p + (i * 10)
        l_topo.add_switch(s2l)
        s_map[s2l] = s2p
        
        h1p = s1p + 5
        h2p = s2p + 5
        
        h1l = h1p + (i* 10)
        l_topo.add_host(h1l)
        h2l = h2p + (i * 10)
        l_topo.add_host(h2l)

        l_topo.add_link(s1l, s2l)
        l_topo.add_link(s1l, h1l)
        l_topo.add_link(s2l, h2l)
        
        l_topo.finalize()

        p_map = dict()
        
        addToPortMap(s1l, s2l, p_map, s_map, l_topo, p_topo)
        addHostPortToMap(s1l, h1l, h1p, p_map, s_map, l_topo, p_topo)
        addHostPortToMap(s2l, h2l, h2p, p_map, s_map, l_topo, p_topo)

        ep1 = (s1l, l_topo.edge_ports(s1l)[0])
        ep2 = (s2l, l_topo.edge_ports(s2l)[0])
        
        if s1p == 1:
            policy = netcore.Header('dstport', 25565)
        else:
            policy = netcore.Header('ethtype', 0x86DD)

        slic = slicing.Slice(l_topo, p_topo, s_map, p_map,
                             {ep1 : policy, ep2 : policy})
        slices.append(slic)
    
    slices.append(getIsolatedFella(p_topo))

    return slices

def getIsolatedFella(p_topo):
    #Add our new isolated fella
    l_topo = nxtopo.NXTopo()
    l_topo.add_switch(35)
    l_topo.add_host(40)
    l_topo.add_link(35, 40)
    l_topo.finalize()
    
    l_port = (35, l_topo.node[35]['ports'][40])
    p_port = (5, p_topo.node[5]['ports'][10])
    
    return slicing.Slice(l_topo, p_topo, {35:5}, {l_port:p_port},
                         {l_port:netcore.Header('srcport', 80)})

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
