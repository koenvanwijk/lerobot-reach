# lerobot-reach (umbrella)

This directory is the local workspace for the lerobot-reach project.
It contains four git repos as siblings:

```
lerobot-reach/          ← this umbrella repo (docs + overview)
lerobot-action-space/   ← pip: lerobot-action-space
lerobot-remote/         ← pip: lerobot-remote
lerobot-matchmaker/     ← pip: lerobot-matchmaker
```

## Cross-repo reading

Claude Code can read files in sibling repos directly:
```
../lerobot-action-space/src/lerobot_action_space/bridge.py
../lerobot-remote/src/lerobot_robot_remote/remote_robot.py
../lerobot-remote/src/lerobot_teleoperator_remote/remote_teleop.py
../lerobot-remote/src/lerobot_remote_transport/
../lerobot-matchmaker/src/lerobot_matchmaker/
```

## Dependency graph

```
lerobot-action-space   (no lerobot deps — numpy + scipy only)
        ▲
        │
lerobot-remote  ──────────────────────────────────────────────┐
  lerobot_robot_remote        (name = "remote_robot")         │
  lerobot_teleoperator_remote (name = "remote_teleop")        │
  lerobot_remote_transport    (shared WebRTC + signaling)     │
        │                                                      │
        │ SignalingClient HTTP long-poll                       │
        ▼                                                      │
lerobot-matchmaker                                            │
  aiohttp signaling server                         ActionBridge
  POST/GET /signal/{room}/{role}/send|recv          auto-selects
                                                   best mode pair
```

## Key interfaces

**ActionMode** (`lerobot-action-space`) — describes the action contract of a device:
`space_type`, `unit`, `command_mode`, `frame`, `preferred_hz`

**ActionBridge** (`lerobot-action-space`) — auto-resolves conversion pipeline:
`ActionBridge.auto(teleop_modes, robot_modes)` → best pair
`bridge.convert(action)` → `dict[str, float]`
`bridge.explain()` → human-readable conversion plan

**RemoteRobot** (`lerobot-remote`) — LeRobot Robot plugin, operator side:
`RemoteRobot(config, teleop_modes)` → `connect()` negotiates modes → `send_action()`

**RemoteTeleop** (`lerobot-remote`) — LeRobot Teleoperator plugin, robot side:
`RemoteTeleop(config, robot_modes)` → `connect()` waits for operator → `get_action()`

**Matchmaker** (`lerobot-matchmaker`) — HTTP long-poll signaling:
`POST /signal/{room}/{role}/send` · `GET /signal/{room}/{role}/recv`
Roles: `operator` | `robot`

## Open issues (cross-repo)

Critical:
- lerobot-remote #7: asyncio Queue/Event created outside event loop (Python 3.10+)
- lerobot-remote #8: deadlock if WebRTC DataChannel never opens
- lerobot-remote #9: assert used for protocol validation (fails with python -O)
- lerobot-matchmaker #6: same asyncio issue in Room dataclass

High:
- lerobot-remote #2: observation reverse channel not implemented
- lerobot-remote #3: no STUN/TURN — fails across NAT
- lerobot-remote #4: lerobot import paths unverified
- lerobot-remote #5: preferred_hz from ActionMode not used

See each repo's issue tracker for full list.
