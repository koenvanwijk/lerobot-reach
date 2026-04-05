#!/usr/bin/env bash
# bootstrap.sh — clone the full lerobot-reach workspace on a new machine
#
# Usage:
#   mkdir -p ~/projects && cd ~/projects
#   curl -fsSL https://raw.githubusercontent.com/koenvanwijk/lerobot-reach/main/bootstrap.sh | bash
#
# Or manually:
#   git clone https://github.com/koenvanwijk/lerobot-reach
#   cd lerobot-reach && bash bootstrap.sh

set -euo pipefail

WORKDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Setting up lerobot-reach workspace in: $WORKDIR"

repos=(
  "https://github.com/koenvanwijk/lerobot-action-space"
  "https://github.com/koenvanwijk/lerobot-remote"
  "https://github.com/koenvanwijk/lerobot-matchmaker"
  "https://github.com/koenvanwijk/lerobot-robot-rerun"
)

for repo in "${repos[@]}"; do
  name="$(basename "$repo")"
  if [ -d "$WORKDIR/$name/.git" ]; then
    echo "  ✓ $name — already cloned, pulling latest"
    git -C "$WORKDIR/$name" pull --ff-only
  else
    echo "  → cloning $name"
    git clone "$repo" "$WORKDIR/$name"
  fi
done

echo ""
echo "Done. Workspace:"
echo "  $WORKDIR/"
echo "  ├── lerobot-action-space/"
echo "  ├── lerobot-remote/"
echo "  └── lerobot-matchmaker/"
echo ""
echo "Open Claude Code from $WORKDIR to get full cross-repo context."
