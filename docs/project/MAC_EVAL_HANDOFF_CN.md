# Mac 展示交接文档

## 目标

我已经在 Linux + NVIDIA GPU 环境中完成了该项目的训练，现在手里有训练产物（至少包含 `.pth`，最好还保留完整实验目录）。

我现在想在一台 macOS 设备上运行这个项目，对训练好的模型做：

1. 加载模型
2. 推理/评估
3. 可视化展示效果

设备信息：

- 芯片：Apple M4
- 系统：macOS
- 没有 CUDA / NVIDIA GPU

要求：

- 不要求在 Mac 上继续大规模训练
- 重点是“能运行模型并展示效果”
- 优先使用 CPU 路线；如果 MPS 可用且改动小，也可以使用，但不要把方案建立在 CUDA 之上

## 当前项目的重要背景

### 1. 训练环境与运行现状

- 项目已经在 Linux + NVIDIA 环境下完成训练
- `main.py` 可在 CPU 跑
- `main_gpu.py` 已补全并可在 Linux + NVIDIA 上训练
- 当前训练链路使用的是 Sample Factory / APPO 风格框架

### 2. 模型保存相关改动

项目代码已做过以下修改：

- 增加 checkpoint 保存
- 增加 milestone 保存
- 增加 best model 逻辑
- 现在采用：
  - 常规模型保留上限 `keep_checkpoints=5`
  - 最优模型保留上限 `keep_best_checkpoints=10`
  - 每 10 分钟保存一次 best snapshot

相关保存目录：

- 常规 checkpoint：
  - `results/train_dir/<run_id>/exp/checkpoint_p0/checkpoint_*.pth`
- 里程碑 checkpoint：
  - `results/train_dir/<run_id>/exp/checkpoint_p0/milestone_*.pth`
- 最优模型：
  - `results/train_dir/<run_id>/exp/checkpoint_p0/best/best_model_obj_*.pth`
- 最佳快照：
  - `results/train_dir/<run_id>/exp/checkpoint_p0/best/best_snapshot_*.pth`

### 3. 重要加载约束

这个项目不能只拿一个孤立的 `.pth` 就稳定运行。

通常还需要同一次训练的：

- `cfg.json`
- 对应实验目录结构
- 与训练时兼容的代码版本

也就是说，最稳妥的输入不是单独的 `.pth`，而是完整实验目录，例如：

`results/train_dir/0001/exp`

其中至少应包含：

- `cfg.json`
- `checkpoint_p0/...`

### 4. 已发现的现成评估入口

项目里已经有原生评估/展示相关入口：

- `sample_factory/algorithms/appo/enjoy_appo.py`
  - 可加载 checkpoint 目录并运行评估/渲染
- `learning/ppo.py`
  - 有 `PpoInference` 类，可基于训练目录做推理
- `test_code/formal_test_maze.py`
- `test_code/formal_test_random.py`
- `test_code/formal_test_street.py`
- `pogema/animation.py`
  - 支持动画输出

### 5. 当前已知问题和限制

- Mac M4 没有 CUDA，因此不能直接沿用 Linux 上的 `device=gpu` CUDA 路线
- 需要改成 CPU 推理优先
- 项目里的 planner / cppimport / C++ 模块是否能在 macOS 上顺利编译，需要实际检查
- 如果有 Linux/CUDA 专属依赖，需要最小化兼容修补

## 你现在需要做的事情

请在当前项目中完成以下工作：

1. 检查该项目在 macOS M4 上做“模型加载 + 推理 + 可视化展示”是否可行
2. 如果可行，直接补全一条完整链路：
   - 安装依赖
   - 编译必要模块
   - 加载训练好的模型
   - 在 Mac 上运行一次演示
3. 优先支持：
   - CPU 运行
   - 使用已有实验目录进行加载
4. 如果原生入口不能直接加载我手头的最佳模型文件：
   - 请补一个最小评估脚本
   - 支持直接指定：
     - `--cfg_dir`
     - `--checkpoint_path`
     - `--device=cpu`
     - `--render`
     - `--save_svg` 或其他可视化输出
5. 最终请给出：
   - Mac 上的运行步骤
   - 一条可直接执行的命令
   - 模型展示产物会输出到哪里
   - 如果不能运行，明确阻塞点是什么

## 我希望的最终交付

我希望最后能做到下面这种体验：

1. 在 Mac 上执行一条命令
2. 加载我在 Linux 上训练好的模型
3. 运行一个演示场景
4. 看到多智能体从起点移动到目标点的效果
5. 最好能导出动画、SVG、视频或一组截图

## 优先级

请按这个优先级处理：

1. 先打通“能加载并跑起来”
2. 再做“能展示”
3. 再做“展示效果更好看”

## 对 Codex 的明确要求

- 不要只给分析，直接动手改代码
- 优先复用项目现有评估入口
- 如果现有入口不够用，就新增一个最小脚本
- 修改后请实际验证
- 如果无法在当前机器完整验证，请明确说明卡在哪里

## 可直接发送给 Codex 的提示词

你现在在这个项目目录中工作。请帮我把“Linux + NVIDIA GPU 上训练好的模型”迁移到“Mac M4 上做推理和展示”这条链路补全并验证。

背景如下：

- 该项目已经能在 Linux + NVIDIA 环境训练
- 我现在手里有训练产物，至少有 `.pth`，最好还有完整实验目录
- 项目当前模型通常需要配套 `cfg.json` 和实验目录结构一起加载
- 当前项目里已有这些入口：
  - `sample_factory/algorithms/appo/enjoy_appo.py`
  - `learning/ppo.py`
  - `test_code/formal_test_maze.py`
  - `pogema/animation.py`
- Mac 机器没有 CUDA，因此不要走 CUDA 路线，优先 CPU

你的任务：

1. 检查当前项目在 macOS M4 上是否能完成模型加载、推理和展示
2. 若可行，直接补全所需代码与运行方式
3. 优先复用现有评估入口；若不够，则新增最小脚本
4. 最好支持直接指定：
   - `--cfg_dir`
   - `--checkpoint_path`
   - `--device=cpu`
   - `--render`
   - `--save_svg` 或可视化输出
5. 帮我给出最终在 Mac 上的一键运行命令
6. 如果需要，把最佳模型文件转换/复制到可被现有评估逻辑加载的目录结构
7. 实际验证能否运行；若不能，请定位具体阻塞点（依赖、编译、平台兼容、路径问题等）

要求：

- 直接改代码，不要只停留在建议
- 尽量少改动，优先最小修补
- 最终回答请给我：
  - 改了哪些文件
  - 如何运行
  - 展示产物输出在哪里
  - 是否已实际验证成功

