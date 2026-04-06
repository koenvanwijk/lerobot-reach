# lerobot-reach (umbrella)

This directory is the local workspace for the lerobot-reach project.
It contains four git repos as siblings:

```
lerobot-reach/          ← this umbrella repo (docs + overview)
lerobot-action-space/   ← pip: lerobot-action-space
lerobot-remote/         ← pip: lerobot-remote
lerobot-matchmaker/     ← pip: lerobot-matchmaker
```

## New machine setup

**See [SETUP.md](SETUP.md) for complete installation instructions** including:
- Udev rules setup (USB serial device aliasing)
- Python environment configuration (Miniconda + dependencies)
- Calibration file setup for SO101 robots
- Running lerobot-teleoperate with all three components

**Quick clone:**

```bash
git clone https://github.com/koenvanwijk/lerobot-reach
cd lerobot-reach
bash bootstrap.sh   # clones lerobot-action-space, lerobot-remote, lerobot-matchmaker as siblings
```

Then open Claude Code from the `lerobot-reach/` directory to get full cross-repo context.

## Finding robot arm ports

Use these commands to rediscover connected arm serial devices:

```bash
# Quick list of likely serial devices
ls -1 /dev/tty_* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# With USB metadata (model/serial)
for d in /dev/tty_* /dev/ttyACM* /dev/ttyUSB*; do
        [ -e "$d" ] || continue
        echo "=== $d ==="
        udevadm info -q property -n "$d" | grep -E 'ID_MODEL=|ID_SERIAL=|ID_VENDOR=|DEVNAME='
done

# LeRobot helper
lerobot-find-port
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

## Packaging note (lerobot-remote)

`lerobot-remote` currently uses a **single `src/` package layout** (no split into
`transport/`, `robot/`, `teleop/` sub-packages).

- Distribution name is `lerobot_robot_remote` for LeRobot plugin discovery.
- `lerobot_robot_remote.__init__` imports `lerobot_teleoperator_remote` so both
        plugin types are registered (`remote_robot` and `remote_teleop`) in one install.
- Keep `pyproject.toml`, `pytest.ini`, and test import paths aligned to `src/`.

## How LeRobot finds configs/classes

LeRobot discovers third-party plugins via `register_third_party_plugins()`:

- It scans installed distributions with names starting with `lerobot_robot_`,
        `lerobot_teleoperator_`, `lerobot_camera_`, `lerobot_policy_`.
- Matching distributions are imported (via `importlib.import_module`).
- Import side-effects run decorators such as:
        - `@RobotConfig.register_subclass("remote_robot")`
        - `@TeleoperatorConfig.register_subclass("remote_teleop")`
- After that, CLI flags like `--robot.type=remote_robot` and
        `--teleop.type=remote_teleop` resolve to those config/classes.

For this repo (single-package layout), `lerobot_robot_remote` is the discovered
distribution and it imports `lerobot_teleoperator_remote` so both plugin types
are registered in one install.

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
- ~~lerobot-remote #3: no STUN/TURN — fails across NAT~~ (STUN added; TURN still missing for symmetric NAT)
- lerobot-remote #4: lerobot import paths unverified
- lerobot-remote #5: preferred_hz from ActionMode not used

See each repo's issue tracker for full list.
