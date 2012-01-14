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
