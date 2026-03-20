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

## 10. 问答文档补充（运营模式穿墙现象解释）

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么运营模式里会看到无人机穿过灰色墙体”问答；
  - 明确说明当前运营模式使用前端示例轨迹（线性插值动画），尚未接入带避障约束的真实规划/推理轨迹，因此可能出现视觉穿墙。

## 11. 运营模式轨迹生成替换（线性插值 -> A* 避障路径）

- 文件：`web_frontend/src/modules/shared/renderer.js`
- 背景：运营模式动画存在“无人机穿过灰色墙体”的视觉错误。
- 主要修改：
  - 将 `buildSampleRun()` 的轨迹生成从线性插值改为基于障碍地图的 A* 搜索路径；
  - 新增 A* 相关辅助函数：可通行判断、曼哈顿启发、路径重建；
  - 帧数据改为按路径步进生成，并同步计算顶点冲突统计；
  - 指标字段 `tasks_completed`、`throughput`、`vertex_conflicts` 按新轨迹链路重新计算。

- 文件：`解疑.md`
- 主要修改：
  - 将“穿墙现象”问答更新为“原因 + 已修复状态”，避免文档与当前代码不一致。

## 12. 运营模板地图绑定（仓储/园区/应急）

- 文件：`web_frontend/src/modules/shared/renderer.js`
- 主要修改：
  - 为运营模式新增模板配置 `TEMPLATE_CONFIGS`，定义模板对应 `map_name` 与起终点集合；
  - 新增模板障碍生成函数，三类模板使用不同地图布局：
    - `warehouse` -> 货架/通道风格；
    - `campus` -> 园区道路/建筑块风格；
    - `emergency` -> 封锁区/应急通道风格；
  - `buildSampleRun(template)` 支持按模板生成环境与 A* 轨迹，`meta.map_name` 与 `warnings` 同步模板信息。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 切换模板时调用 `buildSampleRun(selectedTemplate)` 重建播放数据；
  - 切换后自动重置帧索引与选中无人机，并重绘画布；
  - 状态文案显示中文模板名，便于运营端识别当前场景。

- 文件：`解疑.md`
- 主要修改：
  - 新增“三个任务模板是否有各自对应地图”问答，记录当前模板映射与切换行为。

## 13. 新增 3D 仿真预览页面（演示骨架）

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 新建“3D仿真预览（演示）”页面，包含场景模板、镜头模式、速度控制、开始/暂停/重置控制；
  - 使用原生 Canvas 实现轻量 3D 占位渲染（透视投影、网格、障碍体线框、无人机动态点）；
  - 页面内补充 3D 技术路线建议卡片（推荐 Three.js，备选 Cesium/Unity）。

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 从双模式扩展为三模式导航；
  - 新增 tab：`3D仿真预览（演示）`，并接入新页面组件。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增 3D 页面布局和卡片样式，适配桌面/移动端。

- 文件：`解疑.md`
- 主要修改：
  - 新增“未来 3D 模拟页面用哪种方式展示更好”问答；
  - 明确推荐技术选型为 `Three.js + glTF + WebSocket`。

## 14. 3D 页面新增“缓慢环绕视角速度”控制

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 新增独立控制项：`环绕速度 (rad/s)`，仅在“环绕观察”镜头下显示；
  - 将相机环绕角速度与仿真时间解耦，不再依赖“仿真速度”间接影响；
  - 新增“环绕周期(秒)”指标，便于调节到慢速演示节奏；
  - 在画面 chip 中展示当前环绕速度，便于录屏和讲解。

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否单独控制缓慢环绕视角速度”问答，说明控制逻辑与指标含义。

## 15. 3D 环绕观察中心锁定修复

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 背景：用户反馈“环绕观察看起来没有绕着地图环绕”。
- 主要修改：
  - 修正 `lookAtCamera` 的 yaw 方向计算符号，使相机在环绕时稳定朝向地图中心；
  - 默认环绕速度由 `0.08` 调整为 `0.12 rad/s`，提升演示可感知性；
  - 保持“仿真速度”和“环绕速度”解耦逻辑不变。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么环绕观察看起来没有绕着地图转”问答，记录原因与修复结论。

## 16. 3D 页面接入 2D 地图与模型推理回放

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 将 3D 页面从“纯占位动画”重构为“2D 回放数据驱动”：
    - 支持调用后端 `runInference`（`/api/run-demo`）加载真实模型回放；
    - 支持加载前端 2D 示例作为兜底演示链路；
  - 基于 `environment + frames` 实现 3D 映射渲染：
    - `obstacles` 转换为 3D 方块；
    - `agents` 与 `target` 转换为 3D 位置与目标圈；
  - 新增模型回放参数输入（`map_name / num_agents / max_frames / device`）和控制按钮；
  - 播放链路改为按回放帧推进，并保留镜头控制（环绕/跟随/俯视）。

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否把现在的 2D 地图和模型推理先跑在 3D 展示里”问答；
  - 明确当前已打通“后端推理 -> 3D 展示”。
