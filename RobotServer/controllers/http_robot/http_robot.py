import threading               
import sys                             
import logging
import time
import json

from flask import Flask, request       
from controller import Node, Robot

app = Flask(__name__)

# flask log level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

def get_device_id(device):
    return device.getName().split("#")[0].strip()

@app.route("/ping")
def ping():
    "Basic Health check"
    return "pong"

@app.route("/motors", methods=['PUT'])
def put_motors():
    global device_map
    request_data = request.json
    for request_motor_values in request_data['motors']:
        request_motor_id = request_motor_values.get("id")
        motor = device_map["Motors"].get(request_motor_id)
        if motor:
            # TODO: handle other modes of setting motor output
            throttle_percent = request_motor_values.get("val")
            if throttle_percent:
                motor.setVelocity(float(throttle_percent * motor.getMaxVelocity()))
        else:
            raise Exception(f"No motor named {request_motor_id} found")

    # return sensor data
    return json.dumps({
        "Sensors": [
            {
                "ID": get_device_id(distance_sensor),
                "Payload": {
                    "Distance": distance_sensor.getValue()
                }
            }
            for distance_sensor in device_map["DistanceSensors"].values()
        ]
    })
    
def build_device_map(robot):
    device_map = {
        "Motors": {},
        "DistanceSensors": {}
    }

    device_count = robot.getNumberOfDevices()
    for i in range(device_count):
        device = robot.getDeviceByIndex(i)
        device_type = device.getNodeType()
        device_id = get_device_id(device)
        
        if device_type == Node.ROTATIONAL_MOTOR:
            # Initialize the motor with an infinite target position so that we can directly control velocity
            device.setPosition(float("inf"))
            device.setVelocity(0)
            device_map["Motors"][device_id] = device

        elif device_type == Node.DISTANCE_SENSOR:
            # Initialize the distance sensor with an update frequency
            device.enable(timestep)
            device_map["DistanceSensors"][device_id] = device

    return device_map

def start_flask():
    global app
    # TODO: use argparse to clean this up
    port = int(sys.argv[2])
    app.run(port=port)

if __name__ == "__main__":
    # Create the robot
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    # If the controller started before the supervisor inserted all of the args,
    # just run an empty simulator loop so we don't block the simulation while
    # we wait for the supervisor to restart this controller
    if sys.argv[-1] != "READY":
        while robot.step(timestep) != -1:
            pass

    print("Starting flask server")
    device_map = build_device_map(robot)
    threading.Thread(target=start_flask).start()

    # Run the simulation loop
    print("Starting null op simulation loop")
    while robot.step(timestep) != -1:
        time.sleep(timestep / 1000)
    print("Finished")


