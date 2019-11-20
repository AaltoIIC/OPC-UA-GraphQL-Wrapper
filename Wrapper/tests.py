from django.test import TestCase
#from django.test import Client
import time, json
from string import Template

import graphene
from opcua import Client
from Wrapper.schema import Query
from django.conf import settings

class SimpleTest(TestCase):

    def setUp(self):
        self.server = "TestServer"
        self.endPointAddress = opc.tcp://localhost:4840/freeopcua/server/"
        self.opcUa = Client(self.endPointAddress)
        self.graphQl = graphene.Schema(query=Query)
        self.nodeId = ""

    def opcUaServerTest(self):
        start = time.time()
        node = self.opcUa.get_node(self.nodeId)
        value = node.get_value()
        opcUaTime = int((time.time() - start)*1000)
        print("Direct request time: " + opcUaTime + "ms")
        self.assertEqual(type(value), int)

    def apiTest(self):
        start = time.time()
        query = Template("""{
            node(server: "$server", nodeId: "$nodeId") {
                variable {
                    value
                }
            }
        }""").substitute(server=self.server, nodeId=self.nodeId)
        value = self.graphQl.Query(json.dumps(query))
        apiTime = int((time.time() - start)*1000)
        print("API request time: " + apiTime + "ms")
        self.assertEqual(type(value), int)