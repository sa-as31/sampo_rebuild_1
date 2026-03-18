# 训练问题修复说明（2026-02-28）

本文档记录 2026 年 2 月 28 日对训练链路所做的修复，目标是让当前项目在关键实现上更接近论文《Learn to Refine: Synergistic Multi-Agent Path Optimization for Lifelong Conflict-Free Navigation of Autonomous Vehicles》描述的训练逻辑，尤其是初始规划阶段（PP）的代价建模与决策精炼阶段（DR）的奖励输入一致性。

## 1. 修复背景

在对当前仓库代码、历史修改记录和论文描述进行对照后，发现训练链路里有几处会直接影响训练结果的偏差：

1. 训练实际使用的是 C++ planner 路径，而不是后来补的 Python `replan_algo.py`。
2. 训练入口中没有把论文里的 LB-A* 参数暴露到真实训练链路。
3. PeCC 的历史衰减系数 `gamma` 在现有代码里等价于固定值 `0.8`，与论文给出的 `0.5 / (map_w + map_h)` 不一致。
4. C++ planner 中 PlCC 与 PeCC 的代价逻辑混在一起，没有严格按照论文里的“时间拥堵惩罚”和“感知拥堵衰减”分开计算。
5. `env/SMAPO.py` 中对子目标奖励和路径子目标的处理存在边界问题，当某个 agent 没有有效 path 时，奖励记录可能与 agent 数量错位。

## 2. 本次修改内容

### 2.1 为训练用 planner 暴露论文参数

修改文件：

- `env/planning.py`

新增并接入的参数：

- `plcc_alpha`
- `plcc_beta`
- `plcc_lambda`
- `plcc_delta_t`
- `pecc_gamma`

对应默认值：

- `plcc_alpha = 2.0`
- `plcc_beta = 0.5`
- `plcc_lambda = 0.8`
- `plcc_delta_t = 2`
- `pecc_gamma = None`

其中 `pecc_gamma = None` 的含义是：训练时默认不再硬编码为某个固定值，而是在 planner 初始化时根据真实地图尺寸自动计算：

```text
pecc_gamma = 0.5 / (map_w + map_h)
```

这样可以使训练链路中的 PeCC 衰减更接近论文设定。

### 2.2 修复 C++ LB-A* 中 PlCC / PeCC 的成本逻辑

修改文件：

- `planner/LB_A/planner.h`
- `planner/LB_A/planner.cpp`

主要修复：

1. 将原先单一 `gamma` 拆分为：
   - `plcc_alpha`
   - `plcc_beta`
   - `plcc_lambda`
   - `pecc_gamma`
   - `plcc_delta_t`

2. 将 PlCC 的代价计算改成论文对应形式：

```text
k = 0     -> alpha * count^2
k != 0    -> beta * count * lambda^|k|
```

3. 将时间窗口从固定写死改为由 `plcc_delta_t` 控制，并改成包含式窗口：

```text
[t - delta_t, t + delta_t]
```

4. 为 PeCC 增加真正的历史衰减更新：

```text
PeCC_t = pecc_gamma * PeCC_{t-1} + 当前观测占用
```

也就是说，动态占用矩阵 `num_occupations` 在每步更新前会先做衰减，而不是一直无衰减累加。

5. 更新 pybind11 绑定，使新的 planner 构造参数可以从 Python 训练入口传入。

### 2.3 修复 SMAPO 预处理中的奖励/子目标边界问题

修改文件：

- `env/SMAPO.py`

主要修复：

1. `add_r` 显式声明为布尔类型，避免配置解析时行为不稳定。
2. 每个 agent 都会稳定追加一条 intrinsic reward 记录，不再因为 `path is None` 或路径长度不足导致 `intrinsic_rewards` 长度与 agent 数量不一致。
3. 只有在 `path` 长度大于 1 时才使用 `path[1]` 作为子目标，否则回退到最终目标 `target_xy`。
4. 子目标命中判断改成显式 tuple 比较，避免列表/数组类型差异带来的误判。

这些修改的直接作用是防止训练过程中 reward 链路错位，减少因为预处理异常造成的策略学习噪声。

## 3. 修改后的关键行为

修复后，训练链路中的规划与奖励行为变为：

1. 环境 reset 后，`env/SMAPO.py` 会先调用训练用 C++ planner。
2. planner 使用论文参数风格的 LB-A* 代价：
   - PlCC 负责已规划路径的时序拥堵惩罚
   - PeCC 负责局部感知拥堵的历史衰减累计
3. planner 生成路径后，预处理器把路径标记写入局部观测。
4. agent 每一步根据局部观测、路径标记、邻居信息和 RNN 历史状态做决策。
5. 若 agent 命中当前子目标，则按 `intrinsic_target_reward = 0.01` 给予内在奖励。

## 4. 验证结果

本次修改后已完成以下验证：

### 4.1 Python 语法验证

已通过：

```bash
python -m py_compile env/planning.py env/SMAPO.py
```

### 4.2 Docker 内 planner 编译验证

已通过：

```bash
python -c "import cppimport; cppimport.imp('planner.LB_A.planner')"
```

说明新的 pybind11 构造函数签名和 C++ 修改可正常编译。

### 4.3 Docker 内环境 reset / step 烟测

已通过：

- `env.reset()` 正常
- `env.step()` 正常
- 新 planner 参数已进入训练环境

### 4.4 极小规模训练验证

已验证训练可以推进到：

- APPO 初始化
- shared buffer 分配

当前 Docker 镜像中的最小训练在后续阶段中断，原因不是本次代码修改，而是镜像内缺少 `git` 命令，导致 Sample Factory 在执行 `save_git_diff(...)` 时失败。

这说明：

- 本次训练逻辑修复本身没有阻断训练主链路
- 若要让 Docker 中训练完整跑通，还需要补镜像依赖或跳过 git diff 保存步骤

## 5. 仍未补齐的论文项

本次修复主要解决了训练链路中最关键的 PP 参数偏差和奖励边界问题，但还有一项论文能力尚未补入：

### 5.1 DT（Dual Transformation）双重变换数据增强

论文中提到训练期间会利用旋转和镜像对称生成对偶样本，提高样本利用率和泛化能力。当前仓库中没有发现完整的 DT 训练增强实现，因此本次未纳入修复。

如果后续需要继续贴近论文复现，建议下一步优先补：

1. 地图与轨迹的旋转变换
2. 地图与轨迹的镜像变换
3. 动作标签同步映射
4. 对偶样本缓冲或在线增强逻辑

## 6. 本次修改涉及文件

- `env/planning.py`
- `env/SMAPO.py`
- `planner/LB_A/planner.h`
- `planner/LB_A/planner.cpp`

## 7. 结论

本次修复的核心意义是：

1. 让论文中的 LB-A* 关键参数真正进入训练使用的 C++ planner。
2. 将 PlCC 与 PeCC 的成本逻辑从“近似实现”修正为更接近论文描述的形式。
3. 修复预处理阶段可能污染 reward 信号的边界问题。
4. 将训练链路从“参数写在文档里但未真实生效”修正为“参数可以实际驱动训练行为”。

如果后续继续进行论文级复现，建议基于本次修复继续补齐 DT 数据增强和 Docker 训练环境中的 `git` 依赖问题。
