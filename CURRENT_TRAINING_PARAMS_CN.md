# 当前训练参数说明（运行中配置）

## 1. 当前实际运行命令

```bash
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:False python main_gpu.py \
  --train_for_seconds=36000 \
  --num_workers=4 \
  --num_envs_per_worker=2 \
  --worker_num_splits=1 \
  --target_num_agents=256 \
  --num_agents=128 \
  --batch_size=1024 \
  --rollout=8 \
  --recurrence=8 \
  --use_wandb=False
```

## 2. 参数逐项解释

- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:False`  
  关闭 PyTorch 的 `expandable_segments` 分配模式，避免多进程训练中 CUDA tensor 共享报错。

- `train_for_seconds=36000`  
  训练最长运行 36000 秒（10 小时）。这是“时间上限”，不代表一定跑满，达到其他停止条件也会提前结束。

- `num_workers=4`  
  采样 worker 进程数量。越大通常采样更快，但 CPU 压力和进程通信开销也更高。

- `num_envs_per_worker=2`  
  每个 worker 同时运行的环境数。总并行环境数约为 `num_workers * num_envs_per_worker`。

- `worker_num_splits=1`  
  worker 内部采样分片数。`1` 表示不做双缓冲分片，结构更简单。

- `target_num_agents=256`  
  目标并行智能体规模。环境构建与采样会围绕该规模组织。

- `num_agents=128`  
  单环境智能体数量。需要满足 `target_num_agents % num_agents == 0`。

- `batch_size=1024`  
  learner 每次优化的 mini-batch 大小。增大通常更稳但更吃显存/算力。

- `rollout=8`  
  每条轨迹切片长度（时间步）。影响采样与训练的节奏。

- `recurrence=8`  
  RNN 的反向传播时间长度（BPTT 长度）。通常和 `rollout` 设置一致。

- `use_wandb=False`  
  本次不上传 wandb 在线日志。

## 3. 哪些参数主要影响训练效率

- `num_workers`
- `num_envs_per_worker`
- `worker_num_splits`
- `batch_size`
- `rollout`
- `recurrence`
- `target_num_agents`
- `num_agents`

## 4. 哪些参数主要影响最终训练结果

- `train_for_seconds`（或总训练步数）
- `batch_size`
- `rollout`
- `recurrence`
- `target_num_agents`
- `num_agents`

## 5. 同时影响效率和效果的关键参数

- `batch_size`
- `rollout`
- `recurrence`
- `num_workers`
- `num_envs_per_worker`

