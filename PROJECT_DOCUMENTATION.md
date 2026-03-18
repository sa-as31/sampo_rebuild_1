# SMAPO 项目详细文档

## 目录
1. [项目概述](#1-项目概述)
2. [核心架构](#2-核心架构)
3. [环境模块详解](#3-环境模块详解)
4. [规划器模块详解](#4-规划器模块详解)
5. [学习模块详解](#5-学习模块详解)
6. [神经网络架构](#6-神经网络架构)
7. [训练流程](#7-训练流程)
8. [配置参数详解](#8-配置参数详解)
9. [使用指南](#9-使用指南)

---

## 1. 项目概述

### 1.1 项目简介

**SMAPO (Synergistic Multi-Agent Pathfinding Optimization)** 是一个用于**多智能体路径规划 (MAPF, Multi-Agent Path Finding)** 的深度强化学习框架。该项目创新性地将**传统A\*规划算法**与**深度强化学习 (PPO)** 相结合，通过规划器提供的路径引导和内在奖励机制，使智能体学会在复杂环境中协同导航。

### 1.2 核心创新点

| 特性 | 说明 |
|------|------|
| **混合架构** | 结合传统规划算法（A*）与深度强化学习 |
| **子目标引导** | 规划器生成路径上的子目标点，引导智能体行为 |
| **内在奖励** | 智能体到达子目标时获得内在奖励信号 |
| **注意力机制** | 智能体之间通过注意力机制进行信息交互 |
| **高效规划器** | C++ 实现的高性能 A* 规划器 |
| **可扩展性** | 支持 64-512 个智能体的协同规划 |

### 1.3 项目结构

```
SMAPO/
├── env/                        # 环境模块
│   ├── SMAPO.py               # 核心包装器（观察预处理、奖励塑形）
│   ├── planning.py            # 规划器接口
│   ├── create_env.py          # 环境创建工厂
│   ├── wrappers.py            # 附加包装器
│   ├── custom_maps.py         # 自定义地图
│   └── replan.py              # 重规划配置
│
├── learning/                   # 学习模块
│   ├── learning_config.py     # 配置类定义
│   ├── ppo.py                 # PPO 推理类
│   ├── encoder_residual.py    # ResNet 编码器
│   └── utils_common.py        # 工具函数
│
├── planner/                    # C++ 规划器
│   ├── LB_A/                  # 低延迟 A* 规划器
│   │   ├── planner.cpp
│   │   ├── planner.h
│   │   └── planner.cpython-*.so
│   └── Static_A/              # 静态 A* 规划器
│
├── pogema/                     # 多智能体网格环境
│   ├── grid.py                # 网格环境核心
│   ├── grid_config.py         # 环境配置
│   ├── generator.py           # 随机生成器
│   ├── envs.py                # 环境定义
│   └── integrations/          # 框架集成
│
├── sample_factory/             # 异步 PPO 训练框架
│   ├── algorithms/
│   │   └── appo/              # APPO 实现
│   └── envs/                  # 环境接口
│
├── utils/                      # 工具模块
│   ├── training_tools.py      # 训练工具
│   └── files.py               # 文件操作
│
├── main.py                     # 主入口
└── training_run.py            # 训练运行脚本
```

---

## 2. 核心架构

### 2.1 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         SMAPO 整体架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   环境       │    │   规划器     │    │   学习器     │      │
│  │  (Pogema)   │───▶│   (A* C++)  │───▶│    (PPO)     │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                    │               │
│         ▼                   ▼                    ▼               │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                    SMAPOWrapper                       │      │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │      │
│  │  │ 观察预处理   │  │ 路径注入    │  │ 内在奖励    │  │      │
│  │  │ (BFS邻居)   │  │ (子目标)    │  │ (奖励塑形)  │  │      │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  │      │
│  └──────────────────────────────────────────────────────┘      │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────────────────────────────────────────────┐      │
│  │                 神经网络模型                          │      │
│  │  ┌───────────┐  ┌───────────┐  ┌───────────────┐   │      │
│  │  │ ResNet    │──▶│ Attention │──▶│ Actor-Critic │   │      │
│  │  │ Encoder   │  │  Module   │  │    Head       │   │      │
│  │  └───────────┘  └───────────┘  └───────────────┘   │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 数据流程

```
原始观察 (障碍物、智能体位置、目标位置)
         │
         ▼
┌─────────────────────────────────────┐
│          SMAPOWrapper               │
│  1. 更新规划器状态                   │
│  2. 获取每智能体规划路径             │
│  3. 将路径信息编码到观察空间         │
│  4. 计算 BFS 邻居信息                │
│  5. 生成内在奖励                    │
└─────────────────────────────────────┘
         │
         ▼
处理后的观察
┌─────────────────────────────────────┐
│  - obs: 障碍物 + 智能体 + 路径信息  │
│  - ids_oth: 邻居智能体 ID           │
│  - relative_xy: 邻居相对位置        │
│  - attention_mask: 注意力掩码       │
│  - id_: 当前智能体 ID               │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         神经网络前向传播             │
│  Encoder → Attention → GRU → Head  │
└─────────────────────────────────────┘
         │
         ▼
动作输出 + 价值估计
```

---

## 3. 环境模块详解

### 3.1 核心网格环境 (pogema/grid.py)

`Grid` 类是多智能体网格环境的核心实现：

```python
class Grid:
    def __init__(self, grid_config: GridConfig, add_artificial_border: bool = True, num_retries=10):
        self.config = grid_config
        self.conflict = 0  # 冲突计数器
        self.rnd = np.random.default_rng(grid_config.seed)

        # 生成障碍物
        if self.config.map is None:
            obstacles = generate_obstacles(self.config)
        else:
            obstacles = np.array([np.array(line) for line in self.config.map])

        # 生成智能体起点和终点
        starts_xy, finishes_xy = generate_positions_and_targets_fast(obstacles, self.config)

        # 添加人工边界（用于观察半径）
        if add_artificial_border:
            r = self.config.obs_radius
            filled_obstacles = np.zeros(np.array(obstacles.shape) + r * 2)
            # ... 边界处理

        self.obstacles = obstacles
        self.positions = filled_positions
        self.finishes_xy = finishes_xy
        self.positions_xy = starts_xy
```

**关键方法：**

```python
def move(self, agent_id, action):
    """执行智能体移动，处理碰撞"""
    x, y = self.positions_xy[agent_id]
    self.positions[x, y] = self.config.FREE

    dx, dy = self.config.MOVES[action]  # 移动方向

    # 检查是否可以移动（无障碍物且无其他智能体）
    if self.obstacles[x + dx, y + dy] == self.config.FREE and \
       self.positions[x + dx, y + dy] == self.config.FREE:
        x += dx
        y += dy
    else:
        self.conflict += 1  # 记录冲突

    self.positions_xy[agent_id] = (x, y)
    self.positions[x, y] = self.config.OBSTACLE

def get_obstacles_for_agent(self, agent_id):
    """获取智能体局部观察范围内的障碍物"""
    x, y = self.positions_xy[agent_id]
    r = self.config.obs_radius
    return self.obstacles[x - r:x + r + 1, y - r:y + r + 1].astype(np.float32)
```

### 3.2 环境配置 (pogema/grid_config.py)

配置类定义了环境的所有参数：

```python
class GridConfig(BaseModel):
    FREE: Literal[0] = 0                    # 空格标记
    OBSTACLE: Literal[1] = 1                # 障碍物标记
    MOVES: list = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1]]  # 5个动作

    on_target: Literal['finish', 'nothing', 'restart'] = 'finish'  # 到达目标行为
    seed: Optional[int] = None              # 随机种子
    size: int = 8                           # 网格大小
    density: float = 0.3                    # 障碍物密度
    num_agents: int = 1                     # 智能体数量
    obs_radius: int = 5                     # 观察半径
    collision_system: Literal['block_both', 'priority'] = 'priority'
    observation_type: Literal['POMAPF', 'MAPF', 'default'] = 'default'
    max_episode_steps: int = 64             # 最大步数
```

### 3.3 SMAPO 核心包装器 (env/SMAPO.py)

这是项目的核心组件，实现了观察预处理和奖励塑形：

```python
class SMAPOWrapper(ObservationWrapper):
    def __init__(self, env, config: PreprocessorConfig):
        super().__init__(env)
        self._cfg: PreprocessorConfig = config
        self.re_plan = ResettablePlanner(self._cfg)  # 初始化规划器
        self.prev_goals = None
        self.intrinsic_reward = None

    def observation(self, observations):
        """观察预处理核心方法"""

        # 1. 更新规划器状态
        self.re_plan.update(observations)

        # 2. 获取每智能体的规划路径
        paths = self.re_plan.get_path()

        new_goals = []
        intrinsic_rewards = []
        pos_xy = self.grid.positions_xy
        obstacle = self.grid.obstacles

        # 3. 使用 BFS 获取邻居信息
        ids_oth, relative_xy = self.bfs_obs(pos_xy, obstacle)

        # 4. 处理每智能体的观察
        for k, path in enumerate(paths):
            obs = observations[k]

            if path is None:
                # 无路径，使用原始目标
                new_goals.append(obs['target_xy'])
                path = []
            else:
                # 检查是否到达上一子目标
                subgoal_achieved = self.prev_goals and obs['xy'] == self.prev_goals[k]
                # 计算内在奖励
                intrinsic_rewards.append(
                    self._cfg.intrinsic_target_reward if subgoal_achieved else 0.0
                )
                new_goals.append(path[1])  # 设置下一个子目标

            # 将路径信息编码到障碍物观察中
            obs['obstacles'][obs['obstacles'] > 0] *= -1
            r = obs['obstacles'].shape[0] // 2
            for idx, (gx, gy) in enumerate(path):
                x, y = self.get_relative_xy(*obs['xy'], gx, gy, r)
                if x is not None and y is not None:
                    obs['obstacles'][x, y] = 1.0
                else:
                    break

        # 5. 添加注意力机制所需的信息
        for k, _ in enumerate(paths):
            ids_oth_k = np.array(self.Padding(ids_oth[k], 64)).astype(int)
            relative_xy_k = np.array(self.Padding_shape(relative_xy[k], (64, 2))).astype(int)
            observations[k]['ids_oth'] = ids_oth_k
            observations[k]['relative_xy'] = relative_xy_k
            observations[k]['attention_mask'] = self.create_mask(...)
            observations[k]['id_'] = k

        self.prev_goals = new_goals
        self.intrinsic_reward = intrinsic_rewards
        return observations
```

**BFS 邻居观察：**

```python
def bfs_obs(self, id_pos, obstacle, d=5):
    """使用 BFS 找到指定距离内的邻居智能体"""
    num_agents = len(id_pos)
    dx = [0, 1, -1, 0]
    dy = [1, 0, 0, -1]

    pos_id = dict()  # 位置到ID的映射
    ids_oth = dict()  # 每智能体的邻居ID
    relative_xy = dict()  # 邻居的相对位置

    for i, pos in enumerate(id_pos):
        pos_id[pos] = i

    for i in range(num_agents):
        pos = id_pos[i]
        posed = {pos}
        q = queue.Queue()
        q.put(pos)

        while not q.empty():
            x, y = q.get()
            for k in range(4):
                nx_x, nx_y = x + dx[k], y + dy[k]
                tp_nx = (nx_x, nx_y)
                man_d = self.manhattan_distance(nx_x, nx_y, pos[0], pos[1])

                if man_d > d or tp_nx in posed or obstacle[tp_nx] == 1:
                    continue

                posed.add(tp_nx)
                q.put(tp_nx)

                if tp_nx in pos_id.keys():
                    ids_oth[i].append(pos_id[tp_nx] - i)
                    relative_xy[i].append((nx_x - pos[0], nx_y - pos[1]))

    return ids_oth, relative_xy
```

### 3.4 内在奖励机制

```python
def get_intrinsic_rewards(self, reward):
    """计算内在奖励"""
    for agent_idx, r in enumerate(reward):
        if self._cfg.add_r == True:
            reward[agent_idx] += self.intrinsic_reward[agent_idx]
        else:
            reward[agent_idx] = self.intrinsic_reward[agent_idx]
    return reward

def step(self, action):
    observation, reward, done, info = self.env.step(action)
    return self.observation(observation), self.get_intrinsic_rewards(reward), done, info
```

---

## 4. 规划器模块详解

### 4.1 规划器接口 (env/planning.py)

Python 接口层封装 C++ 规划器：

```python
class Planner:
    def __init__(self, cfg: PlannerConfig):
        self.planner = None
        self.obstacles = None
        self.starts = None
        self.cfg = cfg

    def add_grid_obstacles(self, obstacles, starts):
        """添加全局障碍物和起始位置"""
        self.obstacles = obstacles
        self.starts = starts
        self.planner = None

    def update(self, obs):
        """更新规划器状态"""
        num_agents = len(obs)
        obs_radius = len(obs[0]['obstacles']) // 2

        if self.planner is None:
            # 为每个智能体创建规划器实例
            self.planner = [
                planner(self.obstacles,
                       self.cfg.use_static_cost,
                       self.cfg.use_dynamic_cost,
                       self.cfg.reset_dynamic_cost)
                for _ in range(num_agents)
            ]
            for i, p in enumerate(self.planner):
                p.set_abs_start(self.starts[i])

            if self.cfg.use_static_cost:
                # 预计算静态惩罚矩阵
                pen_calc = planner(...)
                penalties = pen_calc.precompute_penalty_matrix(obs_radius)
                for p in self.planner:
                    p.set_penalties(penalties)

        # 更新每智能体的观察和路径
        hash_map = dict()
        for k in range(num_agents):
            if obs[k]['xy'] == obs[k]['target_xy']:
                continue
            obs[k]['agents'][obs_radius][obs_radius] = 0
            self.planner[k].update_occupations(obs[k]['agents'],
                                               (obs[k]['xy'][0] - obs_radius,
                                                obs[k]['xy'][1] - obs_radius),
                                               obs[k]['target_xy'])
            obs[k]['agents'][obs_radius][obs_radius] = 1
            self.planner[k].update_path(obs[k]['xy'], obs[k]['target_xy'], hash_map)
            self.planner[k].update_cur_map(hash_map)
```

### 4.2 C++ A* 规划器实现 (planner/LB_A/planner.h)

高性能 A* 规划器的核心数据结构：

```cpp
// 带时间维度的状态节点
struct Node {
    Node(int _i = INF, int _j = INF, int _t = INF, float _g = INF, float _h = 0)
        : i(_i), j(_j), t(_t), g(_g), h(_h), f(_g+_h) {}
    int i;        // x 坐标
    int j;        // y 坐标
    int t;        // 时间步
    float g;      // 实际代价
    float h;      // 启发式估计
    float f;      // 总代价 f = g + h
    std::pair<int, int> parent;  // 父节点
};

class planner {
    std::pair<int, int> start;
    std::pair<int, int> goal;
    std::priority_queue<Node, std::vector<Node>, std::greater<Node>> OPEN;
    std::vector<std::vector<int>> grid;
    std::vector<std::vector<float>> num_occupations;  // 动态占用计数
    std::vector<std::vector<float>> penalties;        // 静态惩罚矩阵
    std::vector<std::vector<float>> h_values;         // 启发式值
    std::vector<std::vector<Node>> nodes;             // 节点存储

    bool use_static_cost;   // 是否使用静态代价
    bool use_dynamic_cost;  // 是否使用动态代价
    bool reset_dynamic_cost;
    double gamma;           // 时间惩罚衰减因子
};
```

**核心搜索算法：**

```cpp
void compute_shortest_path(py::dict& cur_map) {
    Node current;
    while(!OPEN.empty() && !(current == goal)) {
        current = OPEN.top();
        OPEN.pop();

        if(nodes[current.i][current.j].g < current.g)
            continue;

        for(auto n: get_neighbors({current.i, current.j})) {
            float cost(1);
            std::tuple<int,int,int> tep_cur{n.first, n.second, current.t + 1};

            // 计算时间相关的冲突惩罚
            cost += calc_penalties(cur_map, tep_cur);

            // 动态代价：考虑其他智能体占用
            if(use_dynamic_cost)
                cost += num_occupations[n.first][n.second];

            // 静态代价：预计算的位置惩罚
            if(nodes[n.first][n.second].g > current.g + cost) {
                OPEN.push(Node(n.first, n.second, current.t + 1,
                              current.g + cost, h(n)));
                nodes[n.first][n.second].g = current.g + cost;
                nodes[n.first][n.second].parent = {current.i, current.j};
                nodes[n.first][n.second].t = current.t + 1;
            }
        }
    }
}
```

**静态惩罚预计算：**

```cpp
std::vector<std::vector<float>> precompute_penalty_matrix(int obs_radius) {
    penalties = std::vector<std::vector<float>>(
        grid.size(), std::vector<float>(grid.front().size(), 0));

    float max_avg_dist(0);

    // 计算每个位置的平均到达距离
    for(size_t i = obs_radius; i < grid.size() - obs_radius; i++)
        for(size_t j = obs_radius; j < grid.front().size() - obs_radius; j++)
            if(grid[i][j] == 0) {
                penalties[i][j] = get_avg_distance(i, j);
                max_avg_dist = std::fmax(max_avg_dist, penalties[i][j]);
            }

    // 归一化惩罚值
    for(size_t i = obs_radius; i < grid.size() - obs_radius; i++)
        for(size_t j = obs_radius; j < grid.front().size() - obs_radius; j++)
            if(grid[i][j] == 0)
                penalties[i][j] = max_avg_dist / penalties[i][j];

    return penalties;
}
```

---

## 5. 学习模块详解

### 5.1 配置类 (learning/learning_config.py)

完整的实验配置定义：

```python
class AsyncPPO(BaseModel, extra=Extra.forbid):
    """PPO 超参数配置"""
    experiment_summaries_interval: int = 20
    adam_eps: float = 1e-6
    adam_beta1: float = 0.9
    adam_beta2: float = 0.999
    gae_lambda: float = 0.95        # GAE lambda 参数
    rollout: int = 8                 # rollout 长度
    num_workers: int = 5            # 工作进程数
    recurrence: int = 8              # RNN 展开步数
    use_rnn: bool = True            # 是否使用 RNN
    rnn_type: str = 'gru'           # RNN 类型
    rnn_num_layers: int = 1
    ppo_clip_ratio: float = 0.2     # PPO clip 参数
    ppo_clip_value: float = 1.0
    batch_size: int = 2048
    ppo_epochs: int = 1

    exploration_loss_coeff: float = 0.023  # 熵正则化系数
    atten_hidden_size: int = 256          # 注意力隐藏层大小
    value_loss_coeff: float = 0.5         # 价值损失系数


class ExperimentSettings(BaseModel, extra=Extra.forbid):
    """实验设置"""
    learning_rate: float = 0.000146
    train_for_env_steps: int = 60000000  # 训练步数
    gamma: float = 0.9756                # 折扣因子
    reward_scale: float = 1.0
    reward_clip: float = 10.0

    # 网络架构
    encoder_type: str = 'resnet'
    encoder_custom: str = 'pogema_residual'
    encoder_subtype: str = 'resnet_impala'
    encoder_extra_fc_layers: int = 1
    num_filters: int = 64        # 卷积核数量
    num_res_blocks: int = 8      # ResNet 块数量
    hidden_size: int = 512       # 隐藏层大小


class Experiment(BaseModel):
    """完整实验配置"""
    environment: Union[Environment, EnvironmentMazes] = EnvironmentMazes()
    async_ppo: AsyncPPO = AsyncPPO()
    experiment_settings: ExperimentSettings = ExperimentSettings()
    global_settings: GlobalSettings = GlobalSettings()
    evaluation: Evaluation = Evaluation()
```

### 5.2 PPO 推理类 (learning/ppo.py)

用于加载训练好的模型进行推理：

```python
class PpoInference:
    def __init__(self, algo_cfg):
        self.algo_cfg: PpoConfig = algo_cfg

        path = algo_cfg.path_to_weights
        device = algo_cfg.device

        # 注册自定义组件
        register_custom_components()
        register_custom_encoder('pogema_residual', ResnetEncoder)

        # 加载配置
        config_path = join(path, 'cfg.json')
        with open(config_path, "r") as f:
            config = json.load(f)
        self.exp, flat_config = validate_config(config['full_config'])

        # 创建环境和模型
        env = create_env(algo_cfg.env, cfg=algo_cfg, env_config={})
        actor_critic = create_actor_critic(algo_cfg, env.observation_space, env.action_space)
        env.close()

        # 加载权重
        if device == 'cpu' or not torch.cuda.is_available():
            device = torch.device('cpu')
        else:
            device = torch.device('cuda')
        self.device = device

        actor_critic.model_to_device(device)
        checkpoints = join(path, f'checkpoint_p{algo_cfg.policy_index}')
        checkpoints = LearnerWorker.get_checkpoints(checkpoints)
        checkpoint_dict = LearnerWorker.load_checkpoint(checkpoints, device)
        actor_critic.load_state_dict(checkpoint_dict['model'])

        self.ppo = actor_critic
        self.rnn_states = None

    def act(self, observations):
        """根据观察选择动作"""
        if self.rnn_states is None:
            self.rnn_states = torch.zeros(
                [len(observations), get_hidden_size(self.cfg)],
                dtype=torch.float32, device=self.device
            )

        with torch.no_grad():
            obs_torch = AttrDict(transform_dict_observations(observations))
            for key, x in obs_torch.items():
                obs_torch[key] = torch.from_numpy(x).to(self.device).float()

            policy_outputs = self.ppo(obs_torch, self.rnn_states,
                                      with_action_distribution=True)
            self.rnn_states = policy_outputs.rnn_states
            actions = policy_outputs.actions

        return actions.cpu().numpy()
```

---

## 6. 神经网络架构

### 6.1 ResNet 编码器 (learning/encoder_residual.py)

```python
class ResnetEncoder(EncoderBase):
    def __init__(self, cfg, obs_space, timing):
        super().__init__(cfg, timing)

        obs_shape = get_obs_shape(obs_space)
        input_ch = obs_shape.obs[0]  # 输入通道数

        # ResNet 配置
        resnet_conf = [[cfg.num_filters, cfg.num_res_blocks]]
        curr_input_channels = input_ch
        layers = []

        for out_channels, res_blocks in resnet_conf:
            # 初始卷积层
            layers.extend([
                nn.Conv2d(curr_input_channels, out_channels,
                         kernel_size=3, stride=1, padding=1)
            ])
            # 残差块
            layers.extend([
                ResBlock(cfg, out_channels, out_channels)
                for _ in range(res_blocks)
            ])
            curr_input_channels = out_channels

        layers.append(activation_func(cfg))
        self.conv_head = nn.Sequential(*layers)

        # 计算卷积输出大小
        self.conv_head_out_size = calc_num_elements(
            self.conv_head, obs_space['obs'].shape
        )
        self.encoder_out_size = self.conv_head_out_size

        # 额外的全连接层
        if cfg.encoder_extra_fc_layers:
            self.extra_linear = nn.Sequential(
                nn.Linear(self.encoder_out_size, cfg.hidden_size),
                activation_func(cfg),
            )
            self.encoder_out_size = cfg.hidden_size

        # 坐标编码 MLP
        self.coordinates_mlp = nn.Sequential(
            nn.Linear(4, cfg.hidden_size),
            nn.ReLU(),
            nn.Linear(cfg.hidden_size, cfg.hidden_size),
            nn.ReLU(),
        )

        self.init_fc_blocks(self.conv_head_out_size + cfg.hidden_size)

    def forward(self, x):
        x = x['obs']
        x = self.conv_head(x)
        x = x.contiguous().view(-1, self.conv_head_out_size)

        if self.cfg.encoder_extra_fc_layers:
            x = self.extra_linear(x)

        return x


class ResBlock(nn.Module):
    """残差块"""
    def __init__(self, cfg, input_ch, output_ch):
        super().__init__()
        layers = [
            activation_func(cfg),
            nn.Conv2d(input_ch, output_ch, kernel_size=3, stride=1, padding=1),
            activation_func(cfg),
            nn.Conv2d(output_ch, output_ch, kernel_size=3, stride=1, padding=1),
        ]
        self.res_block_core = nn.Sequential(*layers)

    def forward(self, x):
        identity = x
        out = self.res_block_core(x)
        out = out + identity  # 残差连接
        return out
```

### 6.2 Actor-Critic 模型 (sample_factory/algorithms/appo/model.py)

```python
class _ActorCriticSharedWeights(nn.Module):
    """共享权重的 Actor-Critic 网络"""
    def __init__(self, make_encoder, make_core, action_space, cfg, timing):
        super().__init__()
        hidden_size = cfg.hidden_size

        Layers = [
            nn.Linear(hidden_size, hidden_size),
            nonlinearity(cfg),
            nn.Linear(hidden_size, hidden_size)
        ]

        self.encoder = make_encoder()
        self.core = make_core(self.encoder)

        # 注意力模块
        self.atten_cob = Attention_cob(cfg, Timing())

        core_out_size = self.core.get_core_out_size()

        # Critic 头
        self.critic_linear = nn.Linear(core_out_size, 1)
        self.critic_pre = nn.Sequential(*Layers)

        # Actor 头
        self.actor_pre = nn.Sequential(*Layers)
        self.action_parameterization = self.get_action_parameterization(core_out_size)

        self.apply(self.initialize_weights)
        self.train()

    def forward_head(self, obs_dict, oth_ids):
        """前向传播：编码器 + 注意力"""
        normalize_obs(obs_dict, self.cfg)
        x = self.encoder(obs_dict)

        # 注意力机制：聚合邻居信息
        oth_info = self.atten_cob(
            x, oth_ids.long(),
            obs_dict['attention_mask'],
            obs_dict['relative_xy']
        )
        x = x + oth_info  # 残差连接

        return x

    def forward_core(self, head_output, rnn_states):
        """前向传播：RNN 核心"""
        x, new_rnn_states = self.core(head_output, rnn_states)
        return x, new_rnn_states

    def forward_tail(self, core_output, with_action_distribution=False):
        """前向传播：输出头"""
        # Critic 输出
        values = self.critic_linear(core_output + self.critic_pre(core_output))

        # Actor 输出
        action_distribution_params, action_distribution = self.action_parameterization(
            core_output + self.actor_pre(core_output)
        )
        actions, log_prob_actions = sample_actions_log_probs(action_distribution)

        result = AttrDict(dict(
            actions=actions,
            action_logits=action_distribution_params,
            log_prob_actions=log_prob_actions,
            values=values,
        ))

        if with_action_distribution:
            result.action_distribution = action_distribution

        return result

    def forward(self, obs_dict, rnn_states, with_action_distribution=False):
        """完整前向传播"""
        oth_ids = obs_dict['ids_oth']
        xx = torch.arange(oth_ids.shape[0]).unsqueeze(1).cuda()
        oth_ids = xx + oth_ids

        x = self.forward_head(obs_dict, oth_ids)
        x, new_rnn_states = self.forward_core(x, rnn_states)
        result = self.forward_tail(x, with_action_distribution)
        result.rnn_states = new_rnn_states

        return result
```

---

## 7. 训练流程

### 7.1 主入口 (main.py)

```python
from learning.learning_config import Experiment
from training_run import run
from utils.files import select_free_dir_name

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

def update_dict(target_dict, keys, values):
    """递归更新配置字典"""
    for key, value in zip(keys, values):
        if recursive_update(target_dict, key, value):
            print(f'Updated {key} to {value}')
        else:
            print(f'Could not find {key} in experiment')

list_or_args = list(argv)
experiment = Experiment()

# 设置实验根目录
if experiment.global_settings.experiments_root is None:
    experiment.global_settings.experiments_root = \
        select_free_dir_name(experiment.global_settings.train_dir)

experiment = experiment.dict()

# 解析命令行参数
keys = []
values = []
for arg in list_or_args[1:]:
    key, value = arg.split('=')
    key = key.replace('--', '')
    keys.append(key)
    values.append(value)

update_dict(experiment, keys, values)
experiment = Experiment(**experiment)

# 运行训练
run(config=experiment.dict(exclude_unset=True))
```

### 7.2 训练运行 (training_run.py)

```python
import wandb
from sample_factory.run_algorithm import run_algorithm

def run(config=None):
    # 注册自定义编码器
    register_custom_encoder('pogema_residual', ResnetEncoder)
    params = Namespace(**config)
    params.wandb_thread_mode = False

    register_custom_components()
    exp, flat_config = validate_config(config)

    # 设置实验目录
    if exp.global_settings.experiments_root is None:
        exp.global_settings.experiments_root = \
            select_free_dir_name(exp.global_settings.train_dir)
        exp, flat_config = validate_config(exp.dict())

    # 初始化 WandB
    if exp.global_settings.use_wandb:
        wandb.init(
            project=exp.environment.env,
            config=exp.dict(),
            save_code=False,
            sync_tensorboard=True,
            anonymous="allow",
        )

    # 运行训练
    status = run_algorithm(flat_config)

    # 获取最终指标
    last_quartile_metrics = get_summary_metrics(
        summaries_dir(experiment_dir(cfg=flat_config)) + '/0'
    )

    if exp.global_settings.use_wandb:
        # 保存结果
        path = Path(exp.global_settings.train_dir) / exp.global_settings.experiments_root
        shutil.make_archive(str(path), 'zip', path)
        wandb.save(str(path) + '.zip')
        wandb.log(last_quartile_metrics)
        wandb.finish()

    return status
```

### 7.3 环境创建 (env/create_env.py)

```python
def create_env(env_cfg: Environment, auto_reset=False):
    """创建训练环境"""
    env = create_env_base(env_cfg)
    env = SMAPO_preprocessor(env, env_cfg, auto_reset)
    return env

def create_env_base(env_cfg: Environment):
    """创建基础环境"""
    env = pogema_v0(grid_config=env_cfg.grid_config)
    env = ProvideGlobalObstacles(env)  # 提供全局障碍物访问
    if env_cfg.use_maps:
        env = MultiMapWrapper(env)  # 多地图包装器
    return env


class MultiEnv(gym.Wrapper):
    """多环境包装器，支持不同智能体数量"""
    def __init__(self, env_cfg: Environment):
        if env_cfg.target_num_agents is None:
            self.envs = [create_env(env_cfg, auto_reset=True)]
        else:
            num_envs = env_cfg.target_num_agents // env_cfg.grid_config.num_agents
            self.envs = [create_env(env_cfg, auto_reset=True) for _ in range(num_envs)]
        super().__init__(self.envs[0])

    def step(self, actions):
        obs, rewards, dones, infos = [], [], [], []
        last_agents = 0
        for env in self.envs:
            env_num_agents = env.get_num_agents()
            action = actions[last_agents: last_agents + env_num_agents]
            o, r, d, i = env.step(action)
            obs += o
            rewards += r
            dones += d
            infos += i
        return obs, rewards, dones, infos
```

---

## 8. 配置参数详解

### 8.1 环境配置

```python
class Environment(BaseModel):
    grid_config: DMAPFConfig = DMAPFConfig()
    env: Literal['Pogema-v0'] = "Pogema-v0"
    grid_memory_obs_radius: Optional[int] = None
    observation_type: str = 'POMAPF'
    preprocessing: PreprocessorConfig = PreprocessorConfig()
    sub_goal_distance: Optional[int] = None
    with_animation: bool = False
    worker_index: int = None
    vector_index: int = None
    env_id: int = None
    target_num_agents: Optional[int] = None
    agent_bins: Optional[list] = [64, 128, 256, 256]
    use_maps: bool = True
    full_grid: bool = True


class DMAPFConfig(GridConfig):
    integration: Literal['SampleFactory'] = 'SampleFactory'
    collision_system: Literal['priority', 'block_both'] = 'priority'
    observation_type: Literal['POMAPF'] = 'POMAPF'
    auto_reset: Literal[False] = False

    num_agents: int = 128
    obs_radius: int = 5
    max_episode_steps: int = 512
    map_name: str = r'mazes-.+'
```

### 8.2 预处理器配置

```python
class PreprocessorConfig(PlannerConfig):
    network_input_radius: int = 5        # 网络输入半径
    intrinsic_target_reward: float = 0.01  # 内在奖励值
    add_r: bool = False                  # 是否叠加外在奖励
```

### 8.3 规划器配置

```python
class RePlanConfig(AlgoBase, extra=Extra.forbid):
    name: Literal['Randomized A*'] = 'Randomized A*'
    num_process: int = 5
    no_path_random: bool = True
    fix_nones: bool = True
    ignore_other_agents: float = 1.0
    cost_penalty_coefficient: float = 0.4
    device: str = 'cpu'
```

---

## 9. 使用指南

### 9.1 安装依赖

```bash
# 基础依赖
pip install torch numpy gym pydantic

# 可选：WandB 日志
pip install wandb

# 编译 C++ 规划器
cd planner/LB_A
python setup.py build_ext --inplace
```

### 9.2 训练模型

```bash
# 基础训练
python main.py

# 自定义参数训练
python main.py --learning_rate=0.001 --num_agents=256 --train_for_env_steps=100000000

# 使用 GPU
CUDA_VISIBLE_DEVICES=0 python main.py
```

### 9.3 评估模型

```python
from learning.ppo import PpoInference, PpoConfig

# 加载模型
config = PpoConfig(
    path_to_weights='results/SMAPO',
    device='cuda'
)
inference = PpoInference(config)

# 获取动作
observations = env.reset()
actions = inference.act(observations)
```

### 9.4 自定义环境

```python
from pogema import GridConfig, pogema_v0
from env.SMAPO import SMAPO_preprocessor

# 创建自定义配置
grid_config = GridConfig(
    size=64,
    density=0.3,
    num_agents=128,
    obs_radius=5,
    max_episode_steps=512,
    map_name='custom_map'
)

# 创建环境
env = pogema_v0(grid_config=grid_config)
env = SMAPO_preprocessor(env, config)
```

---

## 附录

### A. 观察空间结构

| 键名 | 形状 | 类型 | 描述 |
|------|------|------|------|
| `obs` | (C, 11, 11) | float32 | 卷积输入（障碍物+智能体+路径） |
| `ids_oth` | (64,) | int64 | 邻居智能体相对ID |
| `relative_xy` | (64, 2) | int64 | 邻居相对位置 |
| `attention_mask` | (64,) | float32 | 注意力掩码 |
| `id_` | scalar | int64 | 当前智能体ID |

### B. 动作空间

| 动作值 | 移动方向 |
|--------|----------|
| 0 | 停留 (0, 0) |
| 1 | 向上 (-1, 0) |
| 2 | 向下 (1, 0) |
| 3 | 向左 (0, -1) |
| 4 | 向右 (0, 1) |

### C. 奖励设计

- **外在奖励**：到达目标点时 +1.0
- **内在奖励**：到达子目标点时 +0.01（可配置）
- **总奖励**：`add_r=True` 时叠加，否则仅内在奖励

### D. 参考文献

1. **POGEMA**: Partially Observable Grid Environment for Multi-Agent Pathfinding
2. **Sample Factory**: A Framework for Asynchronous PPO
3. **MAPF**: Multi-Agent Path Finding: Definitions and Variants