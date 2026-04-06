# lerobot-reach — Machine Setup & Installation

Complete setup guide for deploying lerobot-reach with remote teleoperation on SO101 robot arms.

## Overview

The lerobot-reach umbrella project requires:
1. **OS-level setup**: udev rules for USB serial device aliasing
2. **Python environment**: Miniconda + lerobot 0.5.0 + lerobot-remote plugins
3. **Calibration files**: Pre-flight calibration for SO follower/leader arms
4. **Signaling server**: lerobot-matchmaker running on accessible network port

## Quick Start

### Option 1: Automated Setup (Raspberry Pi / Linux)

Clone the automated setup repository:

```bash
git clone https://github.com/koenvanwijk/teleop_lerobot.git
cd teleop_lerobot
./install.sh
```

This script will:
- Install Miniconda (x86_64 or aarch64)
- Install lerobot 0.5.0 + dependencies
- Download and install udev rules from `mapping.csv`
- Create symlinks like `/dev/tty_pink_follower_so101`

**See `teleop_lerobot/INSTALL.md` for detailed Raspberry Pi instructions.**

### Option 2: Manual Setup (Any Linux / macOS)

#### 1. Install Miniconda

```bash
# Download (choose appropriate architecture)
# Linux x86_64:
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh

# Linux aarch64 (Raspberry Pi):
curl -fsSL https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh -o miniconda.sh

# macOS:
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh -o miniconda.sh

# Install
bash miniconda.sh -b -p $HOME/miniconda3
$HOME/miniconda3/bin/conda init bash
source ~/.bashrc
```

#### 2. Clone lerobot-reach workspace

```bash
git clone https://github.com/koenvanwijk/lerobot-reach.git
cd lerobot-reach
bash bootstrap.sh  # clones sibling repos
```

#### 3. Create Python environment

```bash
conda create -n lerobot python=3.10
conda activate lerobot
pip install -e ./lerobot-action-space
pip install -e ./lerobot-remote
pip install -e ./lerobot-matchmaker
pip install lerobot==0.5.0
```

#### 4. Set up udev rules

Get device serial numbers:

```bash
# List USB serial devices with metadata
for d in /dev/ttyACM* /dev/ttyUSB*; do
  [ -e "$d" ] || continue
  echo "=== $d ==="
  udevadm info -q property -n "$d" | grep -E 'ID_MODEL=|ID_SERIAL_SHORT=|ID_VENDOR='
done
```

Create or update `/etc/udev/rules.d/99-usb-serial-aliases.rules`:

```bash
# For each device, add one line (replace SERIAL_SHORT with actual value):
# Leader (e.g., serial 58FA083461):
sudo tee -a /etc/udev/rules.d/99-usb-serial-aliases.rules > /dev/null <<EOF
SUBSYSTEM=="tty", ENV{ID_BUS}=="usb", ENV{ID_SERIAL_SHORT}=="58FA083461", SYMLINK+="tty_pink_leader_so101", SYMLINK+="tty_leader"
EOF

# Follower (e.g., serial 5A7A055274):
sudo tee -a /etc/udev/rules.d/99-usb-serial-aliases.rules > /dev/null <<EOF
SUBSYSTEM=="tty", ENV{ID_BUS}=="usb", ENV{ID_SERIAL_SHORT}=="5A7A055274", SYMLINK+="tty_pink_follower_so101", SYMLINK+="tty_follower"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Verify (should show symlinks)
ls -la /dev/tty_pink_*
```

Or use the `gen_udev_rules.py` script from `teleop_lerobot`:

```bash
# Create mapping.csv:
cat > /tmp/mapping.csv <<EOF
SERIAL_SHORT,NICE_NAME,ROLE,TYPE
58FA083461,pink,leader,so101
5A7A055274,pink,follower,so101
EOF

# Generate and install rules:
python3 teleop_lerobot/gen_udev_rules.py /tmp/mapping.csv \
  --output /tmp/99-usb-serial-aliases.rules

sudo cp /tmp/99-usb-serial-aliases.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

#### 5. Set up calibration files

Copy pre-computed calibration from another machine or run calibration:

```bash
# Using teleop_lerobot calibration tools:
python3 teleop_lerobot/scripts/calibrate_endstops.py \
  --port /dev/tty_pink_follower_so101 \
  --baud 1000000 \
  --ids 1 2 3 4 5 6 \
  --apply

python3 teleop_lerobot/scripts/calibrate_endstops.py \
  --port /dev/tty_pink_leader_so101 \
  --baud 1000000 \
  --ids 1 2 3 4 5 6 \
  --apply
```

Or copy existing calibration files:

```bash
# From another machine with working calibration:
scp -r user@otherhost:~/.cache/huggingface/lerobot/calibration/robots/so_follower/pink.json \
  ~/.cache/huggingface/lerobot/calibration/robots/so_follower/

scp -r user@otherhost:~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/pink.json \
  ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/
```

---

## Running lerobot-teleoperate

After setup, use three terminals to run the system:

### Terminal 1: Start Matchmaker (signaling server)

```bash
# On any machine with network access from both robot and operator
python -m lerobot_matchmaker \
  --host 0.0.0.0 \
  --port 8080
