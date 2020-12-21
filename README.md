# Webots

 1. Open one of the RobotServer worlds in Webots.
 2. Press play, if it's not already running. This should start the Supervisor controller with a UDP server, awaiting the following requests:
     - `spawn <robotTemplate>`: spawns a robot of the requested template, with a TCP controller listening on the port that is sent in the response
 3. Run a client to connect to the UDP and TCP servers. After the client requests a spawn from the Supervisor, it should connect to the TCP Robot controller at the specified port.
    - The TCP server accepts requests with the following JSON payload, where each property is optional:
        ```python
        {
	        "vFrontLeft": float,
	        "vFrontRight": float,
	        "vBackLeft": float,
	        "vBackRight": float
        }
        ```
    - The server responds to each request with a JSON payload containing all sensor values.

 # Example
 1. Open `RobotServer/worlds/sample_arena.wbt` in Webots.
 2. Press play, if it's not already running.
 3. In a console, run `python RobotServer/controllers/tcp_robot/tcp_robot_sample_client.py` to spawn a robot and control its speed.
 4. In a separate console, run `python RobotServer/controllers/tcp_robot/tcp_robot_sample_client.py 10002` (where 10002 is the port that the TCP Robot controller is listening to). This runs the sample client in "passive" mode, where it connects to a pre-spawned robot controller and receives sensor values without controlling the robot.
