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

## 16. 训练输入维度概念澄清文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“把模型感知范围改成 `11 x 11 x 4` 里的 `4` 代表什么”问答；
  - 明确说明这里的 `4` 指的是 4 个观测通道，而不是 4 层空间高度；
  - 同时记录当前项目训练主输入更接近 `2 x 11 x 11`，便于后续讨论是否扩成 4 通道。

## 17. 二维环境与三维升降改造范围说明文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“想让无人机可以上下移动，需要改什么”问答；
  - 明确说明当前项目训练环境本质上是二维栅格；
  - 记录若要支持真实升降飞行，需要同时修改动作空间、状态坐标、局部观测、规划器、训练与前端回放链路。

## 18. SMAPO 论文适用场景与二维抽象原因说明文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“SMAPO 这类训练框架主要是为了解决什么场景的问题，为什么只有 2D”问答；
  - 说明该框架主要面向 MAPF / LMAPF 类长期多智能体协同导航问题；
  - 澄清当前项目虽然可类比无人机调度，但训练主链路仍采用二维离散路径规划抽象；
  - 总结 2D 设定的原因包括问题建模、训练成本、基准数据和论文关注点等。

## 19. 2D 迁移到 3D 的复杂度与可行性评估文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“将当前 2D 训练框架迁移为 3D 的复杂度和可行性如何”问答；
  - 明确给出总体判断：可行但复杂度高，且更适合作为研究型重构；
  - 区分 `2.5D / 分层高度`、`真 3D 离散体素`、`真实飞控级 3D` 三种路径；
  - 说明环境、规划器、模型、DT 数据增强和重新训练成本都会显著增加。

## 20. 三种 3D 迁移方案详细说明文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“从当前 2D 框架迁移到 3D，可以考虑哪 3 种方案”问答；
  - 分别详细说明：
    - `2.5D / 分层高度`
    - `真 3D 离散体素`
    - `真实飞控级 3D`
  - 对每种方案补充核心思想、典型建模方式、代码改动范围、优缺点和适用目标；
  - 给出结合当前仓库的推荐路线：先 `2.5D`，再视情况升级。

## 21. 方案一对 `100 x 100 x 4` 分层空间适用性说明文档补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“方案一里，无人机能否在 `100 x 100 x 4` 这样的 3D 空间中飞行”问答；
  - 说明方案一可以支持分层离散空间中的飞行与跨层绕障；
  - 同时澄清该能力属于“离散高度层近似 3D”，不能直接等同于连续真实 3D 飞行。

## 22. 2.5D 分层高度训练链路接入

- 文件：
  - `pogema/grid_config.py`
  - `learning/learning_config.py`
- 主要修改：
  - 新增 `height_levels` 配置，默认值为 `1`；
  - 在 `GridConfig` 中新增 `MOVES_2P5D` 和 `get_action_deltas()`，使环境可在保持默认 2D 的同时，显式切换到 7 动作分层高度模式。

- 文件：
  - `pogema/grid.py`
  - `pogema/envs.py`
- 主要修改：
  - 扩展底层网格与环境状态，支持 `(x, y, z)` 分层位置；
  - 在 `height_levels > 1` 时，动作空间切换为 `停留/前后左右/升降`；
  - 局部观测改为“按高度层展开的多通道 2D 张量”，继续兼容现有 `Conv2d` 编码器；
  - 生命周期环境中新增分层目标高度的生成逻辑。

- 文件：
  - `env/SMAPO.py`
  - `env/planning.py`
- 主要修改：
  - `SMAPO` 预处理支持分层高度观测、3D 相对位置、3D BFS 邻居搜索和分层路径注入；
  - `ResettablePlanner` 新增自动后端切换：
    - 2D 继续使用原 C++ planner；
    - 分层高度模式自动改用新的 Python `LayeredPlanner`；
  - `LayeredPlanner` 提供最小可训练的分层 A* 路径引导能力，避免在首轮迁移中同时重写底层 C++ 规划器。

- 文件：
  - `sample_factory/algorithms/appo/model_utils.py`
- 主要修改：
  - 将原本二维写死的相对位置编码扩展为支持 `2D/3D` 两种输入维度；
  - 注意力模块会根据 `relative_xy` 的最后一维自动切换 2D 或 3D 相对位置编码；
  - 动作编码器首层改为 `LazyLinear`，兼容 7 动作分层模式。

- 验证情况：
  - 已通过 `python -m py_compile` 对核心训练链路文件做语法级验证；
  - 当前运行级烟测受本机缺少 `gym` 依赖限制，未能在此环境内完成 `reset/step` 实例验证。

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

## 17. 角色化界面重构（管理员/执行者）

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 顶部新增角色切换按钮（右上角）：`执行者 / 管理员`；
  - 研究模式归入管理员权限，执行者仅保留“运营中心 + 3D回放”；
  - 切换角色时自动校正当前激活页面，避免进入不可见模块。

- 文件：`web_frontend/src/modules/research/ResearchModeView.vue`
- 主要修改：
  - 标题调整为管理员语义；
  - 去除解释型段落，保留核心操作与回放信息。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 精简页头与说明文字，突出任务下发与运行态势。

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 精简说明文本，保留必要的系统摘要信息。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 将大幅“展示页”风格改为“控制台”风格：
    - 新增紧凑 Top Bar 与角色切换样式；
    - 收敛标题、面板、标签尺寸；
    - 缩短主区域间距，整体更像真实业务系统。

- 文件：`解疑.md`
- 主要修改：
  - 新增“如何把研究模式放到管理员里，并让系统界面更像真实产品”问答。

## 18. 3D 页面新增放大调节

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 新增“视图放大”滑杆（`0.60 ~ 2.50`）；
  - 在指标与状态 chip 中展示当前放大倍率；
  - 将放大倍率接入投影焦距（`focal`）计算，实现实时放大/缩小；
  - 新增对放大倍率变化的重绘监听，暂停状态下调整也能立即生效。

- 文件：`解疑.md`
- 主要修改：
  - 新增“3D 界面能否支持放大调节”问答，记录范围与生效方式。

## 19. 3D 页面新增鼠标拖拽视角控制

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 为 3D 画布新增 Pointer 事件交互（`pointerdown / move / up`）；
  - 支持鼠标左键拖拽调整视角：
    - 环绕模式：水平拖拽调环绕角，垂直拖拽调相机高度；
    - 跟随/俯视：拖拽调偏航与俯仰偏移；
  - 拖拽期间暂停自动环绕角速度叠加，避免用户操作被自动旋转抵消；
  - 新增角度范围限制（clamp）防止俯仰过冲导致视角异常；
  - 在画面 overlay 增加“左键旋转视角”提示。

- 文件：`解疑.md`
- 主要修改：
  - 新增“鼠标是否可以拖拽 3D 视角”问答，说明各镜头下的拖拽行为。

## 20. 3D 页面新增“无人机视角”与局部视野展示

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 新增镜头模式：`无人机视角`；
  - 新增“视角无人机”选择器，可切换到指定无人机编号；
  - 相机逻辑新增第一视角跟随机制：
    - 优先根据该无人机最近位移方向确定朝向；
    - 静止时回退到目标方向；
    - 支持拖拽做偏航/俯仰微调；
  - 渲染链路新增局部窗口过滤：
    - 在无人机视角下，仅绘制该无人机 `11 x 11`（半径5）局部范围内的网格、障碍、无人机与目标；
  - 当前视角无人机增加高亮描边，便于识别主体。

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否切换到某个无人机视角并显示它看到的 3D 地图”问答，记录已实现能力和范围。

## 21. 3D 回放窗口空白修复

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 背景：用户反馈“3D 回放窗口变空白”。
- 主要修改：
  - 修正相机俯仰角限制：
    - 非无人机模式改为 `[-1.2, 1.2]`；
    - 无人机模式改为 `[-1.2, 0.7]`；
  - 避免相机被限制到错误角度导致场景整体落出视野；
  - 新增空数据提示文案（`无可绘制地图数据`），提升异常可观测性。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么 3D 回放窗口突然空了”问答，记录根因与修复方案。

## 22. 无人机视角障碍渲染升级 + 快速 bug 巡检

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 在 `cameraMode === "drone"` 时，将障碍块渲染从线框升级为实体不透明立方体；
  - 新增 `drawBoxSolid()`：
    - 根据相机相对位置选择可见侧面；
    - 按深度排序填充面片并描边，增强立体感与遮挡关系；
  - `projectPoint()` 返回 `depth`，用于实体面绘制排序；
  - 拖拽微调中对无人机视角单独设置俯仰限制，防止过冲角导致视角异常。

- 快速检查结果：
  - `npm --prefix web_frontend run build` 通过；
  - 未发现新的编译级错误。

- 文件：`解疑.md`
- 主要修改：
  - 新增“无人机视角里方块能否改成实体不透明，是否还有其他 bug”问答，记录本次修复与检查结果。

## 23. 无人机视角改造为第三人称跟随镜头

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 主要修改：
  - 将无人机视角从近似第一人称改为第三人称跟随：
    - 相机固定在无人机后上方；
    - 朝向优先基于移动方向，静止时回退到目标方向；
  - 新增跟随平滑（lerp）相机状态，降低移动过程抖动；
  - 保留拖拽微调能力（偏航/俯仰），并与跟随逻辑叠加；
  - 新增角度归一化与方向解析辅助函数，避免连续拖拽导致角度漂移；
  - 合并 `cameraMode` 重复监听，避免重复重绘逻辑。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过。

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否把无人机视角改成游戏里的第三人称跟随镜头”问答，记录新行为与稳定性处理。

## 24. 3D 回放“再次播放”逻辑修复

- 文件：`web_frontend/src/modules/simulation3d/Simulation3DView.vue`
- 背景：用户反馈在无人机模式中，播放到末帧后点击“播放”无法再次播放。
- 主要修改：
  - 在 `startPreview()` 增加末帧检测；
  - 若当前已在末帧，先调用 `resetPlaybackCursor()` 再进入播放流程；
  - 行为统一为“播放结束后再次点击播放可从头重播”。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过。

- 文件：`解疑.md`
- 主要修改：
  - 新增“无人机模式里为什么播放结束后不能再次播放”问答，记录根因与修复结果。

## 23. 问答文档补充（Page Agent 是否可直接安装为 Codex skill）

- 文件：`解疑.md`
- 主要修改：
  - 新增“`https://github.com/alibaba/page-agent` 这个项目可以安装给 Codex 使用吗”问答；
  - 结论为“不能直接作为 skill 安装”，并补充原因（缺少 `SKILL.md` skill 结构）；
  - 补充两种替代方案：作为普通 npm 依赖使用，或二次封装为 Codex skill 后安装。

## 25. 新增并安装 Codex 技能：`page-agent-codex`

- 新增目录：`codex_skills/page-agent-codex/`
- 新增文件：
  - `codex_skills/page-agent-codex/SKILL.md`
  - `codex_skills/page-agent-codex/agents/openai.yaml`
  - `codex_skills/page-agent-codex/references/page-agent-integration.md`
- 主要内容：
  - 定义 Page Agent 接入场景的技能触发描述与标准流程；
  - 提供 `npm` 与 `CDN` 两种接入路径、验证清单与常见故障排查；
  - 配置技能 UI 元数据（display name / short description / default prompt）。
