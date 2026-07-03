# AI-FABLE

> Web chat + REST API for **[huihui-ai/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated](https://huggingface.co/huihui-ai/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated)**, served through **Ollama**.

---

## ⚠️ Important: why this uses Ollama, not `transformers`

The model repo declares its architecture as `gemma4_unified` / `Gemma4UnifiedForConditionalGeneration`. **This architecture does not exist in the `transformers` library** — Google has only ever released Gemma, Gemma2, and Gemma3; there is no official "Gemma 4". The repo also ships **no custom modeling code**, so `trust_remote_code=True` cannot help either. The "how to use" code snippets shown on the model's HuggingFace page (`AutoModelForMultimodalLM`, `Gemma4Processor`) reference classes that don't exist anywhere — that page is auto-generated and simply wrong for this repo.

The only way people actually run this model is through a **GGUF quantization** (a self-contained tensor format with an embedded chat template) via an engine like **llama.cpp** or **Ollama**, which don't care what the original architecture is called. That's exactly what this project does:

```
Browser  →  AI-FABLE (FastAPI proxy + web UI)  →  Ollama (runs the GGUF model)
```

---

## Contents

- [Requirements](#requirements)
- [Project Structure](#project-structure)
- [Quick Start — Docker (any OS, recommended)](#quick-start--docker-any-os-recommended)
- [Quick Start — macOS native (max GPU perf)](#quick-start--macos-native-max-gpu-perf)
- [Configuration](#configuration)
- [Web Interface](#web-interface)
- [API Reference](#api-reference)
- [Choosing a quantization](#choosing-a-quantization)
- [Portability notes](#portability-notes)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| | Docker (any OS) | macOS native |
|---|---|---|
| Docker | 24.x+ with Compose v2 | not needed |
| Ollama | runs in its own container | installed by `run_local.sh` (Homebrew) |
| GPU | NVIDIA + Container Toolkit (Linux only, optional) | Apple Silicon Metal — automatic |
| RAM/VRAM | 8 GB+ free (Q4_K_M) | 8 GB+ free (Q4_K_M) |
| Disk | ~7 GB for the model | ~7 GB for the model |
| Architecture | amd64 or arm64 — both supported | Apple Silicon or Intel |

> **Docker Desktop on macOS/Windows cannot access any GPU** — not NVIDIA, not Apple Silicon. That's a platform limitation of Docker Desktop itself, not something a compose file can work around. On a Mac, use `run_local.sh` for GPU acceleration; on a GPU Linux box, use Docker with the GPU override.

---

## Project Structure

```
AI-model/
├── deploy.sh                 # universal launcher — auto-detects GPU, same command on any OS
├── Dockerfile                 # lightweight Ubuntu image for the proxy/UI (no CUDA, multi-arch)
├── docker-compose.yml         # base stack — Ollama + AI-FABLE, CPU-safe, works everywhere
├── docker-compose.gpu.yml     # additive override — enables NVIDIA GPU (Linux only)
├── run_local.sh               # macOS native setup — installs Ollama, runs proxy directly
├── main.py                    # thin entrypoint — `python main.py` (used by Docker/run_local.sh)
├── app/                        # the actual application (see "Architecture" below)
│   ├── main.py                 # FastAPI app factory (`create_app`)
│   ├── config.py                # Settings (pydantic-settings, reads env vars / .env)
│   ├── enums.py                  # ModelStatus enum
│   ├── state.py                   # thread-safe AppState (model loading lifecycle)
│   ├── schemas.py                  # Pydantic request/response models
│   ├── dependencies.py              # FastAPI dependency providers
│   ├── logging_config.py             # loguru setup
│   ├── routers/
│   │   ├── system.py                  # /, /health, /info, /ready
│   │   └── generate.py                 # /generate, /generate/vision(+/upload)
│   └── services/
│       ├── ollama_client.py            # HTTP client for the Ollama API
│       └── model_loader.py              # background pull/readiness workflow
├── tests/                       # pytest suite (unit + route tests, no real network calls)
├── static/
│   ├── index.html              # Chat web UI
│   └── loading.html            # Animated loading / model-download page
├── pyproject.toml               # ruff / mypy / pytest configuration
├── requirements.txt              # runtime dependencies (used by the Docker image)
├── requirements-dev.txt           # + ruff, mypy, pytest, respx
├── .env.example                    # fully optional — compose has working defaults without it
└── .env                             # your local overrides (not committed)
```

---

## Architecture

The app follows a fairly standard layered FastAPI structure:

```
routers/  (HTTP layer — request/response only, no business logic)
   ↓ depends on
services/ (business logic — OllamaClient, background model loader)
   ↓ depends on
state.py + config.py (shared, injectable state and configuration)
```

A few deliberate choices worth calling out:

- **No module-level globals for mutable state.** The old version used top-level `model_status`/`model_error` variables mutated from a background thread — not thread-safe, and impossible to isolate in tests. `AppState` now encapsulates that behind a lock, and is attached to `app.state` per FastAPI instance instead of being a process-wide singleton.
- **Dependency injection via `Depends`, not imports.** Routers never import `OllamaClient` or `AppState` instances directly — they receive them through `app/dependencies.py`. This is what lets tests swap in mocks with `app.dependency_overrides` instead of monkeypatching module attributes.
- **`create_app()` factory instead of a bare module-level `app`.** Tests (and anything else that wants a fresh instance, e.g. multiple workers with different config) call `create_app(settings, start_background_loader=False)` rather than importing a singleton.
- **Settings via `pydantic-settings`** instead of scattered `os.getenv(...)` calls — one typed, validated source of truth for configuration.
- **Enums instead of magic strings** for the model lifecycle (`ModelStatus`), so typos like `"raedy"` fail at typecheck/import time instead of silently comparing `False`.

---

## Quick Start — Docker (any OS, recommended)

Works identically on Linux, macOS, and Windows (WSL2), on amd64 or arm64 — no OS-specific setup required.

```bash
cd /Users/admin/projects/AI-model
./deploy.sh
```

`deploy.sh` automatically:
1. Checks Docker/Compose are installed
2. Detects whether a usable NVIDIA GPU is reachable from Docker (Linux only) and layers `docker-compose.gpu.yml` on top when it is — otherwise runs CPU-only
3. Builds and starts both containers (`AI-FABLE-ollama` + `AI-FABLE`)

```bash
./deploy.sh          # start (default)
./deploy.sh logs     # follow logs from both containers
./deploy.sh restart  # restart both services
./deploy.sh down     # stop and remove containers
```

Open **`http://localhost:8080`** — a loading page shows progress while the ~7 GB GGUF model downloads (one-time, cached in a Docker volume), then it redirects to the chat UI automatically.

### Manual equivalent (no script)

```bash
# CPU-only, any device
docker compose up --build -d

# With NVIDIA GPU (Linux + Container Toolkit installed)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d
```

### Installing the NVIDIA Container Toolkit (Linux, optional)

Only needed if you want GPU acceleration via Docker on a Linux host:

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

---

## Quick Start — macOS native (max GPU perf)

Docker Desktop can't reach the Apple Silicon GPU, so for maximum performance on a Mac, run Ollama natively instead of in Docker:

```bash
cd /Users/admin/projects/AI-model
./run_local.sh
```

This installs Ollama via Homebrew, starts it natively (full Metal GPU acceleration), and runs the lightweight proxy in a local virtualenv.

---

## Configuration

`.env` is **entirely optional** — `docker-compose.yml` already has working defaults for everything. Copy `.env.example` only if you want to override something:

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `hf.co/mradermacher/...-GGUF:Q4_K_M` | GGUF model + quant tag to pull and run |
| `PORT` | `8080` | Host port for the AI-FABLE web UI / API |
| `OLLAMA_PORT` | `11434` | Host port for Ollama's own API |
| `LOG_LEVEL` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |
| `OLLAMA_HOST` | `http://localhost:11434` | Only used by `run_local.sh` — Docker always uses the internal service name automatically |

---

## Web Interface

Open `http://localhost:8080`:

- **Text chat** with adjustable max tokens, temperature, top-p, system prompt
- **Image attachment** (📎) for multimodal prompts
- **Live status sidebar** — server state, backend, active quantization
- **Clear chat** button

---

## API Reference

Interactive docs at `http://localhost:8080/docs`.

### `GET /health`
```bash
curl http://localhost:8080/health
```
```json
{ "status": "ok", "model_loaded": true, "model_status": "ready", "progress": null, "error": null }
```

### `GET /info`
```bash
curl http://localhost:8080/info
```

### `POST /generate`
```bash
curl -X POST http://localhost:8080/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a Python function to merge two sorted lists.", "max_new_tokens": 512}'
```

### `POST /generate/vision` (image URL or base64)
```bash
curl -X POST http://localhost:8080/generate/vision \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Describe this image.", "image_url": "https://example.com/photo.jpg"}'
```

### `POST /generate/vision/upload` (file upload)
```bash
curl -X POST http://localhost:8080/generate/vision/upload \
  -F "prompt=What do you see?" \
  -F "file=@/path/to/image.jpg"
```

---

## Choosing a quantization

Set `OLLAMA_MODEL` in `.env` to any of these tags (from [mradermacher's GGUF repo](https://huggingface.co/mradermacher/Huihui-gemma-4-12B-coder-fable5-composer2.5-v1-abliterated-GGUF)):

| Tag | Size | Notes |
|---|---|---|
| `Q4_K_S` | ~7.1 GB | fast, recommended |
| `Q4_K_M` | ~7.5 GB | fast, recommended (default) |
| `Q5_K_M` | ~8.6 GB | better quality |
| `Q6_K` | ~9.9 GB | very good quality |
| `Q8_0` | ~12.8 GB | best quality, slowest |

After changing it, restart:
```bash
./run_local.sh
# or
./deploy.sh restart
```

---

## Development

Install dev dependencies (adds `ruff`, `mypy`, `pytest`, `respx` on top of the runtime requirements):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the checks used to validate this project:

```bash
ruff check .          # lint
ruff format .         # auto-format
mypy app/ main.py     # type-check
pytest                # unit + route tests (no real network calls; Ollama is always mocked)
```

The test suite never talks to a real Ollama server — `create_app(..., start_background_loader=False)` skips the background pull thread entirely, and individual tests inject fake `AppState`/`OllamaClient` instances via `app.dependency_overrides`.

---

## Portability notes

This project is designed so the **same Docker Compose setup runs unmodified on any device**:

- **Single base compose file** (`docker-compose.yml`) is CPU-safe and works on any host — no GPU drivers required. GPU support is purely additive via `docker-compose.gpu.yml`, never required.
- **No hard dependency on `.env`** — every variable has a working default baked into `docker-compose.yml` via `${VAR:-default}` interpolation. A missing `.env` file no longer breaks startup (previously `env_file: .env` would fail outright if the file didn't exist).
- **Logs use a named Docker volume**, not a host bind-mount — avoids UID/permission mismatches between host and container that show up differently on Linux, macOS, and Windows. Inspect with `docker compose logs -f ai-fable` or `./deploy.sh logs`.
- **`Dockerfile` only depends on Ubuntu 22.04's default `python3`** — no PPA / backport repositories. That removes an external-network dependency and an architecture-specific package availability risk during `docker build`, so builds are reliable on both `amd64` and `arm64` (the `ubuntu:22.04` and `ollama/ollama` images are both multi-arch).
- **`deploy.sh` is the single entrypoint** — it detects GPU availability itself, so you never need to remember which compose file(s) to pass on a given machine.
- **`run_local.sh` remains as an opt-in, non-Docker fast path** for Apple Silicon Macs specifically, since Docker Desktop cannot access that GPU at all. It is not required for portability — Docker is the primary, unified deployment path.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'torch'` / import errors from `transformers`
You're looking at an old version of this project. The current version doesn't use `torch` or `transformers` at all — it proxies to Ollama. Pull the latest files and re-run `./run_local.sh`.

### `Unrecognized processing class` / `AutoModelForMultimodalLM` import errors
Same root cause — see the [warning at the top](#️-important-why-this-uses-ollama-not-transformers) of this README. This is why the project now uses Ollama.

### `could not select device driver "nvidia"`
This means the GPU override (`docker-compose.gpu.yml`) was applied on a host without a working NVIDIA Container Toolkit. Either install the toolkit (see above) or just run `docker compose up --build -d` (base file only, no GPU) / `./deploy.sh`, which only adds the GPU override when it detects one actually works.

### Browser shows connection refused
The server starts instantly, but Ollama needs to download the model on first run. Open `http://localhost:8080` — you'll see a loading page that polls `/ready` and redirects automatically once the model is available.

### Check what's happening
```bash
# macOS native
tail -f logs/server.log
tail -f /tmp/ollama-ai-fable.log

# Docker
./deploy.sh logs
# or individually:
docker logs AI-FABLE -f
docker logs AI-FABLE-ollama -f
```

### Restart everything
```bash
# macOS native
pkill ollama; ./run_local.sh

# Docker (quick restart)
./deploy.sh restart

# Docker (full reset, including downloaded model)
./deploy.sh down
docker volume rm ai-model_ollama-data ai-model_ai-fable-logs
./deploy.sh
```
