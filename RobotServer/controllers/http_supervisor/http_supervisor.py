from controller import Field, Node, Robot, Supervisor
from flask import Flask, request
import logging
from os import path
import socket
import sys
import threading
import time

# flask log level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

SUPERVISOR_PORT = 10001
tcp_ports_available = [str(port) for port in range(SUPERVISOR_PORT + 6, SUPERVISOR_PORT, -1)]
tcp_ports_in_use = []
next_robot_id = 0
app = Flask(__name__)
supervisor = Supervisor()

def get_public_ip():
    try:
        # In case there are multiple network interfaces,
        # get the public IP address by connecting to Google.
        probe_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe_socket.connect(("8.8.8.8", 80))
        ip = probe_socket.getsockname()[0]
        probe_socket.close()
        return ip
    except:
        return '127.0.0.1'

@app.route("/ping")
def ping():
    "Basic Health check"
    return "pong"

@app.route("/robot", methods=['POST'])
def post_robot():
    request_data = request.json
    template = request_data.get("template")
    port = spawn_robot(template)
    return str(port)

def spawn_robot(robot_template):
    global supervisor, tcp_ports_available, tcp_ports_in_use, next_robot_id

    # Check if there are enough available ports
    if len(tcp_ports_available) == 0:
        return "Error: TCP ports exhausted. Too many robots."

    # Check if the template exists
    template_file = "../../objects/{}.wbo".format(robot_template)
    if not path.exists(template_file):
        return "Error: robot template '{}' not found.".format(robot_template)

    # Claim the next port
    tcp_port = tcp_ports_available.pop()
    tcp_ports_in_use.append(tcp_port)

    # Spawn the robot at the end of the root children list
    root_children_field = Node.getField(supervisor.getRoot(), "children")
    root_children_field.importMFNode(-1, template_file)
    new_robot = root_children_field.getMFNode(-1)
    next_robot_id += 1

    # Pass the robot ID and port as a controller arg
    controller_args_field = new_robot.getField("controllerArgs")
    controller_args_field.insertMFString(-1, str(next_robot_id))
    controller_args_field.insertMFString(-1, tcp_port)

    # Finally set the controller
    controller_field = new_robot.getField("controller")
    controller_field.setSFString("http_robot")

    return tcp_port


def start_flask():
    global app

    # Set the host to allow remote connections
    app.run(host='0.0.0.0', port=SUPERVISOR_PORT)

if __name__ == "__main__":
    print(f'[Supervisor] Server listening on http://{get_public_ip()}:{SUPERVISOR_PORT}')

    # Run the simulation loop
    timestep = int(supervisor.getBasicTimeStep())
    threading.Thread(target=start_flask).start()

    # Run the simulation loop
    while supervisor.step(timestep) != -1:
        time.sleep(timestep / 1000)
    print("Finished")
