import threading               
import sys                             
import logging
import time
import json

from flask import Flask, request       
from controller import Robot    

app = Flask(__name__)

# flask log level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route("/ping")
def ping():
    "Basic Health check"
    return "pong"

@app.route("/motors", methods=['PUT'])
def put_motors():
    global motor_map
    requestData = request.json
    for motor_dict in requestData['motors']:
        motor_id = motor_dict["id"]
        if motor_id in motor_map:
            motor = motor_map[motor_id]
            # TODO: handle other modes of setting motor output
            throttlePercent = motor_dict.get("val")
            if throttlePercent:
                motor.setVelocity(float(throttlePercent * motor.getMaxVelocity()))
        else:
            raise Exception(f"No motor named {motor_id} found")


    # return sensor data
    sensors = []
    response_data = {
        "Sensors": sensors
    }
    for distance_sensor in distance_sensors:
        sensors.append({
            "ID": distance_sensor.getName(),
            "Payload": {
                "Distance": distance_sensor.getValue()
            }
        })
    
    return json.dumps(response_data)

def build_motor_map(robot):
    # Initialize motors
    result = {}
    for i in range(1, 50):
        name = f"Motor{i}"
        # TODO: Find a way to test for motor presence by name without the warning logs this approach generates
        motor = robot.getMotor(name)
        if motor:
            result[name] = motor
            # This sets the motor into velocity control (rather than position)
            motor.setPosition(float("inf"))
            motor.setVelocity(0)
    return result

def build_distance_sensor_list(robot):
    result = []
    for i in range(1, 50):
        name = f"Analog{i}"
        distanceSensor = robot.getDistanceSensor(name)
        if distanceSensor:
            distanceSensor.enable(timestep)
            result.append(distanceSensor)
    return result
        

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
    motor_map = build_motor_map(robot)
    distance_sensors = build_distance_sensor_list(robot)
    threading.Thread(target=start_flask).start()

    # Run the simulation loop
    print("Starting null op simulation loop")
    while robot.step(timestep) != -1:
        time.sleep(timestep / 1000)
    print("Finished")