```

### Terminal 2: Robot side (follower + remote teleop)

```bash
# On the machine connected to follower hardware
conda activate lerobot
lerobot-teleoperate \
  --robot.type=so101_follower \
  --robot.port=/dev/tty_pink_follower_so101 \
  --robot.id=pink \
  --teleop.type=remote_teleop \
  --teleop.id=remote_teleop_pink \
  --teleop.signaling_url=http://192.168.86.25:8080 \
  --teleop.room=so101-pink \
  --display_data=true
```

### Terminal 3: Operator side (remote robot + leader)

```bash
# On the machine connected to leader hardware
conda activate lerobot
lerobot-teleoperate \
  --robot.type=remote_robot \
  --robot.id=remote_robot_pink \
  --robot.signaling_url=http://192.168.86.25:8080 \
  --robot.room=so101-pink \
  --teleop.type=so101_leader \
  --teleop.port=/dev/tty_pink_leader_so101 \
  --teleop.id=pink \
  --display_data=true
```

**Key parameters:**
- `signaling_url`: Must point to matchmaker server (reachable from both sides)
- `room`: Must match exactly on both sides (this is the negotiation point)
- `--robot.id` / `--teleop.id`: Used to load calibration files

---

## Device Discovery

### Find USB serial devices

```bash
# Quick list of likely devices
ls -1 /dev/tty_* /dev/ttyACM* /dev/ttyUSB* 2>/dev/null

# With USB metadata (model/serial)
for d in /dev/tty_* /dev/ttyACM* /dev/ttyUSB*; do
  [ -e "$d" ] || continue
  echo "=== $d ==="
  udevadm info -q property -n "$d" | grep -E 'ID_MODEL=|ID_SERIAL=|ID_VENDOR=|DEVNAME='
done

# LeRobot helper (if installed)
lerobot-find-port
```

### Verify udev symlinks

```bash
# Should show symlinks after rules are loaded
ls -la /dev/tty_pink_* /dev/tty_leader /dev/tty_follower 2>/dev/null
```

---

## Calibration File Locations

LeRobot stores calibration in:

```
~/.cache/huggingface/lerobot/calibration/
├── robots/
│   ├── so_follower/
│   │   └── pink.json           ← robot.id="pink"
│   ├── so_leader/
│   │   └── pink.json
│   └── ...
└── teleoperators/
    ├── so_leader/
    │   └── pink.json           ← teleop.id="pink"
    ├── so_follower/
    │   └── pink.json
    └── ...
```

File loading logic:
```python
calibration_fpath = calibration_dir / f"{self.id}.json"
# Example: ~/.cache/huggingface/lerobot/calibration/robots/so_follower/pink.json
```

**ID recommendations:**
- Use consistent IDs across operator and robot
- Example setup: `robot.id=pink`, `teleop.id=pink`
- Pre-computed calibrations exist at `pink` (check before picking new ID to avoid recalibration)

---

## Troubleshooting

### Udev rules not applying

```bash
# Verify rules file exists and is readable
sudo cat /etc/udev/rules.d/99-usb-serial-aliases.rules

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Check if devices are recognized
udevadm info /dev/ttyACM0  # or /dev/ttyUSB0

# Or use verbose mode
sudo udevadm monitor          # in one terminal
# Then reconnect USB device in another
```

### Symlinks not appearing

```bash
# Unplug USB devices, then:
sudo udevadm control --reload-rules
sudo udevadm trigger

# Plug devices back in
ls -la /dev/tty_*
```

### Port already open error

```bash
# Check if another process is using the port
lsof /dev/tty_pink_follower_so101

# Kill if needed (be careful!)
kill -9 <PID>
```

### Calibration file not found

```bash
# Check if calibration exists
ls ~/.cache/huggingface/lerobot/calibration/robots/so_follower/pink.json

# If missing, run calibration:
python3 teleop_lerobot/scripts/calibrate_endstops.py \
  --port /dev/tty_pink_follower_so101 \
  --ids 1 2 3 4 5 6 \
  --apply
```

### Signaling connection failed

```bash
# Verify matchmaker is running
curl http://192.168.86.25:8080/signal/test/operator/ping

# Expected response: {"status": "pong"} or similar

# Check network connectivity from both sides
ping 192.168.86.25

# Verify room code matches exactly on both sides
```

---

## Related Resources

- **LeRobot**: https://github.com/huggingface/lerobot
- **lerobot-reach**: https://github.com/koenvanwijk/lerobot-reach
- **teleop_lerobot setup**: https://github.com/koenvanwijk/teleop_lerobot
- **SO101 calibration**: `/home/kwijk/.openclaw/workspace/so101-arm-calibration/`

---

## Next Steps

After successful setup:

1. Run `lerobot-teleoperate --help` to see available robot/teleop types
2. Test with `--robot.type=remote_robot --teleop.type=so101_leader` (operator sends commands)
3. Capture demonstrations: `lerobot-record --output /tmp/demo.mdb`
4. Train policies with captured data

See LeRobot 0.5.0 documentation for imitation learning workflows.
