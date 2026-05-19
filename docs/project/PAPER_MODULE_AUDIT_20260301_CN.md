# 论文模块实现核对说明（2026-03-01）

本文档记录 2026 年 3 月 1 日对论文模块实现情况的逐项核对结果，并同步记录本次将 DT 默认变换数量调整为 `8` 的修改。

## 1. 本次修改

本次根据论文描述，将训练配置中的：

- `dt_num_transforms_per_batch`

默认值从 `4` 调整为 `8`，位置在：

- `learning/learning_config.py`

这样当前训练默认会使用完整 D4 变换集合：

- `rot0`
- `rot90`
- `rot180`
- `rot270`
- `flip_lr_rot0`
- `flip_lr_rot90`
- `flip_lr_rot180`
- `flip_lr_rot270`

该调整更贴近论文中对 DT 的完整使用方式，但同时也会提高显存占用与 learner 端训练开销。

## 2. 论文模块逐项核对

以下核对以论文提到的 SMAPO 主要模块为顺序，对照当前仓库代码判断其是否已经实现。

### 2.1 PP 阶段：LB-A*

结论：**已实现**

对应代码：

- `env/planning.py`
- `planner/LB_A/planner.h`
- `planner/LB_A/planner.cpp`

说明：

- 当前训练环境会在 `SMAPO` 预处理阶段调用 LB-A* planner。
- C++ planner 已支持论文所需的 PlCC 和 PeCC 参数入口。
- 训练链路中 `pecc_gamma` 已支持按地图尺寸自动解析，而不是继续完全写死。

### 2.2 PlCC：计划拥堵成本

结论：**已实现**

对应代码：

- `planner/LB_A/planner.h`

说明：

- 已按论文拆分同时间冲突与异时间冲突两种代价。
- 当前实现中：
  - `alpha = 2.0`
  - `beta = 0.5`
  - `lambda = 0.8`
- 时间窗口由 `plcc_delta_t` 控制。

与论文的一致点：

- `k = 0` 使用更强惩罚
- `k != 0` 使用衰减惩罚
- 在时间窗口内累加时域拥堵代价

### 2.3 PeCC：感知拥堵成本

结论：**已实现**

对应代码：

- `planner/LB_A/planner.h`
- `env/planning.py`
- `env/replan.py`
- `planning/replan_algo.py`

说明：

- 训练主链路里的 C++ planner 已支持 PeCC 的历史衰减更新。
- `env/planning.py` 中若未显式传入 `pecc_gamma`，会按地图尺寸自动解析。
- 轻量 Python replanner 现在也会优先按论文公式解析 `gamma`，不再保留孤立的 `0.8` 硬编码默认值。

需要注意的一点：

- 如果轻量 replanner 在运行时拿不到全图尺寸，会退回到观测窗口尺寸估计 `gamma`
- 这仍比固定 `0.8` 更接近论文口径，但精确性不如显式提供地图宽高

### 2.4 DR 阶段：基于 MARL 的决策精炼

结论：**已实现**

对应代码：

- `env/SMAPO.py`
- `sample_factory/algorithms/appo/model.py`
- `sample_factory/algorithms/appo/model_utils.py`

说明：

- 规划结果会先写入观测，再送入策略网络。
- 策略网络输出每个智能体下一步离散动作。
- 环境使用同步 step 方式推进多智能体动作。

论文中的“PP 给初始路径，DR 做局部决策精炼”的总流程，当前代码已经具备。

### 2.5 SA：空间感知模块

结论：**已实现**

对应代码：

- `learning/learning_config.py`
- `learning/encoder_residual.py`

说明：

- 当前配置中 `num_res_blocks = 8`
- 编码器主干使用 ResNet 风格残差块堆叠
- 输入是局部观测张量，符合论文中对空间特征提取的设定

需要注意的一点：

- `learning/encoder_residual.py` 中存在 `coordinates_mlp`
- 但当前 `forward` 主路径并未实际使用这一分支

这不影响 SA 主干已经实现，但说明当前实现与论文表述并非逐层完全一一对应。

### 2.6 IP：交互感知模块

结论：**已实现**

对应代码：

- `sample_factory/algorithms/appo/model_utils.py`

说明：

- 当前实现使用 `Attention_cob`
- 结合 `attention_mask` 处理动态数量邻居
- 符合论文中“可见邻居数量动态变化，因此使用 mask-attention”的描述

### 2.7 RVE：相对向量嵌入

结论：**已实现**

对应代码：

- `sample_factory/algorithms/appo/model_utils.py`

说明：

- 当前实现中存在 `RelativeEmbedding2D`
- 并被 `Attention_cob` 调用
- 用于把相对位置编码并融入注意力计算

这与论文中为 IP 模块补充位置信息的设计是一致的。

### 2.8 TA：时间感知模块

结论：**已实现**

对应代码：

- `sample_factory/algorithms/appo/model_utils.py`

说明：

- 当前策略核心 `PolicyCoreRNN` 支持 `GRU`
- 当前代码路径中使用的是 GRU 型循环核心
- 这与论文中“利用历史信息缓解 POMDP”的设计一致

### 2.9 GAD：群组动作解码器

结论：**已实现**

对应代码：

- `sample_factory/algorithms/appo/model.py`

说明：

- actor 分支负责输出动作分布
- critic 分支负责输出状态价值
- 当前环境动作空间为离散 5 动作：
  - 停留
  - 上
  - 下
  - 左
  - 右

与论文 GAD 的基本功能一致。

### 2.10 DT：双重变换数据增强

结论：**已实现**

对应代码：

- `sample_factory/algorithms/appo/learner.py`
- `learning/learning_config.py`

说明：

- DT 已真正接入 learner 的 minibatch 训练阶段
- 当前支持旋转与镜像组合
- 会同步变换：
  - 局部栅格观测
  - 坐标特征
  - 动作标签
  - 旧策略 logits

本次又把默认 `dt_num_transforms_per_batch` 调整为 `8`，使其默认使用完整 D4 变换集合，更贴近论文。

需要说明的一点：

- 当前 DT 是在 learner 端在线增强 minibatch
- 并没有单独实现一个“对偶缓冲区”对象

但从训练效果和数据变换逻辑上，它已经满足论文 DT 的核心要求。

## 3. 与论文相比仍存在的差异

当前仓库与论文已经高度接近，但仍不是逐项完全无差异复刻，主要残留差异如下：

1. SA 模块里存在未实际参与主前向路径的 `coordinates_mlp`
2. DT 采用的是 learner 端在线增强，而不是单独的 dual buffer 结构
3. 论文里的若干消融变体（如移除 IP、移除 RVE、移除 TA）没有做成独立开关化配置

## 4. 当前结论

如果按论文模块逐项核对，当前代码状态可以概括为：

- PP：已实现
- PlCC：已实现
- PeCC：已实现
- DR：已实现
- SA：已实现
- IP：已实现
- RVE：已实现
- TA：已实现
- GAD：已实现
- DT：已实现，并已将默认增强数调整为 `8`

也就是说，论文提出的核心模块在当前仓库中已经基本都能找到对应实现；当前更需要关注的是“个别默认参数和辅助路径是否彻底统一到论文口径”。
