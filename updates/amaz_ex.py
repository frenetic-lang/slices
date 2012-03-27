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
    
    p_map1[l_topo1.node[11]['ports'][13]] = p_topo.node[1]['ports'][3]
    print  l_topo1.node[11]['ports'][13]
    print  l_topo1.node[11]['ports'][14]
    print  l_topo1.node[13]['ports'][17]
    print  l_topo1.node[14]['ports'][18]
    p_map1[l_topo1.node[11]['ports'][14]] = p_topo.node[1]['ports'][4]
    p_map1[l_topo1.node[13]['ports'][17]] = p_topo.node[3]['ports'][7]
    p_map1[l_topo1.node[14]['ports'][18]] = p_topo.node[4]['ports'][8]

    print p_map1


get_slices()    



