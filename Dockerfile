# AI-FABLE — lightweight API/UI proxy in front of Ollama.
# Base: Ubuntu 22.04 LTS, multi-arch (builds natively on amd64 and arm64).
# No CUDA here — the heavy inference runs inside the separate `ollama/ollama`
# container (see docker-compose.yml), which handles its own GPU/CPU
# detection independently of this image.
#
# Deliberately uses the distro's default `python3` (3.10 on Jammy) instead of
# pinning python3.11 from a backport/PPA — that dependency is unnecessary for
# this codebase and made the build fragile / architecture-sensitive on some
# hosts. Fewer external repos = more portable builds.
FROM ubuntu:22.04

LABEL maintainer="AI-FABLE"
LABEL description="Fable AI — web UI + REST proxy for the Gemma-4 12B coder model (via Ollama)"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    python3 \
    python3-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash fable
WORKDIR /app

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/logs && chown -R fable:fable /app

USER fable

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

ENTRYPOINT ["python3", "main.py"]
