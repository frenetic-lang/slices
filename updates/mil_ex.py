import nxtopo
import slicing
import netcore

def get_slices():
    p_topo = nxtopo.NXTopo()
    for i in range(1,5):
        p_topo.add_switch(i)
        for j in range(1,i):
            p_topo.add_link(i,j)

    for i in range(6,10):
        p_topo.add_host(i)
        p_topo.add_link(i-5, i)

    p_topo.finalize()

get_slices()