- 安装动作：
  - 已将该技能复制安装到 `~/.codex/skills/page-agent-codex/`。
- 说明：
  - `quick_validate.py` 依赖 `PyYAML`，受当前网络限制无法安装依赖，未执行官方脚本校验；
  - 已完成手动结构校验（目录与关键文件完整）。

## 26. `page-agent-codex` 技能可用性测试记录

- 文件：`解疑.md`
- 主要修改：
  - 新增“这个 skill 现在能不能直接跑通测试”问答；
  - 记录结构校验结果（安装目录与关键文件齐全、YAML/frontmatter 可解析）；
  - 记录端到端 `codex exec` 测试失败原因（后端连接中断 + `.codex` 权限告警）与复测命令；
  - 明确结论为“技能结构可用，但当前受限环境无法完成在线响应链路测试”。

## 27. 前端架构问答补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“目前前端的架构文件是怎么分工的”问答；
  - 按当前代码结构说明入口、总壳、API 层、共享渲染层、本地模板层和各业务页面的职责；
  - 记录开发代理配置仅在 `vite.config.js` 中完成，便于后续排查前端请求链路。

## 27. 角色切换升级为“真实切换界面”

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 将右上角“直接点按钮切角色”升级为“身份切换弹窗”流程；
  - 新增当前身份展示（`当前身份：执行者/管理员`）；
  - 新增“切换身份”按钮，弹窗中可选择角色并确认后生效；
  - 切换后仍保留权限校验：执行者仅显示“运营中心 + 3D回放”，管理员可额外访问“研究模式”。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增弹窗与角色卡片样式（遮罩层、角色选中态、确认区）；
  - 清理已废弃的旧 `.role-switch` 样式块，避免样式冗余。

- 文件：`解疑.md`
- 主要修改：
  - 新增“管理员和执行者如何做真实切换”问答，说明当前前端交互和权限行为。

## 28. P0 闭环落地（任务生命周期 + 实时通道 + 落库 + 告警 + 运营看板）

- 文件：`web_demo/task_runtime.py`（新增）
- 主要修改：
  - 新增后端任务运行时引擎 `TaskRuntime`，实现任务全生命周期：
    - `PREPARING -> READY -> RUNNING -> PAUSED -> COMPLETED/FAILED/STOPPED`；
  - 新增任务执行链路：
    - 支持 `sample/model` 两类数据源；
    - `model` 失败时自动降级到 `sample` 并记录 warning；
  - 新增 SQLite 持久化：
    - `tasks`（任务主表）
    - `task_events`（事件流）
    - `task_alerts`（告警记录）
  - 新增安全基础告警规则：
    - 顶点冲突告警 `VERTEX_CONFLICT`
    - 智能体卡滞告警 `STALL_AGENT_*`
    - 低吞吐超时告警 `LOW_THROUGHPUT_TIMEOUT`
  - 新增后端样例回放生成器（模板地图 + A* 路径 + 指标）。

- 文件：`web_demo/server.py`
- 主要修改：
  - 新增任务 API：
    - `POST /api/tasks`（创建任务）
    - `GET /api/tasks`（任务列表）
    - `GET /api/tasks/{id}`（任务详情/快照）
    - `POST /api/tasks/{id}/control`（start/pause/resume/stop）
    - `GET /api/tasks/{id}/alerts`（告警列表）
  - 新增实时通道：
    - `GET /api/tasks/{id}/events`（SSE）
  - 新增系统汇总接口：
    - `GET /api/dashboard/summary`（任务状态与吞吐均值）。

- 文件：`web_frontend/src/services/api.js`
- 主要修改：
  - 新增运营模式任务 API 客户端：
    - `createOpsTask`
    - `controlOpsTask`
    - `getOpsTask`
    - `fetchOpsAlerts`
    - `connectOpsTaskEvents`（SSE）。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 运营模式从“前端本地定时器回放”升级为“后端驱动任务”；
  - 接入任务创建、开始、暂停、继续、停止；
  - 接入 SSE 实时事件流，实时刷新：
    - 地图回放帧
    - 运行状态卡片
    - 无人机表格
    - 告警列表
  - 新增执行配置项：数据源、无人机数量、最大帧数、节拍。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增运营模式告警组件样式（告警列表、级别色、代码与步数展示）。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - `TaskRuntime` 本地 smoke 脚本通过（任务可从 `READY` 运行到 `COMPLETED`）。

## 29. 前端增强（任务中心 + 运营大屏 + 参数模板系统 + 报告导出）

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 扩展导航页签：
    - `任务中心`
    - `运营大屏`
  - 新增页面组件挂载：
    - `TaskCenterView`
    - `OpsDashboardView`
  - 增加全局模式切换事件监听（`app-switch-mode`），支持跨页面一键跳转。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`（新增）
- 主要修改：
  - 实现任务中心页：
    - 任务列表筛选（状态/模板/关键词）；
    - 任务详情与告警查看；
    - 历史回放入口（加载任务回放数据并在 Canvas 回放）；
    - 一键跳转运营中心并聚焦任务；
    - 任务报告导出（Markdown）；
    - 参数模板库管理（保存/删除/应用到运营中心）。

- 文件：`web_frontend/src/modules/dashboard/OpsDashboardView.vue`（新增）
- 主要修改：
  - 实现只读运营大屏：
    - 汇总指标卡片（总任务、运行中、完成数、平均吞吐）；
    - 任务列表与焦点任务切换；
    - 焦点任务地图快照与最近告警展示。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 接入参数模板系统：
    - 模板选择/应用；
    - 保存当前配置为模板；
    - 删除当前模板；
  - 支持从任务中心带入：
    - 预填模板参数（`OPS_TEMPLATE_PREFILL`）；
    - 聚焦指定任务（`OPS_FOCUS_TASK_ID`）。

- 文件：`web_frontend/src/modules/shared/templateStore.js`（新增）
- 主要修改：
  - 新增参数模板本地存储工具：
    - `loadOpsTemplates`
    - `upsertOpsTemplate`
    - `deleteOpsTemplate`
  - 统一模板字段规范和范围校验；
  - 通过 `ops-template-updated` 事件同步多页面模板状态。

- 文件：`web_frontend/src/services/api.js`
- 主要修改：
  - 新增 API 封装：
    - `fetchOpsTasks`
    - `fetchDashboardSummary`
    - `fetchTaskReplay`

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 新增 `get_replay(task_id)`：
    - 运行中/本进程内任务可返回 `environment + frames`；
    - 仅历史数据库任务返回 `available=false` 与原因说明。

- 文件：`web_demo/server.py`
- 主要修改：
  - 新增接口：
    - `GET /api/tasks/{id}/replay`

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增任务中心/运营大屏布局与元信息卡样式；
  - 新增任务列表选中态样式；
  - 增补移动端自适配样式。

- 验证结果：
  - `python3 -m py_compile web_demo/server.py web_demo/task_runtime.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - `TaskRuntime.get_replay()` 本地 smoke 校验通过。

## 30. 2D/3D 页面整合（同任务同页联动）+ 参数侧边栏隐藏

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 将原“运营中心（2D）”重构为“联合运行视图（2D + 3D）”：
    - 左侧 2D 俯视运行状态；
    - 右侧 3D 运行状态；
    - 两者绑定同一 `task_id` 与同一实时帧数据；
  - 保留任务生命周期控制（开始/暂停/继续/停止）与实时告警展示；
  - 保留并接入参数模板能力（保存/应用/删除）；
  - 新增 3D 联动渲染（环绕/俯视/跟随镜头，放大倍率、环绕速度）。

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 导航文案调整为“联合运行”；
  - 移除独立“3D回放”入口，避免 2D/3D 分页割裂；
  - 页面入口统一到单页联动视图。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增联合页面布局样式：
    - 可折叠参数侧边栏；
    - 双视图网格（2D + 3D）；
    - 主区与移动端自适应。

- 交互结果：
  - 现在同一次任务中，可在一个页面同时观察 2D 和 3D 运行状态；
  - 参数添加与调整都在左侧栏，支持隐藏以扩大主画面区域。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - `python3 -m py_compile web_demo/server.py web_demo/task_runtime.py` 通过。

## 29. 文档补充：SMAPO 训练是否需要训练数据

- 文件：`解疑.md`
- 主要修改：
  - 新增“这个训练需不需要训练数据”问答；
  - 明确说明当前项目主训练链路属于强化学习 APPO，不依赖传统标注数据集；
  - 说明训练依赖的是环境在线生成的地图、障碍、起终点和交互轨迹，而不是离线样本文件。

## 30. 文档补充：当前训练场景是否已经改为 2.5D

- 文件：`解疑.md`
- 主要修改：
  - 新增“当前训练场景是否已经改成 2.5D”问答；
  - 明确区分“代码已支持 2.5D 模式”和“默认配置仍是 2D”；
  - 说明当前 2.5D 场景本质上是二维障碍地图复制到多层，并非每层独立障碍的完整 3D 体素地图。

## 31. 文档补充：`100 x 100 x 4` 的含义

- 文件：`解疑.md`
- 主要修改：
  - 新增“`100 x 100 x 4` 是不是地图大小”问答；
  - 明确区分“全局地图大小”和“局部观测窗口大小”；
  - 说明 `100 x 100 x 4` 表示分层地图空间大小，而 `11 x 11 x 4` 表示单个智能体的局部观测范围。

## 32. 文档补充：是否可以改成原生 3D 地图生成

- 文件：`解疑.md`
- 主要修改：
  - 新增“能不能把地图生成改成原生 3D，而不是每一层复制”问答；
  - 说明当前代码仍在二维障碍语义上运行，分层模式只是多层扩展；
  - 明确指出若要升级为原生 3D，需要同步修改地图生成、起终点采样、环境障碍存储、规划器和预处理逻辑。

## 33. 文档补充：GitHub 可复用的 3D 地图生成/体素项目调研

- 文件：`解疑.md`
- 主要修改：
  - 新增“GitHub 上有没有可以直接用的 3D 地图生成项目”问答；
  - 汇总并分类记录可参考仓库：
    - `PyOctoMap`
    - `OctoMap`
    - `UFOMap`
    - `wavemap`
    - `map_manager`
    - `VoxCity`
    - `voxelmap`
    - `Mesh Vox`
    - `BlenderProc`
    - `scene_synthesizer`
    - `monocular-slam-drone`
  - 明确给出和当前 SMAPO Python 训练框架的适配建议，指出暂无“零改造直接替换”的现成仓库。

## 34. 文档补充：PyOctoMap 的地图表示类型

- 文件：`解疑.md`
- 主要修改：
  - 新增“PyOctoMap 是离散地图还是非离散地图”问答；
  - 明确说明其本质是基于八叉树的离散占据地图，而非连续地图；
  - 说明其接口可接收连续坐标，但底层仍会按分辨率量化到离散体素单元。

## 35. 原生 3D 地图生成：接入 PyOctoMap 后端

- 文件：`pogema/grid_config.py`
- 主要修改：
  - 新增 `native_3d_obstacles`、`obstacle_backend`、`octomap_resolution` 配置；
  - 新增 `is_native_3d_obstacles()`；
  - 扩展位置校验，支持 `(x, y, z)` 坐标输入。

