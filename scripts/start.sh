#!/usr/bin/env bash
# Usage: ./scripts/start.sh [dev|staging|prod]

ENV="${1:-dev}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$ROOT_DIR/.pids"

# ── Colors ────────────────────────────────────────────────────────
BLUE='\033[0;34m'; GREEN='\033[0;32m'
YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()     { echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $*"; }
success() { echo -e "${GREEN}[$(date +%H:%M:%S)] ✓${NC} $*"; }
warn()    { echo -e "${YELLOW}[$(date +%H:%M:%S)] !${NC} $*"; }
error()   { echo -e "${RED}[$(date +%H:%M:%S)] ✗${NC} $*"; exit 1; }

# ── Validate env ──────────────────────────────────────────────────
case "$ENV" in
  dev|staging|prod) ;;
  *) error "Unknown environment '$ENV'. Usage: $0 [dev|staging|prod]" ;;
esac

# ── Guard: already running? ───────────────────────────────────────
if [ -f "$PID_FILE" ]; then
  warn "Found existing .pids — services may already be running."
  warn "Run './scripts/stop.sh' first, or press Enter to continue anyway."
  read -r
fi

echo ""
log "============================================================"
log " Radixweb RAG  |  env: $ENV"
log "============================================================"
echo ""

# ── Python environment detection ──────────────────────────────────
UVICORN=""

if [ -f "$ROOT_DIR/.venv/bin/uvicorn" ]; then
  source "$ROOT_DIR/.venv/bin/activate" || true
  UVICORN="$ROOT_DIR/.venv/bin/uvicorn"
  log "Python env: .venv"
elif command -v conda &>/dev/null && conda env list 2>/dev/null | grep -q "^llms "; then
  eval "$(conda shell.bash hook 2>/dev/null)" || true
  conda activate llms || true
  UVICORN="$(which uvicorn 2>/dev/null)"
  log "Python env: conda (llms)"
else
  UVICORN="$(which uvicorn 2>/dev/null)"
  log "Python env: system"
fi

[ -z "$UVICORN" ] && error "uvicorn not found. Activate a venv or conda env first."

# ── npm path (stable even after venv activation) ──────────────────
NPM="$(which npm 2>/dev/null)" || error "npm not found. Install Node.js first."

# ── PID tracking + cleanup ────────────────────────────────────────
> "$PID_FILE"

cleanup() {
  echo ""
  log "Shutting down..."
  if [ -f "$PID_FILE" ]; then
    while IFS= read -r pid; do
      [ -z "$pid" ] && continue
      kill "$pid" 2>/dev/null && log "Stopped PID $pid" || true
    done < "$PID_FILE"
    rm -f "$PID_FILE"
  fi
  success "All services stopped."
}
trap cleanup EXIT INT TERM

# ── Backend ───────────────────────────────────────────────────────
cd "$ROOT_DIR"

case "$ENV" in
  dev)     "$UVICORN" api:app --host 0.0.0.0 --port 8000 --reload & ;;
  staging) "$UVICORN" api:app --host 0.0.0.0 --port 8000 --workers 2 & ;;
  prod)    "$UVICORN" api:app --host 0.0.0.0 --port 8000 --workers 4 & ;;
esac
BACKEND_PID=$!
echo "$BACKEND_PID" >> "$PID_FILE"
success "Backend started  →  http://localhost:8000  (PID $BACKEND_PID)"
success "API docs         →  http://localhost:8000/docs"

# ── Frontend ──────────────────────────────────────────────────────
cd "$ROOT_DIR/frontend"

# Reinstall if node_modules is missing OR if the next binary lacks execute permission
if [ ! -d "node_modules" ] || [ ! -x "node_modules/.bin/next" ]; then
  log "Installing frontend dependencies..."
  "$NPM" install
fi

# Always ensure all .bin/* scripts are executable — npm install doesn't
# re-chmod existing files, so this fixes stale permission issues.
chmod +x node_modules/.bin/* 2>/dev/null || true

case "$ENV" in
  dev)
    log "Starting frontend on :3000  (next dev)"
    "$NPM" run dev &
    ;;
  staging|prod)
    log "Building frontend (next build)..."
    "$NPM" run build
    log "Starting frontend on :3000  (next start)"
    "$NPM" run start &
    ;;
esac
FRONTEND_PID=$!
echo "$FRONTEND_PID" >> "$PID_FILE"
success "Frontend started →  http://localhost:3000  (PID $FRONTEND_PID)"

echo ""
success "All services running in $ENV mode. Press Ctrl+C to stop."
echo ""

wait
