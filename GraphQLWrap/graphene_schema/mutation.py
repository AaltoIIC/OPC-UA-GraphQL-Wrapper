from graphql import GraphQLError
from graphene import ObjectType, Mutation, Boolean, Int, String, Field
from opcuautils import getServer, getServers, setupServers
from graphene_schema.query import OPCUAVariable
from graphene_schema.scalars import OPCUADataVariable
import graphene_schema.descriptions as d
import os
import asyncio
import json


class SetNodeValue(Mutation):
    """
    Set value of an OPC UA variable node.

    Value has to be of correct dataType for the target variable node.
    Including correct dataType for the target value speeds up
    """

    ok = Boolean(description=d.ok)
    writeTime = Int(description=d.write_time)

    class Arguments:
        server = String(required=True, description=d.server)
        node_id = String(required=True, description=d.node_id)
        value = OPCUADataVariable(required=True, description=d.value)
        dataType = String(description=d.data_type)

    async def mutate(self, info, server, node_id, value, dataType=None):

        server = getServer(server)
        ok, writeTime = await server.set_node_attribute(
            node_id, "Value", value, dataType
        )
        return SetNodeValue(ok=ok, writeTime=writeTime)


class SetNodeDescription(Mutation):
    """
    Set description of an OPC UA node.
    Requires admin access.

    Description must be a string.
    """

    ok = Boolean(description=d.ok)

    class Arguments:
        server = String(required=True, description=d.server)
        node_id = String(required=True, description=d.node_id)
        description = OPCUADataVariable(
            required=True,
            description=d.description
        )

    def mutate(self, info, server, node_id, description):

        server = getServer(server)
        ok = server.set_node_attribute(node_id, "Description", description)
        return SetNodeDescription(ok=ok)


class AddNode(Mutation):
    """
    Adds node to to OPC UA server address space.

    If value argument is given, adds a variable node to OPC UA server.
    Otherwise, adds a folder type node.

    Writable is true by default.

    Can return specified fields of added node.
    """

    class Arguments:
        server = String(required=True, description=d.server)
        name = String(required=True, description=d.name)
        node_id = String(required=True, description=d.node_id)
        parent_id = String(required=True, description=d.parent_id)
        value = OPCUADataVariable(required=False, description=d.value)
        writable = Boolean(required=False, description=d.writable)

    name = String(description=d.name)
    variable = Field(lambda: OPCUAVariable, description=d.variable)
    node_id = String(description=d.node_id)
    server = String(description=d.server)
    writable = Boolean(description=d.writable)
    ok = Boolean(description=d.ok)

    def mutate(
        self, info, server, name, node_id, parent_id,
        value=None, writable=True
    ):

        server = getServer(server)
        result = server.add_node(name, node_id, parent_id, value, writable)

        if result.get("value") is not None:
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
            server=server.name,
            writable=writable,
            ok=True
        )


class DeleteNode(Mutation):
    """
    Deletes node from OPC UA address space.

    If recursive is true, delete node and its sub nodes from
    OPC UA server (default = true, recommended).
    If recursive is false, sub nodes of deleted node can be
    left floating without references in the address space.
    """

    class Arguments:
        server = String(required=True, description=d.server)
        node_id = String(required=True, description=d.node_id)
        recursive = Boolean(required=False, description=d.recursive)

    ok = Boolean(description=d.ok)

    def mutate(self, info, server, node_id, recursive=True):

        server = getServer(server)
        ok = server.delete_node(node_id, recursive)
        return DeleteNode(ok=ok)


class AddServer(Mutation):
    """
    Configure a new server to be accessed by the GraphQL API.
    """

    class Arguments:
        name = String(required=True, description=d.server)
        endPointAddress = String(
            required=True,
            description=d.end_point_address
        )

    ok = Boolean(description=d.ok)

    def mutate(self, info, name, endPointAddress):

        ok = False
        try:
            servers = getServer(name)
            raise GraphQLError("Server with that name is already configured")
        except ValueError:
            pass

        with open(
            os.path.join(os.getcwd(), "servers.json"),
            "r+"
        ) as serversFile:
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
        return AddServer(ok=ok)


class DeleteServer(Mutation):
    """
    Delete a server from API's accessable servers.
    """

    class Arguments:
        name = String(required=True, description=d.server)

    ok = Boolean(description=d.ok)

    def mutate(self, info, name):

        ok = False
        server = getServer(name)
        with open(
            os.path.join(os.getcwd(), "servers.json"),
            "r+"
        ) as serversFile:
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


class ClearServerSubscriptions(Mutation):
    """
    Clear automatically created subscriptions
    between the GraphQL API and OPC UA server.
    """

    class Arguments:
        name = String(required=True, description=d.server)

    ok = Boolean(description=d.ok)

    def mutate(self, info, name):

        ok = False
        server = getServer(name)
        try:
            server.sub.delete()
        except Exception as e:
            print(type(e).__name__)
            print(str(e))
            pass
        server.sub = None
        server.subscriptions.clear()
        ok = True

        return ClearServerSubscriptions(ok=ok)


class Mutation(ObjectType):
    """ Queries for modifying data on OPC UA server """

    set_value = SetNodeValue.Field(description=SetNodeValue.__doc__)
    set_description = SetNodeDescription.Field(
        description=SetNodeDescription.__doc__
    )
    add_node = AddNode.Field(description=AddNode.__doc__)
    delete_node = DeleteNode.Field(description=DeleteNode.__doc__)
    add_server = AddServer.Field(description=AddServer.__doc__)
    delete_server = DeleteServer.Field(description=DeleteServer.__doc__)
    clear_server_subcriptions = ClearServerSubscriptions.Field(
        description=ClearServerSubscriptions.__doc__
    )
