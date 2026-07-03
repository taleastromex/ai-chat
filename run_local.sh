#!/bin/bash
# Run AI-FABLE directly on macOS using a native Ollama install.
#
# Why Ollama instead of transformers/PyTorch?
# The huihui-ai/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated
# model declares a "gemma4_unified" architecture that does not exist in the
# transformers library (there is no official "Gemma 4" from Google, and the
# repo ships no custom modeling code). The only working way to run it is via
# a GGUF quantization through Ollama or llama.cpp — which is exactly what
# this script sets up. Ollama also uses Apple's Metal/MPS GPU natively when
# installed directly on macOS (Docker Desktop cannot access the GPU at all).
#
# Usage:
#   chmod +x run_local.sh
#   ./run_local.sh

set -e

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${CYAN}→  $*${NC}"; }
success() { echo -e "${GREEN}✔  $*${NC}"; }
warn()    { echo -e "${YELLOW}⚠  $*${NC}"; }
die()     { echo -e "${RED}✖  $*${NC}"; exit 1; }

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}  AI-FABLE — macOS (native, via Ollama)${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# ── Install Ollama if missing ────────────────────────────────────────────────
if ! command -v ollama &>/dev/null; then
  if command -v brew &>/dev/null; then
    info "Installing Ollama via Homebrew..."
    brew install ollama
  else
    die "Ollama not found and Homebrew is not installed. Install Ollama manually from https://ollama.com/download"
  fi
fi
success "Ollama found: $(ollama --version 2>&1 | head -n1)"

# ── Start the Ollama server if not already running ──────────────────────────
if curl -s http://localhost:11434 &>/dev/null; then
  success "Ollama server is already running"
else
  info "Starting Ollama server in the background..."
  nohup ollama serve > /tmp/ollama-ai-fable.log 2>&1 &
  disown
  for i in $(seq 1 20); do
    curl -s http://localhost:11434 &>/dev/null && break
    sleep 1
  done
  curl -s http://localhost:11434 &>/dev/null \
    && success "Ollama server started (logs: /tmp/ollama-ai-fable.log)" \
    || die "Ollama server failed to start. Check /tmp/ollama-ai-fable.log"
fi

# ── Python virtual environment for the lightweight proxy ────────────────────
PYTHON=""
for candidate in python3.12 python3.11 python3.10 python3.9 python3; do
  if command -v "$candidate" &>/dev/null; then PYTHON="$candidate"; break; fi
done
[ -z "$PYTHON" ] && die "Python 3 not found. Install via: brew install python@3.11"

if [ ! -d ".venv" ]; then
  info "Creating virtual environment..."
  $PYTHON -m venv .venv
fi

source .venv/bin/activate
success "Virtual environment activated: $(python --version)"

info "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
success "Dependencies installed"

# ── Load .env ────────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  warn ".env not found — copying from .env.example"
  cp .env.example .env
fi

export $(grep -v '^#' .env | xargs)
export OLLAMA_HOST="http://localhost:11434"
success "Environment loaded — model: ${OLLAMA_MODEL}"

echo ""
info "Starting AI-FABLE server at http://localhost:8080"
info "The model (~7 GB in Q4_K_M) will download automatically on first run."
info "Open the URL above — you'll see a loading page until it's ready."
echo ""

python main.py
