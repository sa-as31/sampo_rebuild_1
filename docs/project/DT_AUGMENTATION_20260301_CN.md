# DT 数据增强接入说明（2026-03-01）

本文档记录 2026 年 3 月 1 日为训练链路补入 Dual Transformation（DT）数据增强的实现与验证结果。

## 1. 修改目标

根据论文描述，SMAPO 在训练阶段会利用 LMAPF 任务的对称性与旋转不变性，对轨迹样本进行在线增强，以提高样本利用率和训练稳定性。

本次修改的目标是：

1. 将 DT 真正接入当前训练主链路。
2. 保持现有环境采样逻辑不变，避免对环境本体和共享缓存结构做大改动。
3. 让增强后的样本同时满足：
   - 观测一致变换
   - 动作标签一致变换
   - 旧策略 logits 一致变换
   - 价值目标与优势值保持不变

## 2. 接入位置

本次 DT 没有放在环境采样端，而是放在 learner 的 minibatch 训练阶段。

修改文件：

- `sample_factory/algorithms/appo/learner.py`
- `learning/learning_config.py`

选择这个接入点的原因：

1. 论文强调的是“在线训练期间增强轨迹样本”，放在 learner 侧最直接。
2. 不需要改 actor 采样进程、shared buffer 格式或环境 reset/step 逻辑。
3. 可以直接在 PPO/IPPO 损失计算前，对整批轨迹样本做对偶变换。

## 3. 本次实现方式

### 3.1 新增 DT 训练配置

在 `learning/learning_config.py` 中新增：

- `dt_enabled: bool = True`
- `dt_include_reflections: bool = True`
- `dt_num_transforms_per_batch: int = 8`

含义如下：

- `dt_enabled`
  是否启用 DT。

- `dt_include_reflections`
  是否将镜像变换加入 DT 集合。

- `dt_num_transforms_per_batch`
  每个 minibatch 实际扩增出的变换数量，默认值为 8。

### 3.2 采用的变换集合

当前实现构造了一个 D4 风格的变换池：

1. 旋转：
   - `rot0`
   - `rot90`
   - `rot180`
   - `rot270`

2. 镜像 + 旋转：
   - `flip_lr_rot0`
   - `flip_lr_rot90`
   - `flip_lr_rot180`
   - `flip_lr_rot270`

当 `dt_include_reflections=True` 时，完整变换池大小为 8。

### 3.3 默认训练策略

为进一步贴近论文当前描述，本仓库现已默认启用完整 D4 变换集合：

- 每个 minibatch 至少保留原始样本
- 并使用其余全部对偶变换
- 默认总数为 8 个变换

也就是说，默认情况下每个 minibatch 会扩成约 8 倍。

如果后续为了节省显存或加快实验，可以手动把 `dt_num_transforms_per_batch` 调回更小的值，但那将不再是当前默认的论文贴近配置。

## 4. 具体增强内容

### 4.1 对观测的变换

对于 `obs['obs']` 这种局部栅格观测：

- 使用 `torch.rot90(...)`
- 使用 `torch.flip(...)`

对于坐标类特征：

- `xy`
- `target_xy`
- `relative_xy`

会同步执行相同几何变换，确保空间语义保持一致。

对于以下字段：

- `attention_mask`
- `ids_oth`
- `id_`

不改变其值，仅按批次复制。

### 4.2 对动作标签的变换

离散动作定义仍然是：

- `0`: stay
- `1`: up
- `2`: down
- `3`: left
- `4`: right

在 DT 中，动作会根据对应几何变换自动重映射。例如：

- `rot90` 下，`up -> left`
- `rot180` 下，`left -> right`
- `flip_lr` 下，`left <-> right`

这样可以保证：

- 变换后的观测
- 变换后的动作

仍然表示同一个策略语义。

### 4.3 对旧策略 logits 的变换

PPO 的重要比例项依赖旧策略分布，因此不能只变换动作标签。

本次实现里，`action_logits` 也会按相同动作置换顺序重排，使得：

