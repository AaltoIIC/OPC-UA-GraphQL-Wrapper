import csv
import numpy
import plotly.graph_objects as go

tests = [1, 5, 10]  # Nodes per query
queriesPerTest = 50  # Queries per test

with open('test_data.csv', newline='') as csvfile:
    data = list(csv.reader(csvfile))

# Refine data to only required data points
del data[0]
refinedData = []
i = 0
while i < len(data):
    if data[i][4] == "TCP":
        i += 1
        continue
    else:
        refinedData.append([data[i][1], data[i][4], data[i][5], data[i][6]])
    i += 1
data = refinedData
refinedData = []
i = 0
length = len(data)
while i < length:
    if data[i][3] == "Hello message":
        refinedData.pop()
        refinedData.pop()
        i += 8
        continue
    else:
        refinedData.append(data[i])
        i += 1
data = refinedData
for i in range(len(data)):
    data[i][0] = int(float(data[i][0])*1000)

# Calculate average times for each request type

avgTimes = {}

# Fast
for nodes in tests:
    fastPoints = 2*queriesPerTest
    fastData = data[:fastPoints]
    i, tot, count = (0, 0, 0)
    while i < len(fastData):
        tot += fastData[i+1][0] - fastData[i][0]
        count += 1
        i += 2
    avgTimes["Fast " + str(nodes)] = tot / count
    data = data[fastPoints:]

# Read
for nodes in tests:
    readPoints = (4*queriesPerTest)
    readData = data[:readPoints]
    i, C1Tot, C2Tot, C4Tot, count = (0, 0, 0, 0, 0)
    while i < len(readData):
        C1Tot += readData[i+1][0] - readData[i][0]
        C2Tot += readData[i+2][0] - readData[i+1][0]
        C4Tot += readData[i+3][0] - readData[i+2][0]
        count += 1
        i += 4
    avgTimes["Read " + str(nodes)] = {}
    avgTimes["Read " + str(nodes)]["C1"] = C1Tot / count
    avgTimes["Read " + str(nodes)]["C2"] = C2Tot / count
    avgTimes["Read " + str(nodes)]["C4"] = C4Tot / count
    data = data[readPoints:]

# Write
for nodes in tests:
    writePoints = (2 + 2*nodes) * queriesPerTest
    writeData = data[:writePoints]
    i, C1Tot, C2Tot, C3Tot, C4Tot, count, c = (0, 0, 0, 0, 0, 0, 0)
    while i < len(writeData)-1:
        C1 = writeData[i+1][0] - writeData[i][0]
        C1Tot += writeData[i+1][0] - writeData[i][0]
        i += 1
        while writeData[i][1] == "OpcUa":
            C2Tot += writeData[i+1][0] - writeData[i][0]
            i += 1
            if writeData[i+1][1] == "OpcUa":
                C3Tot += writeData[i+1][0] - writeData[i][0]
            i += 1
        C4Tot += writeData[i][0] - writeData[i-1][0]
        i += 1
        count += 1
    avgTimes["Write " + str(nodes)] = {}
    avgTimes["Write " + str(nodes)]["C1"] = C1Tot / count
    avgTimes["Write " + str(nodes)]["C2"] = C2Tot / count
    avgTimes["Write " + str(nodes)]["C3"] = C3Tot / count
    avgTimes["Write " + str(nodes)]["C4"] = C4Tot / count
    data = data[writePoints:]

# Read OPC
for nodes in tests:
    opcReadPoints = 2*queriesPerTest
    opcReadData = data[:opcReadPoints]
    i, tot, count = (0, 0, 0)
    while i < len(opcReadData):
        tot += opcReadData[i+1][0] - opcReadData[i][0]
        count += 1
        i += 2
    avgTimes["ReadOPC " + str(nodes)] = tot / count
    data = data[opcReadPoints:]

