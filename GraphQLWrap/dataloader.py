from aiodataloader import DataLoader
import asyncio

from opcua import ua
from opcuautils import getServer
from collections import defaultdict


class AttributeLoader(DataLoader):

    async def batch_load_fn(self, attributeKeys):
        """
        Iterates through the attributeKeys and retrieves data
        from OPC UA servers based on the attributeKey values.

        Arguments
        attributeKeys:  List of strings with required infromation
                        to retrieve the attributes from OPC UA servers.
        Template:       "Server/NodeId/Attribute"
        Example:        "TestServer/ns=2;i=2/Value"

        Results
        sortedResults:  List of values returned by the OPC UA server
                        for each attribute.
                        In same order as attributeKeys.
        """

        servers = defaultdict(list)
        i = 0
        for attribute in attributeKeys:
            info = attribute.split("/")
            servers[info[0]].append([i, info[1], info[2]])
            i += 1

        sortedResults = [None] * len(attributeKeys)
        for serverName, attributes in servers.items():
            params = ua.ReadParameters()
            server = getServer(serverName)
            for info in attributes:
                rv = ua.ReadValueId()
                if info[1] == "":
                    rv.NodeId = ua.NodeId.from_string(server.rootNodeId)
                else:
                    rv.NodeId = ua.NodeId.from_string(info[1])
                rv.AttributeId = ua.AttributeIds[info[2]]
                params.NodesToRead.append(rv)

            results, latency = await server.read(params)

            i = 0
            for info in attributes:
                sortedResults[info[0]] = [results[i], latency]
                i += 1

        return sortedResults
