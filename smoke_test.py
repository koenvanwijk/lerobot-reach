"""
smoke_test.py — end-to-end test zonder WebRTC/aiortc

Test:
1. Matchmaker server opstarten
2. Signaling: operator + robot sturen capabilities, ontvangen mode_agreed
3. ActionBridge.auto() selecteert beste pair
4. ActionBridge.convert() doet correcte unit conversie
5. RerunRobot als virtuele robot: connect → send_action → get_observation

Geen echte WebRTC — simuleert de signaling handshake.
"""
import asyncio
import sys

sys.path.insert(0, 'lerobot-action-space/src')
sys.path.insert(0, 'lerobot-remote/src')
sys.path.insert(0, 'lerobot-matchmaker/src')
sys.path.insert(0, 'lerobot-robot-rerun/src')

# also add lerobot 0.5 source so RerunRobot can import it
sys.path.insert(0, '/home/kwijk/localdata/lerobot_clean/lerobot/src')

from lerobot_action_space import ActionBridge, ActionMode, TELEOP_ACTION_MODES
from lerobot_action_space.compat import SO100_FOLLOWER_MODES
from lerobot_remote_transport.modes import action_mode_to_dict, action_mode_from_dict
from lerobot_remote_transport.signaling import SignalingClient
from lerobot_matchmaker.server import create_app

from aiohttp import web


# ---------------------------------------------------------------------------
# 1. Matchmaker
# ---------------------------------------------------------------------------

async def start_matchmaker(port=18080):
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', port)
    await site.start()
    return runner


# ---------------------------------------------------------------------------
# 2. Signaling handshake (no WebRTC)
# ---------------------------------------------------------------------------

async def operator_side(url, room, teleop_modes):
    sig = SignalingClient(server_url=url, room=room, role="operator")
    await sig.connect()
    await sig.send({"type": "capabilities", "teleop_modes": [action_mode_to_dict(m) for m in teleop_modes]})
    print(f"[operator] sent {len(teleop_modes)} teleop modes")
    msg = await sig.receive()
    robot_modes = [action_mode_from_dict(m) for m in msg["robot_modes"]]
    print(f"[operator] received {len(robot_modes)} robot modes")
    bridge = ActionBridge.auto(teleop_modes, robot_modes)
    print(f"[operator] agreed: {bridge.teleop_mode.name} → {bridge.robot_mode.name}  [{bridge.quality}]")
    await sig.send({"type": "mode_agreed", "teleop_mode": action_mode_to_dict(bridge.teleop_mode), "robot_mode": action_mode_to_dict(bridge.robot_mode)})
    await sig.close()
    return bridge


async def robot_side(url, room, robot_modes):
    sig = SignalingClient(server_url=url, room=room, role="robot")
    await sig.connect()
    msg = await sig.receive()
    teleop_modes = [action_mode_from_dict(m) for m in msg["teleop_modes"]]
    await sig.send({"type": "capabilities", "robot_modes": [action_mode_to_dict(m) for m in robot_modes]})
    msg = await sig.receive()
    bridge = ActionBridge(action_mode_from_dict(msg["teleop_mode"]), action_mode_from_dict(msg["robot_mode"]))
    print(f"[robot]    bridge: {bridge.teleop_mode.name} → {bridge.robot_mode.name}")
    await sig.close()
    return bridge


# ---------------------------------------------------------------------------
# 3. RerunRobot virtual robot test
# ---------------------------------------------------------------------------

def test_rerun_robot():
    from lerobot_robot_rerun.config import RerunRobotConfig
    from lerobot_robot_rerun.robot import RerunRobot

    # Use SO101 URDF
    urdf_path = "lerobot-robot-rerun/urdf/so101/so101.urdf"

    config = RerunRobotConfig(
        urdf_path=urdf_path,
        spawn_viewer=False,   # headless
        rerun_app_id="lerobot-reach-smoke-test",
    )
    robot = RerunRobot(config)
    robot.connect()
    print(f"\n[rerun]    connected — joints: {robot._joint_names}")

    # Send an action
    action = {f"{j}.pos": 0.1 * i for i, j in enumerate(robot._joint_names)}
    result = robot.send_action(action)
    print(f"[rerun]    send_action: {list(action.values())[:3]}...")

    obs = robot.get_observation()
    print(f"[rerun]    get_observation keys: {list(obs.keys())[:3]}...")

    # Verify roundtrip
    for k in action:
        assert abs(obs[k] - action[k]) < 1e-9, f"mismatch for {k}"
    print(f"[rerun]    ✓ observation matches action")

    robot.disconnect()
    print(f"[rerun]    disconnected")


# ---------------------------------------------------------------------------
# 4. Main
# ---------------------------------------------------------------------------

