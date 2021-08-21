from typing import List
from collections import defaultdict
from controller import Node, Supervisor, TouchSensor
from flask import Flask, request
from itertools import zip_longest
import itertools
import json
import logging
import math
import socket
import sys
import threading
import time
import traceback

# TODO: use argparse to clean this up
robotId = int(sys.argv[1])
port = int(sys.argv[2])

app = Flask(__name__)

# flask log level
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

line_map = {}

def get_device_id(device: str):
    return device.getName().split("#")[0].strip()

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
            if throttle_percent is not None:
                motor.setVelocity(float(throttle_percent * motor.getMaxVelocity()))
        else:
            raise Exception(f"No motor named {request_motor_id} found")

    # return sensor data

    distance_sensor_values = [{
            "ID": get_device_id(distance_sensor),
            "Payload": {
                "Distance": distance_sensor.getValue()
            }
        }
        for distance_sensor in device_map["DistanceSensors"].values()
    ]

    bumper_touch_sensor_values = [{
            "ID": get_device_id(bumper_touch_sensor_values),
            "Payload": {
                "Triggered": bumper_touch_sensor_values.getValue() == 1
            }
        }
        for bumper_touch_sensor_values in device_map["BumperTouchSensors"].values()
    ]

    position_sensor_values = [{
            "ID": get_device_id(position_sensor),
            "Payload": {
                "EncoderTicks": position_sensor.getValue()
            }
        }
        for position_sensor in device_map["PositionSensors"].values()
    ]

    position_sensor_limit_switch_values = []
    for position_sensor_limit_switch in device_map["PositionSensorLimitSwitch"].values():
        proto_node = robot.getFromDevice(position_sensor_limit_switch)
        limits_field = proto_node.getField("limits")
        position_sensor_name = proto_node.getField("name").getSFString()
        sensor_names_field = proto_node.getField("sensorNames")
        limit_width = proto_node.getField("limitWidth").getSFFloat()
        if (limits_field.getCount() != sensor_names_field.getCount()):
            print(f"Ignoring misconfigured sensor {position_sensor_name}")
            continue
        for limit_switch_index in range(limits_field.getCount()):
            sensor_name = sensor_names_field.getMFString(limit_switch_index)
            sensor_limit = limits_field.getMFFloat(limit_switch_index)
            position_sensor_limit_switch_values.append({
                "ID": sensor_name.split("#")[0].strip(), # get_device_id only works for real devices
                "Payload": {
                    "Triggered": position_sensor_limit_switch.getValue() > sensor_limit - limit_width / 2 and position_sensor_limit_switch.getValue() < sensor_limit + limit_width / 2
                }
            })

    imu_sensor_values =  [{
            "ID": get_device_id(imu),
            "Payload": {
                "Roll": imu.getRollPitchYaw()[2],
                "Pitch": imu.getRollPitchYaw()[1],
                "Yaw": imu.getRollPitchYaw()[0],
                "YawVelocity" : gyro.getValues()[2]
            }
        }
        for imu, gyro in zip_longest(device_map["IMUs"].values(), device_map["Gyros"].values())
    ]

    # return exact robot world pose for debugging
    robot_node = robot.getSelf()
    position = robot_node.getPosition()
    rotation = robot_node.getOrientation()
    yaw = math.degrees(math.atan2(rotation[0], rotation[1])) % 360

    # simulation time is reported in seconds
    time = robot.getTime()
    return json.dumps({
        "Sensors": list(itertools.chain(
            distance_sensor_values,
            bumper_touch_sensor_values,
            position_sensor_values,
            position_sensor_limit_switch_values,
            imu_sensor_values
        )),
        "WorldPose": {
            "Position": position,
            "Yaw": yaw,
            "Time": time
        }
    })

@app.route("/position", methods=['PUT'])
def reset_position():
    request_data = request.json or {}
    target_position = request_data.get("position", [0,0,0.1])
    # defaults to straight up
    target_rotation = request_data.get("rotation", [1, 0, 0, 0]) 
    print(f"Resetting position to {target_position} @ {target_rotation}")

    robot_node = robot.getSelf()
    translation_field = robot_node.getField("translation")
    rotation_field = robot_node.getField("rotation")

    translation_field.setSFVec3f(target_position)
    rotation_field.setSFRotation(target_rotation)
    robot_node.resetPhysics()

    return 'OK'
    

@app.route("/overlay/line", methods=['PUT'])
def put_line():
    request_data = request.json or {}
    
    name = request_data['name']
    point_1 = request_data['point_1']
    point_2 = request_data['point_2']
    color_rgb = request_data.get('color', [0, 1, 1])

    draw_line(name, point_1, point_2, color_rgb=color_rgb)
    
    return 'OK'

