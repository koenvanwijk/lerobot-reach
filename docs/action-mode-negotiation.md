# ActionMode negotiation

lerobot-reach automatically negotiates the best compatible action space between
a teleop and a robot during `connect()`. No manual configuration of units, frames,
or command modes is needed.

## ActionMode

An `ActionMode` describes the action contract of a device:

```python
ActionMode(
    name="joint_absolute_norm",
    space_type="joint",          # joint | cartesian | gripper | base | wholebody | custom
    unit="normalized",           # rad | deg | mm | m | normalized | binary | m/s | rad/s
    command_mode="absolute",     # absolute | delta | velocity | binary | torque
    frame=None,                  # FrameDefinition (coordinate frame) or None
    is_default=True,
    preferred_hz=30,
    description="Joint positions in [-100, 100]",
)
```

## ConversionQuality

`ActionBridge.auto()` scores every possible teleop × robot pair and picks the best:

| Quality | Meaning |
|---------|---------|
| `EXACT` | Lossless conversion (e.g. rad ↔ deg, m ↔ mm) |
| `APPROXIMATE` | Small error acceptable (e.g. delta→absolute integration) |
| `REQUIRES_IK` | Needs inverse kinematics (cartesian → joint) |
| `LOSSY` | Information lost (e.g. normalized → binary via threshold) |
| `IMPOSSIBLE` | Cannot convert |

## Built-in conversion steps

`ActionBridge` assembles a pipeline automatically from these steps:

| Step | Trigger | Quality |
|------|---------|---------|
| `FrameRotationStep` | teleop.frame ≠ robot.frame | EXACT |
| `ScaleStep` | unit mismatch (e.g. m vs mm) | EXACT |
| `DeltaToAbsoluteStep` | teleop=delta, robot=absolute | APPROXIMATE |
| `NoopStep (IK)` | teleop=cartesian, robot=joint | REQUIRES_IK |
| `ScaleStep` | binary ↔ normalized gripper | EXACT / LOSSY |

`bridge.explain()` prints the full pipeline:
```
teleop mode : ee_delta_m  (m, delta, frame=opencv)
robot mode  : joint_absolute_norm  (normalized, absolute, frame=none)
conversions :
  [✓] frame_rotation: opencv → none
  [✓] unit_scale: m → normalized (×100)
  [~] delta_to_absolute: integrate delta into absolute position
overall     : approximate ~  (small error acceptable)
```

## Pre-declared modes (compat.py)

`lerobot-action-space` ships modes for all built-in LeRobot devices:

```python
from lerobot_action_space.compat import (
    # Teleoperators
    SO100_LEADER_MODES, SO101_LEADER_MODES, KOCH_LEADER_MODES,
    KEYBOARD_JOINT_MODES, KEYBOARD_EE_MODES, GAMEPAD_MODES,
    REACHY2_TELEOP_MODES, PHONE_MODES,

    # Robots
    SO100_FOLLOWER_MODES, SO101_FOLLOWER_MODES, KOCH_FOLLOWER_MODES,
    LEKIWI_MODES, REACHY2_ROBOT_MODES,
    HOPE_JR_ARM_MODES, HOPE_JR_HAND_MODES,
    ROARM_MODES,
)
```

## Custom modes

For devices not in `compat.py`, declare modes directly:

```python
from lerobot_action_space import ActionMode

MY_ROBOT_MODES = [
    ActionMode(
        name="joint_absolute_deg",
        space_type="joint",
        unit="deg",
        command_mode="absolute",
        is_default=True,
        preferred_hz=50,
        description="Joint positions in degrees",
    )
]
```

Then use them wherever modes are needed:

```python
# With lerobot-remote (remote teleop):
from lerobot_teleoperator_remote import RemoteTeleop, RemoteTeleopConfig
teleop = RemoteTeleop(config, robot_modes=MY_ROBOT_MODES)

# Or directly with ActionBridge for local use:
bridge = ActionBridge.auto(teleop_modes=MY_TELEOP_MODES, robot_modes=MY_ROBOT_MODES)
robot_action = bridge.convert(teleop_action)
```
