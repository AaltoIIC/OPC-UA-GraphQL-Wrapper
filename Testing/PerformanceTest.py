import opcua
from opcua import ua
import requests

url = "http://localhost:4840/freeopcua/server/"
nodeId = "ns=2;i=2"
#attribute = "Value"

rv = ua.ReadValueId()
rv.NodeId = ua.NodeId.from_string(nodeId)
rv.AttributeId = ua.AttributeIds.Value

params = ua.ReadParameters()
params.NodesToRead.append(rv)

result = requests.post(url, data={"ReadParams": params})
print(result)