@app.route("/overlay/arrow", methods=['PUT'])
def put_arrow():
    request_data = request.json or {}
    
    name = request_data['name']
    point_1 = request_data['point_1']
    point_2 = request_data['point_2']
    color_rgb = request_data.get('color', [0, 1, 1])

    draw_arrow(name, point_1, point_2, color_rgb=color_rgb)
    
    return 'OK'


@app.route("/overlay/circle", methods=['PUT'])
def put_circle():
    request_data = request.json or {}
    
    name = request_data['name']
    center = request_data['center']
    radius = request_data['radius']
    color_rgb = request_data.get('color', [0, 1, 1])

    draw_circle(name=name, center=center, color_rgb=color_rgb, radius=radius)
    
    return 'OK'

def build_device_map(robot):
    device_map = defaultdict(dict)

    device_count = robot.getNumberOfDevices()
    for i in range(device_count):
        device = robot.getDeviceByIndex(i)
        device_type = device.getNodeType()
        device_id = get_device_id(device)

        if device_type == Node.ROTATIONAL_MOTOR or device_type == Node.LINEAR_MOTOR:
            # Initialize the motor with an infinite target position so that we can directly control velocity
            device.setPosition(float("inf"))
            device.setVelocity(0)
            device_map["Motors"][device_id] = device
        elif device_type == Node.DISTANCE_SENSOR:
            # Initialize the distance sensor with an update frequency
            device.enable(timestep)
            device_map["DistanceSensors"][device_id] = device
        elif device_type == Node.TOUCH_SENSOR and device.getType() == TouchSensor.BUMPER:
            device.enable(timestep)
            device_map["BumperTouchSensor"][device_id] = device
        elif device_type == Node.POSITION_SENSOR:
            device.enable(timestep)
            device_map["PositionSensors"][device_id] = device
            # Handle PositionSensorLimitSwitch
            device_node = robot.getFromDevice(device)
            if (device_node and device_node.isProto() and device_node.getTypeName() == "PositionSensorLimitSwitch"):
                device_map["PositionSensorLimitSwitch"][device_id] = device
        elif device_type == Node.INERTIAL_UNIT:
            device.enable(timestep)
            device_map["IMUs"][device_id] = device
        elif device_type == Node.CAMERA:
            device.enable(timestep)
            device_map["Cameras"][device_id] = device
        elif device_type == Node.GYRO:
            device.enable(timestep)
            device_map["Gyros"][device_id] = device

    return device_map


# Draws a line between point_1 and point_2
# name creates the node in the tree so we just update the same node each time
def draw_line(name: str, point_1: List[float], point_2: List[float], color_rgb: List[float]):
    # Create node with name if it doesn't exist yet
    node_name = f'LINE_{name}'

    if node_name not in line_map:
        node = robot.getFromDef(node_name)
        root_node = robot.getRoot();
        root_children_field = root_node.getField("children");

        template = f"DEF {node_name} " + """Shape {
            appearance Appearance {
                material Material {
                    emissiveColor """ + " ".join(map(str, color_rgb)) + """
                }
            }
            geometry DEF TRAIL_LINE_SET IndexedLineSet {
                coord Coordinate {
                    point [
                        0 0 0
                        0 0 0
                    ]
                }
                coordIndex [
                    0 1 -1
                ]
            }
        }"""
        root_children_field.importMFNodeFromString(-1, template)
        node = robot.getFromDef(node_name)

        # Update the coords based on points
        trail_set_node = robot.getFromDef(f"{node_name}.TRAIL_LINE_SET")
        coordinates_node = trail_set_node.getField("coord").getSFNode()
        point_field = coordinates_node.getField("point")
        line_map[node_name] = point_field
    else:
        point_field = line_map[node_name]

    point_field.setMFVec3f(0, point_1)
    point_field.setMFVec3f(1, point_2)


