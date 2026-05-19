# 轻量 RePlan gamma 同步修复说明（2026-03-01）

本文档记录 2026 年 3 月 1 日对轻量 Python replanner 链路的参数同步修复。

## 1. 问题背景

仓库中存在两条与规划相关的代码路径：

- 主训练/主评估链路：`env/planning.py` -> `planner/LB_A/planner`
- 轻量 Python replanner 链路：`env/replan.py` -> `planning/replan_algo.py`

此前主链路已经支持论文式的 PlCC / PeCC 参数入口，但轻量链路仍有两个偏差：

1. `env/replan.py` 没有把论文参数透传给 `RePlanBase`
2. `planning/replan_algo.py` 的 `gamma` 仍保留旧默认值 `0.8`

这会导致轻量 replanner 在未显式指定参数时，继续使用旧近似实现，而不是与论文口径保持一致。

## 2. 本次修改

### 2.1 `env/replan.py`

新增并透传以下参数：

- `plcc_alpha`
- `plcc_beta`
- `plcc_lambda`
- `plcc_delta_t`
- `pecc_gamma`
- `map_width`
- `map_height`

同时新增了：

- `_resolve_map_width()`
- `_resolve_map_height()`
- `_resolve_pecc_gamma()`

解析优先级如下：

1. 优先使用显式传入的 `pecc_gamma`
2. 否则使用配置或挂载环境中的地图宽高，按 `0.5 / (map_w + map_h)` 计算
3. 若仍拿不到，再由 `RePlanBase` 在首次 `act()` 时用观测窗口做兜底估计

### 2.2 `planning/replan_algo.py`

修改点：

- 将构造默认 `gamma=0.8` 改为 `gamma=None`
- 新增 `map_width` / `map_height`
- 在首次 `act()` 时调用 `_ensure_gamma(...)`
- 当外部没有提供完整地图尺寸时，使用观测窗口尺寸做最后兜底，避免继续硬编码 `0.8`

## 3. 结果

修复后，轻量 replanner 链路与主 planner 链路在参数设计上已经基本统一：

- PlCC：`alpha=2.0`、`beta=0.5`、`lambda=0.8`
- PeCC：优先使用论文式 `gamma = 0.5 / (map_w + map_h)`

## 4. 仍需注意的点

轻量 replanner 不是当前训练主链路，它更多用于轻量推理/旧接口兼容，因此仍有一个现实限制：

- 如果这条链路在运行时拿不到完整地图尺寸，就只能用观测窗口大小估计 `gamma`

这比固定 `0.8` 更接近论文逻辑，但仍不如显式提供全图尺寸精确。

## 5. 本次结论

这次修复的核心目的不是重写轻量 replanner，而是消除一个容易混淆的历史残留默认值：

- 旧行为：默认 `gamma = 0.8`
- 新行为：优先使用论文式解析；只有缺乏全图信息时才做合理兜底
