import unittest
import datetime
import time
from starlette.testclient import TestClient
from string import Template
from main import app
from opcua import Server

testServerName = "Terver"
testServerEndpoint = "opc.tcp://localhost:4840/freeopcua/server/"

queryNodeTemplate = Template("""
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
queryAddServerTemplate = Template("""
    mutation {
        addServer(name: "$name", endPointAddress: "$endPointAddress") {
            ok
        }
    }
""")
queryDeleteServerTemplate = Template("""
    mutation {
        deleteServer(name: "$name") {
            ok
        }
    }
""")


class TestReadAttribute(unittest.TestCase):

    def test_variable_node_attributes(self):
        query = queryNodeTemplate.substitute({
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
        assert variable.get("value") == 1.1
        assert variable.get("dataType") == "Double"
        timestamp = datetime.datetime.strptime(
            variable.get("sourceTimestamp"),
            "%Y-%m-%dT%H:%M:%S.%f"s
        )
        assert isinstance(timestamp, datetime.datetime)
        assert variable.get("statusCode") == "Good"
        assert node.get("nodeId") == "ns=2;i=2"
        assert node.get("subNodes") == []
        assert node.get("server") == testServerName

    def test_add_server(self):
        query = queryAddServerTemplate.substitute({
            "name": "Hoppah",
            "endPointAddress": testServerEndpoint
        })

        response = client.post("/graphql/", json={"query": query})
        assert response.status_code == 200
        response = response.json()
        server = response["data"]["addServer"]
        assert server.get("ok") is True

        response = client.post("/graphql/", json={"query": query})
        """ with self.assertRaises():
            response = client.post("/graphql/", json={"query": query}) """
        assert response.status_code == 400
        response = response.json()
        server = response["data"]["addServer"]
        assert server is None
        errors = response.get("errors")
        assert errors is not None
        assert errors[0].get("message") == "Server with that name \\
            is already configured"
        assert errors[0].get("path")[0] == "addServer"

    def test_delete_server(self):
        query = queryDeleteServerTemplate.substitute({
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


if __name__ == "__main__":
    client = TestClient(app)

    # Set up OPC UA server and populate namespace
    server = Server()
    server.set_endpoint(testServerEndpoint)

    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    objects = server.get_objects_node()

    obj = objects.add_object(idx, "ObjectNode")
    var = obj.add_variable(idx, "VariableNode", 1.1)
    var.set_writable()

    try:
        print("Starting OPC UA server")
        server.start()
        query = queryAddServerTemplate.substitute({
            "name": testServerName,
            "endPointAddress": testServerEndpoint
        })
        client.post("/graphql/", json={"query": query})
        unittest.main()
    finally:
        query = queryDeleteServerTemplate.substitute({
            "name": testServerName
        })
        client.post("/graphql/", json={"query": query})
        print("Stopping OPC UA server")
        server.stop()
        print("Finished")
