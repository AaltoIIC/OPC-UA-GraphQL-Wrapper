import requests
import time
from datetime import datetime
from string import Template
from opcua import Client

tests = [1, 5, 25, 100]
queriesPerTest = 10

GraphQL_API_URL = "http://127.0.0.1:8000/graphql/"
OPC_UA_Endpoint = "opc.tcp://localhost:4840/testserver/"

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
    query = query + """vn1:
        node(server: "PrfTestServer", nodeId: "ns=2;i=2") {
            variable {
                value
                dataType
                sourceTimestamp
                statusCode
                readTime
            }
        }"""
    for i in range(2, n + 1):
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

def write_query_gen(n):
    query = "mutation { "
    for i in range(1, n + 1):
        node = "vn" + str(i) \
            + ': node(server: "PrfTestServer", nodeId: "ns=2;i=' \
            + str(i + 1)
            + '", value: ' \
            + i + ') { writeTime }'
        query = query + node
    query = query + "}"
    return query

def read_node_variable(session, query):
    # time.sleep(0.05)
    start = time.time_ns()
    response = session.post(GraphQL_API_URL, json={"query": query})
    latency = round((time.time_ns() - start) / 1000000)
    readTime = response.json()["data"]["vn1"]["variable"]["readTime"]
    return latency, round(readTime / 1000000)


def write_node_variable(session, query):
    start = time.time_ns()
    response = session.post(GraphQL_API_URL, json={"query": query})
    latency = round((time.time_ns() - start) / 1000000)
    writeTime = response.json()["data"]["vn1"]["writeTime"]
    return latency, round(writeTime / 1000000)


with requests.Session() as session:
    try:
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
            tot = {"lat": 0, "opc": 0}
            for i in range(queriesPerTest):
                latency, readTime = read_node_variable(session, query)
                print(
                    "Read " + str(test) + " latency: " + str(latency) +
                    " Read Time: " + str(readTime)
                )
                tot["lat"] += latency
                tot["opc"] += readTime
            avgLat = tot["lat"]/queriesPerTest
            avgOpc = tot["opc"]/queriesPerTest
            print(
                "Read " + str(test) + " average latency: " + str(avgLat) +
                "\nAverage read time: " + str(avgOpc)
            )

        # Write tests
        for test in tests:
            query = write_query_gen(test)
            tot = {"lat": 0, "opc": 0}
            for i in range(queriesPerTest):
                latency, writeTime = write_node_variable(session, query)
                print(
                    "Write " + str(test) + " latency: " + str(latency) +
                    " Write Time: " + str(readTime)
                )
                tot["lat"] += latency
                tot["opc"] += writeTime
            avgLat = tot["lat"]/queriesPerTest
            avgOpc = tot["opc"]/queriesPerTest
            print(
                "Write " + str(test) + " average latency: " + str(avgLat) +
                "\nAverage write time: " + str(avgOpc)
            )

    finally:
        # Remove set up test server from GraphQL API
        deleteQuery = queryDeleteServer.substitute({
            "name": "PrfTestServer"
        })
        session.post(GraphQL_API_URL, json={"query": deleteQuery})


def read_node_variable_opcua(session, n):
    params = ua.ReadParameters()
    for i in range(1, n + 1):
        rv = ua.ReadValueId()
        rv.NodeId = ua.NodeId.from_string("ns=2;i=" + str(i + 1))
        rv.AttributeId = ua.AttributeIds[Value]
        params.NodesToRead.append(rv)
    start = time.time_ns()
    session.read(params)
    latency = round((time.time_ns() - start) / 1000000)
    return latency


def write_node_variable_opcua(session, n):
    params = ua.WriteParameters()
    for i in range(1, n + 1):
        rv = ua.WriteValue()
        rv.NodeId = ua.NodeId.from_string("ns=2;i=" + str(i + 1))
        rv.AttributeId = ua.AttributeIds[Value]
        params.NodesToRead.append(rv)
    start = time.time_ns()
    session.read(params)
    latency = round((time.time_ns() - start) / 1000000)
    return latency


with Client(OPC_UA_Endpoint) as session:

    # OPC UA read tests
    tot = 0
    for test in tests:
        latency = read_node_variable_opcua(session, test)
        print("Read " + str(test) + " latency: " + str(latency))
        tot += latency
    print("Read " + str(test) + " average latency: " + str(tot))

    # OPC UA write tests
    tot = 0
    for test in tests:
        latency = write_node_variable_opcua(session, test)
        print("Write " + str(test) + " latency: " + str(latency))
        tot += latency
    print("Write " + str(test) + " average latency: " + str(tot))