- 旧策略 logits
- 新动作标签

在变换后仍然保持一致。

### 4.4 对 value / advantage / return 的处理

以下量不会因为几何对偶变换而改变数值：

- `advantages`
- `returns`
- `values`
- `log_prob_actions`
- `rewards`
- `dones`
- `rnn_states`

这些字段在 DT 扩增时只是按批次复制。

其中 `log_prob_actions` 可以直接复制，是因为在纯动作置换下，对应动作的旧策略 log-prob 数值保持不变。

## 5. 对旧半成品 DT 代码的处理

在原有 `learner.py` 中，已经存在一些未接通的旋转增强残留代码，例如：

- `rot_actions_1`
- `rot_actions_2`
- `rot_actions_3`
- `_extend_obs`
- `_extend_mbs`

这些代码存在两个问题：

1. 它们没有真正接入 `_train(...)` 主循环。
2. 只处理了旋转动作映射，没有把完整观测、坐标特征和 logits 一起变换。

本次修改已经：

- 删除这些残留路径上的依赖
- 改成统一的 `minibatch -> 变换 -> 拼接` 逻辑

## 6. 验证结果

### 6.1 Python 语法验证

已通过：

```bash
python -m py_compile learning/learning_config.py sample_factory/algorithms/appo/learner.py
```

### 6.2 Docker 内 DT 形状与动作映射测试

已在 Docker 中使用伪造 minibatch 做了专项测试，验证内容包括：

1. DT 能正常扩增 batch
2. `obs.obs` 的形状扩增正确
3. `actions` 能按变换规则重映射
4. `action_logits` 形状与重排逻辑正常
5. `xy`、`relative_xy` 等坐标特征会同步变换
6. `attention_mask` 等非几何字段按批次复制

测试结果摘要：

- 早期专项 batch 变换测试：
  - `num_specs = 4`
  - `obs_shape = (8, 2, 3, 3)`
  - `logits_shape = (8, 5)`
  - 动作标签已按几何变换发生对应重映射

- 默认配置回归测试（2026-03-01 补充）：
  - DT 变换池大小 `pool = 8`
  - 默认实际选中数量 `selected = 8`
  - 默认会使用完整 D4 集合：
    - `rot0`
    - `rot90`
    - `rot180`
    - `rot270`
    - `flip_lr_rot0`
    - `flip_lr_rot90`
    - `flip_lr_rot180`
    - `flip_lr_rot270`

## 7. 当前实现与论文的关系

这次实现已经满足论文 DT 的核心精神：

1. 在线训练期间对轨迹样本进行几何对偶增强
2. 同时处理观测与动作标签的一致性
3. 提高单批样本的信息利用率

2026 年 3 月 1 日补充调整：

- 为了更贴近论文式全变换训练，默认 `dt_num_transforms_per_batch` 已从 `4` 调整为 `8`
- 因此当前默认会使用完整 D4 变换集合，而不是随机子集

但仍有一个现实取舍：

- 为了控制训练开销，默认不是每个 minibatch 使用全部 8 个变换，而是默认使用 4 个

如果后续要进一步逼近论文表达式中的全变换平均形式，建议直接把：

```text
dt_num_transforms_per_batch = 8
```

## 8. 本次修改涉及文件

- `learning/learning_config.py`
- `sample_factory/algorithms/appo/learner.py`

## 9. 结论

本次修改后，当前项目已经不再只是“文档中提到 DT”，而是把 DT 真实接入到了训练 minibatch 的优化流程中。

当前 DT 具备以下特点：

1. 与现有训练主链路兼容
2. 不破坏环境采样和共享缓存设计
3. 支持旋转与镜像增强
4. 支持控制每批实际使用的变换数量

如果后续继续加强论文复现，可以在此基础上继续做两件事：

1. 将 `dt_num_transforms_per_batch` 提升到 `8`
2. 进一步评估 DT 对吞吐量和收敛曲线的真实增益
