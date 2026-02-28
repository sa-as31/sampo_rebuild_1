#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-smapo:gpu}"
DOCKERFILE="${DOCKERFILE:-Dockerfile.gpu}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ $# -gt 0 ]]; then
  TRAIN_ARGS="$*"
else
  TRAIN_ARGS="${SMAPO_TRAIN_ARGS:---train_for_seconds=300 --num_workers=2 --num_envs_per_worker=2 --worker_num_splits=1 --target_num_agents=256 --num_agents=128 --use_wandb=False}"
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is not installed." >&2
  exit 1
fi

if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi not found. This script requires Linux + NVIDIA driver." >&2
  exit 2
fi

echo "[1/4] Checking NVIDIA runtime on host..."
nvidia-smi >/dev/null

echo "[2/4] Building GPU image: ${IMAGE_NAME} (${DOCKERFILE})..."
docker build -f "${DOCKERFILE}" -t "${IMAGE_NAME}" .

echo "[3/4] Validating container CUDA visibility..."
docker run --rm --gpus all --ipc=host "${IMAGE_NAME}" python scripts/verify_gpu.py

echo "[4/4] Starting training with main_gpu.py..."
docker run --rm --gpus all --ipc=host \
  -e WANDB_MODE=disabled \
  -v "${REPO_ROOT}:/app" \
  -w /app \
  "${IMAGE_NAME}" \
  bash -lc "python main_gpu.py ${TRAIN_ARGS}"