- 文件：`pogema/generator.py`
- 主要修改：
  - 新增可选依赖 `pyoctomap` 的导入与 `generate_obstacles_pyoctomap()`；
  - 支持在 `height_levels > 1` 且显式启用时生成原生 `z,x,y` 三维占据障碍；
  - 将起点/终点采样和连通域标记扩展为兼容 2D / 3D；
  - `generate_positions_and_targets_fast()`、`get_components()` 支持 3D 连通空间。

- 文件：`pogema/grid.py`
- 主要修改：
  - 新增 `native_3d_obstacles` 语义；
  - 支持三维障碍存储、带边界填充的 3D 障碍裁剪；
  - 局部障碍观测改为读取真实 3D 体素窗口，而非每层复制；
  - 移动、强制放置、渲染投影和 lifelong 组件检查均兼容原生 3D 障碍。

- 文件：`env/planning.py`
- 主要修改：
  - `LayeredPlanner` 改为可读取原生 3D 障碍；
  - 真实按 `obstacles[z][x][y]` 判断可通行性；
  - 自动从 3D 障碍张量解析高度层数。

- 文件：`env/SMAPO.py`
- 主要修改：
  - 修复分层模式下 `relative_xy` 填充维度，支持三维相对坐标；
  - `bfs_obs_3d()` 改为兼容真实 3D 障碍查询；
  - 修复 `CutObservationWrapper` 在 3D 观测下错误使用层数计算半径的问题。

- 文件：`pogema/envs.py`
- 主要修改：
  - lifelong 模式下新目标生成改为兼容 3D 连通域键值；
  - 原生 3D 障碍场景下，目标可以直接落到三维可达体素。

- 文件：`env/replan.py`
- 主要修改：
  - 修正三维障碍张量下地图宽高解析逻辑，避免把层数误当成地图高度。

- 文件：`requirements.txt`
- 主要修改：
  - 新增 `pyoctomap` 依赖。

- 文件：`scripts/smoke_pyoctomap_env.py`（新增）
- 主要修改：
  - 新增 Docker / 本地通用 smoke 脚本；
  - 验证 `native_3d_obstacles=True + obstacle_backend=pyoctomap` 下：
    - 全局障碍形状；
    - 局部观测形状；
    - 智能体三维坐标；
    - 多层障碍差异。

## 36. Docker 支持与验证：PyOctoMap 构建链路

- 文件：`Dockerfile`
- 主要修改：
  - 新增 `liboctomap-dev` 与 `libdynamicedt3d-dev`，解决 `pyoctomap` 在 Docker 中源码构建缺少系统库的问题。

- 文件：`Dockerfile.gpu`
- 主要修改：
  - 同步补充 `liboctomap-dev` 与 `libdynamicedt3d-dev`，保持 GPU 镜像能力一致。

- 文件：`.dockerignore`（新增）
- 主要修改：
  - 排除 `.git`、`results/`、`wandb/`、`web_frontend/node_modules/` 等大目录；
  - 大幅缩小 Docker 构建上下文，避免无关文件拖慢镜像构建。

- 文件：`README.md`
- 主要修改：
  - 新增 PyOctoMap 原生 3D 地图后端的 Docker smoke 命令说明。

- 文件：`解疑.md`
- 主要修改：
  - 新增“PyOctoMap 是否已经接入当前地图生成系统”问答；
  - 新增“PyOctoMap 接入后，Docker 中测试结果如何”问答。

- 验证结果：
  - `python3 -m py_compile pogema/grid_config.py pogema/generator.py pogema/grid.py pogema/envs.py env/planning.py env/SMAPO.py env/replan.py scripts/smoke_pyoctomap_env.py` 通过；
  - `docker build -t smapo:pyoctomap-test .` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_pyoctomap_env.py` 通过；
  - `docker run --rm smapo:pyoctomap-test sh -lc "python main.py ... --height_levels=4 --native_3d_obstacles=True --obstacle_backend=pyoctomap ..."` 已成功走通最小化训练启动与退出流程。

## 37. 完整训练链路审计：2.5D / 原生 3D 适配缺口确认

- 文件：`解疑.md`
- 主要修改：
  - 新增“当前训练完整路径是否已经全部适配 2.5D / 原生 3D”问答；
  - 明确结论为“尚未全部完成”；
  - 记录两处高风险问题：
    - 默认训练路径 `EnvironmentMazes / use_maps=True` 在 3D 模式下仍会因二维地图 + 三维动作导致 reset 时报错；
    - `ProvideGlobalObstacles -> SMAPO -> LayeredPlanner` 会把 3D 障碍先转成 Python list，导致规划器没有真正按 3D 障碍空间搜索；
  - 补充说明当前地图集仍是二维地图集，即使修复崩溃链，也还不能自动得到原生 3D 地图集训练。

## 38. 训练主链路补全：修复默认 mazes 路径与 planner 3D 障碍传递

- 文件：`pogema/generator.py`
- 主要修改：
  - 新增 `_get_connectivity_moves()`；
  - 连通域搜索会根据障碍维度自动选择二维或三维动作；
  - 修复 `use_maps=True + height_levels>1` 时二维 `bfs()` 被三维动作直接打崩的问题；
  - `generate_positions_and_targets_fast()`、`get_components()` 现在都会按障碍图维度选择正确的连通域邻接方式。

- 文件：`env/create_env.py`
- 主要修改：
  - `ProvideGlobalObstacles.get_global_obstacles()` 不再把障碍张量 `.tolist()`；
  - 改为直接传递 `np.ndarray`，保留 3D 障碍的 `.shape` 信息。

- 文件：`env/planning.py`
- 主要修改：
  - `Planner.add_grid_obstacles()` 统一把二维障碍标准化为 `np.ndarray -> list`，保持原二维 C++ planner 兼容；
  - `LayeredPlanner.add_grid_obstacles()` 统一把障碍标准化为 `np.ndarray`；
  - `_in_bounds()`、`_is_free()` 直接按标准化后的二维 / 三维张量判定；
  - 修复 planner 在 3D 模式下因为收到 Python list 而退回二维语义的问题。

- 文件：`scripts/smoke_2p5d_training_paths.py`（新增）
- 主要修改：
  - 新增双链路 smoke 脚本；
  - 同时验证：
    - 原生 3D 随机场景路径；
    - 默认 `EnvironmentMazes` 的 2.5D fallback 路径；
  - 会检查 planner 类型、planner 障碍形状以及路径是否非平凡。

- 文件：`解疑.md`
- 主要修改：
  - 新增“现在 2.5D / 原生 3D 训练主链路修好了吗，复测结果如何”问答；
  - 新增“为什么改了 `num_agents` 后训练还是按 64/128 个 agent 启动”问答；
  - 记录 `agent_bins` 会覆盖 `grid_config.num_agents` 的旧训练配置行为。

- 验证结果：
  - `python3 -m py_compile pogema/generator.py env/create_env.py env/planning.py scripts/smoke_2p5d_training_paths.py` 通过；
  - `docker build -t smapo:pyoctomap-test .` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_pyoctomap_env.py` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_2p5d_training_paths.py` 通过；
  - `docker run --rm smapo:pyoctomap-test sh -lc "python main.py --env=Pogema-v0 ... --target_num_agents=64 --use_maps=False --height_levels=4 --native_3d_obstacles=True --obstacle_backend=pyoctomap"` 通过；
  - `docker run --rm smapo:pyoctomap-test sh -lc "python main.py --env=PogemaMazes-v0 ... --target_num_agents=128 --height_levels=4 --native_3d_obstacles=True --obstacle_backend=pyoctomap"` 通过。

## 39. 文档补充：解释“use_maps=True 仍不是原生 3D 地图集”

- 文件：`解疑.md`
- 主要修改：
  - 新增“`use_maps=True` 仍然不是原生 3D 地图集”含义解释；
  - 明确区分：
    - 现状：二维地图资源 + 分层高度训练逻辑；
    - 真正原生 3D：每个高度层都有独立障碍定义的三维地图资产；
  - 说明当前 `mazes/random/street` 地图已经可用于 2.5D 训练，但还不是独立层结构的 3D 地图文件。

## 40. 文档补充：为什么这次没有直接接入原生 3D 地图集

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么这次没有直接接入原生 3D 地图集”问答；
  - 说明当前改造顺序是：
    - 先修训练主链路；
    - 再升级地图资产；
  - 明确指出原生 3D 地图集需要额外完成：
    - 三维地图文件格式设计；
    - `use_maps=True` 的三维加载逻辑；
    - 三维地图资产制作；
    - 层间连通与起终点语义规范。

## 41. 原生 3D 地图资产接入：让 `use_maps=True` 直接读取 3D map

- 文件：`pogema/grid_config.py`
- 主要修改：
  - `GridConfig.map` 扩展为支持 `dict` 形式的 3D map 定义；
  - 新增 3D map 解析逻辑，支持：
    - `layers` 多层切片；
    - 逐层字符串地图；
    - 可选的三维 `agents_xy / targets_xy`；
  - 新增三维地图尺寸一致性校验；
  - 加载 3D map 时会自动推导：
    - `height_levels`
    - `density`
    - `native_3d_obstacles=True`

- 文件：`env/custom_maps.py`
- 主要修改：
  - 新增 `env/maps_3d.yaml` 的加载；
  - 让 3D 地图资产直接进入 `MAPS_REGISTRY`。

- 文件：`env/create_env.py`
- 主要修改：
  - 新增 `use_maps=True` 时的地图元数据预解析；
  - 在构建 `pogema_v0` 之前先判断匹配到的地图是否为 3D；
  - 若匹配到的是 3D map，会提前把环境配置切到 3D observation/action space；
  - 修复了 SampleFactory 在 reset 前仍按 2D observation space 分配 buffer，导致 `(3,) -> (2,)` 广播失败的问题；
  - 若一个正则同时匹配到层数不一致的地图，会直接报错，避免混合 observation space。

- 文件：`pogema/grid.py`
- 主要修改：
  - map 加载从二维专用数组构造改为统一 `np.asarray(...)`；
  - 兼容直接读取三维障碍体地图。

- 文件：`env/maps_3d.yaml`（新增）
- 主要修改：
  - 新增两张最小可训练的原生 3D 地图样例：
    - `native3d-demo-a`
    - `native3d-demo-b`
  - 地图尺寸均为 `16 x 16 x 4`；
  - 每层障碍结构独立，不再是每层复制。

- 文件：`scripts/smoke_native_3d_maps.py`（新增）
- 主要修改：
  - 新增 `use_maps=True` 的原生 3D 地图 smoke 脚本；
  - 验证：
    - 3D 地图资产是否被选中；
    - 全局障碍是否为 `(4, 16, 16)`；
    - planner 是否拿到 3D 障碍张量；
    - 智能体坐标是否为三维；
    - 规划路径是否非平凡。

- 文件：`解疑.md`
- 主要修改：
  - 新增“现在 `use_maps=True` 已经能直接读取原生 3D 地图了吗”问答；
  - 新增“现在怎么启用原生 3D 地图训练”问答；
  - 给出新 3D map 文件格式和训练示例命令。

- 验证结果：
  - `python3 -m py_compile pogema/grid_config.py pogema/grid.py env/custom_maps.py env/create_env.py scripts/smoke_native_3d_maps.py` 通过；
  - `docker build -t smapo:pyoctomap-test .` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_native_3d_maps.py` 通过；
  - `docker run --rm smapo:pyoctomap-test sh -lc "timeout 45s python main.py --env=Pogema-v0 --train_for_seconds=3 --target_num_agents=64 --map_name=native3d-demo-a --max_episode_steps=48"` 通过；
  - 训练日志已成功走到：
    - `Finished reset for worker 0`
    - `Collecting experience...`
    - 最终 `Done!`。

