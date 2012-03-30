import nxtopo
import slicing
import netcore as nc

def get_slices():
    p_topo = nxtopo.NXTopo()
    server_hub = 1
    p_topo.add_switch(server_hub)

    client_host1 = 3
    p_topo.add_host(client_host1)
    p_topo.add_link(server_hub, client_host1)
    client_host2 = 4
    p_topo.add_host(client_host2)
    p_topo.add_link(server_hub, client_host2)

    server_hosts = [6,7,8,9]
    for server_host in server_hosts:
        p_topo.add_host(server_host)
        p_topo.add_link(server_hub, server_host)

    p_topo.finalize()

    slices = []
    for i in range(1,3):
        if i == 1:
            client_host = client_host1
        else:
            client_host = client_host2
        
        l_client_host = client_host + (i * 10)
        l_server_hub = server_hub + (i * 10)
        l_topo = nxtopo.NXTopo()
        l_topo.add_switch(l_server_hub)
        s_map = {l_server_hub:server_hub}
        
        l_topo.add_host(l_client_host)
        l_topo.add_link(l_server_hub, l_client_host)

        for server_host in server_hosts:
            l_server_host = server_host + (1 * 10)
            l_topo.add_host(l_server_host)
            l_topo.add_link(l_server_hub, l_server_host)
        
        l_topo.finalize()

        p_map = dict()

        client_key = (l_server_hub, 
                      l_topo.node[l_server_hub]['ports'][l_client_host])
        client_value = (server_hub, 
                      p_topo.node[server_hub]['ports'][client_host])
        p_map[client_key] = client_value

        if i == 1:
            mac = 0x00B0D086BBF7
        else:
            mac = 0x080027F40A6B

        edge_policies = {client_key : nc.Header('srcmac', mac)}

        for server_host in server_hosts:
            l_server_host = server_host + (1 * 10)
            key = (l_server_hub, 
                   l_topo.node[l_server_hub]['ports'][l_server_host])
            vlu =  (server_hub, 
                      p_topo.node[server_hub]['ports'][server_host])
            p_map[key] = vlu
            
            edge_policies[key] =  nc.Header('destmac', mac)

        slices.append(slicing.Slice(l_topo, p_topo, s_map, 
                                    p_map, edge_policies))
 
    return slices

get_slices()
