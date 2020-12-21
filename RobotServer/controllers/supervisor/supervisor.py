# Supervisor controller

# Sample client
#   import socket
#   client = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#   client.sendto(str.encode("spawn RobotTemplate"), ("localhost", 10001))
#   bytes.decode(client.recvfrom(128)[0])

from controller import Field
from controller import Node
from controller import Robot
from controller import Supervisor
from os import path
import socket
import threading

SUPERVISOR_PORT = 10001
SUPERVISOR_MSG_BUFFER_SIZE = 64

supervisor = Supervisor()
tcpPortsAvailable = [str(port) for port in range(SUPERVISOR_PORT + 6, SUPERVISOR_PORT, -1)]
tcpPortsInUse = []
nextRobotId = 0

def getPublicIp():

    # In case there are multiple network interfaces,
    # get the public IP address by connecting to Google.
    probeSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probeSocket.connect(("8.8.8.8", 80))
    ip = probeSocket.getsockname()[0]
    probeSocket.close()
    return ip

def spawnRobot(robotTemplate):
    global supervisor, tcpPortsAvailable, tcpPortsInUse, nextRobotId

    # Check if there are enough available ports
    if len(tcpPortsAvailable) == 0:
        return "Error: TCP ports exhausted. Too many robots."

    # Check if the template exists
    templateFile = "../../objects/{}.wbo".format(robotTemplate)
    if not path.exists(templateFile):
        return "Error: robot template '{}' not found.".format(robotTemplate)

    # Claim the next port
    tcpPort = tcpPortsAvailable.pop()
    tcpPortsInUse.append(tcpPort)

    # Spawn the robot at the end of the root children list
    rootChildrenField = Node.getField(supervisor.getRoot(), "children")
    rootChildrenField.importMFNode(-1, templateFile)
    newRobot = rootChildrenField.getMFNode(-1)
    nextRobotId += 1

    # Pass the robot ID and port as a controller arg
    controllerArgs = newRobot.getField("controllerArgs")
    controllerArgs.insertMFString(-1, str(nextRobotId))
    controllerArgs.insertMFString(-1, tcpPort)

    # Insert a final controller arg to let the controller know it's ready.
    # The controller may have already started before any args were set,
    # but this will signal it to wait, without it having to know how many
    # args to expect.
    controllerArgs.insertMFString(-1, "READY")

    # Restart the controller
    newRobot.restartController()

    return tcpPort
    
def handleRequest(request):

    # Parse the message
    tokens = request.split()
    if tokens[0] == "spawn":
        if len(tokens) == 2:
            return spawnRobot(tokens[1])
        else:
            return "Error: improper usage. Usage: 'spawn <robotTemplate>'"
    else:
        print("[Supervisor] Unknown command!")
        return "Error: unknown command '{}'.".format(tokens[0])

def runServer():

    # Start a UDP server
    udpSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    udpSocket.bind(("localhost", SUPERVISOR_PORT))
    print("[Supervisor] UDP server listening on {}".format((getPublicIp(), SUPERVISOR_PORT)))

    while True:
        try:
            # Receive a request
            requestBytes, client = udpSocket.recvfrom(SUPERVISOR_MSG_BUFFER_SIZE)
            request = bytes.decode(requestBytes)
            print("[Supervisor] Received from {}: {}".format(client, request))
            
            # Process the request
            response = handleRequest(request)
                
            # Send response
            print("[Supervisor] Sending to {}: {}".format(client, response)) 
            responseBytes = str.encode(response)
            udpSocket.sendto(responseBytes, client)
            
        except Exception as ex:
            # Catch and print any exceptions
            print(ex)

# Start the server in a background thread so it does not block the simulation
threading.Thread(target=runServer, daemon=True).start()

# Run the simulation loop
timestep = int(supervisor.getBasicTimeStep())
while supervisor.step(timestep) != -1:
    pass