## 42. 文档补充：说明当前 3D 地图资产来源

- 文件：`解疑.md`
- 主要修改：
  - 新增“现在仓库里的 3D 地图资产是哪里来的”问答；
  - 明确说明：
    - 当前 `native3d-demo-a` / `native3d-demo-b` 不是外部下载数据集；
    - 是本次接通原生 3D 地图链路时手工加入的最小工程验证样例；
    - 其主要用途是验证 `use_maps=True` 的 3D 地图加载、planner、训练启动链路。

## 43. 接入 OctoMap 官方现成地图资产

- 文件：`pogema/grid_config.py`
- 主要修改：
  - 新增 `octomap_file` 类型 3D map 解析逻辑；
  - 支持直接从 `.bt` / `.ot` 文件加载 OctoMap 八叉树；
  - 支持通过以下参数重采样为训练栅格：
    - `voxel_size`
    - `metric_min`
    - `metric_max`
    - `width`
    - `height`
    - `height_levels`
  - 加载后自动转换成 `(z, x, y)` 占据张量。

- 文件：`env/maps_3d.yaml`
- 主要修改：
  - 新增 `octomap-geb079-demo` 地图条目；
  - 该条目直接引用官方 OctoMap 示例地图 `geb079.bt`；
  - 通过 `0.5m` 体素尺寸重采样为 `78 x 30 x 7` 的训练网格。

- 文件：`env/octomap_assets/geb079.bt`（新增）
- 主要修改：
  - 新增 OctoMap 官方仓库示例地图资产；
  - 作为当前仓库内可直接使用的外部现成 3D 地图样例。

- 文件：`env/create_env.py`
- 主要修改：
  - `use_maps=True` 的元数据预解析新增对显式 `height_levels` 型 map 资产的识别；
  - 让 `octomap_file` 地图在环境构建前就能切换到 3D observation/action space。

- 文件：`scripts/smoke_octomap_asset.py`（新增）
- 主要修改：
  - 新增 OctoMap 官方资产 smoke 脚本；
  - 验证：
    - 官方 `.bt` 文件读取；
    - OctoMap 到训练网格的体素重采样；
    - planner 3D 障碍接入；
    - `use_maps=True` 下的 3D 位置与路径输出。

- 文件：`解疑.md`
- 主要修改：
  - 新增“现在已经接入 OctoMap 官方现成地图资产了吗”问答；
  - 新增“OctoMap 官方地图资产接入后，验证结果怎么样”问答；
  - 记录官方样例已经完成地图 smoke 和训练启动 smoke。

- 验证结果：
  - `python3 -m py_compile pogema/grid_config.py env/create_env.py scripts/smoke_octomap_asset.py` 通过；
  - `docker build -t smapo:pyoctomap-test .` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_octomap_asset.py` 通过；
  - `docker run --rm smapo:pyoctomap-test sh -lc "timeout 45s python main.py --env=Pogema-v0 --train_for_seconds=3 --target_num_agents=64 --map_name=octomap-geb079-demo --max_episode_steps=64"` 已成功走到：
    - learner 初始化；
    - 官方 `.bt` 文件加载；
    - actor / env runner 初始化；
    - `Decorrelating experience ...`
  - 说明官方 OctoMap 现成资产已完成训练入口接入，只是初始化成本明显高于小型 demo 图。

## 44. 文档补充：总结当前训练主链路是否已打通

- 文件：`解疑.md`
- 主要修改：
  - 新增“目前训练的整个逻辑算完全打通了吗”问答；
  - 明确区分：
    - 主训练链路已经打通；
    - 工程化完善程度仍有边界；
  - 总结当前已打通的 4 类链路：
    - 原始 2D 训练；
    - 2.5D / 原生 3D 随机场景训练；
    - `use_maps=True` 的二维地图 2.5D fallback；
    - `use_maps=True` 的原生 3D 地图资产训练；
  - 记录当前剩余边界：
    - 大型 OctoMap 地图初始化较慢；
    - 3D 地图资产数量仍有限；
    - OctoMap 当前是离线重采样接入；
    - 长时训练效果还未完成系统评测。

## 45. 文档补充：统计当前可直接训练的 3D 地图资产数量

- 文件：`解疑.md`
- 主要修改：
  - 新增“目前可直接用于 3D 训练的地图资产有多少”问答；
  - 明确给出当前数量：
    - 手工 3D 切片样例 2 个；
    - 官方 OctoMap 资产 1 个；
    - 总计 3 个；
  - 同时区分“已可训练的 3D 地图资产样例”和“尚未规模化的大型 3D 地图集”。

## 46. 文档补充：说明当前接入的 OctoMap 官方地图数量

- 文件：`解疑.md`
- 主要修改：
  - 新增“OctoMap 官方地图现在只有一个吗”问答；
  - 明确区分：
    - 当前仓库里已接入的 OctoMap 官方地图资产只有 1 个；
    - 这只是当前接入数量，不代表 OctoMap 外部生态只有 1 张可用地图；
  - 说明当前先接 1 张官方样例，是为了先验证 `.bt` 读取、体素重采样和训练入口链路。

## 47. 文档补充：说明 3D 地图训练最少需要多少个地图

- 文件：`解疑.md`
- 主要修改：
  - 新增“训练最少需要多少个 3D 地图资产”问答；
  - 明确区分两种口径：
    - 从“训练能启动”角度，最少 `1` 个地图即可；
    - 从“训练有泛化意义”角度，建议至少 `5 到 10` 个不同 3D 地图；
  - 补充说明：
    - 仅验证代码链路时 `1` 个即可；
    - 更正式的泛化训练通常需要几十个甚至更多地图。

## 45. 联合运行页全屏修复：侧栏收起异常 + 运行图居中

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 联合运行页根容器增加 `sidebar-collapsed` 条件类，配合收起状态切换布局；
  - 2D 画布点击坐标改为按 `getBoundingClientRect()` 比例映射到 Canvas 像素坐标，修复高分屏/缩放下点击偏移；
  - `draw3D()` 补齐画布显示尺寸同步（与 2D 一致），避免全屏或窗口尺寸变化后渲染比例错位；
  - 新增窗口 `resize` 监听 + 防抖重绘，保证收起/展开和分辨率变化后画面稳定。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增 `.ops-integrated-layout.sidebar-collapsed` 网格规则，收起后固定窄侧栏宽度；
  - 优化 `.ops-sidebar-panel.collapsed` 和头部布局，避免按钮与标题在窄宽度下错位；
  - 统一 `.ops-view-card .canvas-wrap canvas` 为 `width: 100%` + 固定可视高度，确保运行图在卡片内居中展示；
  - 移动端补充 `.ops-integrated-layout.sidebar-collapsed` 的单列回退规则。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - Playwright 复测通过（`1920x1080`、`2560x1440`）：
    - 侧栏收起/展开按钮状态正常；
    - 收起后侧栏宽度固定；
    - 2D/3D 运行图在各自卡片中保持居中且缓冲尺寸与显示尺寸一致。

## 48. 文档补充：说明当前 `16x16x4` 3D 样例地图是否偏小

- 文件：`解疑.md`
- 主要修改：
  - 新增“当前 `16x16x4` 3D 地图尺寸是不是太小”问答；
  - 明确区分两种用途：
    - 作为环境链路验证和 smoke 训练样例时，这个尺寸是合适的；
    - 作为正式 3D 训练主地图时，这个尺寸偏小；
  - 进一步给出推荐的 10 图资产组合思路：
    - 小图用于调试；
    - 中图用于常规训练；
    - 大图用于主实验和泛化验证；
    - 再保留 1 个 OctoMap 现成资产。

## 49. 文档补充：说明后续 10 张 3D 地图准备采用什么生成方式

- 文件：`解疑.md`
- 主要修改：
  - 新增“后续把 3D 地图资产补到 `10` 个，准备用什么方式生成”问答；
  - 明确说明后续策略不是“全部依赖外部现成代码库批量生成”，而是采用混合方案：
    - 主力训练地图优先使用仓库内可控生成/模板化生成；
    - 保留少量外部现成 3D 资产（如 OctoMap）用于真实性验证；
  - 说明这样做的原因：
    - 更容易统一尺寸、障碍率和难度；
    - 更适合作为训练资产；
    - 更便于复现实验与后续调参。

## 50. 账户切换升级：真实用户界面 + 后端数据库持久化

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 在 SQLite 初始化中新增用户与应用状态表：
    - `user_accounts`
    - `app_state`
  - 新增默认账户自动种子逻辑，首次启动自动写入 3 个账号；
  - 新增身份接口数据层方法：
    - `get_identity()`
    - `switch_identity(user_id)`
  - 切换账户时更新 `active_user_id` 与 `last_login_at`，实现后端持久化。

## 51. 3D 地图资产扩充到 10 个：仓库内生成式地图 + 全量 smoke 校验

- 文件：`env/custom_maps.py`
- 主要修改：
  - 新增仓库内确定性 3D 地图生成逻辑；
  - 支持从 `maps_3d.yaml` 的 `generated` 规格自动展开为原生 3D `layers`；
  - 生成策略采用分层走廊、带缺口的横纵障碍和局部块状障碍组合；
  - 保证每层布局不完全相同，并保持地图边界可通行，适合作为训练资产。

- 文件：`env/maps_3d.yaml`
- 主要修改：
  - 在原有：
    - `native3d-demo-a`
    - `native3d-demo-b`
    - `octomap-geb079-demo`
    基础上，新增 `7` 张生成式原生 3D 地图：
    - `native3d-demo-c`
    - `native3d-demo-d`
    - `native3d-demo-e`
    - `native3d-demo-f`
    - `native3d-demo-g`
    - `native3d-demo-h`
    - `native3d-demo-i`
  - 使当前可直接训练的 3D 地图资产总数提升到 `10` 个；
  - 地图尺寸采用混合分布：
    - `16x16x4`
    - `32x32x4`
    - `40x40x4`
    - `64x64x4`
    - `80x80x4`
    - 再加 `1` 个 OctoMap 现成资产。

- 文件：`scripts/smoke_native_3d_maps.py`
- 主要修改：
  - 从“随机命中一张 `native3d-demo-*` 地图做 smoke”升级为“逐张检查所有 `native3d-demo-*` 地图”；
  - 现在会遍历并验证全部 `9` 张仓库内原生 3D 地图；
  - 每张地图都会检查：
    - 全局障碍张量形状；
    - planner 障碍张量形状；
    - 3D 坐标；
    - 路径是否有效；
    - 层间障碍是否存在差异。

- 文件：`解疑.md`
- 主要修改：
  - 更新“当前 3D 地图资产来源”说明：
    - 现在不再只是“手工两张 demo 图”；
    - 已经加入仓库内确定性生成的 3D 训练地图；
  - 更新“当前 3D 地图资产数量”说明：
    - 当前总数改为 `10` 个；
    - 其中仓库内原生 3D 训练地图 `9` 个；
    - OctoMap 官方资产 `1` 个；
  - 更新“后续补到 10 个准备用什么方式生成”问答：
    - 说明该混合方案已经落地完成。

- 验证结果：
  - `python3 -m py_compile env/custom_maps.py scripts/smoke_native_3d_maps.py` 通过；
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_native_3d_maps.py` 通过：
    - 全量校验 `9` 张 `native3d-demo-*` 地图；
    - 形状覆盖：
      - `(4, 16, 16)`
      - `(4, 32, 32)`
      - `(4, 40, 40)`
      - `(4, 64, 64)`
      - `(4, 80, 80)`
  - `docker run --rm smapo:pyoctomap-test python scripts/smoke_octomap_asset.py` 继续通过，确认未回归影响 OctoMap 链路；
  - 基于 `native3d-demo-d` / `native3d-demo-h` 的 Docker 训练启动 smoke 已成功进入 `Decorrelating experience ...` 阶段。

