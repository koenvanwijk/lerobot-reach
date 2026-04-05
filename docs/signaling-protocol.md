# Signaling protocol

The matchmaker routes messages between `operator` and `robot` roles within a named room.

## HTTP endpoints

```
POST /signal/{room}/{role}/send   Store a message sent by {role}
GET  /signal/{room}/{role}/recv   Long-poll: receive a message sent by {role}
GET  /rooms                       List active rooms
GET  /health                      Health check
```

`{role}` must be `operator` or `robot`.

**Routing:** the receiver polls the *sender's* queue.
- Operator reads:  `GET /signal/{room}/robot/recv`
- Robot reads:     `GET /signal/{room}/operator/recv`

`GET .../recv` returns:
- `200 + JSON` when a message is available
- `204` on timeout (25s) — client retries immediately

## Message types

All messages are JSON objects with a `type` field.

### 1. `capabilities` (operator → robot)
Sent by the operator at the start of `connect()`.

```json
{
  "type": "capabilities",
  "teleop_modes": [
    {
      "name": "joint_absolute_norm",
      "space_type": "joint",
      "unit": "normalized",
      "command_mode": "absolute",
      "frame": null,
      "is_default": true,
      "preferred_hz": 30,
      "requires": [],
      "description": "Joint positions in [-100, 100]"
    }
  ]
}
```

### 2. `capabilities` (robot → operator)
Sent by the robot in response.

```json
{
  "type": "capabilities",
  "robot_modes": [
    {
      "name": "joint_absolute_norm",
      "space_type": "joint",
      "unit": "normalized",
      "command_mode": "absolute",
      "frame": null,
      "is_default": true,
      "preferred_hz": 30,
      "requires": [],
      "description": "..."
    }
  ]
}
```

### 3. `mode_agreed` (operator → robot)
Sent by the operator after `ActionBridge.auto()` selects the best pair.

```json
{
  "type": "mode_agreed",
  "teleop_mode": { "name": "joint_absolute_norm", ... },
  "robot_mode":  { "name": "joint_absolute_norm", ... }
}
```

### 4. `offer` (operator → robot)
WebRTC SDP offer.

```json
{
  "type": "offer",
  "sdp": "v=0\r\no=- ..."
}
```

### 5. `answer` (robot → operator)
WebRTC SDP answer.

```json
{
  "type": "answer",
  "sdp": "v=0\r\no=- ..."
}
```

## Full sequence

```
operator                 matchmaker                  robot
   │                         │                          │
   │  POST operator/send     │                          │
   │  {type:capabilities,    │                          │
   │   teleop_modes:[...]}──►│                          │
   │                         │◄──GET operator/recv──────│
   │                         │──{type:capabilities,...}►│
   │                         │                          │
   │                         │  POST robot/send         │
   │◄──GET robot/recv────────│◄─{type:capabilities,     │
   │                         │   robot_modes:[...]}─────│
   │                         │                          │
   │  POST operator/send     │                          │
   │  {type:mode_agreed,...}►│──────────────────────────►│
   │                         │                          │
   │  POST operator/send     │                          │
   │  {type:offer,sdp:...}──►│──────────────────────────►│
   │                         │                          │
   │◄──GET robot/recv────────│◄─POST robot/send──────────│
   │  {type:answer,sdp:...}  │  {type:answer,sdp:...}   │
   │                         │                          │
   │◄══════════ WebRTC DataChannel (peer-to-peer) ══════►│
```

After the DataChannel opens, the matchmaker is no longer involved.

## Actions (over DataChannel, not matchmaker)

Actions are sent as JSON over the WebRTC DataChannel named `"actions"`:

```json
{"joint1.pos": 0.45, "joint2.pos": -0.12, "gripper.pos": 0.8}
```

Feedback from robot to operator uses a reserved key:
```json
{"__feedback__": true, "force": 0.3}
```
