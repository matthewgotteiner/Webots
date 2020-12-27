import threading               
import sys                             

from flask import Flask, request       
from controller import Robot    

app = Flask(__name__)

@app.route("/ping")
def ping():
    "Basic Health check"
    return "pong"

@app.route("/motors", methods=['PUT'])
def put_motors():
    requestData = request.json
    for motor_dict in requestData['motors']:
        motor_id = motor_dict["id"]
        value = motor_dict["val"]
        if motor_id in motor_map:
            motor = motor_map[motor_id]
            motor.setVelocity(float(value))
        else:
            raise Exception(f"No motor named {motor_id} found")

    return "ack"

def build_motor_map(robot):
    # Initialize motors
    motor_map = {}
    for i in range(1, 50):
        name = f"Motor{i}"
        # TODO: Find a way to test for motor presence by name without the warning logs this approach generates
        motor = robot.getMotor(name)
        if motor:
            motor_map[name] = motor
            # This sets the motor into velocity control (rather than position)
            motor.setPosition(float("inf"))
            motor.setVelocity(0)



def start_flask():
    # TODO: use argparse to clean this up
    port = int(sys.argv[2])
    app.run(port=port)

if __name__ == "__main__":
    # If the controller started before the supervisor inserted all of the args,
    # just run an empty simulator loop so we don't block the simulation while
    # we wait for the supervisor to restart this controller
    if sys.argv[-1] != "READY":
        timestep = int(robot.getBasicTimeStep())
        while robot.step(timestep) != -1:
            pass

    print("Starting flask server")
    # Create the robot
    robot = Robot()
    motor_map = build_motor_map()
    threading.Thread(target=start_flask).start()

    # Run the simulation loop
    print("Starting null op simulation loop")
    timestep = int(robot.getBasicTimeStep())
    while robot.step(timestep) != -1:
        pass


