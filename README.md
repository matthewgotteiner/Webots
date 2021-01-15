# Webots

## Pre-reqs

### Install Webots

Visit https://cyberbotics.com/ and hit the big download button and install from there.

### Install Python and requirements

1. The easiest way to install python and windows and get nice contained virtual environments is to use anaconda. You can install it here: https://docs.anaconda.com/anaconda/install/windows/
2. Start an anaconda powershell prompt (hit your windows key and type "anaconda" and it should come up as an option)
3. Create a new environment for webots by running these commands (say yes when prompted):
```bash
conda create --name webots python=3
conda activate webots
```
4. In your anaconda prompt, navigate (using `cd`) to the folder where this repo is cloned on your machine. 
5. In the root Webots repo directory run:
```bash
pip install -r requirements.txt
```
6. Now we just need the path to this python environment so we can give it to the Webots program, to find that out, run: 
```powershell
get-command python
```
7. Copy what the above command spit out under "Source", for me it was `C:\Users\Alex\miniconda3\envs\webots\python.exe `
8. Open the Webots program and in the top menu go Tools -> Preferences and paste the above path into the "Python command" box in the middle

## How to use 

TODO: This section needs updating

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

 ## Example
 1. Open `RobotServer\worlds\frc_rectangle.wbt` in Webots.
 2. Press play, if it's not already running.
 3. In a console, run `python RobotServer/controllers/tcp_robot/tcp_robot_sample_client.py` to spawn a robot and control its speed.
 4. In a separate console, run `python RobotServer/controllers/tcp_robot/tcp_robot_sample_client.py 10002` (where 10002 is the port that the TCP Robot controller is listening to). This runs the sample client in "passive" mode, where it connects to a pre-spawned robot controller and receives sensor values without controlling the robot.