- 文件：`web_demo/server.py`
- 主要修改：
  - 新增 `GET /api/identity`，返回当前账户 + 可切换账户列表；
  - 新增 `POST /api/identity/switch`，根据 `user_id` 执行账户切换并返回最新身份上下文；
  - 增加参数校验与错误返回（缺失 `user_id`、用户不存在）。

- 文件：`web_frontend/src/services/api.js`
- 主要修改：
  - 新增前端身份接口封装：
    - `fetchIdentity()`
    - `switchIdentity(userId)`

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 顶栏由“静态身份标签”改为“账户卡片 + 切换按钮”；
  - 切换弹窗改为真实账户列表（用户名、角色、部门、岗位、最近登录）；
  - 首屏加载时从后端同步当前账户，切换时调用后端接口并回写界面；
  - 权限联动保持：
    - `admin` 显示研究模式；
    - `executor` 隐藏研究模式。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增账户卡片、用户列表卡片、角色徽标、错误提示等样式；
  - 新增切换按钮禁用态样式，避免并发切换操作。

- 文件：`解疑.md`
- 主要修改：
  - 新增“用户切换如何做成更真实界面，并接入后端数据库”问答；
  - 记录本次后端表结构、接口、前端交互和权限联动结论。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - Playwright 联调通过：
    - 可读取后端账户列表；
    - 切换到管理员后出现“研究模式”入口；
    - 切回执行者后“研究模式”入口隐藏；
    - `GET /api/identity` 返回值与当前界面一致。

## 52. 账户系统升级为“登录页 + 双初始账号”（管理员/执行者）

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 引入登录认证辅助逻辑（用户名规范化、密码哈希）；
  - 默认账号改为 2 个：
    - `admin / admin123`
    - `executor / exec123`
  - 新增认证表：
    - `auth_credentials`（保存密码哈希）
  - 扩展 `app_state` 登录态：
    - `auth_logged_in`
  - 新增认证方法：
    - `get_auth_options()`
    - `get_auth_state()`
    - `login(role, username, password)`
    - `logout()`
  - 启动时会同步默认账号并将非默认旧账号标记为 `inactive`。

- 文件：`web_demo/server.py`
- 主要修改：
  - 新增认证接口：
    - `GET /api/auth/options`
    - `GET /api/auth/state`
    - `POST /api/auth/login`
    - `POST /api/auth/logout`
  - 登录失败返回 `401`，参数缺失返回 `400`。

- 文件：`web_frontend/src/services/api.js`
- 主要修改：
  - 新增认证 API 封装：
    - `fetchAuthOptions()`
    - `fetchAuthState()`
    - `loginWithPassword()`
    - `logoutCurrentUser()`

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 新增系统登录页（未登录时不展示业务主界面）；
  - 登录页支持选择身份（管理员/执行者）并输入账号密码；
  - 右上角“切换账户”改为登录式切换弹窗，复用同一认证流程；
  - 登录成功后按角色控制页面权限：
    - 管理员显示研究模式；
    - 执行者隐藏研究模式。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增登录页和登录式切换弹窗样式：
    - 登录容器、身份选择按钮、账号快捷项、输入框样式。

- 文件：`解疑.md`
- 主要修改：
  - 新增“切换账户改成登录界面后，现在怎么用”问答；
  - 明确记录 2 个初始账号与登录入口行为。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - 运行时脚本验证通过：
    - 错误密码登录失败；
    - `executor` 与 `admin` 均可登录；
    - `logout` 后状态回到未登录；
  - Playwright UI 验证通过：
    - 首屏出现登录界面；
    - 执行者登录后无“研究模式”；
    - 通过切换弹窗登录管理员后出现“研究模式”。

## 53. 顶栏主操作改为“退出登录”（替代“切换账户”）

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 登录后顶部按钮从“切换账户”改为“退出登录”；
  - 点击后直接调用 `/api/auth/logout` 并返回登录页；
  - 移除登录态下的“切换账户弹窗”流程，统一改为“退出后在登录页重登切换身份”。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 调整顶部账户卡片交互样式为非点击态（`cursor: default`），避免误导为可直接切换。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么把切换账户改成退出登录”问答，说明交互调整原因和当前行为。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 登录后点击“退出登录”可回到登录页，身份切换改为登录页重新认证。

## 54. 角色分工重构：管理员仅分配，执行者仅执行

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 角色入口页签重构：
    - 管理员仅保留 `任务分配` 页签；
    - 执行者保留 `联合运行 / 任务中心 / 运营大屏`；
  - 子页面透传角色与当前用户信息，作为页面内权限判断依据。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 新增角色入参（`role`、`currentUser`）；
  - 管理员新增“任务分配与地图导入”面板：
    - 创建并分配任务（可选执行者）；
    - 导入地图 JSON，并将地图名写入任务配置；
  - 执行者任务列表改为仅显示“分配给当前账号”的任务；
  - 任务列表新增“执行者”列，明确任务归属。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 新增角色入参并按角色控制参数面板；
  - 执行者禁用任务创建相关参数（模板、数据源、无人机数量、帧数、节拍）；
  - 执行者点击“开始任务”时，若未加载已分配任务，则禁止新建并给出提示；
  - 模板保存/删除仅管理员可见。

- 文件：`解疑.md`
- 主要修改：
  - 新增“管理员和执行者现在怎么分工”问答；
  - 明确记录权限边界和页面行为。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - Playwright 验证通过：
    - 管理员登录仅显示 `任务分配`；
    - 执行者登录显示 `联合运行 / 任务中心 / 运营大屏`；
    - 执行者侧任务创建参数被禁用并显示权限说明。

## 55. 认证账号扩展：新增 10 个执行者账号

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 默认账号种子从“单执行者”扩展为“10 个执行者”；
  - 新增执行者账号：
    - `executor01 ~ executor10`
  - 对应初始密码：
    - `exec01@123 ~ exec10@123`
  - 保留管理员账号不变：
    - `admin / admin123`

- 文件：`解疑.md`
- 主要修改：
  - 新增“已创建 10 个执行者账号了吗”问答；
  - 记录完整账号清单与初始密码。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - 本地脚本验证：
    - `get_auth_options()` 返回总账号 `11` 个，其中执行者 `10` 个；
    - `executor10 / exec10@123` 登录验证通过。

## 56. 登录页精简：不再展示全部执行者账号卡片

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 移除登录页“账号卡片列表”展示；
  - 保留最小登录入口：身份切换 + 账号 + 密码；
  - 增加一行角色示例提示（管理员示例账号、执行者示例账号），避免界面冗长。

- 文件：`解疑.md`
- 主要修改：
  - 新增“登录页为什么不再展示所有执行者账号”问答；
  - 说明账号列表隐藏后，`executor01~executor10` 仍可手动输入登录。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 登录页高度明显收敛，不再铺满账号列表。

## 57. 管理员任务中心重构：拆成多个清晰工作界面

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 将管理员原来的三栏混合界面拆为四个独立工作界面：
    - `总览`
    - `任务列表`
    - `任务回放`
    - `创建与地图`
  - 新增管理员顶部总览卡片，集中展示任务总数、执行中任务、执行者账号数、已导入地图数；
  - 将任务筛选、回放、任务创建、地图导入分离到不同界面中，降低单屏信息密度；
  - 保留执行者工作台逻辑，但将其右侧权限说明简化为更清楚的状态卡。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增管理员工作台样式：
    - 二级导航；
    - 总览卡片；
    - 任务摘要卡；
    - 回放界面双栏布局；
    - 创建任务与地图管理双栏布局；
  - 为中等屏幕和移动端补充响应式收敛规则，避免再次出现元素拥挤。

- 文件：`解疑.md`
- 主要修改：
  - 新增“管理员界面为什么要拆成多个界面”问答；
  - 说明新的管理员工作流与界面分工。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 管理员界面已从单页三栏堆叠改为分步骤工作台结构。

## 58. 管理员任务流重构：创建任务、执行中任务、已完成任务

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 新增任务排期信息能力：
    - 任务参数支持 `scheduled_start_at` 与 `scheduled_start_label`；
    - 计划时间用于约束任务何时可启动；
    - 启动动作仍需由执行者确认触发；
  - 新增执行者反馈数据表 `task_feedback`；
  - 新增反馈读写能力：
    - `get_feedback()`
    - `submit_feedback()`
  - 实时任务摘要 `_task_brief()` 增补 `params` 与 `metrics`，方便前端直接展示执行者、地图、计划时间等信息。

- 文件：`web_demo/server.py`
- 主要修改：
  - 新增反馈接口：
    - `GET /api/tasks/{task_id}/feedback`
    - `POST /api/tasks/{task_id}/feedback`

- 文件：`web_frontend/src/services/api.js`
- 主要修改：
  - 新增前端接口方法：
    - `fetchTaskFeedback()`
    - `submitTaskFeedback()`

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 管理员任务中心按真实工作流改为三个主界面：
    - `创建任务`
    - `执行中任务`
    - `已完成任务`
  - 创建任务界面支持：
    - 选择已导入地图；
    - 指定执行者；
    - 指定计划执行时间；
  - 执行中任务界面支持：
    - 查看当前活动任务；
    - 查看实时状态与当前画面；
    - 执行开始、暂停、继续、停止；
  - 已完成任务界面支持：
    - 查看历史任务；
    - 查看系统告警；
    - 查看执行者反馈；
    - 加载历史回放与导出报告；
  - 执行者界面新增“反馈问题/风险/备注”入口，数据直接提交给后端。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增管理员三段式工作区样式；
  - 新增反馈卡片、搜索框、复盘双栏等样式；
  - 为反馈输入框与管理卡片补充交互样式。

- 文件：`解疑.md`
- 主要修改：
  - 新增“管理员现在应该如何管理任务”问答；
  - 说明管理员三块功能的职责与执行者反馈链路。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - 任务排期、反馈接口与管理员三段式界面已接通。

