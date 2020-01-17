import requests
import time
from datetime import datetime
from string import Template
from opcua import Client, ua

tests = [1, 5, 25]  # Nodes per query
queriesPerTest = 50  # Queries per test

""" GraphQL_API_URL = "http://192.168.0.31:8000/graphql/"
OPC_UA_Endpoint = "opc.tcp://192.168.0.32:4840/testserver/" """

GraphQL_API_URL = "http://localhost:8000/graphql/"
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


def fast_query_gen(n):
    # n = n*2
    query = "query { "
    for i in range(1, n + 1):
        node = "vn" + str(i) \
            + ': node(server: "PrfTestServer", nodeId: "ns=2;i=' \
            + str(i + 1) + '") { nodeId }'
        query = query + node
    query = query + "}"
    return query


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
            + """
                variable {
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
            + ': setValue(server: "PrfTestServer", nodeId: "ns=2;i=' \
            + str(i + 1) \
            + '", value: ' \
            + str(i) \
            + ', dataType: "Int64") { writeTime }'
        query = query + node
    query = query + "}"
    return query


def read_node_id(session, query):
    start = time.time_ns()
    response = session.post(GraphQL_API_URL, json={"query": query})
    latency = round((time.time_ns() - start) / 1000000)
    return latency


def read_node_variable(session, query):
    # time.sleep(0.2)
    start = time.time_ns()
    response = session.post(GraphQL_API_URL, json={"query": query})
    latency = round((time.time_ns() - start) / 1000000)
    readTime = response.json()["data"]["vn1"]["variable"]["readTime"]
    return latency, round(readTime / 1000000)


def write_node_variable(session, query):
    # time.sleep(0.2)
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

        # Fast test
        for test in tests:
            query = fast_query_gen(test)
            tot = 0
            for i in range(queriesPerTest):
                latency = read_node_id(session, query)
                tot += latency
            avgLat = tot/queriesPerTest
            size = round(len(query.encode('utf-16-le'))/1000)
            print("Fast " + str(test) + ":")
            print("  Size: " + str(size) + " kb")
            print("    Latency: " + str(avgLat) + " ms")

        # Read tests
        for test in tests:
            query = read_query_gen(test)
            tot = {"lat": 0, "opc": 0}
            for i in range(queriesPerTest):
                latency, readTime = read_node_variable(session, query)
                tot["lat"] += latency
                tot["opc"] += readTime
            avgLat = tot["lat"]/queriesPerTest
            avgOpc = tot["opc"]/queriesPerTest
            size = round(len(query.encode('utf-16-le'))/1000)
            print("Read " + str(test) + ":")
            print("  Size: " + str(size) + " kb")
            print("    Latency: " + str(avgLat) + " ms")
            print("      Read time: " + str(avgOpc) + " ms")

        # Write tests
        for test in tests:
            query = write_query_gen(test)
            tot = {"lat": 0, "opc": 0}
            for i in range(queriesPerTest):
                latency, writeTime = write_node_variable(session, query)
                tot["lat"] += latency
                tot["opc"] += writeTime
            avgLat = tot["lat"]/queriesPerTest
            avgOpc = tot["opc"]/queriesPerTest
            size = round(len(query.encode('utf-16-le'))/1000)
            print("Write " + str(test) + ":")
            print("  Size: " + str(size) + " kb")
            print("    Latency: " + str(avgLat) + " ms")
            print("      Write one time: " + str(avgOpc) + " ms")

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
        rv.AttributeId = ua.AttributeIds.Value
        params.NodesToRead.append(rv)
    start = time.time_ns()
    session.uaclient.read(params)
    latency = round((time.time_ns() - start) / 1000000)
    return latency


def write_node_variable_opcua(session, n):
    params = ua.WriteParameters()
    for i in range(1, n + 1):
        rv = ua.WriteValue()
        rv.NodeId = ua.NodeId.from_string("ns=2;i=" + str(i + 1))
        rv.AttributeId = ua.AttributeIds.Value
        variantType = ua.VariantType["Int64"]
        rv.Value = ua.DataValue(ua.Variant(i, variantType))
        params.NodesToWrite.append(rv)
    start = time.time_ns()
    session.uaclient.write(params)
    latency = round((time.time_ns() - start) / 1000000)
    return latency


with Client(OPC_UA_Endpoint) as session:

    # OPC UA read tests
    tot = 0
    for test in tests:
        for i in range(queriesPerTest):
            latency = read_node_variable_opcua(session, test)
            tot += latency
        print("Read OPC UA " + str(test) + ":")
        print("    ReadTime: " + str(tot/queriesPerTest))

    # OPC UA write tests
    tot = 0
    for test in tests:
        for i in range(queriesPerTest):
            latency = write_node_variable_opcua(session, test)
            tot += latency
        print("Write OPC UA " + str(test) + ":")
        print("    WriteTime: " + str(tot/queriesPerTest))
