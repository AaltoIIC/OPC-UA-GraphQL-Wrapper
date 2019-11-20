"""
Utilities used with views and schemas
Functions for retrieving data from OPC UA server
"""

from opcua import Client, ua
from opcua.common import manage_nodes
from django.conf import settings
import datetime, json

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
    Finds servers based on what's configured in settings.OPC_UA_SERVERS
    Creates OPCUAServer instances and adds them to serverList
    """
    serverList.clear()
    with open("Wrapper/servers.json") as serversFile:
        servers = json.load(serversFile)["servers"]
        for server in servers:
            serverList.append(OPCUAServer(
                name = server.get("name"),
                endPointAddress = server.get("endPointAddress"),
                nameSpaceUri = server.get("nameSpaceUri"),
                browseRootNodeIdentifier = server.get("browseRootNodeIdentifier")
            ))

class OPCUAServer(object):
    """
    Each instance of this class manages a connection to its own OPC UA server.
    Methods are called to get node data from the server.
    """

    def __init__(self, name, endPointAddress, nameSpaceUri=None, browseRootNodeIdentifier=None):
        #---------- Setup -----------
        self.name = name
        self.endPointAddress = endPointAddress
        self.nameSpaceUri = nameSpaceUri
        self.nameSpaceIndex = None
        self.browseRootNodeIdentifier = browseRootNodeIdentifier
        self.rootNodeId = None
        self.client = Client(self.endPointAddress, timeout=2)
        self.sub = None
        self.subscriptions = {}
        #----------------------------

    def check_connection(self):
        """
        Try to get server state (id: i=2259) from server.
        If fails, try to (re)connect
        """

        try:
            self.client.get_node("i=2259").get_value()
            if self.rootNodeId == None:
                self.update_namespace_and_root_node_id()
        except:    
            try:
                self.client.connect()
                self.update_namespace_and_root_node_id()
            except:
                try:
                    self.client.disconnect()
                except:
                    pass
                raise ConnectionError("Connection to " + self.name + " failed/timed out")
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

        rootNodeId = self.rootNodeId
        if (rootNodeId.split(";")[-1].split("=")[0] == "s") and ("." in rootNodeId):
            nodePath = nodeId.lower().split(rootNodeId.lower().split(".")[-1])[-1]
            nodePath = nodePath.replace(".", "", 1).replace(".", "/")
        else:
            nodePath = nodeId.split("=")[-1]

        return nodePath

    def get_node(self, nodeId=""):
        """
        Returns node from nodeId or identifier
        If no namespace given in nodeId,
        assumes the namespace to namespace given for the server in settings.py
        Only the ns set for the server in settings.py is accessible
        """

        self.check_connection()
        if nodeId == "":
            nodeId = self.rootNodeId
        elif self.nameSpaceIndex == None:
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

    def get_node_value_or_subnodes(self, node):
        """
        Returns either node value, or subnodes of node with given path
        """

        # Get node class to determine what to get from node
        nodeClass = node.get_node_class()
        if nodeClass == 2:
            # Get node value
            attribute = node.get_attribute(ua.AttributeIds.Value)
            result = {
                "value": attribute.Value.Value,
                "dataType": attribute.Value.VariantType.name,
                "serverName": self.name
            }
        elif nodeClass == 1:
            # Get and add subnode names to list
            subnodes = []
            for subNode in node.get_children():
                nodeId = subNode.nodeid.to_string()
                subnodes.append({
                    "name": subNode.get_display_name().to_string(),
                    "nodePath": self.get_node_path(nodeId),
                    "nodeId": nodeId,
                    "serverName": self.name
                })
            result = {"objects": subnodes}
        else:
            raise ValueError("Target has unsupported node class type")
        
        return result

    #def get_variable_nodes(self, nodes, variableList=None, depth=0, maxDepth=10):
    def get_variable_nodes(self, node, nodeClass=2, variableList=None, depth=0, maxDepth=10):
        """
        Eats a list of node object(s)
        Recursively finds nodes under given nodes that have given nodeClass
        Returns node objects in a list
        """

        if variableList == None:
            variableList = []

        depth += 1
        if depth >= maxDepth:
            return variableList

        nodes = node.get_children()
        for node in nodes:
            if nodeClass == node.get_attribute(ua.AttributeIds.NodeClass).Value.Value:
                variableList.append(node)
            self.get_variable_nodes(node=node, nodeClass=nodeClass, variableList=variableList, depth=depth)

        """
        nodeClass = node.get_attribute(ua.AttributeIds.NodeClass).Value.Value
        if nodeClass == 1:
            self.get_variable_nodes(nodes=node.get_children(), variableList=variableList, depth=depth)
        elif nodeClass == 2:
            variableList.append(node)
        """

        return variableList

    def get_variable_information(self, variableNodes, variableList=None):

        """
        Eats a list of variable nodes and possible parentNode, which affects the node paths returned
        Returns a dictionary with keys as node paths and values as dictionaries with keys for
        name, value, dataType, sourceTimestamp, statusCode, path, nodeId, serverName
        """

        if variableList == None:
            variableList = []

        for variable in variableNodes:

            nodeId = variable.nodeid.to_string()
            name = variable.get_attribute(ua.AttributeIds.DisplayName).Value.Value.Text
            attribute = variable.get_attribute( ua.AttributeIds.Value )

            variableList.append({
                "name": name,
                "value": attribute.Value.Value,
                "dataType": attribute.Value.VariantType.name,
                "sourceTimestamp": attribute.SourceTimestamp,
                "statusCode": attribute.StatusCode.name,
                "path": self.get_node_path(nodeId),
                "nodeId": nodeId,
                "serverName": self.name
            })

        return variableList

    def get_variables(self, node=None):
        """
        Gets all variables hierarchically below the given node
        Returns a list of node value dictionaries
        """

        if node == None:
            parentNode = self.get_node(self.rootNodeId)
        else:
            parentNode = self.get_node(node)

        variableNodes = self.get_variable_nodes(parentNode)
        varInfo = self.get_variable_information(variableNodes)

        return varInfo
    
    def subscribe_variable(self, nodeId):

        if self.sub == None:
            handler = self
            self.sub = self.client.create_subscription(100, handler)

        node = self.get_node(nodeId)
        if 2 == node.get_attribute(ua.AttributeIds.NodeClass).Value.Value:
            return self.sub.subscribe_data_change(node)
        else:
            return None


    def datachange_notification(self, node, value, data):

        self.subscriptions[node.nodeid.to_string()] = data.monitored_item.Value


    def set_node_value(self, node, value):
        """ Sets value to node """

        # Get node variable's variant type
        variantType = self.variant_type_finder(value, node)
        variant = ua.Variant(value, variantType)
        datavalue = ua.DataValue(variant)
        sourceTimestamp = datetime.datetime.utcnow()
        #datavalue.SourceTimestamp = sourceTimestamp

        # Set node value
        node.set_value(datavalue)
        return {
            "value": value,
            "dataType": variantType,
            "statusCode": "Good",
            "sourceTimestamp": sourceTimestamp
        }


    def set_node_description(self, node, description):
        """
        Sets description attribute to node
        (Requires admin powers)

        Create a DataValue with LocalizedText that includes the description
        and write it to the description attribute of the Node.

        """

        node.set_attribute(ua.AttributeIds.Description, ua.DataValue(ua.LocalizedText(description)))

        return {
            "description": description
        }

    def add_node(self, name, nodeId, parentId, value=None, writable=True):
        """
        Adds a node to OPC UA server
        If value given, adds a variable node, else, a folder node
        Requires server admin powers in server settings.py, for example
        endPointAddress: "opc.tcp://admin@0.0.0.0:4840/freeopcua/server/"
        """

        if self.nameSpaceIndex != None:
            index = self.nameSpaceIndex
        elif nodeId[:3] == "ns=":
            index = nodeId.split("=")[1][0]
        else:
            index = 0
        browseName = f"{index}:{name}"
        parentNode = self.get_node(parentId)
        
        if value == None:
            node = parentNode.add_folder(nodeId, browseName)
            result = {
                "name": node.get_display_name().to_string(),
                "nodeId": node.nodeid.to_string(),
            }
        else:
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
        
            if writable == True:
                node.set_writable()

        return result

    def delete_node(self, nodeId, recursive=True):
        """
        Recursively deletes node and it's subnodes unless recursive=False
        Requires admins
        Doesn't raise errors if deleting is unsuccessful
        """

        node = self.get_node(nodeId)
        result = self.client.delete_nodes([node], recursive)
        return result


    def variant_type_finder(self, value, node):
        valueType = type(value)
        if isinstance(valueType, datetime.datetime):
            variantType = ua.uatypes.VariantType.DateTime
        elif valueType == bool:
            variantType = ua.uatypes.VariantType.Boolean
        elif valueType == str:
            variantType = ua.uatypes.VariantType.String
        elif node.nodeid.to_string().lower().endswith(".watchdog"):
            variantType = ua.uatypes.VariantType.Int16
        elif valueType == int or valueType == float:
            variantType = node.get_data_type_as_variant_type()
        else:
            raise ValueError("Unsupported datatype")
        return variantType
    
    def string_to_value(self, value):
        try:
            if isinstance(value, (datetime.date, datetime.datetime)):
                value = datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%f")
            elif "." in value:
                value = float(value)
            elif value.isdigit():
                value = int(value)
            elif value in ("True", "true"):
                value = True
            elif value in ("False", "false"):
                value = False
        except:
            raise ValueError("Unsupported datatype")
        return value

setupServers()