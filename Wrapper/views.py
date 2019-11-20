from django.http import JsonResponse
from django.shortcuts import render
from Wrapper.opcuautils import getServer, serverList
import json


# Landing page with browsable node structure
# Returns servers setup in settings.py for browsing
# API documentation can also be found on index page
def index(request):

    result = []
    for server in serverList:
        result.append({"name": server.name})

    if len(result) <= 0:
        result = {
            "error": {
                "code": 404,
                "message": "No OPC UA servers are setup in the API settings"
            }
        }
        return JsonResponse(result, status=result["error"]["code"])

    context = {
        "url": request.build_absolute_uri('?'),
        "data": result
    }

    return render(request, "index.html", context)


# Forward request and respond back to client with json data
def responder(request, server, nodeId=""):

    result = request_handler(request, server, nodeId)

    if "error" in result:
        return JsonResponse(result, status=result["error"]["code"])

    try:
        return JsonResponse({"data": result})
    except Exception as e:
        result = {
            "error": {
                "code": 500,
                "message": str(e)
            }
        }
        return JsonResponse(result, status=result["error"]["code"])


# Gets node with given path from server
# GET: Reads value or returns subnodes of node with given path
# PUT: Sets value of node with given path
def request_handler(request, serverName, nodeId=""):

    try:
        # Get server
        server = getServer(serverName)
        # Get node
        node = server.get_node(nodeId)
        
        # Call correct function based on request method
        if request.method == "GET":

            result = server.get_node_value_or_subnodes(node)
        
        elif request.method == "PUT":

            # Check that a value can be found in request data
            body = json.loads(request.body)
            if "value" in body["data"]:
                result = server.set_node_value(node, body["data"]["value"])
            else:
                raise ValueError("No value found in request data")
        
        else:

            raise ValueError("Unsupported method. Use either GET or PUT")
    
    # Include possible error message to response
    except Exception as e:
        result = {
            "error": {
                "code": 400,
                "message": str(e)
            }
        }
        if isinstance(e, ConnectionError):
            result["code"] = 504

    return result
