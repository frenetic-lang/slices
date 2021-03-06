################################################################################
# The Frenetic Project                                                         #
# frenetic@frenetic-lang.org                                                   #
################################################################################
# Licensed to the Frenetic Project by one or more contributors. See the        #
# NOTICE file distributed with this work for additional information            #
# regarding copyright and ownership. The Frenetic Project licenses this        #
# file to you under the following license.                                     #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided the following conditions are met:       #
# - Redistributions of source code must retain the above copyright             #
#   notice, this list of conditions and the following disclaimer.              #
# - Redistributions in binary form must reproduce the above copyright          #
#   notice, this list of conditions and the following disclaimer in            #
#   the documentation or other materials provided with the distribution.       #
# - The names of the copyright holds and contributors may not be used to       #
#   endorse or promote products derived from this work without specific        #
#   prior written permission.                                                  #
#                                                                              #
# Unless required by applicable law or agreed to in writing, software          #
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT    #
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the     #
# LICENSE file distributed with this work for specific language governing      #
# permissions and limitations under the License.                               #
################################################################################
# /updates/nxtopo.py                                                           #
# Topologies                                                                   #
################################################################################

from mininet.topo import Topo, Node
import copy
import networkx as nx

def from_graph(graph, data=False):
    """Convert another NetworkX graph to an nxtopo.

    Marks all nodes as switches.  Copies extra data in the nodes if data=True.
    Leaves graph unfinalized.
    """
    topo = NXTopo()
    if data:
        for node, data in graph.nodes(data=True):
            topo.add_switch(node, data)
        for n1, n2, data in graph.edges(data=True):
            topo.add_edge(n1, n2, data)
    else:
        for node in graph.nodes():
            topo.add_switch(node)
        for n1, n2 in graph.edges():
            topo.add_edge(n1, n2)
    return topo

class NXTopo(nx.Graph):
    """Representation of network switches.

    PARTIAL (and reverse-engineered) documentation:

    Adds a base field, finalized to track whether mininet has been called
    (assigns ports).

    Adds three fields to the node dictionary:

    isSwitch:  boolean, distinguishes switches from end hosts
    port: {local_port: (destination_switch, destination_port)}
    ports: {destination_switch: local_port}
    """

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

    # This differs from the normal NX.Graph subgraph() in that we need
    # to be very careful in what node attributes we propagate
    # over. For the moment, I propagate all of them except for trimming
    # no-longer-in-use ports out of the switches' dictionaries
    def subgraph(self, nbunch):
        """Return the subgraph induced on switches and hosts in nbunch.

        The induced subgraph of the graph contains the nodes in nbunch
        and the edges between those nodes.

        Parameters
        ----------
        nbunch : list, iterable
            A container of nodes which will be iterated through once.

        Returns
        -------
        G : NXTopo
            A subgraph of the graph with the same edge attributes.
        """
        bunch =self.nbunch_iter(nbunch)
        # create new graph and copy subgraph into it
        H = NXTopo()
        # copy node and attribute dictionaries
        for n in bunch:
            H.node[n]=copy.deepcopy(self.node[n])
        # We need to remove inappropriate ports from the switches
        for n in H.node.values():
            new_port = {}
            for local_port, (switch, port) in n['port'].items():
                if switch in nbunch:
                    new_port[local_port] = (switch, port)
                # Otherwise, don't copy it over
            n['port'] = new_port
            new_ports = {}
            for switch, local_port in n['ports'].items():
                if switch in nbunch:
                    new_ports[switch] = local_port
                # Otherwise, don't copy it over
            n['ports'] = new_ports
        # namespace shortcuts for speed
        H_adj=H.adj
        self_adj=self.adj
        # add nodes and edges (undirected method)
        for n in H.node:
            Hnbrs={}
            H_adj[n]=Hnbrs
            for nbr,d in self_adj[n].items():
                if nbr in H_adj:
                    # add both representations of edge: n-nbr and nbr-n
                    Hnbrs[nbr]=d
                    H_adj[nbr][n]=d
        H.graph=self.graph
        # Can't call finalize() here because the node attributes are
        # shared w/ the parent graph.
        H.finalized = True
        return H

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
            self.node[x]['port'] = {}
            for y in self.neighbors(x):
                x_port, y_port = topo.port(x,y)
                self.node[x]['ports'][y] = x_port
                # Support indexing in by port to get neighbor switch/port
                self.node[x]['port'][x_port] = (y, y_port)


        topo.enable_all()
        self.topo = topo
        self.finalized = True

    def nx_graph(self):
        assert self.finalized
        return self.copy()

    def mininet_topo(self):
        assert self.finalized
        return self.topo
