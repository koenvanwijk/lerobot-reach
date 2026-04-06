# lerobot-reach

Remote control for [LeRobot](https://github.com/huggingface/lerobot) robots over WebRTC.
Plug-and-play: any LeRobot teleop → any LeRobot robot, over the network, with automatic action space negotiation.

## Repos

| Repo | Role | Install |
|------|------|---------|
| [lerobot-action-space](https://github.com/koenvanwijk/lerobot-action-space) | Shared action space primitives — `ActionMode`, `ActionBridge`, `FrameDefinition` | `pip install git+https://github.com/koenvanwijk/lerobot-action-space` |
| [lerobot-remote](https://github.com/koenvanwijk/lerobot-remote) | LeRobot Robot + Teleoperator plugins for WebRTC | `pip install git+https://github.com/koenvanwijk/lerobot-remote` |
| [lerobot-matchmaker](https://github.com/koenvanwijk/lerobot-matchmaker) | WebRTC signaling server (self-hosted or [Firebase cloud](https://europe-west1-lerobot-matchmaker.cloudfunctions.net/matchmaker)) | `pip install git+https://github.com/koenvanwijk/lerobot-matchmaker` |
| [lerobot-robot-rerun](https://github.com/koenvanwijk/lerobot-robot-rerun) | Virtual robot: visualise joint states in Rerun viewer (URDF) | `pip install git+https://github.com/koenvanwijk/lerobot-robot-rerun` |

## Quick start

**1. Start the matchmaker** (any machine reachable by both sides):
```bash
pip install git+https://github.com/koenvanwijk/lerobot-matchmaker
lerobot-matchmaker --host 0.0.0.0 --port 8080
```
Or use the hosted instance (no setup needed):
```
https://europe-west1-lerobot-matchmaker.cloudfunctions.net/matchmaker
```

**2. Robot side** — replace your local teleop with a remote one:
```bash
pip install git+https://github.com/koenvanwijk/lerobot-remote
```
```python
from lerobot_action_space.compat import SO100_FOLLOWER_MODES
from lerobot_teleoperator_remote import RemoteTeleop, RemoteTeleopConfig

teleop = RemoteTeleop(
    RemoteTeleopConfig(signaling_url="http://<matchmaker>:8080", room="arm-1"),
    robot_modes=SO100_FOLLOWER_MODES,
)
teleop.connect()  # waits for operator, negotiates ActionMode, opens WebRTC
action = teleop.get_action()
```

**3. Operator side** — replace your local robot with a remote one:
```python
from lerobot_action_space import TELEOP_ACTION_MODES
from lerobot_robot_remote import RemoteRobot, RemoteRobotConfig

robot = RemoteRobot(
    RemoteRobotConfig(signaling_url="http://<matchmaker>:8080", room="arm-1"),
    teleop_modes=TELEOP_ACTION_MODES,
)
robot.connect()  # negotiates ActionMode via ActionBridge.auto(), opens WebRTC
robot.send_action({"joint1.pos": 0.5})
```

## How it works

```
[operator machine]                        [robot machine]
  local teleop                              physical robot
      │ get_action()                            ▲ send_action()
      ▼                                         │
  LeRobot framework                        LeRobot framework
      │ send_action()                           │ get_action()
      ▼                                         │
  RemoteRobot                            RemoteTeleop
      │                                         │
      └──────── WebRTC DataChannel ─────────────┘
                       │
               lerobot-matchmaker
               (signaling only —
                not in data path
                after handshake)
```

### ActionMode negotiation

Before WebRTC starts, both sides exchange supported `ActionMode` lists over the signaling channel.
`ActionBridge.auto()` selects the best compatible pair and both sides build a bridge:

```
operator → matchmaker → robot:  {"type": "capabilities", "teleop_modes": [...]}
robot    → matchmaker → operator: {"type": "capabilities", "robot_modes": [...]}
operator: ActionBridge.auto() → best pair
operator → matchmaker → robot:  {"type": "mode_agreed", "teleop_mode": {...}, "robot_mode": {...}}
──── WebRTC SDP offer/answer ────────────────────────────────────────────────────
```

## Documentation

- [Architecture](docs/architecture.md)
- [Getting started](docs/getting-started.md)
- [Signaling protocol](docs/signaling-protocol.md)
- [ActionMode negotiation](docs/action-mode-negotiation.md)
