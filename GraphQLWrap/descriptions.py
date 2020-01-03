# Field descriptions for the GraphQL Schema

name = "Display name"
description = "Node description"
node_class = "Node class"
variable = "Variable that contains value related attribute fields"
path = "Attempts to parse node id for a path to parent node"
node_id = "Node id for of the node on OPC UA server"
sub_nodes = "Returns nodes hierarchically below this node"
variable_sub_nodes = """
    Recursively find all variable sub nodes.
    Returns specified fields of found variable nodes.
    Takes a while to fetch, request this field only if necessary!
    """

value = "Node value"
data_type = "Data type of the value"
source_timestamp = "Source timestamp for the value"
status_code = "Status code for the value quality"


server = "Server name (only used in this API). Unique within this API."
end_point_address = "URL to the OPC UA server"

parent_id = "Node id of parent node"
writable = "States if node is writable by clients"
recursive = "If operation should be completed recursively"
ok = "True if operation was successful"

writeTime = """
    Time it took to write the value to the OPC UA
    server from the GraphQL API server
    """
