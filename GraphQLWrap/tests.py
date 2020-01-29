import unittest
import datetime
import time
import logging
import os
from starlette.testclient import TestClient
from string import Template
from main import app
from opcua import Server

testServerName = "Terver"
testServerEndpoint = "opc.tcp://localhost:4840/freeopcua/server/"
testServerNameAdmin = "TerverAdmin"
testServerEndpointAdmin = "opc.tcp://admin@localhost:4840/freeopcua/server"


class TestReadAttribute(unittest.TestCase):

    def setUp(self):
        self.queryNode = Template("""
            query {
                node(server: "$server", nodeId: "$nodeId") {
                    name
                    description
                    nodeClass
                    variable {
                        value
                        dataType
                        sourceTimestamp
                        statusCode
                    }
                    nodeId
                    subNodes {
                        name
                    }
                    server
                }
            }
        """)
        self.queryGetVariables = Template("""
            query {
                node(server: "$server", nodeId: "$nodeId") {
                    variableSubNodes { variable { value } }
                }
            }
        """)

    def test_variable_node_attributes(self):
        query = self.queryNode.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        response = response.json()

        node = response["data"]["node"]
        assert node.get("name") == "VariableNode"
        assert node.get("description") == "VariableNode"
        assert node.get("nodeClass") == "Variable"
        assert node.get("variable") is not None
        variable = node["variable"]
        assert variable.get("value") == 0
        assert variable.get("dataType") == "Int64"
        timestamp = datetime.datetime.strptime(
            variable.get("sourceTimestamp"),
            "%Y-%m-%dT%H:%M:%S.%f"
        )
        assert isinstance(timestamp, datetime.datetime)
        assert variable.get("statusCode") == "Good"
        assert node.get("nodeId") == "ns=2;i=2"
        assert isinstance(node.get("subNodes"), list)
        assert node.get("server") == testServerName

    def test_get_variable_sub_nodes(self):
        query = self.queryGetVariables.substitute({
            "nodeId": "ns=2;i=1",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        nodes = response.json()["data"]["node"].get("variableSubNodes")
        assert nodes is not None
        assert len(nodes) == 2
        for node in nodes:
            assert node.get("variable") is not None
            assert isinstance(node["variable"].get("value"), int)


class TestGetServers(unittest.TestCase):

    def setUp(self):
        self.queryServers = """
            query {
                servers {
                    name
                    endPointAddress
                }
            }
        """

    def test_get_servers(self):
        query = self.queryServers
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        servers = response.json()["data"].get("servers")
        assert len(servers) >= 2
        for server in servers:
            assert isinstance(server.get("name"), str)
            assert isinstance(server.get("endPointAddress"), str)


class TestServerConfig(unittest.TestCase):

    def setUp(self):
        self.queryAddServer = Template("""
            mutation {
                addServer(name: "$name", endPointAddress: "$endPointAddress") {
                    ok
                }
            }
        """)
        self.queryDeleteServer = Template("""
            mutation {
                deleteServer(name: "$name") {
                    ok
                }
            }
        """)

    def test_add_server(self):
        query = self.queryAddServer.substitute({
            "name": "Hoppah",
            "endPointAddress": testServerEndpoint
        })

        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        response = response.json()
        server = response["data"]["addServer"]
        assert server.get("ok") is True

        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 400
        response = response.json()
        server = response["data"]["addServer"]
        assert server is None
        errors = response.get("errors")
        assert errors is not None
        expected = "Server with that name is already configured"
        assert errors[0].get("message") == expected
        assert errors[0].get("path")[0] == "addServer"

    def test_delete_server(self):
        query = self.queryDeleteServer.substitute({
            "name": "Hoppah"
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        response = response.json()
        server = response["data"]["deleteServer"]
        assert server.get("ok") is True

        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 400
        response = response.json()
        server = response["data"]["deleteServer"]
        assert server is None
        errors = response.get("errors")
        assert errors is not None
        assert errors[0].get("message") == "Server not found in server list"
        assert errors[0].get("path")[0] == "deleteServer"


class TestSetValueAttribute(unittest.TestCase):

    def setUp(self):
        self.querySetValue = Template("""
            mutation {
                setValue(
                    server: "$server",
                    nodeId: "$nodeId",
                    value: $value,
                    dataType: "$dataType"
                ) {
                    ok
                    writeTime
                }
            }
        """)
        self.queryGetValue = Template("""
            query {
                node(server: "$server", nodeId: "$nodeId") {
                    variable {
                        value
                        dataType
                        sourceTimestamp
                        statusCode
                    }
                }
            }
        """)
        self.querySetValueWODataType = Template("""
            mutation {
                setValue(
                    server: "$server",
                    nodeId: "$nodeId",
                    value: $value
                ) {
                    ok
                    writeTime
                }
            }
        """)

    def test_set_value_int(self):

        value = 123
        dataType = "Int32"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": value,
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") == value
        assert node.get("dataType") == dataType

    def test_set_value_double(self):

        value = 1.2345678
        dataType = "Double"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": value,
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") == value
        assert node.get("dataType") == dataType

    def test_set_value_datetime(self):

        value = datetime.datetime.now().isoformat()
        dataType = "DateTime"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": '"' + value + '"',
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") == value
        assert node.get("dataType") == dataType

    def test_set_value_boolean(self):

        value = "true"
        dataType = "Boolean"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": value,
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") is True
        assert node.get("dataType") == dataType

    def test_set_value_string(self):

        value = "Pappapapa"
        dataType = "String"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": '"' + value + '"',
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert isinstance(node.get("value"), str)
        assert node.get("value") == value
        assert node.get("dataType") == dataType

    def test_set_value_wrong_datatype(self):

        value = 123.4
        dataType = "Int32"

        query = self.querySetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": value,
            "dataType": dataType
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 400
        setValue = response.json()["data"]["setValue"]
        assert setValue is None
        error = response.json()["errors"][0]
        assert isinstance(error["message"], str)
        assert error["path"][0] == "setValue"

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") != value
        assert node.get("dataType") != dataType

    def test_set_value_without_datatype(self):

        value = 1234

        query = self.querySetValueWODataType.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "value": value,
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True
        assert isinstance(setValue.get("writeTime"), int)

        query = self.queryGetValue.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]["variable"]
        assert node.get("value") == value
        assert node.get("dataType") == "Int64"


class TestSetDescriptionAttribute(unittest.TestCase):

    def setUp(self):
        self.querySetDescription = Template("""
            mutation {
                setDescription(
                    server: "$server",
                    nodeId: "$nodeId",
                    description: "$description"
                ) { ok }
            }
        """)
        self.queryGetDescription = Template("""
            query {
                node(server: "$server", nodeId: "$nodeId", ) {
                    description
                }
            }
        """)

    def test_set_description(self):

        description = "Super node. Maxima admin."

        query = self.querySetDescription.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerNameAdmin,
            "description": description
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setDescription = response.json()["data"]["setDescription"]
        assert setDescription.get("ok") is True

        query = self.queryGetDescription.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]
        assert node.get("description") == description

    def test_set_description_no_admin(self):

        description = "Super node maxima"

        query = self.querySetDescription.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName,
            "description": description
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setDescription = response.json()["data"]["setDescription"]
        assert setDescription.get("ok") is False

        query = self.queryGetDescription.substitute({
            "nodeId": "ns=2;i=2",
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["node"]
        assert node.get("description") != description


class TestNodeManagement(unittest.TestCase):

    def setUp(self):
        self.queryAddVariableNode = Template("""
            mutation {
                addNode(
                    server: "$server",
                    name: "$name",
                    nodeId: "$nodeId",
                    parentId: "$parentId",
                    value: $value,
                    writable: $writable
                ) {
                    name
                    variable {
                        value
                        dataType
                        sourceTimestamp
                        statusCode
                    }
                    nodeId
                    server
                    writable
                    ok
                }
            }
        """)
        self.querySetValue = Template("""
            mutation {
                setValue(
                    server: "$server",
                    nodeId: "$nodeId",
                    value: $value
                    ) { ok }
            }
        """)
        self.queryGetChild = Template("""
            query {
                node(server: "$server", nodeId: "$nodeId") {
                    subNodes {
                        nodeId
                        variable {
                            value
                            dataType
                        }
                    }
                }
            }
        """)
        self.queryAddFolderNode = Template("""
            mutation {
                addNode(
                    server: "$server",
                    name: "$name",
                    nodeId: "$nodeId",
                    parentId: "$parentId"
                ) {
                    name
                    variable { value }
                    nodeId
                    server
                    writable
                    ok
                }
            }
        """)
        self.queryDeleteNode = Template("""
            mutation {
                deleteNode(server: "$server", nodeId: "$nodeId") {
                    ok
                }
            }
        """)

    def test_writable_variable_node(self):

        nodeId = "ns=2;i=123"
        parentId = "ns=2;i=2"
        name = "TestNode"
        value = 12345
        writable = "true"

        query = self.queryAddVariableNode.substitute({
            "nodeId": nodeId,
            "parentId": parentId,
            "server": testServerNameAdmin,
            "name": name,
            "value": value,
            "writable": writable
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["addNode"]
        assert node.get("ok") is True
        assert node.get("writable") is True
        assert node.get("name") == name
        assert node.get("nodeId") == nodeId
        assert node.get("server") == testServerNameAdmin
        assert node.get("variable") is not None
        variable = node.get("variable")
        assert variable.get("value") == value
        assert variable.get("dataType") == "Int64"

        value = 54321

        query = self.querySetValue.substitute({
            "server": testServerName,
            "nodeId": nodeId,
            "value": value
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is True

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNode = response.json()["data"]["node"].get("subNodes")[0]
        assert subNode is not None
        assert subNode.get("nodeId") == nodeId
        assert subNode.get("variable").get("value") == value
        assert subNode.get("variable").get("dataType") == "Int64"

        query = self.queryDeleteNode.substitute({
            "server": testServerNameAdmin,
            "nodeId": nodeId
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        deleteNode = response.json()["data"]["deleteNode"]
        assert deleteNode.get("ok") is True

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNodes = response.json()["data"]["node"].get("subNodes")
        assert subNodes == []

    def test_non_writable_variable_node(self):

        nodeId = "ns=2;i=123"
        parentId = "ns=2;i=2"
        name = "TestNodeNonWritable"
        value1 = 12345
        writable = "false"

        query = self.queryAddVariableNode.substitute({
            "nodeId": nodeId,
            "parentId": parentId,
            "server": testServerNameAdmin,
            "name": name,
            "value": value1,
            "writable": writable
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["addNode"]
        assert node.get("ok") is True
        assert node.get("writable") is False
        assert node.get("name") == name
        assert node.get("nodeId") == nodeId
        assert node.get("server") == testServerNameAdmin
        assert node.get("variable") is not None
        variable = node.get("variable")
        assert variable.get("value") == value1
        assert variable.get("dataType") == "Int64"

        value2 = 54321

        query = self.querySetValue.substitute({
            "server": testServerName,
            "nodeId": nodeId,
            "value": value2
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        setValue = response.json()["data"]["setValue"]
        assert setValue.get("ok") is False

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNode = response.json()["data"]["node"].get("subNodes")[0]
        assert subNode is not None
        assert subNode.get("nodeId") == nodeId
        assert subNode.get("variable").get("value") == value1
        assert subNode.get("variable").get("dataType") == "Int64"

        query = self.queryDeleteNode.substitute({
            "server": testServerNameAdmin,
            "nodeId": nodeId
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        deleteNode = response.json()["data"]["deleteNode"]
        assert deleteNode.get("ok") is True

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNodes = response.json()["data"]["node"].get("subNodes")
        assert subNodes == []

    def test_delete_nonexistent_node(self):

        nodeId = "ns=2;i=123"

        query = self.queryDeleteNode.substitute({
            "server": testServerNameAdmin,
            "nodeId": nodeId
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 400
        deleteNode = response.json()["data"]["deleteNode"]
        assert deleteNode is None
        errors = response.json().get("errors")
        assert errors is not None
        assert errors[0].get("path")[0] == "deleteNode"

    def test_add_folder_node(self):

        nodeId = "ns=2;i=123"
        parentId = "ns=2;i=2"
        name = "TestNode"

        query = self.queryAddFolderNode.substitute({
            "nodeId": nodeId,
            "parentId": parentId,
            "server": testServerNameAdmin,
            "name": name,
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        node = response.json()["data"]["addNode"]
        assert node.get("ok") is True
        assert node.get("name") == name
        assert node.get("nodeId") == nodeId
        assert node.get("server") == testServerNameAdmin
        assert node.get("variable") is None

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNode = response.json()["data"]["node"].get("subNodes")[0]
        assert subNode is not None
        assert subNode.get("nodeId") == nodeId

        query = self.queryDeleteNode.substitute({
            "server": testServerNameAdmin,
            "nodeId": nodeId
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        deleteNode = response.json()["data"]["deleteNode"]
        assert deleteNode.get("ok") is True

        query = self.queryGetChild.substitute({
            "nodeId": parentId,
            "server": testServerName
        })
        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        subNodes = response.json()["data"]["node"].get("subNodes")
        assert subNodes == []


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)

    print("\nCreating test client")
    client = TestClient(app)

    # Set up OPC UA server and populate namespace
    server = Server()
    server.set_endpoint(testServerEndpoint)

    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    objects = server.get_objects_node()

    obj = objects.add_object(idx, "ObjectNode")
    var = obj.add_variable(idx, "VariableNode", 0)
    var.set_writable()
    obj.add_variable(idx, "VariableNodeNonWritable", 0)

    queryAddServer = Template("""
        mutation {
            addServer(name: "$name", endPointAddress: "$endPointAddress") {
                ok
            }
        }
    """)
    queryDeleteServer = Template("""
        mutation {
            deleteServer(name: "$name") {
                ok
            }
        }
    """)

    try:
        print("Starting OPC UA server")
        server.start()

        print("Setting up test OPC UA servers")
        query = queryAddServer.substitute({
            "name": testServerName,
            "endPointAddress": testServerEndpoint,
        })
        client.post("/graphql/", json={"query": query})
        query = queryAddServer.substitute({
            "name": testServerNameAdmin,
            "endPointAddress": testServerEndpointAdmin
        })
        client.post("/graphql/", json={"query": query})

        print("\nRunning tests")
        unittest.main(verbosity=2, exit=False)
    finally:
        print("\nDeleting test OPC UA server setups")
        query = queryDeleteServer.substitute({
            "name": testServerName
        })
        client.post("/graphql/", json={"query": query})
        query = queryDeleteServer.substitute({
            "name": testServerNameAdmin
        })
        client.post("/graphql/", json={"query": query})

        print("Stopping OPC UA server")
        server.stop()

        print("Finished")
        logging.disable(logging.NOTSET)

        os._exit(0)  # Was forced to use this to exit