# Write OPC
for nodes in tests:
    opcWritePoints = 2*queriesPerTest
    opcWriteData = data[:opcWritePoints]
    i, tot, count = (0, 0, 0)
    while i < len(opcWriteData):
        tot += opcWriteData[i+1][0] - opcWriteData[i][0]
        count += 1
        i += 2
    avgTimes["WriteOPC " + str(nodes)] = tot / count
    data = data[opcWritePoints:]

bars = []
""" for nodes in tests:
    del avgTimes["Fast " + str(nodes)] """
for key in avgTimes.keys():
    bars.append(key)

data = []
readList1, writeList1 = ([], [])
readList2, writeList2 = ([], [])
writeList3 = []
readList4, writeList4 = ([], [])
fastList = []
rOpcList, wOpcList, emptyList = ([], [], [0, 0, 0])
for nodes in tests:
    nodes = str(nodes)
    fastList.append(avgTimes["Fast " + nodes])
    readList1.append(avgTimes["Read " + nodes]["C1"])
    readList2.append(avgTimes["Read " + nodes]["C2"])
    readList4.append(avgTimes["Read " + nodes]["C4"])
    writeList1.append(avgTimes["Write " + nodes]["C1"])
    writeList2.append(avgTimes["Write " + nodes]["C2"])
    writeList3.append(avgTimes["Write " + nodes]["C3"])
    writeList4.append(avgTimes["Write " + nodes]["C4"])
    rOpcList.append(avgTimes["ReadOPC " + nodes])
    wOpcList.append(avgTimes["WriteOPC " + nodes])

yData = []
yData.extend(fastList + emptyList * 4)
data.append(go.Bar(
    name="Wrapper: Fast fetch (no OPC UA server)",
    x=bars,
    y=yData
))

yData = []
yData.extend(emptyList + readList1 + writeList1 + emptyList * 2)
data.append(go.Bar(
    name="Wrapper: Receiving/processing query (te1)",
    x=bars,
    y=yData,
    marker_color="rgb(150,150,225)"
))

yData = []
yData.extend(emptyList + readList2 + writeList2 + rOpcList + wOpcList)
data.append(go.Bar(
    name="OPC UA: Reading/Writing data (te2)",
    x=bars,
    y=yData,
    marker_color="rgb(100,100,100)"
))

yData = []
yData.extend(emptyList + emptyList + writeList3 + emptyList * 2)
data.append(go.Bar(
    name="Wrapper: Building subsequent write requests (te2.5)",
    x=bars,
    y=yData,
    marker_color="rgb(150,150,175)"
))

yData = []
yData.extend(emptyList + readList4 + writeList4 + emptyList * 2)
data.append(go.Bar(
    name="Wrapper: Building/sending response (te3)",
    x=bars,
    y=yData,
    marker_color="rgb(150,150,125)"
))

""" OPC1 = avgTimes["Write 1 C2"] / tests[0]
OPC5 = avgTimes["Write 5 C2"] / tests[1]
OPC25 = avgTimes["Write 25 C2"] / tests[2]
if tests[0]-1 == 0:
    GQL1 = 0
else:
    GQL1 = avgTimes["Write 1 C3"] / (tests[0]-1)
GQL5 = avgTimes["Write 5 C3"] / (tests[1]-1)
GQL25 = avgTimes["Write 25 C3"] / (tests[2]-1)
i = 0
while i < tests[0]:
    data.append(go.Bar(
        name="Write OPC UA",
        x=bars,
        y=[
            0, 0, 0,
            0, 0, 0,
            OPC1, OPC5, OPC25,
            0, 0, 0,
            0, 0, 0
        ]
    ))
    if i + 1 < nodes:
        data.append(go.Bar(
            name="Build next write request",
            x=bars,
            y=[
                0, 0, 0,
                0, 0, 0,
                GQL1, GQL5, GQL25,
                0, 0, 0,
                0, 0, 0
            ]
        ))
    i += 1 """

fig = go.Figure(data=data)

# Change the bar mode
fig.update_layout(barmode='stack')
fig.show()
