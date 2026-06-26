#!/usr/bin/env bash
# Pull all AI model files needed for AI FrontDesk.
# Run this ONCE after `docker compose up -d ollama` completes.
# Requires: docker compose up -d ollama (and curl for Piper)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PIPER_DIR="$PROJECT_ROOT/piper-models"

PIPER_VOICE="en_US-lessac-medium"
PIPER_HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"

# ── 1. Pull Qwen3:4b via Ollama ───────────────────────────────────────────────
echo "==> Pulling qwen3:4b into Ollama (this may take 5-10 min on first run)..."
docker compose exec ollama ollama pull qwen3:4b
echo "    qwen3:4b ready."

# ── 2. Download Piper TTS voice model ─────────────────────────────────────────
echo ""
echo "==> Downloading Piper TTS voice: $PIPER_VOICE"
mkdir -p "$PIPER_DIR"

if [ ! -f "$PIPER_DIR/${PIPER_VOICE}.onnx" ]; then
    echo "    Downloading ${PIPER_VOICE}.onnx (~65MB)..."
    curl -L --progress-bar \
        "${PIPER_HF_BASE}/${PIPER_VOICE}.onnx" \
        -o "$PIPER_DIR/${PIPER_VOICE}.onnx"
else
    echo "    ${PIPER_VOICE}.onnx already exists, skipping."
fi

if [ ! -f "$PIPER_DIR/${PIPER_VOICE}.onnx.json" ]; then
    echo "    Downloading ${PIPER_VOICE}.onnx.json..."
    curl -L --progress-bar \
        "${PIPER_HF_BASE}/${PIPER_VOICE}.onnx.json" \
        -o "$PIPER_DIR/${PIPER_VOICE}.onnx.json"
else
    echo "    ${PIPER_VOICE}.onnx.json already exists, skipping."
fi

echo ""
echo "==> All models ready."
echo "    Ollama model : qwen3:4b"
echo "    Piper model  : $PIPER_DIR/${PIPER_VOICE}.onnx"
