# Getting started

## Prerequisites

- Python 3.10+
- Two machines on the same network (or a TURN server for cross-network, see [open issue](https://github.com/koenvanwijk/lerobot-remote/issues/3))
- lerobot installed on the robot machine

## Install

```bash
# On both machines:
pip install git+https://github.com/koenvanwijk/lerobot-remote

# On the matchmaker machine (can be either machine or a server):
pip install git+https://github.com/koenvanwijk/lerobot-matchmaker
```

## Step 1 — Start the matchmaker

On any machine reachable by both operator and robot:

```bash
lerobot-matchmaker --host 0.0.0.0 --port 8080
```

## Step 2 — Robot side

Replace the teleoperator in your LeRobot script with `RemoteTeleop`.
The robot side waits for the operator to connect and negotiates the `ActionMode` automatically.

```python
from lerobot_action_space.compat import SO100_FOLLOWER_MODES
from lerobot_teleoperator_remote import RemoteTeleop, RemoteTeleopConfig

# Your physical robot (any LeRobot robot)
robot = YourRobot(config)
robot.connect()

# RemoteTeleop replaces the local teleop
teleop = RemoteTeleop(
    RemoteTeleopConfig(
        signaling_url="http://<matchmaker-ip>:8080",
        room="arm-1",           # unique name for this session
    ),
    robot_modes=SO100_FOLLOWER_MODES,
)
teleop.connect()  # blocks until operator connects and WebRTC is ready

# Standard LeRobot control loop
while True:
    action = teleop.get_action()  # receives from remote operator
    robot.send_action(action)
```

## Step 3 — Operator side

Replace the robot in your LeRobot script with `RemoteRobot`.

```python
from lerobot_action_space import TELEOP_ACTION_MODES
from lerobot_robot_remote import RemoteRobot, RemoteRobotConfig

# Your local teleop (any LeRobot teleop)
teleop = YourTeleop(config)
teleop.connect()

# RemoteRobot replaces the local robot
robot = RemoteRobot(
    RemoteRobotConfig(
        signaling_url="http://<matchmaker-ip>:8080",
        room="arm-1",           # must match robot side
    ),
    teleop_modes=TELEOP_ACTION_MODES,
)
robot.connect()  # negotiates ActionMode with robot side, opens WebRTC

# Standard LeRobot control loop
while True:
    action = teleop.get_action()
    robot.send_action(action)   # encodes via ActionBridge, sends over WebRTC
```

## What happens during connect()

1. Operator sends its supported `teleop_modes` to the matchmaker
2. Robot sends its supported `robot_modes` back
3. Operator runs `ActionBridge.auto()` to select the best compatible pair
4. Agreed modes are sent to the robot; both sides build an `ActionBridge`
5. WebRTC SDP offer/answer is exchanged via the matchmaker
6. DataChannel opens — matchmaker is no longer involved

Both sides log the full bridge plan:
```
teleop mode : apriltag_cartesian  (m, absolute, frame=opencv)
robot mode  : joint_absolute_norm  (normalized, absolute, frame=none)
conversions :
  [✓] frame_rotation: opencv → none
  [✓] unit_scale: m → normalized (×100)
overall     : exact ✓
```

## Using with existing compat modes

`lerobot-action-space` ships pre-declared modes for all built-in LeRobot devices:

```python
from lerobot_action_space.compat import (
    SO100_FOLLOWER_MODES,
    SO101_FOLLOWER_MODES,
    KOCH_FOLLOWER_MODES,
    LEKIWI_MODES,
    REACHY2_ROBOT_MODES,
)
```

Or patch a live device instance to add `action_modes`:

```python
from lerobot_action_space.compat import patch_robot, patch_teleoperator

patch_robot(my_robot)           # adds my_robot.action_modes
patch_teleoperator(my_teleop)   # adds my_teleop.action_modes
```
