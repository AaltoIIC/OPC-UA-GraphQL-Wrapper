import graphene
from graphql.language import ast
from graphql.execution.executor import collect_fields

from opcua import ua
from Wrapper.opcuautils import getServer, getServers, setupServers

import datetime, asyncio, json

useDataloader = True
if useDataloader:
    from Wrapper.dataloader import AttributeLoader, AttributeWriter
    attribute_loader = AttributeLoader(cache=False)
    attribute_writer = AttributeWriter(cache=False)

subscribeVariables = False

# ------------ Field Descriptions ------------

d_name = "Display name"
d_description = "Node description"
d_node_class = "Node class"
d_variable = "Variable that contains value related attribute fields"
d_path = "Attempts to parse node id for a path to parent node"
d_node_id = "Node id for of the node on OPC UA server"
d_sub_nodes = "Returns nodes hierarchically below this node"
d_variable_sub_nodes = """
    Recursively find all variable sub nodes.
    Returns specified fields of found variable nodes.
    Takes a while to fetch, request this field only if necessary!
    """

d_value = "Node value"
d_data_type = "Data type of the value"
d_source_timestamp = "Source timestamp for the value"
d_status_code = "Status code for the value quality"

d_server = "Server name (only used in this API). Unique within this API."
d_end_point_address = "URL to the OPC UA server"

d_parent_id = "Node id of parent node"
d_writable = "States if node is writable by clients"
d_recursive = "If operation should be completed recursively"
d_ok = "True if operation was successful"

