# TCP Robot controller

# You may need to import some classes of the controller module. Ex:
#  from controller import Robot, Motor, DistanceSensor
from controller import Robot
import json
import socket
import sys
import threading
import traceback

CONTROLLER_MSG_BUFFER_SIZE = 256

# If the controller started before the supervisor inserted all of the args,
# just run an empty simulator loop so we don't block the simulation while
# we wait for the supervisor to restart this controller
if sys.argv[-1] != "READY":
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())
    while robot.step(timestep) != -1:
        pass

ROBOT_ID = sys.argv[1]
PORT = int(sys.argv[2])

clientConnections = []
requestData = {}
responseBytes = str.encode("{}")

def getPublicIp():

    # In case there are multiple network interfaces,
    # get the public IP address by connecting to Google.
    probeSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    probeSocket.connect(("8.8.8.8", 80))
    ip = probeSocket.getsockname()[0]
    probeSocket.close()
    return ip

def handleRequest(request):
    global requestData
    
    # Copy values from the new request to the global request,
    # allowing pre-existing values to stick, rather than getting erased
    # if they weren't explicitly set in this request.
    if request != "":
        newRequestData = json.loads(request)
        for key, value in newRequestData.items():
            requestData[key] = value

def runClientConnection(connection, client):
    global responseBytes

    while True:
        try:
            # Receive a request
            requestBytes = connection.recv(CONTROLLER_MSG_BUFFER_SIZE)
            request = bytes.decode(requestBytes)
            print("got request: " + request)
            # Process the request
            handleRequest(request)
            
            # Send response
            connection.sendall(responseBytes)

        except Exception as ex:
            # In the case of any exception, close the connection
            # Add more fault tolerance here if necessary
            print(ex)
            traceback.print_exception(ex)
            print("[TCP Robot {}] Connection error. Closing connection to {}".format(ROBOT_ID, client))
            connection.close()
            return
            
            # TODO: If the client disconnects, and this was the last remaining client,
            #       kill the controller. Then, whenever the supervisor gets a spawn
            #       request (or on a timer), purge robots with dead controllers.

def runServer():
    global clientConnections

    # Start a TCP server
    tcpSocket = socket.socket()
    tcpSocket.bind(("localhost", PORT))
    tcpSocket.listen()
    print("[TCP Robot {}] TCP server listening on {}".format(ROBOT_ID, (getPublicIp(), PORT)))

    while True:
        try:
            # Accept new clients
            connection, client = tcpSocket.accept()
            print("[TCP Robot {}] Accepted connection from {}".format(ROBOT_ID, client))
            clientConnections.append(connection)
    
            # Start listening to this client in a new thread so it does not block new clients
            threading.Thread(target=runClientConnection, args=(connection, client), daemon=True).start()

        except Exception as ex:
            # Catch and print any exceptions
            print(ex)

# Start the server in a background thread so it does not block the simulation
threading.Thread(target=runServer, daemon=True).start()

# Create the robot
robot = Robot()
timestep = int(robot.getBasicTimeStep())

# TODO: Maybe find a way to generalize the following motor and sensor initializations.
#       For example, the robot template could have motor and sensor identifiers baked
#       into the controller args. These would be specific to a given robot template
#       and would come before any additional args that the supervisor adds.

# Initialize motors
motorFrontLeft = robot.getMotor("FL motor")
motorFrontRight = robot.getMotor("FR motor")
motorBackLeft = robot.getMotor("BL motor")
motorBackRight = robot.getMotor("BR motor")
motorFrontLeft.setPosition(float("inf"))
motorFrontRight.setPosition(float("inf"))
motorBackLeft.setPosition(float("inf"))
motorBackRight.setPosition(float("inf"))
motorFrontLeft.setVelocity(0.0)
motorFrontRight.setVelocity(0.0)
motorBackLeft.setVelocity(0.0)
motorBackRight.setVelocity(0.0)

# Initialize sensors
sensorRed = robot.getDistanceSensor("RED distance sensor")
sensorBlue = robot.getDistanceSensor("BLUE distance sensor")
sensorRed.enable(timestep)
sensorBlue.enable(timestep)

while robot.step(timestep) != -1:

    # Send inputs to the robot
    value = requestData.get("vFrontLeft")
    if value != None:
        motorFrontLeft.setVelocity(float(value))
    value = requestData.get("vFrontRight")
    if value != None:
        motorFrontRight.setVelocity(float(value))
    value = requestData.get("vBackLeft")
    if value != None:
        motorBackLeft.setVelocity(float(value))
    value = requestData.get("vBackRight")
    if value != None:
        motorBackRight.setVelocity(float(value))
    
    # Save outputs to be sent to all clients
    responseBytes = str.encode(json.dumps({
        "red": sensorRed.getValue(),
        "blue": sensorBlue.getValue()
    }))
