import threading               
import sys                             
import logging
import time
from os import path

from flask import Flask, request       
from controller import Robot    
from controller import Field
from controller import Node
from controller import Supervisor

# flask log level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

SUPERVISOR_PORT = 10001
tcpPortsAvailable = [str(port) for port in range(SUPERVISOR_PORT + 6, SUPERVISOR_PORT, -1)]
tcpPortsInUse = []
nextRobotId = 0
app = Flask(__name__)
supervisor = Supervisor()

@app.route("/ping")
def ping():
    "Basic Health check"
    return "pong"

@app.route("/robot", methods=['POST'])
def post_robot():
    requestData = request.json
    template = requestData.get("template")
    port = spawnRobot(template)
    return str(port)

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

    # Finally set the controller
    controllerField = newRobot.getField("controller")
    controllerField.setSFString("http_robot")

    return tcpPort


def start_flask():
    global app
    port = SUPERVISOR_PORT
    app.run(port=port)

if __name__ == "__main__":
    print("Starting supervisor flask server")

    # Run the simulation loop
    timestep = int(supervisor.getBasicTimeStep())
    threading.Thread(target=start_flask).start()

    # Run the simulation loop
    while supervisor.step(timestep) != -1:
        time.sleep(timestep / 1000)
    print("Finished")