# Draws a line between point_1 and point_2
# name creates the node in the tree so we just update the same node each time
def draw_arrow(name: str, point_1: List[float], point_2: List[float], color_rgb: List[float], arrow_angle_deg=35, arrow_len_ratio=0.25):
    # Create node with name if it doesn't exist yet
    node_name = f'ARROW_{name}'

    if node_name not in line_map:
        node = robot.getFromDef(node_name)
        root_node = robot.getRoot();
        root_children_field = root_node.getField("children");

        template = f"DEF {node_name} " + """Shape {
            appearance Appearance {
                material Material {
                    emissiveColor """ + " ".join(map(str, color_rgb)) + """
                }
            }
            geometry DEF TRAIL_LINE_SET IndexedLineSet {
                coord Coordinate {
                    point [
                        0 0 0
                        0 0 0
                        0 0 0
                        0 0 0
                    ]
                }
                coordIndex [
                    0 1 -1
                    1 2 -1
                    1 3 -1
                ]
            }
        }"""
        root_children_field.importMFNodeFromString(-1, template)
        node = robot.getFromDef(node_name)

        # Update the coords based on points
        trail_set_node = robot.getFromDef(f"{node_name}.TRAIL_LINE_SET")
        coordinates_node = trail_set_node.getField("coord").getSFNode()
        point_field = coordinates_node.getField("point")
        line_map[node_name] = point_field
    else:
        point_field = line_map[node_name]

    # calculate arrow points based on start/end
    # convert to polar
    delta = [point_1[0] - point_2[0], point_1[1] - point_2[1]]
    length = math.sqrt(delta[0] ** 2 + delta[1] ** 2)
    angle = math.atan2(delta[0], delta[1])

    left_angle = angle + math.radians(arrow_angle_deg)
    right_angle = angle - math.radians(arrow_angle_deg)

    arrow_length = length * arrow_len_ratio
    arrow_left = [arrow_length * math.sin(left_angle) + point_2[0], arrow_length * math.cos(left_angle) + point_2[1], point_2[2]]
    arrow_right = [arrow_length * math.sin(right_angle) + point_2[0], arrow_length * math.cos(right_angle) + point_2[1], point_2[2]]


    point_field.setMFVec3f(0, point_1)
    point_field.setMFVec3f(1, point_2)
    point_field.setMFVec3f(2, arrow_left)
    point_field.setMFVec3f(3, arrow_right)


def draw_circle(name: str, center: List[float], color_rgb: List[float], radius: float, num_segments=20):
    # Create node with name if it doesn't exist yet
    node_name = f'CIRCLE_{name}'

    if node_name not in line_map:
        node = robot.getFromDef(node_name)
        root_node = robot.getRoot();
        root_children_field = root_node.getField("children");

        template = f"DEF {node_name} " + """Shape {
            appearance Appearance {
                material Material {
                    emissiveColor """ + " ".join(map(str, color_rgb)) + """
                }
            }
            geometry DEF TRAIL_LINE_SET IndexedLineSet {
                coord Coordinate {
                    point [
                        """ + ("0 0 0\n" * num_segments) + """
                    ]
                }
                coordIndex [
                    """ + " ".join(map(str, range(num_segments))) + """ 0 -1
                ]
            }
        }"""
        root_children_field.importMFNodeFromString(-1, template)
        node = robot.getFromDef(node_name)

        # Update the coords based on points
        trail_set_node = robot.getFromDef(f"{node_name}.TRAIL_LINE_SET")
        coordinates_node = trail_set_node.getField("coord").getSFNode()
        point_field = coordinates_node.getField("point")
        line_map[node_name] = point_field
    else:
        point_field = line_map[node_name]

    # Use polar coordinates to find points on the circle
    for i in range(num_segments):
        theta = math.pi * 2 / num_segments * i
        point = [
            center[0] + radius * math.cos(theta),
            center[1] + radius * math.sin(theta),
            center[2],
        ]
        point_field.setMFVec3f(i, point)
    


def start_flask():
    global app, port

    print(f"[HttpRobot{robotId}] Starting flask server on http://{get_public_ip()}:{port}", flush=True)

    # Set the host to allow remote connections
    app.run(host='0.0.0.0', port=port)


def start_zmq():
    global device_map, port

    zmq_video_sleep_seconds = 1 / 60
    zmq_port_offset = 10
    zmq_port = port + zmq_port_offset
    print(f"[HttpRobot{robotId}] Starting zmq server on tcp://{get_public_ip()}:{zmq_port}", flush=True)

    try:
        import zmq

        # Start a ZeroMQ server.
        zmq_context = zmq.Context()
        zmq_socket = zmq_context.socket(zmq.PUB)
        zmq_socket.bind(f"tcp://0.0.0.0:{zmq_port}")

        # Get the camera, and define a message template to send the image.
        camera = next(iter(device_map["Cameras"].values()))
        camera_depth = 4
        message = [
            b"image",
            camera.getHeight().to_bytes(4, byteorder='big'),
            camera.getWidth().to_bytes(4, byteorder='big'),
            camera_depth.to_bytes(4, byteorder='big'),
            None
        ]

        while True:
            # Get the camera image and send the full message.
            message[-1] = bytes(camera.getImage())
            zmq_socket.send_multipart(message)
            
            # Sleep so we don't overload the ZMQ socket.
            # The sleep time is correlated with framerate, but doesn't seem to match it exactly.
            time.sleep(zmq_video_sleep_seconds)

    except:
        print("Could not start zmq!", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)


if __name__ == "__main__":
    # Create the robot
    robot = Supervisor()
    timestep = int(robot.getBasicTimeStep())
    device_map = build_device_map(robot)
    threading.Thread(target=start_flask).start()
    threading.Thread(target=start_zmq).start()

    # Run the simulation loop
    print("Starting null op simulation loop")
    while robot.step(timestep) != -1:
        time.sleep(timestep / 1000)
    print("Finished")
