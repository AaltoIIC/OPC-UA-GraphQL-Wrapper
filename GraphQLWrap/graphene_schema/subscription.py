"""
Subscriptions do not work before some changes are made to
the graphene subscriptions library.
"""

""" class SubscribeVariable(graphene.ObjectType):
    Simple GraphQL subscription.

    # Subscription payload.
    #server = graphene.String(description=d.server)
    node_id = graphene.String(description=d.node_id)
    variable = graphene.Field(lambda: OPCUAVariable, description=d.variable)

    class Arguments:
        That is how subscription arguments are defined.
        server = graphene.String(required=True, description=d.server)
        node_id = graphene.String(required=True, description=d.node_id)

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
