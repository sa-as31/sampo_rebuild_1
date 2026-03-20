import re
from copy import deepcopy

import gym
import numpy as np
from pogema import pogema_v0
from pogema.integrations.sample_factory import AutoResetWrapper

from env.custom_maps import MAPS_REGISTRY
from env.wrappers import MultiMapWrapper, ConcatPositionalFeatures, ProjectionTargetWrapper
from learning.learning_config import Environment
from env.SMAPO import SMAPO_preprocessor

class ProvideGlobalObstacles(gym.Wrapper):
    def get_global_obstacles(self):
        return np.asarray(self.grid.get_obstacles(), dtype=np.int32).copy()

    def get_global_agents_xy(self):
        return self.grid.get_agents_xy()


def _map_height_levels(map_definition):
    if isinstance(map_definition, dict) and map_definition.get('layers'):
        return len(map_definition['layers'])
    if isinstance(map_definition, dict) and map_definition.get('height_levels'):
        return int(map_definition['height_levels'])
    return 1


def _resolve_map_metadata(grid_config):
    if not getattr(grid_config, 'map_name', None):
        return grid_config

    matched_maps = [
        (map_name, map_definition)
        for map_name, map_definition in MAPS_REGISTRY.items()
        if re.match(grid_config.map_name, map_name)
    ]
    if not matched_maps:
        return grid_config

    matched_height_levels = {_map_height_levels(map_definition) for _, map_definition in matched_maps}
    if len(matched_height_levels) > 1:
        raise ValueError(
            f"Matched maps for pattern '{grid_config.map_name}' use incompatible layer counts: "
            f"{sorted(matched_height_levels)}"
        )

    resolved_grid_config = deepcopy(grid_config)
    resolved_height_levels = matched_height_levels.pop()
    if resolved_height_levels > 1:
        resolved_grid_config.height_levels = resolved_height_levels
        resolved_grid_config.native_3d_obstacles = True
    return resolved_grid_config

def create_env_base(env_cfg: Environment):
    resolved_grid_config = _resolve_map_metadata(env_cfg.grid_config) if env_cfg.use_maps else env_cfg.grid_config
    if resolved_grid_config is not env_cfg.grid_config:
        env_cfg = env_cfg.copy(deep=True)
        env_cfg.grid_config = resolved_grid_config

    env = pogema_v0(grid_config=env_cfg.grid_config)
    env = ProvideGlobalObstacles(env)
    if env_cfg.use_maps:
        env = MultiMapWrapper(env)  
    return env


def create_env(env_cfg: Environment, auto_reset=False):
    env = create_env_base(env_cfg)
    env = SMAPO_preprocessor(env, env_cfg, auto_reset)
    return env


class MultiEnv(gym.Wrapper):
    def __init__(self, env_cfg: Environment):
        if env_cfg.target_num_agents is None:
            self.envs = [create_env(env_cfg, auto_reset=True)]
        else:
            assert env_cfg.target_num_agents % env_cfg.grid_config.num_agents == 0, "Target num agents must be divisible by num agents"
            num_envs = env_cfg.target_num_agents // env_cfg.grid_config.num_agents
            self.envs = [create_env(env_cfg, auto_reset=True) for _ in range(num_envs)]

        super().__init__(self.envs[0])

    def step(self, actions):
        obs, rewards, dones, infos = [], [], [], []
        last_agents = 0   
        for env in self.envs:
            env_num_agents = env.get_num_agents()
            action = actions[last_agents: last_agents + env_num_agents]  
            last_agents = last_agents + env_num_agents
            o, r, d, i = env.step(action)
            obs += o
            rewards += r
            dones += d
            infos += i
        return obs, rewards, dones, infos

    def reset(self):
        obs = []
        for env in self.envs:
            obs += env.reset()
        return obs

    def sample_actions(self):
        actions = []
        for env in self.envs:
            actions += list(env.sample_actions())
        return np.array(actions)

    @property
    def num_agents(self):
        return sum([env.get_num_agents() for env in self.envs])
