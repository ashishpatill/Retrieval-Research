#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# ── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'
BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${GREEN}[setup]${NC} $1"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $1"; }
err()   { echo -e "${RED}[error]${NC} $1" >&2; }
header(){ echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}\n"; }

# ── Prerequisite checks ──────────────────────────────────────────────────────
header "Checking prerequisites"

MISSING=0
for cmd in python3 node npm; do
    if ! command -v "$cmd" &>/dev/null; then
        err "Missing: $cmd — install it first"
        MISSING=1
    fi
done
[ "$MISSING" -eq 1 ] && exit 1
log "python3 $(python3 --version 2>&1)"
log "node    $(node --version)"
log "npm     $(npm --version)"

# ── Virtual environment ──────────────────────────────────────────────────────
header "Python environment"

if [ ! -d .venv ]; then
    python3 -m venv .venv
    log "Created virtual environment"
else
    log "Virtual environment already exists"
fi

source .venv/bin/activate
python3 -m pip install --upgrade pip -q
python3 -m pip install -r requirements.txt -q
python3 -m pip install pytest pytest-cov -q
log "Python dependencies installed"

# ── Environment file ─────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    warn "Created .env from .env.example — add your GEMINI_API_KEY if needed"
else
    log ".env already exists"
fi

# ── Frontend dependencies ────────────────────────────────────────────────────
header "Frontend (Next.js)"

cd apps/web
npm install --silent 2>/dev/null || npm install
log "Node dependencies installed"
cd "$ROOT"

# ── Data directory ───────────────────────────────────────────────────────────
mkdir -p data data/jobs data/runs data/generated
log "Data directories ready"

# ── Done ─────────────────────────────────────────────────────────────────────
header "Setup complete"

echo -e "  ${BOLD}Start the backend:${NC}"
echo -e "    ${CYAN}source .venv/bin/activate${NC}"
echo -e "    ${CYAN}python3 -m uvicorn retrieval_research.api:app --host 127.0.0.1 --port 8000 --reload${NC}"
echo ""
echo -e "  ${BOLD}Start the frontend (another terminal):${NC}"
echo -e "    ${CYAN}cd apps/web${NC}"
echo -e "    ${CYAN}NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 npm run dev${NC}"
echo ""
echo -e "  ${BOLD}Open:${NC} ${CYAN}http://localhost:3000${NC}"
echo ""
echo -e "  ${BOLD}Run background worker (optional):${NC}"
echo -e "    ${CYAN}python3 -m retrieval_research.cli worker${NC}"
echo ""
echo -e "  ${BOLD}Run tests:${NC}"
echo -e "    ${CYAN}PYTHONPATH=. pytest tests/ -v${NC}"
echo ""
