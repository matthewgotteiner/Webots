# Webots

## Pre-reqs

### Install Webots

Visit https://cyberbotics.com/ and hit the big download button and install from there.

### Install Python and requirements

1. The easiest way to install python and windows and get nice contained virtual environments is to use anaconda. You can install it here: https://docs.anaconda.com/anaconda/install/windows/
2. Start an anaconda powershell prompt (hit your windows key and type "anaconda" and it should come up as an option)
3. Create a new environment for webots by running these commands (say yes when prompted):

```bash
conda create --name webots python=3.9
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

7. Copy what the above command spit out under "Source", for me it was `C:\Users\Alex\miniconda3\envs\webots\python.exe`
8. Open the Webots program and in the top menu go Tools -> Preferences and paste the above path into the "Python command" box in the middle

## How to use

1.  Open `RobotServer\worlds\frc_rectangle.wbt` in Webots.
2.  This will start a supervisor on port 10001 that you can request robots be spawned from.

### Using curl

Spawning a robot:

```bash
curl -XPOST localhost:10001/robot -d '{"template": "HttpRobotTemplate"}' --header "Content-Type: application/json"
```

which will return the port the new robot was spawned on (10002 for the first robot by default).

Then to send motor values to the robot:

```bash
curl -XPUT localhost:10002/motors -d '{"motors": [{"id": "Motor1", "val": 1.0}]}' --header "Content-Type: application/json"
```

Which will return the current sensor values for the robot.
