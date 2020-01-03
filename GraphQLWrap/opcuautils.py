"""
Utilities used with views and schemas
Functions for retrieving data from OPC UA server
"""

from opcua import Client, ua
import os
import datetime
import json
import logging
import socket

# List that will contain all OPCUAServer objects
serverList = []


def getServer(serverName):
    """
    Returns server object that has the corresponding server name
    """
    for server in serverList:
        if server.name == serverName:
            return server
    else:
        raise ValueError("Server not found in server list")


def getServers():
    """
    Returns set up servers
    """
    return serverList


def setupServers():
    """
    Finds servers based on what's configured in servers.json
    Creates OPCUAServer instances and adds them to serverList
    """
    serverList.clear()
    with open(os.path.join(
        os.getcwd(),
        os.path.dirname(__file__),
        "servers.json")
    ) as serversFile:
        servers = json.load(serversFile)["servers"]
        for server in servers:
            serverList.append(OPCUAServer(
                name=server.get("name"),
                endPointAddress=server.get("endPointAddress"),
                nameSpaceUri=server.get("nameSpaceUri"),
                browseRootNodeIdentifier=server.get("browseRootNodeIdentifier")
            ))


class OPCUAServer(object):
    """
    Each instance of this class manages a connection to its own OPC UA server.
    Methods are called to get node data from the server.
    """

    def __init__(
        self, name, endPointAddress,
        nameSpaceUri=None, browseRootNodeIdentifier=None
    ):
        # ---------- Setup -----------
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.endPointAddress = endPointAddress
        self.nameSpaceUri = nameSpaceUri
        self.nameSpaceIndex = None
        self.browseRootNodeIdentifier = browseRootNodeIdentifier
        self.rootNodeId = None
        self.client = Client(self.endPointAddress, timeout=2)
        self.sub = None
        self.subscriptions = {}
        self.connectedToServer = False
        # ----------------------------

    def check_connection(self):
        """
        Try to get server state (id: i=2259) from server.
        If fails, try to (re)connect
        """

        try:
            self.client.get_node("i=2259").get_value()
            self.connectedToServer = True
        except AttributeError as e:
            self.logger.info("Connection to " + self.name + " is not up.")
            self.connectedToServer = False

        if self.connectedToServer is False:
            try:
                self.logger.info("Connecting to " + self.name + ".")
                self.client.connect()
                self.update_namespace_and_root_node_id()
                self.connectedToServer = True
            except socket.timeout:
                self.logger.info(self.name + " socket timed out.")
                try:
                    self.logger.info("Cleaning up session and socket.")
                    self.client.uaclient.disconnect()
                except AttributeError:
                    pass
                self.logger.info("Socket and session cleaned up.")
                raise TimeoutError(self.name + " timed out.")
        return

    def update_namespace_and_root_node_id(self):
        """
        Update rootNodeId and nameSpaceIndex
        If no namespace given, sets root node (id: i=84) as root node
        """

        if self.nameSpaceUri and self.browseRootNodeIdentifier:
            nsArray = self.client.get_namespace_array()
            index = nsArray.index(self.nameSpaceUri)
            if index > 0:
                nodeId = "ns={};".format(index) + self.browseRootNodeIdentifier
            else:
                nodeId = self.browseRootNodeIdentifier
        else:
            nodeId = "i=84"
            index = None

        self.rootNodeId = nodeId
        self.nameSpaceIndex = index
        return

    def get_node_path(self, nodeId):
        """
        Create node path from node id for current server settings
        Attempts to create a path of node from rootNode
        Only works for folderly like string node ids (folders separated by ".")
        """

        identifierType = rootNodeId.split(";")[-1].split("=")[0]
        if (identifierType == "s") and ("." in rootNodeId):
            rootNodeName = self.rootNodeId.lower().split(".")[-1]
            nodePath = nodeId.lower().split(rootNodeName)[-1]
            nodePath = nodePath.replace(".", "", 1).replace(".", "/")
        else:
            nodePath = nodeId.split("=")[-1]

        return nodePath

    def get_node(self, nodeId=""):
        """
        Returns node from nodeId or identifier
        If no namespace given in nodeId,
        assumes the namespace to namespace given for the server in settings.py
        Only the ns set for the server in servers.json is accessible
        """
        if not self.connectedToServer:
            self.check_connection()

        if nodeId == "":
            nodeId = self.rootNodeId
        elif self.nameSpaceIndex is None:
            nodeId = nodeId
        elif nodeId[:3] == "ns=":
            identifier = nodeId.split(";")[-1]
            if self.nameSpaceIndex == 0:
                nodeId = identifier
            else:
                nodeId = f"ns={self.nameSpaceIndex};{identifier}"
        else:
            nodeId = f"ns={self.nameSpaceIndex};{nodeId}"

        return self.client.get_node(nodeId)

    def get_variable_nodes(
        self, node,
        nodeClass=2, variableList=None, depth=0, maxDepth=10
    ):
        """
        Eats a list of node object(s)
        Recursively finds nodes under given nodes that have given nodeClass
        Returns node objects in a list
        """

        if variableList is None:
            variableList = []

        depth += 1
        if depth >= maxDepth:
            return variableList

        nodes = node.get_children()
        params = ua.ReadParameters()
        for node in nodes:
            rv = ua.ReadValueId()
            rv.NodeId = node.nodeid
            rv.AttributeId = ua.AttributeIds.NodeClass
            params.NodesToRead.append(rv)
        results = self.read(params)

        for i in range(len(results)):
            if nodeClass == results[i].Value.Value:
                variableList.append(nodes[i])
            self.get_variable_nodes(
                node=nodes[i],
                nodeClass=nodeClass,
                variableList=variableList,
                depth=depth
            )

        return variableList

    def subscribe_variable(self, nodeId):

        if self.sub is None:
            handler = self
            self.sub = self.client.create_subscription(100, handler)

        node = self.get_node(nodeId)
        if 2 == node.get_attribute(ua.AttributeIds.NodeClass).Value.Value:
            return self.sub.subscribe_data_change(node)
        else:
            return None

    def datachange_notification(self, node, value, data):

        self.subscriptions[node.nodeid.to_string()] = data.monitored_item.Value

    def set_node_attribute(self, nodeId, attribute, value, dataType=None):
        """
        Sets node attribute based on given arguments.
        Giving correct dataType for value and node speeds
        up the write operation.

        Arguments                               Example
        nodeId:     Target nodeId               "ns=2;i=2"
        attribute:  Target attribute of node    "Value"
        value:      Value for the attribute     1234
        dataType:   Data type of value          "Int32"

        Results
        boolean:    Indicates success           True
        """

        attr = ua.WriteValue()

        if nodeId == "":
            attr.NodeId = ua.NodeId.from_string(self.rootNodeId)
        else:
            attr.NodeId = ua.NodeId.from_string(nodeId)

        attr.AttributeId = ua.AttributeIds[attribute]

        if attribute == "Description":
            dataValue = ua.LocalizedText(value)
        else:
            if dataType is None:
                variantType = self.variant_type_finder(value, nodeId)
            else:
                variantType = ua.VariantType[dataType]
            dataValue = ua.Variant(value, variantType)
        attr.Value = ua.DataValue(dataValue)

        params = ua.WriteParameters()
        params.NodesToWrite.append(attr)

        result = self.write(params)
        return result[0].is_good()

    def add_node(self, name, nodeId, parentId, value=None, writable=True):
        """
        Adds a node to OPC UA server
        If value given, adds a variable node, else, a folder node
        Requires server admin powers in server servers.json, for example
        endPointAddress: "opc.tcp://admin@0.0.0.0:4840/freeopcua/server/"
        """

        if self.nameSpaceIndex is not None:
            index = self.nameSpaceIndex
        elif nodeId[:3] == "ns=":
            index = nodeId.split("=")[1][0]
        else:
            index = 0
        browseName = f"{index}:{name}"
        parentNode = self.get_node(parentId)

        if value is None:
            try:
                node = parentNode.add_folder(nodeId, browseName)
            except:
                node = parentNode.add_folder(nodeId, browseName)
            result = {
                "name": node.get_display_name().to_string(),
                "nodeId": node.nodeid.to_string(),
            }
        else:
            try:
                node = parentNode.add_variable(nodeId, browseName, value)
                attribute = node.get_attribute(ua.AttributeIds.Value)
            except:
                self.check_connection()
                node = parentNode.add_variable(nodeId, browseName, value)
                attribute = node.get_attribute(ua.AttributeIds.Value)

            result = {
                "name": node.get_display_name().to_string(),
                "nodeId": node.nodeid.to_string(),
                "value": attribute.Value.Value,
                "dataType": attribute.Value.VariantType.name,
                "sourceTimestamp": attribute.SourceTimestamp,
                "statusCode": attribute.StatusCode.name
            }

            if writable is True:
                node.set_writable()

        return result

    def delete_node(self, nodeId, recursive=True):
        """
        Recursively deletes node and it's subnodes unless recursive=False
        Requires admins
        Doesn't raise errors if deleting is unsuccessful
        """

        node = self.get_node(nodeId)
        try:
            result = self.client.delete_nodes([node], recursive)
        except:
            self.check_connection()
            result = self.client.delete_nodes([node], recursive)
        return result

    def read(self, params):
        """
        Reads from OPC UA server
        params == ua.ReadParameters() that are properly set up
        """

        if not self.connectedToServer:
            self.check_connection()

        try:
            results = self.client.uaclient.read(params)
        except socket.timeout:
            self.logger.info("TIMEOUT!!!")
            self.check_connection()
            results = self.client.uaclient.read(params)

        return results

    def write(self, params):
        """
        Writes to OPC UA server
        params == ua.WriteParameters() that are properly set up
        """

        if not self.connectedToServer:
            self.check_connection()

        try:
            results = self.client.uaclient.write(params)
        except:
            self.check_connection()
            results = self.client.uaclient.write(params)

        return results

    def variant_type_finder(self, value, nodeId):
        valueType = type(value)
        if isinstance(valueType, datetime.datetime):
            variantType = ua.uatypes.VariantType.DateTime
        elif valueType == bool:
            variantType = ua.uatypes.VariantType.Boolean
        elif valueType == str:
            variantType = ua.uatypes.VariantType.String
        elif valueType == int or valueType == float:
            node = self.get_node(nodeId)
            try:
                variantType = node.get_data_type_as_variant_type()
            except:
                self.check_connection()
                variantType = node.get_data_type_as_variant_type()
        else:
            raise ValueError("Unsupported datatype")
        return variantType


setupServers()