## 59. 围绕任务主线继续收束：执行者动作、日期筛选、地图版本化、演示任务

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 调整计划任务启动逻辑：
    - 不再“到点自动开始”；
    - 改为“到达计划时间后允许开始，仍需执行者确认”；
  - 执行者反馈类型扩展为：
    - `issue`
    - `risk`
    - `note`
    - `delay_request`
    - `anomaly`

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 任务展示状态按业务阶段简化为：
    - `待执行`
    - `执行中`
    - `已完成`
  - 管理员任务列表和执行者任务列表均新增按日期筛选；
  - 执行者工作台新增动作：
    - `开始执行`
    - `申请延期`
    - `标记异常`
    - `提交备注`
  - 执行者仍可进入联合运行页查看 2D + 3D 回放，但任务启动动作回收到任务中心；
  - 导入地图时如果同名地图再次导入，不再覆盖，改为生成新版本地图名（符合“改动即新地图”的规则）。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 执行者进入联合运行页时，侧栏改为只读任务概览；
  - 不再在联合运行页暴露任务参数编辑入口，收束为观察/回放界面。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增执行者只读概览与反馈/筛选相关样式。

- 文件：`解疑.md`
- 主要修改：
  - 新增“围绕任务已确认的规则”；
  - 新增“已给执行操作员01准备两条演示任务”说明。

- 演示数据：
  - 已通过本地运行中的后端服务创建两条分配给 `executor01` 的任务：
    - `demo_executor01_warehouse`
    - `demo_executor01_campus`
  - 当前均处于 `READY` 状态，可在任务中心直接看到并手动启动。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - 本地接口确认两条演示任务已成功写入当前运行服务。

## 60. 页面结构重排：任务中心成为主入口，联合运行嵌入任务执行页

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 执行者顶层导航移除独立的 `联合运行` 标签；
  - 任务中心改为执行者主入口；
  - 保留 `任务中心 / 运营大屏` 两个顶层入口。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 执行者任务中心布局从“三栏并列”重排为：
    - 左侧：任务列表；
    - 右侧：任务执行页；
  - 点击左侧任务后，右侧进入该任务的专属页面；
  - 任务执行页中新增三个内部分区：
    - `任务执行`
    - `反馈与操作`
    - `回放与告警`
  - 原来独立页面中的联合运行视图，已内嵌到 `任务执行` 分区中。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 联合运行组件新增嵌入式模式 `embedded`；
  - 支持通过 `focusTaskId` 直接聚焦某个任务；
  - 嵌入模式下隐藏外部侧栏跳转语义，只保留任务内的 2D + 3D 联合运行能力。

- 文件：`web_frontend/src/modules/dashboard/OpsDashboardView.vue`
- 主要修改：
  - 移除“进入运营中心”旧按钮，避免和新的任务内执行页冲突。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增执行者“左列表 + 右任务页”布局样式；
  - 新增嵌入式联合运行、空态页、任务栈布局样式；
  - 调整响应式行为，确保小屏下仍能收敛为单列。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么把联合运行放进任务执行页”问答；
  - 说明新的任务驱动页面流程。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 执行者不再从独立标签进入联合运行，而是在任务中心选中任务后直接进入任务执行页。

## 61. 修复任务详情加载 404：Vite 开发代理端口错误

- 文件：`web_frontend/vite.config.js`
- 主要修改：
  - 将 Vite 开发代理目标从 `http://127.0.0.1:8090` 修正为 `http://127.0.0.1:8080`；
  - `/api` 与 `/uav-icon.png` 均同步修正。

- 问题原因：
  - 当前实际运行的后端服务在 `8080`；
  - 前端开发服务代理错误地转发到 `8090`；
  - 导致页面请求任务详情时出现 `404`。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么会出现加载任务失败 404”说明；
  - 明确指出是前端代理配置端口错误，而不是任务数据本身丢失。

## 62. 执行者任务中心交互优化：默认纯列表态，点击后展开详情

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 执行者进入任务中心时，不再默认自动选中第一条任务；
  - 左侧任务列表在未选中任务时占满下部主区域；
  - 点击某条任务后，右侧任务详情页再展开；
  - 新增“收起详情”按钮，可回到纯列表态。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 执行者任务中心新增双态布局：
    - 未选中任务：`1fr 0fr`
    - 选中任务后：左列表 + 右详情双栏
  - 为右侧详情面板补充平滑的透明度与位移动画；
  - 为整个网格补充 `grid-template-columns` 过渡，形成丝滑展开效果。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么现在默认只显示左侧任务列表”说明；
  - 解释任务中心从纯列表态进入任务详情页的交互逻辑。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 执行者任务中心现在默认以纯列表态呈现，点选任务后再展开右侧详情。

## 63. 修复任务中心日期筛选：按任务阶段匹配不同时间语义

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 重写 `matchTaskDate()` 逻辑，不再只使用单一时间字段；
  - 新增 `collectTaskDateCandidates()`：
    - `待执行`：匹配计划开始时间、创建时间、更新时间；
    - `执行中`：匹配计划时间、开始时间、创建时间、更新时间；
    - `已完成`：优先匹配完成时间，再回退更新时间、计划时间、创建时间；
  - 新增 `formatDateOnly()` 用于统一日期比对；
  - 在执行者任务中心补充日期筛选说明文案。

- 文件：`解疑.md`
- 主要修改：
  - 新增“任务中心按时间筛选之前为什么看起来没做出来”说明；
  - 解释新的日期筛选规则。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 日期筛选已从“单字段比较”改为“按任务阶段匹配不同时间语义”。

## 64. 补全管理员历史回放：支持已完成任务加载并播放 2D 回放

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 新增历史回放持久化目录：`results/mac_eval/task_replays/`；
  - 任务在 `READY` 阶段完成回放准备后，会把 `environment / frames / metrics / meta` 写入对应的 JSON 文件；
  - 重写 `get_replay()`：
    - 当前内存中的任务继续直接返回实时回放帧；
    - 历史任务优先读取落盘的回放文件；
    - 若旧任务没有回放文件，则按任务参数重新构建回放并自动补存；
  - 抽出 `_build_playback()`，统一处理：
    - `model` 源优先真实推理；
    - 推理失败时回退到 sample 回放；
    - `sample` 源直接使用模板回放。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 执行者 / 管理员切换任务时会先重置旧回放状态，避免沿用上一条任务的帧；
  - 管理员在“已完成任务”页选中任务后，会自动尝试加载历史回放；
  - `播放回放` 按钮改为：
    - 若还未加载回放，先自动请求历史回放；
    - 加载成功后直接开始播放；
  - 保留静默加载模式，避免自动加载时不断覆盖状态提示。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么管理员里的‘播放回放’之前看起来没做出来”说明；
  - 解释之前 `0/0` 的根因是历史帧未持久化；
  - 说明现在已支持历史任务落盘回放与旧任务补建回放。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - `python3` 直接调用 `TaskRuntime.get_replay('4511d2d0c5d6')` 与 `TaskRuntime.get_replay('d7d20597684c')` 均返回可用回放；
  - `curl http://127.0.0.1:8080/api/tasks/4511d2d0c5d6/replay` 已确认返回 `available=True` 且带有历史帧。

## 65. 中期汇报 PPT 提示词问答补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“毕业设计中期汇报 PPT 的 AI 生成提示词应该怎么写”问答；
  - 总结适合本项目的中期汇报结构主线：
    - 课题背景与意义；
    - 系统总体方案；
    - 已完成模块；
    - 前端界面展示；
    - 当前成果、问题与后续计划；
  - 明确 PPT AI 生成时应偏向“答辩汇报风格、少字清晰、多图示与界面页”。

## 66. 新增中期汇报 PPT 正文稿

- 新增文件：`MIDTERM_PPT_CONTENT_CN.md`
- 主要内容：
  - 按约 13 页结构编写毕业设计中期汇报正文；
  - 每页包含：
    - 标题
    - 可直接上 PPT 的页面正文
    - 页面备注 / 版式建议
  - 内容覆盖：
    - 课题背景
    - 研究目标
    - 系统总体方案
    - 算法与训练框架
    - 后端设计
    - 前端架构
    - 主要界面展示
    - 已完成成果
    - 当前问题
    - 后续计划

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否直接给出这套中期汇报 PPT 的每一页正文内容”问答；
  - 说明正文稿已整理完成，并记录其适用用途（手工制作 / PPT AI 生成 / 后续改稿）。

## 67. 答辩现场“小改代码”问答补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“答辩时老师可能会让我现场改什么代码”问答；
  - 结合当前项目结构，判断答辩现场更可能出现的是：
    - 前端页面文案、默认值、筛选逻辑、指标展示、模板选项、2D/3D 显示行为等小改动；
  - 明确列出最值得提前熟悉的文件：
    - `web_frontend/src/App.vue`
    - `web_frontend/src/modules/taskcenter/TaskCenterView.vue`
    - `web_frontend/src/modules/dashboard/OpsDashboardView.vue`
    - `web_frontend/src/modules/operations/OperationsModeView.vue`
    - `web_frontend/src/modules/shared/renderer.js`
    - `web_frontend/src/services/api.js`
  - 说明一般不太会现场要求重改强化学习训练主流程或底层 C++ 规划器。

## 68. 新增 modules 页面说明文档

- 新增文件：`web_frontend/src/modules/MODULES_UI_OVERVIEW_CN.md`
- 主要内容：
  - 逐个介绍 `modules` 目录下各个 `.vue` 文件对应的页面界面；
  - 说明每个页面的主要职责、适用对象、页面特点；
  - 补充答辩现场最可能被要求修改的点，便于快速定位代码。

- 文件：`解疑.md`
- 主要修改：
  - 新增“能否在 `modules` 目录下单独放一份文档，介绍每个 Vue 文件对应的界面”问答；
  - 说明该文档已生成，并概述其适用场景（答辩复习 / 页面讲解 / 快速定位文件）。

## 69. 吞吐量计算口径问答补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“界面中显示的平均吞吐量是如何计算的”问答；
  - 明确区分两层口径：
    - 单任务吞吐量：`tasks_completed / total_steps`
    - 运营大屏平均吞吐量：各任务 `metrics.throughput` 的算术平均
  - 补充说明运行中实时快照会使用 `tasks_completed / current_step`，并用 `max(1, step)` 避免除零。

## 70. 截图对应 Vue 文件问答补充

- 文件：`解疑.md`
- 主要修改：
  - 新增“这张界面截图对应哪个 Vue 文件”问答；
  - 明确指出整张截图的外层页面是 `web_frontend/src/modules/taskcenter/TaskCenterView.vue`；
  - 补充说明其中的联合运行区域实际上由 `OperationsModeView.vue` 嵌入渲染；
  - 记录答辩时可直接使用的口径：外层是任务中心，内层是联合运行页，执行/反馈/回放都属于任务中心详情态。

