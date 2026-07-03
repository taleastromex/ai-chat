#!/bin/bash
# AI-FABLE — universal Docker deployment launcher.
#
# Same command on any device: Linux, macOS, Windows (WSL2), amd64 or arm64.
# Automatically detects whether an NVIDIA GPU + Container Toolkit is usable
# from within Docker and layers docker-compose.gpu.yml on top when it is.
#
# Usage:
#   ./deploy.sh              # start (build if needed)
#   ./deploy.sh down         # stop and remove containers
#   ./deploy.sh logs         # follow logs
#   ./deploy.sh restart      # restart both services

set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${CYAN}→  $*${NC}"; }
success() { echo -e "${GREEN}✔  $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $*${NC}"; }
die()     { echo -e "${RED}✖  $*${NC}"; exit 1; }

cd "$(dirname "$0")"

command -v docker &>/dev/null || die "Docker is not installed. See: https://docs.docker.com/get-docker/"
docker compose version &>/dev/null || die "Docker Compose v2 is required (bundled with modern Docker Desktop / Docker Engine)."

COMPOSE_FILES=(-f docker-compose.yml)

detect_gpu() {
  # Docker Desktop on macOS/Windows never exposes a GPU to containers —
  # skip the check entirely there to avoid a slow, pointless probe.
  case "$(uname -s)" in
    Darwin) return 1 ;;
  esac

  command -v nvidia-smi &>/dev/null || return 1
  nvidia-smi &>/dev/null || return 1

  # Confirm the Docker daemon itself can actually reach the GPU
  docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi &>/dev/null
}

ACTION="${1:-up}"

case "$ACTION" in
  down)
    info "Stopping AI-FABLE..."
    docker compose -f docker-compose.yml down
    success "Stopped"
    exit 0
    ;;
  logs)
    docker compose -f docker-compose.yml logs -f
    exit 0
    ;;
  restart)
    info "Restarting AI-FABLE..."
    docker compose -f docker-compose.yml restart
    success "Restarted"
    exit 0
    ;;
  up|"")
    ;;
  *)
    die "Unknown action: $ACTION (expected: up | down | logs | restart)"
    ;;
esac

if detect_gpu; then
  success "NVIDIA GPU detected and reachable from Docker — enabling GPU acceleration"
  COMPOSE_FILES+=(-f docker-compose.gpu.yml)
else
  warn "No usable NVIDIA GPU found in Docker — running in CPU mode"
  warn "On Apple Silicon Macs, use ./run_local.sh instead for native Metal GPU acceleration"
fi

if [ ! -f .env ]; then
  info "No .env found — creating one from .env.example"
  cp .env.example .env
fi

info "Starting AI-FABLE (docker compose ${COMPOSE_FILES[*]} up --build -d)"
docker compose "${COMPOSE_FILES[@]}" up --build -d

echo ""
docker compose -f docker-compose.yml ps
echo ""
success "AI-FABLE is starting up."
echo "   Open:        http://localhost:8080"
echo "   Follow logs: ./deploy.sh logs"
echo "   Stop:        ./deploy.sh down"
echo ""
warn "First run downloads the GGUF model (several GB) — this can take a while."