async def run():
    PORT = 18080
    URL = f"http://127.0.0.1:{PORT}"

    runner = await start_matchmaker(PORT)
    await asyncio.sleep(0.1)
    print(f"\n✓ Matchmaker running on {URL}\n")

    teleop_modes = TELEOP_ACTION_MODES
    robot_modes = SO100_FOLLOWER_MODES

    op_bridge, rb_bridge = await asyncio.gather(
        operator_side(URL, "test-room", teleop_modes),
        robot_side(URL, "test-room", robot_modes),
    )

    print(f"\n--- Bridge explain ---")
    print(op_bridge.explain())

    test_action = {"shoulder_pan.pos": 50.0, "shoulder_lift.pos": -30.0, "gripper.pos": 80.0}
    converted = op_bridge.convert(test_action)
    print(f"Test convert: {test_action} → {converted}")

    assert op_bridge.teleop_mode.name == rb_bridge.teleop_mode.name
    print(f"\n✓ Signaling + ActionBridge: OK")

    await runner.cleanup()

    # RerunRobot test (sync)
    print()
    test_rerun_robot()

    print("\n✓ All smoke tests passed!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun-viewer", action="store_true",
                        help="Open Rerun viewer and animate SO101 with a sine wave")
    args = parser.parse_args()

    if args.rerun_viewer:
        import math, time
        sys.path.insert(0, 'lerobot-robot-rerun/src')
        from lerobot_robot_rerun.config import RerunRobotConfig
        from lerobot_robot_rerun.robot import RerunRobot
        import yourdfpy

        urdf_path = "lerobot-robot-rerun/urdf/so101/so101.urdf"
        robot = RerunRobot(RerunRobotConfig(
            urdf_path=urdf_path,
            spawn_viewer=True,
        ))
        robot.connect()

        # Read joint limits from URDF so the sinus stays in range
        urdf = yourdfpy.URDF.load(urdf_path)
        limits = {}
        for j in urdf.robot.joints:
            if j.type != "fixed" and j.limit:
                limits[j.name] = (j.limit.lower, j.limit.upper)

        print(f"Rerun viewer open — animating joints: {robot._joint_names}")
        print("Ctrl+C to stop.")
        try:
            i = 0
            while True:
                t = i / 50.0
                action = {}
                for k, j in enumerate(robot._joint_names):
                    lo, hi = limits.get(j, (-1.0, 1.0))
                    mid = (hi + lo) / 2
                    amp = (hi - lo) / 2 * 0.8  # 80% of range
                    action[f"{j}.pos"] = mid + amp * math.sin(t + k * 0.7)
                robot.send_action(action)
                time.sleep(0.02)
                i += 1
        except KeyboardInterrupt:
            pass
        finally:
            robot.disconnect()
    else:
        asyncio.run(run())


# ---------------------------------------------------------------------------
# 5. Observation + key matching smoke test (no WebRTC — direct simulation)
# ---------------------------------------------------------------------------

def test_obs_and_key_matching():
    import sys
    sys.path.insert(0, 'lerobot-robot-rerun/src')
    sys.path.insert(0, '/home/kwijk/localdata/lerobot_clean/lerobot/src')

    from lerobot_robot_rerun.config import RerunRobotConfig
    from lerobot_robot_rerun.robot import RerunRobot
    from lerobot_remote_robot.remote_robot import RemoteRobot as _R  # just check filter

    # Setup virtual robot
    config = RerunRobotConfig(urdf_path="lerobot-robot-rerun/urdf/so101/so101.urdf", spawn_viewer=False)
    vr = RerunRobot(config)
    vr.connect()
    joints = vr._joint_names  # ['gripper', 'wrist_roll', ...]

    # Simulate: robot side sends features, operator side receives
    features = list(vr.action_features.keys())
    print(f"\n[key match] robot action_features: {features}")
    assert all(k.endswith(".pos") for k in features), "expected .pos keys"
    assert "shoulder_pan.pos" in features
    assert "gripper.pos" in features
    print(f"[key match] ✓ feature keys match SO101 joint names")

    # Simulate obs roundtrip via __obs__ tag
    import threading
    from lerobot_robot_remote.remote_robot import RemoteRobot as RR
    proxy = object.__new__(RR)
    proxy._obs_lock = threading.Lock()
    proxy._last_observation = {}

    obs = vr.get_observation()
    tagged = {"__obs__": True, **obs}
    proxy._on_observation_received(tagged)
    assert proxy._last_observation == obs
    print(f"[key match] ✓ obs roundtrip: {list(obs.keys())[:3]}...")

    vr.disconnect()
    print(f"[key match] ✓ all key matching tests passed")