## 70. 优化任务中心日期筛选交互：改为点击弹出日历选择

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 将执行者任务中心、管理员执行中任务、管理员已完成任务这 3 处日期筛选统一改为“点击弹出日历”的交互；
  - 为 3 个日期筛选输入框分别增加 `ref`，并新增 `openDatePicker()`：
    - 优先使用浏览器原生 `showPicker()` 打开日历；
    - 不支持时回退到 `focus() + click()`；
  - 在日期输入框上拦截 `keydown` 与 `beforeinput`，避免用户把日期框当作纯文本输入框手动键入。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增 `date-picker-trigger`、`date-picker-input`、`date-picker-button` 样式；
  - 将日期筛选区域整理为“日期框 + 选择日期按钮”的清晰结构；
  - 强化可点击感，让筛选控件更像正式业务系统里的日历筛选器。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么把任务中心的日期筛选改成弹出式日历选择”问答；
  - 说明修改原因是避免看起来像普通文本框、减少手动输入日期。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 日期筛选现在会通过点击输入框或按钮弹出原生日历，而不是依赖手动输入。

## 71. 补全任务历史回放视图：回放页改为 2D + 3D 双视图

- 文件：`web_frontend/src/modules/shared/renderer.js`
- 主要修改：
  - 新增共享的 `drawScene3D()`；
  - 将 3D 网格、障碍物、目标点、无人机投影绘制能力沉淀到共享渲染模块；
  - 新增 `resizeCanvasToDisplaySize()` 供 3D 画布自适应使用。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 管理员“已完成任务”中的历史回放区域，从单一 2D 画布改为：
    - `2D 历史回放`
    - `3D 历史回放`
  - 执行者任务页中的“回放与告警”区域，同样改为 2D + 3D 双视图；
  - 历史回放绘制逻辑改为同时驱动两块画布，确保同一帧下 2D 与 3D 同步播放；
  - 新增回放视图状态 `replayViewState.selectedDroneId`，用于 3D 相机聚焦；
  - 新增 `getReplayCanvasTargets()` 与 `syncReplaySelectedDrone()`，分别处理：
    - 当前应绘制到哪一组回放画布；
    - 选中无人机不存在时自动回退到首个无人机；
  - 切换到执行者“回放与告警”页签时，会自动重绘当前历史回放。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么任务回放页不应该只有 2D 视图”问答；
  - 说明回放页已经统一为和联合运行页一致的 2D + 3D 双视图复盘方式。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 任务中心中的历史回放区域现在会同步展示 2D 与 3D；
  - 播放历史回放时，两块画布会使用同一历史帧同步更新。

## 72. 调整历史回放画布比例：2D 与 3D 分别按视图类型适配容器

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 为任务中心中的历史回放视图补充专用类名：
    - `history-view-card`
    - `history-canvas-wrap`
    - `history-canvas-wrap-2d`
    - `history-canvas-wrap-3d`
  - 让 2D 与 3D 回放窗口在模板层面具备独立比例控制，而不再共用默认窗口尺寸。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增 `history-dual-view-grid` 和 `history-view-card` 布局样式；
  - 将 `2D 历史回放` 容器改为方形比例；
  - 将 `3D 历史回放` 容器改为更适合空间展示的宽屏比例；
  - 为历史回放专用画布单独设置 `width: 100%` 与 `height: 100%`，不再沿用通用固定高度。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么历史回放里的 2D 和 3D 画面比例还需要单独适配”问答；
  - 解释之前的问题是 2D / 3D 共用同一种固定画布比例，导致观感不自然。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 历史回放页中的 2D 与 3D 现在会分别按更合适的比例展示，不再共用同一固定拉伸规则。

## 73. 修正历史回放绘制尺寸：与任务执行页对齐 canvas resize 逻辑

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 引入共享工具 `resizeCanvasToDisplaySize`；
  - 在以下场景绘制前，先同步 canvas 内部像素尺寸：
    - `drawEmptyCanvas()`
    - `drawTaskSnapshotTo()`
    - `drawReplayFrame()` 中的 2D 历史回放绘制
  - 让历史回放页的 2D 画布与任务执行页使用同样的尺寸同步逻辑。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 取消历史回放区之前单独设置的特殊 `aspect-ratio`；
  - 将历史回放画布高度重新对齐到任务执行页一致的 `500px`；
  - 避免“CSS 尺寸改了，但 canvas 内部像素尺寸还停留在旧值”的错位感。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么任务执行页正常，但历史回放页看起来还是比例不对”问答；
  - 说明根因是历史回放页没有完整对齐执行页的 canvas resize 机制。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 历史回放页现在已按与任务执行页一致的 canvas 尺寸同步规则绘制，比例表现会更接近执行页。

## 74. 修复待执行任务无法启动：服务重启后恢复非终态任务到运行时

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 新增 `RESTORABLE_STATUSES = {'PREPARING', 'READY', 'RUNNING', 'PAUSED'}`；
  - 在 `TaskRuntime.__init__()` 中加入 `_restore_live_tasks()`；
  - 启动服务时会从数据库恢复非终态任务到运行时内存 `self.tasks`；
  - 新增 `TaskDB.list_restorable_tasks()`，专门读取需要恢复的任务；
  - 恢复任务时会：
    - 优先读取已落盘的历史回放；
    - 若没有回放文件则按任务参数重建；
    - 还原任务参数、帧索引、运行指标、历史告警；
    - 将重启前处于 `RUNNING` 的任务恢复为 `PAUSED`，避免服务重启后自动继续执行。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么待执行任务会提示‘开始执行失败：Task not found’”问答；
  - 说明根因是任务在数据库中存在，但没有恢复成运行时 live task。

- 运行与验证：
  - `python3 -m py_compile web_demo/task_runtime.py web_demo/server.py` 通过；
  - 本地验证 `d7d20597684c` 在修复前为“数据库中 READY，但 live task 不存在”；
  - 修复后，新建演示任务 `6c0b04af4958 / demo_executor01_campus_restore`；
  - 通过 HTTP 调用 `/api/tasks/6c0b04af4958/control`，已验证能从 `READY` 正常切到 `RUNNING`。

## 75. 修复管理员“执行中任务”详情显示：改为嵌入式联合运行视图

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 管理员“执行中任务”右侧详情区，不再单独渲染一块静态 canvas；
  - 改为直接嵌入 `OperationsModeView` 的 `embedded` 版本；
  - 任务焦点继续由当前 `selectedTaskId` 驱动。

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 新增 `admin-active-embedded` 样式；
  - 对嵌入式联合运行视图做管理员页适配：
    - 去掉重复的外层 panel 边框和背景；
    - 隐藏内部重复标题；
    - 保持状态卡片与当前管理员详情布局自然衔接。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么管理员‘执行中任务’里的任务详情显示要改成嵌入式联合运行视图”问答；
  - 说明之前管理员和执行者展示不一致，而且单独 canvas 更容易出空白问题。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - 管理员任务详情现在与执行者使用同一套联合运行视图展示逻辑。

## 76. 快速修复管理员“执行中任务”页在桌面全屏下的右侧详情溢出

- 文件：`web_frontend/src/styles.css`
- 主要修改：
  - 给管理员工作区内的 panel 补充 `min-width: 0`，避免 grid item 以内容最小宽度继续向外撑开；
  - 调整 `admin-active-embedded` 相关样式：
    - 嵌入式联合运行视图改为更紧凑的单列画布布局；
    - 状态卡片保持两列但允许在当前容器内收缩；
    - 内嵌表格改为可横向滚动，避免表格把右侧详情区撑出边界；
    - 统一补充 `min-width: 0`，让内嵌 canvas、视图卡片和表格都受容器约束。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么管理员‘执行中任务’页在全屏下会出现右侧详情溢出”问答；
  - 记录问题根因是外层双栏 + 内嵌联合运行视图双列布局叠加导致的最小宽度溢出；
  - 说明本次修复目标仅覆盖桌面全屏可用。

- 验证结果：
  - `npm --prefix web_frontend run build` 通过；
  - Playwright 在桌面全屏下复测管理员“执行中任务”页，右侧详情已回到容器内，不再横向溢出。

## 77. 补充训练损失曲线查看位置说明

- 文件：`解疑.md`
- 主要修改：
  - 新增“模型训练时损失曲线的图片是在哪个网站看”问答；
  - 说明项目训练日志接入的是 `Weights & Biases (wandb)`；
  - 说明 `training_run.py` 中使用了 `wandb.init(..., sync_tensorboard=True)`；
  - 同时标注当前默认训练参数为 `use_wandb=False`，因此当前训练默认不会上传在线曲线。

## 78. 角色展示名称统一：将“执行者”改为“监督员”

- 文件：`web_frontend/src/App.vue`
- 主要修改：
  - 登录页身份按钮从“执行者”改为“监督员”；
  - 顶部身份标签改为“管理员 / 监督员”；
  - 登录提示文案改为“监督员账号示例”。

- 文件：`web_frontend/src/modules/taskcenter/TaskCenterView.vue`
- 主要修改：
  - 管理员创建任务、搜索、反馈、报告导出等区域中的“执行者”统一改为“监督员”；
  - “分配执行者”改成“分配监督员”；
  - “执行者反馈”改成“监督员反馈”；
  - 执行侧任务中心说明改为“分配给当前监督员的任务”；
  - 相关状态提示也同步替换。

- 文件：`web_frontend/src/modules/operations/OperationsModeView.vue`
- 主要修改：
  - 只读说明改为“监督员仅查看当前任务”；
  - 启动限制提示改为“监督员不能新建任务”。

- 文件：`web_demo/task_runtime.py`
- 主要修改：
  - 默认账号展示名从“执行操作员01~10”改为“监督员01~10”；
  - 默认部门从“运营执行组”改为“运营监督组”；
  - 默认岗位从“无人机调度执行”改为“无人机运行监督”；
  - 提交未分配任务反馈时的报错文案改为“当前监督员不能提交...”。

- 文件：`解疑.md`
- 主要修改：
  - 新增“为什么把‘执行者’统一改成‘监督员’”问答；
  - 说明这次只改对外展示名称，不修改底层 `executor` 角色值。

- 验证结果：
  - `python3 -m py_compile web_demo/task_runtime.py` 通过；
  - `npm --prefix web_frontend run build` 通过；
  - 后端已重启，`/api/auth/options` 返回的默认账号展示名已变为“监督员01”。

## 79. 补充项目技术介绍说明

- 文件：`解疑.md`
- 主要修改：
  - 新增“这个项目的技术介绍应该怎么写”问答；
  - 按当前仓库真实技术栈整理了一版可直接用于论文或系统说明的技术介绍；
  - 明确前端采用 `HTML + CSS + JavaScript + Vue.js + Vite + Canvas`；
  - 明确后端采用 `Python + ThreadingHTTPServer` 的轻量服务结构；
  - 明确数据存储采用 `SQLite`，而不是 Django/MySQL 方案。

## 80. 补充论文表述风险说明：不建议将当前项目写成 Django

- 文件：`解疑.md`
- 主要修改：
  - 新增“论文里能不能直接写‘用了 Django’”问答；
  - 说明当前项目真实技术栈并非 Django；
  - 补充答辩风险点：若写成 Django，容易被追问 `settings.py / urls.py / ORM / manage.py` 等实现细节；
  - 建议论文里保持为“Python 后端服务”表述，更符合当前代码实现。

## 81. 后端迁移为 Django，并完成前端接口兼容检查

- 文件：`manage.py`
- 主要修改：
  - 新增 Django 项目入口，支持使用标准 `manage.py runserver` 启动后端。

- 文件：`backend_django/settings.py`
- 主要修改：
  - 新增 Django 基础配置；
  - 使用 `SQLite` 作为 Django 默认数据库；
  - 设置时区、静态资源基础配置和最小中间件。

