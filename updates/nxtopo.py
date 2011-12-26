from mininet.topo import Topo, Node
import networkx as nx

class NXTopo(nx.Graph):

    def __init__(self):
        super(NXTopo, self).__init__()
        self.finalized=False

    def add_switch(self,sid):
        assert not self.finalized
        self.add_node(sid, isSwitch=True)

    def add_host(self,hid):
        assert not self.finalized
        self.add_node(hid, isSwitch=False)

    def add_link(self,hid,sid):
        assert not self.finalized
        self.add_edge(hid,sid)
        
    def switches(self):
        assert self.finalized
        return [s for (s,d) in self.nodes(data=True) if d['isSwitch']]

    def hosts(self):
        assert self.finalized
        return [h for (h,d) in self.nodes(data=True) if not d['isSwitch']]

    def edge_switches(self):
        result = set()
        for h in self.hosts():
            for s in self.neighbors(h):
                if self.node[s]['isSwitch']:
                    result.add(s)
        return list(result)

    def edge_ports(self,sid):
        result = set()
        for x in self.neighbors(sid):
            if not self.node[x]['isSwitch']:
                result.add(self.node[sid]['ports'][x])
        return list(result)

    def finalize(self):
        # make mininet topo
        topo = Topo()
        
        # add nodes
        for x,d in self.nodes(data=True):
            topo.add_node(x,Node(is_switch=d['isSwitch']))
                
        # add links
        for src,dst in self.edges():
            topo.add_edge(src,dst)
            
        # backpatch ports into original graph
        for x in self.nodes():
            self.node[x]['ports'] = {}
            for y in self.neighbors(x):               
                self.node[x]['ports'][y] = topo.port(x,y)[0]

        topo.enable_all()
        self.topo = topo        
        self.finalized = True

    def nx_graph(self):
        assert self.finalized
        return self.copy()

    def mininet_topo(self):
        assert self.finalized
        return self.topo
