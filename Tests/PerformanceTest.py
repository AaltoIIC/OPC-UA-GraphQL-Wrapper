import requests
import time
from datetime import datetime
from string import Template
from opcua import Server

tests = [1, 5, 25, 100]
queriesPerTest = 10

GraphQL_API_URL = "http://127.0.0.1:8000/graphql/"
OPC_UA_Endpoint = "opc.tcp://localhost:4840/freeopcua/server/"

queryAddServer = Template("""
    mutation {
        addServer(name: "$name", endPointAddress: "$endPointAddress") {ok}
    }
""")
queryDeleteServer = Template("""
    mutation {
        deleteServer(name: "$name") {ok}
    }
""")


def read_query_gen(n):
    query = "query { "
    for i in range(1, n + 1):
        node = "vn" + str(i) \
            + ': node(server: "PrfTestServer", nodeId: "ns=2;i=' \
            + str(i + 1) + '") {' \
            + """variable {
                    value
                    dataType
                    sourceTimestamp
                    statusCode
                }
            }"""
        query = query + node
    query = query + "}"
    return query


def read_node_variable(session, query):
    # time.sleep(0.05)
    start = time.time_ns()
    response = session.post(GraphQL_API_URL, json={"query": query})
    latency = round((time.time_ns() - start) / 1000000)
    return latency


with requests.Session() as session:

    # Set up test server address to GraphQL API
    addQuery = queryAddServer.substitute({
        "name": "PrfTestServer",
        "endPointAddress": OPC_UA_Endpoint
    })
    session.post(GraphQL_API_URL, json={"query": addQuery})

    # Initialize connections between GraphQL API and OPC UA server
    read_node_variable(session, read_query_gen(1))

    # Read tests
    for test in tests:
        query = read_query_gen(test)
        tot = 0
        for i in range(queriesPerTest):
            latency = read_node_variable(session, query)
            print("Read " + str(test) + " latency: " + str(latency))
            tot += latency
        avg = tot/queriesPerTest
        print("Read " + str(test) + " average latency: " + str(avg))

    # Remove set up test server from GraphQL API
    deleteQuery = queryDeleteServer.substitute({
        "name": "PrfTestServer"
    })
    session.post(GraphQL_API_URL, json={"query": deleteQuery})
