""" import sys
sys.path.insert(0, "..") """
import time
from opcua import Server


if __name__ == "__main__":

    # setup our server
    server = Server()
    server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")

    # setup our own namespace, not really necessary but should as spec
    uri = "http://examples.freeopcua.github.io"
    idx = server.register_namespace(uri)

    # get Objects node, this is where we should put our nodes
    objects = server.get_objects_node()

    # populating our address space
    obj = objects.add_object(idx, "ObjectNode")

    for i in range(1, 101):
        bname = "VariableNode" + str(i)
        obj.add_variable(idx, bname, i)
    # var = obj.add_variable(idx, "VariableNode", 1.0)
    # var.set_writable()    # Set MyVariable to be writable by clients

    # starting!
    server.start()

    try:
        # count = 0
        while True:
            time.sleep(1)
            """ count += 0.1
            var.set_value(count) """
    finally:
        # close connection, remove subcsriptions, etc
        server.stop()
