# TCP Robot client

import math
import json
import socket
import sys
import time

SERVER_IP = "localhost"
SUPERVISOR_PORT = 10001
MSG_BUFFER_SIZE = 256

def spawnRobot():

    # Request a spawn from the Supervisor
    supervisorClient = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    supervisorServer = (SERVER_IP, SUPERVISOR_PORT)
    request = "spawn RobotTemplate"
    print("[TCP Robot Client] Sending UDP to {}: {}".format(supervisorServer, request)) 
    supervisorClient.sendto(str.encode(request), supervisorServer)
    
    # Read the controller port from the response
    requestBytes, server = supervisorClient.recvfrom(MSG_BUFFER_SIZE)
    request = bytes.decode(requestBytes)
    print("[TCP Robot Client] Received UDP from {}: {}".format(server, request))
    return int(request)

# Check if a port was specified on the command line for an existing controller
isActiveClient = len(sys.argv) < 2
controllerPort = spawnRobot() if isActiveClient else int(sys.argv[1])

# Connect to the robot controller
controllerClient = socket.socket()
controllerServer = (SERVER_IP, controllerPort)
print("[TCP Robot Client] Connecting TCP to {}".format(controllerServer))
controllerClient.connect(controllerServer)

while True:

    time.sleep(0.1)
    
    # Generate request data
    requestData = {}
    if isActiveClient:
        velocity = 5 * math.sin(time.time())
        requestData = {
            "vFrontLeft": velocity,
            "vFrontRight": velocity,
            "vBackLeft": velocity,
            "vBackRight": velocity
        }

    # Send the request
    controllerClient.sendall(str.encode(json.dumps(requestData)))
    
    # Receive a response
    responseBytes = controllerClient.recv(MSG_BUFFER_SIZE)
    response = bytes.decode(responseBytes)
    responseData = json.loads(response)
    print(responseData)
