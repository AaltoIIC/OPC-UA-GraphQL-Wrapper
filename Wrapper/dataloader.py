from promise import Promise
from promise.dataloader import DataLoader
from opcua import ua
from Wrapper.opcuautils import getServer
from collections import defaultdict

class AttributeLoader(DataLoader):

    def batch_load_fn(self, attributeKeys):
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
            
            results = server.client.uaclient.read(params)
            
            i = 0
            for info in attributes:
                sortedResults[info[0]] = results[i]
                i += 1

        return Promise.resolve(sortedResults)


class AttributeWriter(DataLoader):

    def batch_load_fn(self, attributeKeys):
        """
        Iterates through the attributeKeys and writes data
        to OPC UA servers based on the attributeKey values.

        Arguments
        attributeKeys:  List of strings with required infromation
                        to write the attributes to OPC UA servers.
        Template:       "Server/NodeId/Attribute/Value/DataType"
        Example:        "TestServer/ns=2;i=2/Value/1234/Int32"

        Results
        sortedResults:  List of status codes returned by the OPC UA server
                        for each attribute.
                        In same order as attributeKeys.
        """

        servers = defaultdict(list)
        i = 0
        for attribute in attributeKeys:
            info = attribute.split("/")
            servers[info[0]].append([i, info[1], info[2], info[3], info[4]])
            i += 1

        """
        For when mutations support this function properly.
        Also remember to edit the schema.py then.
        """
        """ for serverName, attributes in servers.items():
            params = ua.ReadParameters()
            server = getServer(serverName)
            attributePositions = []
            for info in attributes:
                if info[2] == "Value":
                    rv = ua.ReadValueId()
                    if info[1] == "":
                        rv.NodeId = ua.NodeId.from_string(server.rootNodeId)
                    else:
                        rv.NodeId = ua.NodeId.from_string(info[1])
                    rv.AttributeId = ua.AttributeIds.Value
                    params.NodesToRead.append(rv)
                    attributePositions.append(info[0])
            
            if len(attributePositions) > 0:
                results = server.client.uaclient.read(params)
                
                i = 0
                for pos in attributePositions:
                    servers[serverName][pos][4] = results[i].Value.VariantType.name
                    i += 1 """

        sortedResults = [None] * len(attributeKeys)
        for serverName, attributes in servers.items():
            params = ua.WriteParameters()
            server = getServer(serverName)
            for info in attributes:
                attr = ua.WriteValue()
                if info[1] == "":
                    attr.NodeId = ua.NodeId.from_string(server.rootNodeId)
                else:
                    attr.NodeId = ua.NodeId.from_string(info[1])
                attr.AttributeId = ua.AttributeIds[info[2]]
                attr.Value = ua.DataValue(ua.Variant(server.string_to_value(info[3]), ua.VariantType[info[4]]))
                params.NodesToWrite.append(attr)

            results = server.client.uaclient.write(params)
            
            i = 0
            for info in attributes:
                sortedResults[info[0]] = results[i]
                i += 1

        return Promise.resolve(sortedResults)