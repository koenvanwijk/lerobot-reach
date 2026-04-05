# Architecture

## System overview

lerobot-reach adds a network layer between a LeRobot teleoperator and a LeRobot robot.
Both sides use the standard LeRobot `Robot` and `Teleoperator` interfaces — the remote layer is transparent to the LeRobot framework.

```
[operator machine]                          [robot machine]

  ┌─────────────────────────────┐           ┌─────────────────────────────┐
  │  LeRobot framework          │           │  LeRobot framework          │
  │                             │           │                             │
  │  local_teleop.get_action()  │           │  local_robot.send_action()  │
  │           │                 │           │           ▲                 │
  │           ▼                 │           │           │                 │
  │  RemoteRobot                │           │  RemoteTeleop               │
  │  (Robot plugin)             │           │  (Teleoperator plugin)      │
  └────────────┬────────────────┘           └───────────┬─────────────────┘
               │ WebRTC DataChannel                     │
               │ dict[str, float] as JSON               │
               └──────────────────┬─────────────────────┘
                                  │
                         (during connect() only)
                                  │
                        ┌─────────▼─────────┐
                        │  lerobot-matchmaker│
                        │  HTTP long-poll   │
                        │  signaling server │
                        └───────────────────┘
```

The matchmaker is only involved during the handshake phase (mode negotiation + SDP exchange). After WebRTC is established, all data flows directly peer-to-peer.

## Repos and responsibilities

### lerobot-action-space
- `ActionMode` — describes the action contract of a device (space type, unit, command mode, frame, hz)
- `ActionBridge` — auto-resolves a conversion pipeline between any two `ActionMode`s
- `compat.py` — pre-declared `action_modes` for built-in LeRobot devices (SO-100/101, Koch, LeKiwi, Reachy2, ...)
- No dependencies on lerobot internals

### lerobot-remote
Three Python packages in one pip install:

| Package | Role |
|---------|------|
| `lerobot_robot_remote` | LeRobot `Robot` plugin — operator side, sends actions over WebRTC |
| `lerobot_teleoperator_remote` | LeRobot `Teleoperator` plugin — robot side, receives actions over WebRTC |
| `lerobot_remote_transport` | Shared WebRTC (aiortc) + HTTP signaling (aiohttp) transport |

### lerobot-matchmaker
- `aiohttp` HTTP server
- Routes messages between `operator` and `robot` roles within named rooms via long-poll
- Not in the data path after WebRTC handshake completes

## connect() sequence

```
time →

operator                    matchmaker                      robot
   │                            │                             │
   │──connect()─────────────────│                             │──connect()──
   │                            │                             │  (waiting)
   │  POST operator/send        │                             │
   │  {"type":"capabilities",   │                             │
   │   "teleop_modes":[...]}───►│                             │
   │                            │◄──GET operator/recv─────────│
   │                            │   (long-poll)               │
   │                            │                             │
   │                            │──{"type":"capabilities",...}►│
   │                            │                             │
   │                            │  POST robot/send            │
   │◄──GET robot/recv───────────│◄─{"type":"capabilities",    │
   │   (long-poll)              │   "robot_modes":[...]}──────│
   │                            │                             │
   │  ActionBridge.auto()       │                             │
   │  → best teleop+robot pair  │                             │
   │                            │                             │
   │  POST operator/send        │                             │
   │  {"type":"mode_agreed",...}►│──────────────────────────►│
   │                            │                             │  build bridge
   │                            │                             │
   │  POST operator/send        │                             │
   │  {"type":"offer","sdp":...}►│──────────────────────────►│
   │                            │                             │
   │◄──GET robot/recv───────────│◄─{"type":"answer","sdp":...}│
   │                            │                             │
   │◄═══════════════ WebRTC DataChannel ════════════════════►│
   │         (matchmaker no longer involved)                  │
```

## ActionBridge conversion pipeline

`ActionBridge.auto(teleop_modes, robot_modes)` selects the pair with the best `ConversionQuality`:

```
EXACT → APPROXIMATE → REQUIRES_IK → LOSSY → IMPOSSIBLE
```

For a selected pair, the bridge builds an ordered pipeline of `ConversionStep`s:

1. **FrameRotationStep** — if teleop and robot use different coordinate frames
2. **ScaleStep** — unit conversion (e.g. m → mm, rad → deg)
3. **DeltaToAbsoluteStep** — integrate delta commands into absolute positions
4. **NoopStep (REQUIRES_IK)** — cartesian → joint space (IK not yet implemented, see lerobot-action-space#4)
5. **ScaleStep** — gripper normalization (binary ↔ normalized)

`bridge.explain()` prints the full pipeline with quality indicators.

## Dependency graph

```
                   lerobot (HuggingFace)
                   ├── Robot (ABC)
                   ├── RobotConfig
                   ├── Teleoperator (ABC)
                   └── TeleopConfig
                            ▲
                            │ optional — registers plugins via
                            │ @RobotConfig.register_subclass()
                            │ falls back to standalone stubs if not installed
                            │
numpy ──► scipy              │
    ▲                        │
    │                        │
lerobot-action-space         │
(ActionMode, ActionBridge)   │
    ▲                        │
    │                        │
    └───── lerobot-remote ───┘
           ├── lerobot_robot_remote
           ├── lerobot_teleoperator_remote
           └── lerobot_remote_transport
                   │ aiortc (WebRTC)
                   │ aiohttp (HTTP signaling)
                   │
                   │ HTTP long-poll
                   ▼
           lerobot-matchmaker
                   │ aiohttp
```

### lerobot dependency

`lerobot-remote` has a **soft dependency** on lerobot. If lerobot is installed, `RemoteRobot`
and `RemoteTeleop` register themselves as proper LeRobot plugins via:
```python
@RobotConfig.register_subclass("remote_robot")
@TeleopConfig.register_subclass("remote_teleop")
```
This enables lerobot's CLI and config system to instantiate them by name.

If lerobot is not installed, both classes fall back to standalone stub base classes and
still work — but won't appear in lerobot's plugin registry.

`lerobot-action-space` has **no dependency** on lerobot. It only uses `numpy` and `scipy`.
