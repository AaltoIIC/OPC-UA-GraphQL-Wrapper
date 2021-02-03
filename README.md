# GraphQL API for OPC UA servers

This project wraps OPC UA servers with a GraphQL API so that most of the information model node data is available via the GraphQL API.

Information on GraphQL can be found [here](https://graphql.org/)

[Starlette](https://www.starlette.io/) framework and [graphene](https://github.com/graphql-python/graphene) library are mainly used to build the web interface

Communication with the OPC UA in the backend is done with the help of [python-opcua](https://github.com/FreeOpcUa/python-opcua) library

Built with Python 3.8. Python 3.7 and 3.6 might work as well.

## Contents

- [Introduction](#introduction)
- [Schema](#schema)
    - [Query Schema](#query-schema)
    - [Mutation Schema](#mutation-schema)
- [Example Queries](#example-queries)
- [Installation](#installation)
    - [Setup](#setup)
    - [Running with Docker](#running-with-docker)
    - [Running the API locally](#running-the-api-locally)

<a name="introduction"></a>
## Introduction

This application waits for GraphQL queries with fields for desired OPC UA Node attributes and other information. Queries commonly take arguments to specify which OPC UA server and node the attributes are retrieved from. Based on the query fields, the API transforms queries into a service request that is forwarded to the OPC UA server. The GraphQL API finally returns a response in a GraphQL-like structure.

Mutations are mainly used to change values of nodes on the OPC UA server. Nodes can also be created and OPC UA servers can be setup with their corresponding mutation queries.

The GraphQL API should work with most OPC UA specification compliant OPC UA servers. Some features, however, might not work or require admin access depending on the OPC UA server in question.

<a name="schema"></a>
## Schema
Schema shows you the available resources to query or mutate.
It should give you a good idea on what resources are available.

The "!" behind an input argument (e.g. server: String!) means that the argument is mandatory when retrieveing data from the resource.

If the field type is within "[ ]" (e.g. servers: [OPCUAServer]), it means that the field returns a list with possibly multiple values.

<a name="query-schema"></a>
### Query schema
```javascript
type Query {
    node(
        server: String!
        nodeId: String!
    ): OPCUANode
    servers: [OPCUAServer]
}

type OPCUANode {
    name: String
    description: String
    nodeClass: String
    variable: OPCUAVariable
    path: String
    nodeId: String
    subNodes: [OPCUANode]
    variableSubNodes: [OPCUANode]
    server: String
}

type OPCUAVariable {
    value: OPCUADataVariable
    dataType: String
    sourceTimestamp: DateTime
    statusCode: String
}

type OPCUAServer {
    name: String
    endPointAddress: String
    subscriptions: [String]
}
```

<a name="mutation-schema"></a>
### Mutation schema
Mutations can return "ok" -field in addition to some other situational fields.
Emphasis is, however, on the input argumens seen below.
```javascript
type Mutation {

    setValue(
        nodeId: String!
        server: String!
        value: OPCUADataVariable!
    ): SetNodeValue

    setDescription(
        description: OPCUADataVariable!
        nodeId: String!
        server: String!
    ): SetNodeDescription

    addNode(
        name: String!
        nodeId: String!
        parentId: String!
        server: String!
        value: OPCUADataVariable
        writable: Boolean
    ): AddNode

    deleteNode(
        nodeId: String!
        recursive: Boolean
        server: String!
    ): DeleteNode

    addServer(
        endPointAddress: String!
        name: String!
    ): AddServer

    deleteServer(name: String!): DeleteServer

    clearServerSubcriptions(name: String!): ClearServerSubscriptions
}
```

<a name="example-queries"></a>
## Example queries
Queries are sent with HTTP POST method. The queries below are in the request body in json format.
### Query
```javascript
query {
    node(server: "TestServer", nodeId: "ns=2;i=1234") {
        name
        description
        variable {
            value
            dataType
        }
    }
}
```
### Mutation
```javascript
mutation {
    setValue(server: "TestServer", nodeId: "ns=2;i=1234", value: 5, dataType: "Int32") {
        ok
    }
}
```

### Example read request with python requests
```python
import requests

url = "http://localhost:8000/graphql"
query = """
    query {
        node(server: "TestServer", nodeId: "ns=2;i=1234") {
            name
            description
        }
    }
"""
response = requests.post(url, json={"query": query})
name = response.json()["data"]["node"]["name"]
```

<a name="installation"></a>
## Installation
Clone the repository
```
git clone https://github.com/AaltoIIC/OPC-UA-GraphQL-Wrapper.git
```

<a name="running-with-docker"></a>
### Running with Docker
Docker installation guide for Raspbian on Raspberry Pi can be found [here](https://dev.to/rohansawant/installing-docker-and-docker-compose-on-the-raspberry-pi-in-5-simple-steps-3mgl).

For Windows, the docker install file can be downloaded from [Here](https://docs.docker.com/docker-for-windows/release-notes/). Older versions seem to be possible to download without login.

Navigate to the project folder where the Dockerfile is located with Windows CMD or Raspbian Bash.

Build the docker image with:
```
docker build -t opcqlwrapper .
```

Run a docker container of the image with:
```
docker run -p 80:8000 --name opcqlwrapper opcqlwrapper
```
To run the GraphQL wrapper always on boot run the following command instead:
```
docker run -p 80:8000 --restart always --name opcqlwrapper opcqlwrapper
```

The server can be now accessed either locally at address:
```
http://localhost/
```
or remotely from the host devices ip address such as:
```
http://192.168.0.XX/
```
GraphQL queries are POST to corresponding URLs:
```
http://localhost/graphql        # Local
or
http://192.168.0.XX/graphql     # Remote
```

<a name="running-the-api-locally"></a>
### Running the API locally as development server
Navigate to the project folder with Windows CMD or Raspbian Bash

Install dependencies from with command:

(suggested to use virtual environment)
```
pip install -r requirements.txt
```

From the cloned project's [GraphQLWrap](https://github.com/AaltoIIC/OPC-UA-GraphQL-Wrapper/tree/master/GraphQLWrap) folder run the command:

(Within virtual environment, if used)
```
uvicorn main:app --reload --port 8000
```
Application index is now available at localhost via port 8000. On the index page you can find an OPC UA server browser that can be used to familiarize yourself with the OPC UA server node structures.
```
http://localhost:8000
```
GraphQL queries are sent as HTTP POST to URL:
```
http://localhost:8000/graphql
```
Above URL has also a Graph*i*QL developer interface available if opening the URL with a browser. You can build and test GraphQL queries there.

<a name="setup"></a>
### Setup

You can setup OPC UA server endpoints with GraphQL queries to the GraphQL API (once its running).

Example query:
```javascript
mutation {
    addServer(
        name: "TestServer"
        endPointAddress: "opc.tcp://localhost:4840/freeopcua/server/"
    ) { ok }
}
```
### More resources
This wrapper was developed as part of Master's thesis:
Hietala, J. 2020. Real-time two-way data transfer with a Digital Twin via web interface. Master's thesis, Aalto University, Espoo, Finland. Available from: http://urn.fi/URN:NBN:fi:aalto-202003222557

In addition, a conference paper about the wrapper has been published:
Hietala, J., Ala-Laurinaho, R., Autiosalo J. and Laaki, H., GraphQL Interface for OPC UA, 2020 IEEE Conference on Industrial Cyberphysical Systems (ICPS), Tampere, Finland, 2020, pp. 149-155, https://doi.org/10.1109/ICPS48405.2020.9274754 .
Open access manuscript available at https://research.aalto.fi/en/publications/graphql-interface-for-opc-ua



