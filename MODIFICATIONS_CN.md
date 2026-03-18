# 项目修改说明（中文）

本文档记录我基于原始项目所做的主要修改，目标是让项目在 Docker/CPU 环境可稳定运行，并补充 GPU 入口。

## 1. 依赖与容器化

### 1.1 新增/补全依赖
- 文件：`requirements.txt`
- 主要内容：
  - 固定兼容版本：`numpy<2`、`gym==0.23.1`、`pydantic<2`
  - 补充训练与日志依赖：`torch`、`ray[tune]`、`wandb`、`tensorboard`、`tensorboardX`、`faster-fifo`、`threadpoolctl` 等

### 1.2 完成 Docker 构建流程
- 文件：`Dockerfile`
- 主要修改：
  - 基础镜像改为 `python:3.9-slim`
  - 安装 C++ 编译所需系统依赖（`build-essential`、`g++`、`libgl1`、`libglib2.0-0`）
  - 安装 Python 依赖 + `pybind11` + `cppimport`
  - 构建期预编译两个规划器扩展：
    - `planner.LB_A.planner`
    - `planner.Static_A.planner`

## 2. 论文相关功能补全

### 2.1 新增重规划算法模块
- 文件：
  - `planning/replan_algo.py`
  - `planning/__init__.py`
- 主要实现：
  - `RePlanBase`
  - `NoPathSoRandomOrStayWrapper`
  - `FixNonesWrapper`
- 核心思路：
  - 按论文思路加入拥堵相关代价建模（PlCC/PeCC），用于多智能体重规划与冲突缓解。

## 3. Sample Factory 兼容与运行修复

### 3.1 补全缺失空间类型
- 文件：
  - `sample_factory/algorithms/utils/spaces/discretized.py`
  - `sample_factory/algorithms/utils/spaces/__init__.py`
- 作用：补全 `Discretized`，修复动作空间导入与类型判断链路。

### 3.2 修复 APPO 相关运行问题
- 文件：
  - `sample_factory/algorithms/appo/model.py`
  - `sample_factory/algorithms/appo/model_utils.py`
  - `sample_factory/algorithms/appo/learner.py`
  - `sample_factory/algorithms/appo/policy_worker.py`
  - `sample_factory/algorithms/appo/appo.py`
- 主要修改：
  - 去除不可用导入（`create_atten_layer`）导致的启动问题
  - 修复部分硬编码 `.cuda()` 带来的 CPU 运行崩溃，改为设备自适应
  - 在 GPU 不可用时自动回退 CPU（主流程、learner、policy worker）
  - 为注意力模块缺省参数补充默认值（`num_heads`）

## 4. 新增 GPU 训练入口

- 文件：`main_gpu.py`
- 说明：
  - 逻辑与 `main.py` 基本一致
  - 默认强制 `global_settings.device = "gpu"`
  - 可通过命令行参数继续覆盖其余配置

## 5. 运行验证结果

已在 Docker 中完成如下验证：

1. CPU 主流程（`main.py`）
- 能完成初始化、采样、训练流程并正常退出（退出码 `0`）。

2. 较大规模 CPU 测试
- 使用 `num_workers=2`、`num_envs_per_worker=2`、`target_num_agents=256`、`num_agents=128` 测试通过（退出码 `0`）。

3. GPU 入口文件（`main_gpu.py`）
- 在无 CUDA 的容器中可正确启动，并触发自动回退到 CPU，流程可正常结束（退出码 `0`）。

## 6. 新增文档

- `README.md`：补充本地运行、Docker 运行、GPU 运行和常见问题说明。

## 7. Linux + NVIDIA 一键 GPU 链路补全

为满足“在 Linux + NVIDIA 环境一键直接跑”的目标，新增如下文件：

1. `Dockerfile.gpu`
- 基于 `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`
- 明确安装 CUDA 版 PyTorch（`torch==2.3.1` + `cu121`）
- 构建期预编译规划器扩展（LB_A / Static_A）

2. `docker-compose.gpu.yml`
- 提供独立 GPU compose 服务（`gpus: all`、`ipc: host`）
- 启动前先执行容器内 GPU 检查脚本，再运行 `main_gpu.py`

3. `scripts/verify_gpu.py`
- 在容器内校验：
  - `torch` 是否为 CUDA 构建
  - CUDA runtime 是否可用
  - 是否存在可见 GPU
- 失败会返回非 0 退出码，避免“误以为在 GPU 上训练”

4. `scripts/run_gpu_one_click.sh`
- 一键脚本（Linux + NVIDIA）：
  - 检查 `nvidia-smi`
  - 构建 GPU 镜像
  - 运行 `verify_gpu.py`
  - 启动 `main_gpu.py` 训练
- 支持直接透传训练参数，便于快速复现实验

## 8. 文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“这个项目如何用两句话写进简历”问答
  - 沉淀一版适合简历使用的项目描述，便于后续复用

## 9. 运营模式动画回放逻辑修复

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 背景：运营模式在到达末帧后会回到第 0 帧，导致用户观察到“任务完成后又播放一遍”。
- 主要修改：
  - 抽离 `tickOpsFrame()` 统一推进帧逻辑；
  - 到达末帧时停止定时器并保持在末帧，不再循环回卷；
  - `opsStatus` 在末帧结束时显示“任务已完成”；
  - 补充无帧/单帧场景提示（“暂无可播放轨迹”或直接完成）。

- 文件：`解疑.md`
- 主要修改：
  - 新增“运营模式里为什么到终点后又播放了一遍动画”问答；
  - 记录已落地修复行为，便于后续答辩和排障复盘。
