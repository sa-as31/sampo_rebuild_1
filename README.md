# SMAPO

本项目为多智能体路径规划与训练代码（基于 Sample Factory + Pogema）。
当前版本已经补齐关键模块，`main.py` 可在 CPU 环境运行，`main_gpu.py` 可用于 GPU 训练入口（无 CUDA 时会自动回退到 CPU）。

## 1. 环境要求

- Python: `3.9`
- 操作系统: Linux/macOS（推荐在 Docker 中运行）
- 可选 GPU: NVIDIA + nvidia-container-toolkit（仅 Docker GPU 运行需要）

## 2. Linux + NVIDIA 一键运行（推荐）

仅适用于 Linux + NVIDIA 驱动已安装的机器。

```bash
bash scripts/run_gpu_one_click.sh
```

自定义训练参数示例：

```bash
bash scripts/run_gpu_one_click.sh \
  --train_for_seconds=600 \
  --num_workers=4 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --use_wandb=False
```

该脚本会自动执行：
1. 检查主机 NVIDIA 驱动可用性（`nvidia-smi`）
2. 构建 GPU 镜像（`Dockerfile.gpu`）
3. 在容器内检查 CUDA 与 PyTorch（`scripts/verify_gpu.py`）
4. 启动 `main_gpu.py` 训练

## 3. 本地运行（不使用 Docker）

### 3.1 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pybind11 cppimport
```

### 3.2 编译规划器扩展

```bash
python -c "import cppimport; cppimport.imp('planner.LB_A.planner')"
python -c "import cppimport; cppimport.imp('planner.Static_A.planner')"
```

### 3.3 CPU 训练（推荐先跑通）

```bash
python main.py \
  --train_for_seconds=30 \
  --num_workers=2 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --use_wandb=False
```

### 3.4 GPU 训练入口

```bash
python main_gpu.py \
  --train_for_seconds=30 \
  --num_workers=2 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --use_wandb=False
```

说明：`main_gpu.py` 默认将 `global_settings.device` 设为 `gpu`。若机器无 CUDA，会在日志中提示并自动切换 CPU。

## 4. Docker 指南

### 4.1 CPU 镜像构建

```bash
docker build -t smapo:local .
```

### 4.2 在 Docker 中运行 CPU 训练

```bash
docker run --rm smapo:local sh -lc "python main.py \
  --train_for_seconds=30 \
  --num_workers=2 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --use_wandb=False"
```

### 4.3 手动构建 GPU 镜像

```bash
docker build -f Dockerfile.gpu -t smapo:gpu .
```

### 4.4 在 Docker 中运行 GPU 训练

```bash
docker run --rm --gpus all --ipc=host smapo:gpu bash -lc "python scripts/verify_gpu.py && python main_gpu.py \
  --train_for_seconds=300 \
  --num_workers=2 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --use_wandb=False"
```

### 4.5 使用 docker compose（GPU）

```bash
docker compose -f docker-compose.gpu.yml up --build
```

### 4.6 使用 docker compose（CPU）

```bash
docker compose up --build
```

## 5. 常见问题

1. 日志出现 Gym 弃用警告
- 这是上游依赖提示，不影响本项目当前训练流程。

2. 报错 `Target num agents must be divisible by num agents`
- 需要保证 `target_num_agents % num_agents == 0`，例如：`256 % 128 == 0`。

3. 训练结果在哪里
- 默认输出目录在 `results/train_dir`。

4. 在 macOS 上能否测试 CUDA？
- 不能。macOS（包括 Apple Silicon）没有 NVIDIA CUDA 运行时。请在 Linux + NVIDIA 环境使用上面的 GPU 一键脚本。