- 文件：`backend_django/urls.py`
- 主要修改：
  - 将原有后端 API 路径迁移到 Django 路由体系；
  - 保持 `/api/...` 路径不变，兼容现有前端调用。

- 文件：`backend_django/views.py`
- 主要修改：
  - 将原先 `web_demo/server.py` 中的接口逻辑迁移为 Django 视图；
  - 接入原有 `TaskRuntime`，保持任务、认证、反馈、回放、推理等逻辑继续复用；
  - 使用 `StreamingHttpResponse` 兼容任务事件 SSE 流；
  - 保留 `/uav-icon.png` 与静态首页入口。

- 文件：`web_demo/server.py`
- 主要修改：
  - 从原先自建 `ThreadingHTTPServer` 改为 Django 启动兼容包装器；
  - 保留原来的 `python web_demo/server.py --host ... --port ...` 启动习惯；
  - 内部转为调用 Django `runserver --noreload`。

- 文件：`requirements.txt`
- 主要修改：
  - 新增 `Django>=5,<6` 依赖。

- 文件：`web_demo/README.md`
- 主要修改：
  - 增加 Django 本地启动说明；
  - 保留旧兼容入口说明；
  - 说明前端仍通过同样的 `/api/...` 路径访问后端。

- 文件：`解疑.md`
- 主要修改：
  - 更新项目技术介绍，将后端表述改为 Django；
  - 更新“论文里能不能直接写用了 Django”的结论；
  - 新增“后端迁移到 Django 后，前端对后端的引用要不要改”问答。

- 前端引用检查结果：
  - `web_frontend/src/services/api.js` 中所有 `fetch` 与 `EventSource` 调用路径继续保持不变；
  - `web_frontend/vite.config.js` 中 `/api` 和 `/uav-icon.png` 代理目标仍可继续指向 `127.0.0.1:8080`；
  - 本次迁移无需修改前端业务接口路径。

- 验证结果：
  - `python3 -m py_compile manage.py backend_django/*.py web_demo/server.py` 通过；
  - `python3 manage.py check` 通过；
  - 已安装 Django 并成功启动 `http://127.0.0.1:8080`；
  - 已验证 `/api/auth/options`、`/api/tasks`、`/uav-icon.png` 正常返回；
  - 通过 Playwright 验证前端经 Vite 代理后可正常访问 Django 后端并完成登录。

## 79. 补充文献综述论文检索结果，并建立“章节-论文”映射

- 文件：`文献综述-薛文清-2210720131-修订源.html`
- 主要修改：
  - 在引言中补入检索范围、数据库来源、关键词和筛选数量说明；
  - 按现有章节结构补强了 MAPF、LMAPF、搜索方法、学习方法、混合式方法的代表论文引用；
  - 将参考文献从 5 篇扩充到 15 篇；
  - 修正了原先过于单薄的引用结构，使“正文论述”和“参考文献列表”真正对应起来。

- 文件：`文献综述-薛文清-2210720131.docx`
- 主要修改：
  - 根据修订后的 HTML 源重新导出正式 `.docx` 文档；
  - 已确认导出结果包含新的检索说明、正文引用和 15 篇参考文献。

- 文件：`文献综述论文映射.md`
- 主要修改：
  - 新增一份单独的“论文映射”说明；
  - 明确列出每个章节适合引用哪些论文，以及这些论文主要支撑什么论述。

- 文件：`解疑.md`
- 主要修改：
  - 新增“文献综述应该补哪些论文，以及各自适合放在哪一部分”问答；
  - 便于后续写论文正文或答辩时直接复用。

- 处理结果：
  - 当前文献综述已经不再只有零散 5 篇参考文献；
  - 已具备“检索说明 + 正文引用 + 章节映射 + 扩充参考文献”的基本完整形态。

## 80. 按陈晶文献综述的结构重排当前文档

- 文件：`文献综述-薛文清-2210720131-修订源.html`
- 主要修改：
  - 参考 `2110716219_陈晶_文献综述.doc` 的结构，不参考其具体内容；
  - 将原先按“搜索方法 / 学习方法 / 混合方法”平铺展开的结构，重组为更接近学校常见文献综述写法的层次：
    - `【内容摘要】`
    - `【关键词】`
    - `导言`
    - `研究背景及意义`
    - `国内外研究现状`
    - `相关理论介绍`
    - `系统架构设计及技术介绍`
    - `总结`
    - `参考文献`
  - 同时保留原来与你课题相关的 MAPF、LMAPF、强化学习、混合式方法和系统实现内容。

- 文件：`文献综述-薛文清-2210720131.docx`
- 主要修改：
  - 根据重排后的 HTML 源重新导出 Word；
  - 已核对导出内容，确认正式文档已变为新结构。

- 文件：`解疑.md`
- 主要修改：
  - 新增“文献综述已经按陈晶那份的结构重排了吗”问答；
  - 记录本次调整是“只参考结构，不参考内容”。

- 处理结果：
  - 当前文献综述更贴近样本文档的组织方式；
  - 章节层次更像学校提交版，不再只是技术路线型综述。

## 81. 重写文献综述导言

- 文件：`文献综述-薛文清-2210720131-修订源.html`
- 主要修改：
  - 重写“导言”部分，不再采用偏项目介绍式的开头；
  - 改为“现实需求背景 -> 学术问题界定 -> 技术路线概述 -> 文献检索说明 -> 全文结构说明”的写法；
  - 强化了 MAPF / LMAPF 的问题界定，以及搜索方法、学习方法、混合式方法三类路线的过渡。

- 文件：`文献综述-薛文清-2210720131.docx`
- 主要修改：
  - 已重新导出并覆盖正式 Word 文件；
  - 已核对导言内容，确认正式文件中已替换为新版本。

- 文件：`解疑.md`
- 主要修改：
  - 新增“导言这次是怎么重写的”问答；
  - 说明本次调整的逻辑和目标。

## 82. 补充一段可直接复用的文献综述概括表述

- 文件：`解疑.md`
- 主要修改：
  - 新增“按样句格式，怎么概括本项目的文献综述目的”问答；
  - 提供一段可直接放入文献综述或论文中的标准表述；
  - 内容围绕 MAPF、LMAPF、多智能体强化学习及“全局规划 + 局部强化学习”路线展开。

## 83. 按陈晶结构重写文献综述，并做多轮自检

- 文件：`文献综述-薛文清-2210720131-修订源.html`
- 主要修改：
  - 不再做零散修补，而是按陈晶文献综述的结构对正文进行整篇重写；
  - 重新组织了导言、背景意义、国内外研究现状、理论基础、系统架构和总结之间的逻辑关系；
  - 增强了“问题定义 -> 技术路线 -> 文献评述 -> 项目方案落点”的上下文衔接；
  - 调整了参考文献组织和正文引用关系，使国内外文献、经典方法、学习方法和混合方法的使用更清晰。

- 文件：`文献综述-薛文清-2210720131.docx`
- 主要修改：
  - 根据重写后的 HTML 多次重新导出正式 Word；
  - 最终以复核后的终稿覆盖正式文件名。

- 文件：`解疑.md`
- 主要修改：
  - 新增“这次文献综述是如何按陈晶结构重写并做自检的”问答；
  - 记录本次重写的思路和检查过程。

- 自检结果：
  - 已检查章节结构是否完整；
  - 已检查引用编号与参考文献条目数量一致；
  - 已通过导出后的 Word 文本再次通读，确认主要段落之间逻辑可顺读；
  - 当前版本比之前更接近正式毕业设计文献综述的行文方式。

## 84. 新增当前项目的系统模块图 Markdown 版本

- 文件：`SYSTEM_MODULE_DIAGRAM_CN.md`
- 主要修改：
  - 参考用户提供的样例模块图组织方式，为当前项目整理了一版可直接用于论文或 PPT 的模块图；
  - 使用 Markdown + Mermaid 表达系统总模块、一级功能模块和二级子模块；
  - 模块划分不是按代码目录机械拆分，而是按系统真实职责抽象为：
    - 登录与身份管理模块
    - 任务调度管理模块
    - 路径规划与算法运行模块
    - 运行监控与可视化模块
    - 数据存储与服务支撑模块

- 文件：`解疑.md`
- 主要修改：
  - 新增“当前这个项目的系统模块图应该怎么画”问答；
  - 说明这次模块划分为何更适合论文中的系统模块图，而不是代码目录图。

## 85. 将系统模块图改为仅展示可演示功能的功能模块图

- 文件：`SYSTEM_MODULE_DIAGRAM_CN.md`
- 主要修改：
  - 将原先偏“系统职责/架构”的模块图，改成偏“用户可见功能”的功能模块图；
  - 删除 `数据存储与服务支撑模块`、`路径规划与算法运行模块` 这类不适合现场演示的内部实现模块；
  - 重新整理为四个一级模块：
    - `登录模块`
    - `任务中心模块`
    - `联合运行模块`
    - `运营大屏模块`
  - 各一级模块下补充对应的可演示子功能，如任务创建分配、2D/3D 联合运行、任务统计和告警展示等。

- 文件：`解疑.md`
- 主要修改：
  - 新增“功能模块图和系统架构图有什么区别，当前项目该怎么改”问答；
  - 说明为什么这次要把模块图改成只展示前端可演示功能的版本。

## 86. 补充当前四大功能模块划分的合理性分析与命名建议

- 文件：`解疑.md`
- 主要修改：
  - 新增“现在这四个大模块这样分合理吗，有什么建议”问答；
  - 说明当前四模块划分方向上合理，但 `系统管理模块` 与 `人员管理` 存在边界重叠问题；
  - 给出两套更适合答辩的命名建议：
    - 正式版：`登录与身份管理模块 / 任务中心模块 / 联合运行与状态监控模块 / 运营展示模块`
    - 直白版：`登录模块 / 任务中心模块 / 联合运行模块 / 运营大屏模块`
  - 解释为什么不建议继续把 `人员管理` 单独作为一级核心模块。

## 87. 补充四个功能模块对应的二级子模块建议

- 文件：`解疑.md`
- 主要修改：
  - 新增“这四个模块下的子模块分别是什么”问答；
  - 按正式版四模块结构补充二级子模块建议：
    - `登录与身份管理模块`：管理员登录、监督员登录、角色切换、退出登录
    - `任务中心模块`：任务创建与分配、地图导入与模板选择、执行中任务查看、已完成任务复盘、反馈与告警查看
    - `联合运行与状态监控模块`：任务控制、2D/3D 视图、无人机状态、任务回放与异常监控
    - `运营展示模块`：任务统计、运行监控、实时地图快照、平均吞吐量、最近告警
  - 说明这套拆法更适合答辩中的功能模块图表达。

## 88. 补充登录子模块命名合并建议

- 文件：`解疑.md`
- 主要修改：
  - 新增“管理员登录和监督员登录能不能合并成一个名字”问答；
  - 说明两者本质同属登录功能，适合在功能模块图中合并表达；
  - 给出 `用户登录 / 角色登录 / 身份登录` 三种可选命名；
  - 推荐在当前项目中使用 `用户登录`，并说明其下包含管理员登录和监督员登录两种角色入口。
