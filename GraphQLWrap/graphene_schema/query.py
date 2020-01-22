from graphene import ObjectType, String, Field, List, Int
from graphene.types.datetime import DateTime
from opcuautils import getServer, getServers
from graphene_schema.scalars import OPCUADataVariable
import graphene_schema.descriptions as d
import asyncio
from graphene_schema.dataloader import AttributeLoader

attribute_loader = AttributeLoader(cache=False)
subscribeVariables = False


class OPCUANode(ObjectType):
    """
    Retrieves specified attributes of this node from OPC UA server.
    Represents an OPC UA node with relevant attributes.

    API only retrieves the specified attribute fields from the OPC UA server.
    """

    name = String(description=d.name)
    description = String(description=d.description)
    node_class = String(description=d.node_class)
    variable = Field(lambda: OPCUAVariable, description=d.variable)
    path = String(description=d.path)
    node_id = String(description=d.node_id)
    sub_nodes = List(lambda: OPCUANode, description=d.sub_nodes)
    variable_sub_nodes = List(
        lambda: OPCUANode, description=d.variable_sub_nodes
    )
    server = String(description=d.server)

    node = None
    server_object = None
    node_key = None

    def set_node(self):
        if self.node is None:
            if self.server_object is None:
                self.server_object = getServer(self.server)
            self.node = self.server_object.get_node(self.node_id)
            self.node_key = self.server + "/" + self.node_id
        return

    """
    Resolvers for the fields above so that only requested
    fields are fetched from the OPC UA server
    """

    async def resolve_name(self, info):
        self.set_node()
        attributeKey = self.node_key + "/DisplayName"
        x = await attribute_loader.load(attributeKey)
        return x[0].Value.Value.Text

    async def resolve_description(self, info):
        self.set_node()
        attributeKey = self.node_key + "/Description"
        x = await attribute_loader.load(attributeKey)
        return x[0].Value.Value.Text

    async def resolve_node_class(self, info):
        self.set_node()
        attributeKey = self.node_key + "/NodeClass"
        x = await attribute_loader.load(attributeKey)
        return x[0].Value.Value.name

    async def resolve_variable(self, info):
        self.set_node()

        if subscribeVariables is True:
            variable = self.server_object.subscriptions.get(self.node_id)
            if variable is not None:
                return OPCUAVariable(
                    value=variable.Value.Value,
                    data_type=variable.Value.VariantType.name,
                    source_timestamp=variable.SourceTimestamp,
                    status_code=variable.StatusCode.name
                )
            else:
                self.server_object.subscribe_variable(self.node_id)
        else:
            attributeKey = self.node_key + "/Value"
            x = await attribute_loader.load(attributeKey)
            return OPCUAVariable(
                value=x[0].Value.Value,
                data_type=x[0].Value.VariantType.name,
                source_timestamp=x[0].SourceTimestamp,
                status_code=x[0].StatusCode.name,
                read_time=x[1]
            )

    def resolve_path(self, info):
        self.set_node()
        return self.server_object.get_node_path(self.node_id)

    def resolve_node_id(self, info):
        return self.node_id

    def resolve_sub_nodes(self, info):
        self.set_node()
        print(self.server_object.name)
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


class OPCUAVariable(ObjectType):
    """
    Represents an OPC UA node DataVariable with relevant attributes
    """

    value = OPCUADataVariable(description=d.value)
    data_type = String(description=d.data_type)
    source_timestamp = DateTime(
        description=d.source_timestamp
    )
    status_code = String(description=d.status_code)
    read_time = Int(description=d.read_time)


class OPCUAServer(ObjectType):
    """
    Information on configured OPC UA servers for this API.
    """

    name = String(description=d.server)
    end_point_address = String(description=d.end_point_address)
    subscriptions = List(String)

    def resolve_subscriptions(self, info):
        server = getServer(self.name)
        return server.subscriptions.keys()


class Query(ObjectType):
    """
    Query for fetching data from OPC UA server nodes.
    """

    # Query options
    node = Field(
        OPCUANode,
        server=String(required=True, description=d.server),
        node_id=String(required=True, description=d.node_id),
        description=OPCUANode.__doc__
    )

    servers = List(
        OPCUAServer,
        description=OPCUAServer.__doc__
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