class OPCUADataVariable(graphene.types.Scalar):
    """
    Custom scalar type that accepts all common data types.

    Formats datetime objects into JSONifiable format.
    Supports multiple different value types
    (int, float, datetime, string(without '.'), boolean).
    """

    class Meta():
        description = __doc__
    
    # Serialization for returned values
    @staticmethod
    def serialize(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        return value

    # Parsing for inputted value
    @staticmethod
    def parse_literal(node):
        value = node.value
        try:
            if isinstance(node, ast.StringValue):
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
            pass
        return value

    @staticmethod
    def parse_value(value):
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
            pass
        return value

# ---------------- Query things ----------------

class OPCUANode(graphene.ObjectType):
    """
    Represents an OPC UA node with relevant attributes.

    API only retrieves the specified attribute fields from the OPC UA server.
    """

    name = graphene.String(description=d_name)
    description = graphene.String(description=d_description)
    node_class = graphene.String(description=d_node_class)
    variable = graphene.Field(lambda: OPCUAVariable, description=d_variable)
    path = graphene.String(description=d_path)
    node_id = graphene.String(description=d_node_id)
    sub_nodes = graphene.List(lambda: OPCUANode, description=d_sub_nodes)
    variable_sub_nodes = graphene.List(lambda: OPCUANode, description=d_variable_sub_nodes)
    server = graphene.String(description=d_server)

    node = None
    server_object = None
    node_key = None

    def set_node(self):
        if self.node == None:
            if self.server_object == None:
                self.server_object = getServer(self.server)
            self.node = self.server_object.get_node(self.node_id)
            self.node_key = self.server + "/" + self.node_id
        return

    """
    Resolvers for the fields above so that only requested
    fields are fetched from the OPC UA server
    """
    @staticmethod
    def resolve_name(self, info):
        self.set_node()
        if useDataloader:
            attributeKey = self.node_key + "/DisplayName"
            return attribute_loader.load(attributeKey).then(lambda x : x.Value.Value.Text)
        else:
            return self.node.get_attribute(ua.AttributeIds.DisplayName).Value.Value.Text

    def resolve_description(self, info):
        self.set_node()
        if useDataloader:
            attributeKey = self.node_key + "/Description"
            return attribute_loader.load(attributeKey).then(lambda x : x.Value.Value.Text)
        else:
            return self.node.get_attribute(ua.AttributeIds.Description).Value.Value.Text

    def resolve_node_class(self, info):
        self.set_node()
        if useDataloader:
            attributeKey = self.node_key + "/NodeClass"
            return attribute_loader.load(attributeKey).then(lambda x : x.Value.Value.name)
        else:
            return self.node.get_attribute(ua.AttributeIds.NodeClass).Value.Value.name

    def resolve_variable(self, info):
        self.set_node()

        if subscribeVariables == True:
            variable = self.server_object.subscriptions.get(self.node_id)
            if variable != None:
                return OPCUAVariable(
                    value=variable.Value.Value,
                    data_type = variable.Value.VariantType.name,
                    source_timestamp = variable.SourceTimestamp,
                    status_code = variable.StatusCode.name
                )
            else:
                self.server_object.subscribe_variable(self.node_id)

        if useDataloader:
            attributeKey = self.node_key + "/Value"
            return attribute_loader.load(attributeKey).then(lambda x : 
                OPCUAVariable(
                    value = x.Value.Value,
                    data_type = x.Value.VariantType.name,
                    source_timestamp = x.SourceTimestamp,
                    status_code = x.StatusCode.name
                )
            )

        else:
            variable = self.node.get_attribute(ua.AttributeIds.Value)
            return OPCUAVariable(
                value=variable.Value.Value,
                data_type = variable.Value.VariantType.name,
                source_timestamp = variable.SourceTimestamp,
                status_code = variable.StatusCode.name
            )

    def resolve_path(self, info):
        self.set_node()
        return self.server_object.get_node_path(self.node_id)

    def resolve_node_id(self, info):
        return self.node_id

    def resolve_sub_nodes(self, info):
        self.set_node()
        subNodes = []
        for subNode in self.node.get_children():
            subNodes.append(OPCUANode(
                    server=self.server,
                    node_id=subNode.nodeid.to_string()
                ))
        return subNodes
    
    def resolve_variable_sub_nodes(self, info):
        self.set_node()
        variableNodes = self.server_object.get_variable_nodes(self.node)
        nodes = []
        for variable in variableNodes:
            node_id = variable.nodeid.to_string()
            nodes.append(OPCUANode(
                server=self.server,
                node_id=node_id
            ))
        return nodes

    def resolve_server(self, info):
        return self.server

class OPCUAVariable(graphene.ObjectType):
    """
    Represents an OPC UA node DataVariable with relevant attributes
    """

    value = OPCUADataVariable(description=d_value)
    data_type = graphene.String(description=d_data_type)
    source_timestamp = graphene.types.datetime.DateTime(description=d_source_timestamp)
    status_code = graphene.String(description=d_status_code)

class OPCUAServer(graphene.ObjectType):
    """
    Information on configured OPC UA servers for this API.
    """

    name = graphene.String(description=d_server)
    end_point_address = graphene.String(description=d_end_point_address)
    subscriptions = graphene.List(graphene.String)

    def resolve_subscriptions(self, info):
        server = getServer(self.name)
        return server.subscriptions.keys()

class Query(graphene.ObjectType):
    """
    Query for fetching data from OPC UA server nodes.
    """

    # Query options
    node = graphene.Field(
        OPCUANode,
        server=graphene.String(required=True, description=d_server),
        node_id=graphene.String(required=True, description=d_node_id),
        description="Get attributes of an OPC UA node in addition to some potentially helpful fields"
    )

    servers = graphene.List(
        OPCUAServer,
        description="Get configured servers' info"
    )

    def resolve_node(self, info, server, node_id):
        """
        Get specified attributes of an OPC UA node.
        """
        server = getServer(server)
        return OPCUANode(
            server=server.name,
            node_id=node_id
        )

    def resolve_servers(self, info):
        """
        Get set up servers info
        """

        servers = getServers()
        result = []
        for server in servers:
            result.append(OPCUAServer(
                name=server.name,
                end_point_address=server.endPointAddress
            ))

        return result

# ---------------- Mutate things ----------------

class SetNodeValue(graphene.Mutation):
    """
    Set value of an OPC UA variable node.

    Value has to be of correct dataType for the target variable node.
    """

    ok = graphene.Boolean(description=d_ok)

    class Arguments:
        server = graphene.String(required=True, description=d_server)
        node_id = graphene.String(required=True, description=d_node_id)
        value = OPCUADataVariable(required=True, description=d_value)
    
    def mutate(self, info, server, node_id, value):
        """
        Sets value of node with given value
        Returns set value, dataType and ok=True if successful
        """

        server = getServer(server)
        if useDataloader:
            node = server.get_node(node_id)
            variantType = server.variant_type_finder(value, node)
            attributeKey = server.name + "/" + node_id + "/Value/" + str(value) + "/" + variantType.name

            return attribute_writer.load(attributeKey).then(lambda x : 
                SetNodeValue(ok = x.is_good())
            )
        else:
            node = server.get_node(node_id)
            server.set_node_value(node, value)

            return SetNodeValue(ok = True)

class SetNodeDescription(graphene.Mutation):
    """
    Set description of an OPC UA node.

    Description must be a string.
    """

    description = graphene.String(description=d_description)
    ok = graphene.Boolean(description=d_ok)

    class Arguments:
        server = graphene.String(required=True, description=d_server)
        node_id = graphene.String(required=True, description=d_node_id)
        description = OPCUADataVariable(required=True, description=d_description)

    def mutate(self, info, server, node_id, description):

        server = getServer(server)
        
        if useDataloader:
            attributeKey = server.name + "/" + node_id + "/Description/" + str(description) + "/String"

            return attribute_writer.load(attributeKey).then(lambda x : 
                SetNodeDescription(ok = x.is_good())
            )
        else:
            node = server.get_node(node_id)
            result = server.set_node_description(node, description)

            return SetNodeDescription(
                description=result["description"],
                ok=True
            )

class AddNode(graphene.Mutation):
    """
    Adds node to to OPC UA server address space.

    If value argument is given, adds a variable node to OPC UA server.
    Otherwise, adds a folder type node.

    Writable is true by default.

    Can return specified fields of added node.
    """

    class Arguments:
        server = graphene.String(required=True, description=d_server)
        name = graphene.String(required=True, description=d_name)
        node_id = graphene.String(required=True, description=d_node_id)
        parent_id = graphene.String(required=True, description=d_parent_id)
        value = OPCUADataVariable(required=False, description=d_value)
        writable = graphene.Boolean(required=False, description=d_writable)

    name = graphene.String(description=d_name)
    variable = graphene.Field(lambda: OPCUAVariable, description=d_variable)
    node_id = graphene.String(description=d_node_id)
    server = graphene.String(description=d_server)
    writable = graphene.Boolean(description=d_writable)
    ok = graphene.Boolean(description=d_ok)

    def mutate(self, info, server, name, node_id, parent_id, value=None, writable=True):

        server = getServer(server)
        result = server.add_node(name, node_id, parent_id, value, writable)

        if result.get("value") != None:
            variable = OPCUAVariable(
                value=result.get("value"),
                data_type=result.get("dataType"),
                source_timestamp=result.get("sourceTimestamp"),
                status_code=result.get("statusCode"),
            )
        else:
            variable = None

        return AddNode(
            name=result["name"],
            node_id=result["nodeId"],
            variable=variable,
            server=server,
            writable=writable,
            ok=True
        )

class DeleteNode(graphene.Mutation):
    """
    Deletes node from OPC UA address space.

    If recursive is true, delete node and its sub nodes from
    OPC UA server (default = true, recommended).
    If recursive is false, sub nodes of deleted node can be
    left floating without references in the address space.
    """

    class Arguments:
        server = graphene.String(required=True, description=d_server)
        node_id = graphene.String(required=True, description=d_node_id)
        recursive = graphene.Boolean(required=False, description=d_recursive)

    ok = graphene.Boolean(description=d_ok)
    
    def mutate(self, info, server, node_id, recursive=True):

        server = getServer(server)
        server.delete_node(node_id, recursive)
        try:
            server.get_node(node_id)
            ok = False
        except:
            ok = True

        if ok == False:
            raise Warning("Could not delete node. Perhaps no access rights?")

        return DeleteNode(ok=ok)

class AddServer(graphene.Mutation):
    """
    Configure a new server to be accessed by the GraphQL API.
    """

    class Arguments:
        name = graphene.String(required=True, description=d_server)
        endPointAddress = graphene.String(required=True, description=d_end_point_address)

    name = graphene.String(description=d_server)
    end_point_address = graphene.String(description=d_end_point_address)
    ok = graphene.Boolean(description=d_ok)

    def mutate(self, info, name, endPointAddress):

        ok = False
        serverExists = True
        try:
            server = getServer(name)
        except ValueError:
            serverExists = False
            
        if serverExists:
            raise ValueError("Server with that name is already configured")

        with open("Wrapper/servers.json", "r+") as serversFile:
            servers = json.load(serversFile)
            servers["servers"].append({
                "name": name,
                "endPointAddress": endPointAddress
            })
            serversFile.seek(0)
            json.dump(servers, serversFile, indent=4)
            serversFile.truncate()
            ok = True
        
        setupServers()
        
        return AddServer(
            name=name,
            end_point_address=endPointAddress,
            ok=ok
        )

class DeleteServer(graphene.Mutation):
    """
    Delete a server from API's accessable servers.
    """

    class Arguments:
        name = graphene.String(required=True, description=d_server)

    ok = graphene.Boolean(description=d_ok)

    def mutate(self, info, name):
        
        ok = False
        server = getServer(name)
        with open("Wrapper/servers.json", "r+") as serversFile:
            servers = json.load(serversFile)
            i = 0
            for server in servers["servers"]:
                if server["name"] == name:
                    del servers["servers"][i]
                    ok = True
                    break
                i += 1
            serversFile.seek(0)
            json.dump(servers, serversFile, indent=4)
            serversFile.truncate()
        
        setupServers()
        return AddServer(ok=ok)

class ClearServerSubscriptions(graphene.Mutation):
    """
    Clear automatically created subscriptions between the GraphQL API and OPC UA server.
    """

    class Arguments:
        name = graphene.String(required=True, description=d_server)

    ok = graphene.Boolean(description=d_ok)

    def mutate(self, info, name):
        
        ok = False
        server = getServer(name)
        try:
            server.sub.delete()
        except:
            pass
        server.sub = None
        server.subscriptions.clear()
        ok = True

        return ClearServerSubscriptions(ok=ok)

class Mutation(graphene.ObjectType):
    """ Queries for modifying data on OPC UA server """

    set_value = SetNodeValue.Field(description=SetNodeValue.__doc__)
    set_description = SetNodeDescription.Field(description=SetNodeDescription.__doc__)
    add_node = AddNode.Field(description=AddNode.__doc__)
    delete_node = DeleteNode.Field(description=DeleteNode.__doc__)
    add_server = AddServer.Field(description=AddServer.__doc__)
    delete_server = DeleteServer.Field(description=DeleteServer.__doc__)
    clear_server_subcriptions = ClearServerSubscriptions.Field(description=ClearServerSubscriptions.__doc__)

# --------------- Subscribe things ---------------
"""
Subscriptions do not work before some changes are made to
the graphene subscriptions library.
"""
""" class SubscribeVariable(graphene.ObjectType):
    Simple GraphQL subscription.

    # Subscription payload.
    #server = graphene.String(description=d_server)
    node_id = graphene.String(description=d_node_id)
    variable = graphene.Field(lambda: OPCUAVariable, description=d_variable)

    class Arguments:
        That is how subscription arguments are defined.
        server = graphene.String(required=True, description=d_server)
        node_id = graphene.String(required=True, description=d_node_id)

    @staticmethod
    def subscribe(self, info, server, node_id):
        Called when user subscribes.

        subGroup = server + "/" + node_id
        server = getServer(server)

        sub = server.client.create_subscription(500, self)

        node = server.get_node(node_id)
        subGroup = node
        sub.subscribe_data_change(node)

        # Return the list of subscription group names.
        return [subGroup]

    @staticmethod
    def publish(payload, info, server, node_id, variable):
        Called to notify the client.

        node_id = payload["node_id"]
        variable = payload["variable"]

        return SubscribeVariable(
            #server=server,
            node_id=node_id,
            variable=OPCUAVariable(
                value=variable.Value.Value,
                data_type=variable.Value.VariantType.name,
                source_timestamp=variable.SourceTimestamp,
                status_code=variable.StatusCode.name
            )
        )
    
    @classmethod
    def datachange_notification(self, node, variable, data):
        pass
        SubscribeVariable.broadcast(
            #group=server + "/" + node_id,
            group=node,
            payload={
                "node_id": node.nodeid,
                "variable": variable
            }
        )

class Subscription(graphene.ObjectType):

    count_seconds = graphene.Int(up_to=graphene.Int())

    async def resolve_count_seconds(self, info, up_to=5):
        for i in range(up_to):
            yield i
            #await asyncio.sleep(1.)
        yield up_to

        return None


    #subscribe_variable = SubscribeVariable.Field() """

schema = graphene.Schema(
    query=Query,
    mutation=Mutation
    #subscription=Subscription
)