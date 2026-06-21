#!/usr/bin/env bash
# Stop all services started by scripts/start.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.pids"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

if [ ! -f "$PID_FILE" ]; then
  echo -e "${YELLOW}No .pids file found — nothing to stop.${NC}"
  exit 0
fi

echo "Stopping services..."
while IFS= read -r pid; do
  [ -z "$pid" ] && continue
  if kill "$pid" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Stopped PID $pid"
  else
    echo "  PID $pid already stopped"
  fi
done < "$PID_FILE"

rm -f "$PID_FILE"
echo -e "${GREEN}Done.${NC}"
