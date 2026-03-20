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
