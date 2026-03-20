try:
    from typing import Literal, Optional
except ImportError:
    from typing_extensions import Literal, Optional

from pydantic import Extra

from learning.utils_common import AlgoBase
from planning.replan_algo import RePlanBase, NoPathSoRandomOrStayWrapper, FixNonesWrapper


class RePlanConfig(AlgoBase, extra=Extra.forbid):
    name: Literal['Randomized A*'] = 'Randomized A*'
    num_process: int = 5
    no_path_random: bool = True
    fix_nones: bool = True
    ignore_other_agents: float = 1.0
    cost_penalty_coefficient: float = 0.4
    plcc_alpha: float = 2.0
    plcc_beta: float = 0.5
    plcc_lambda: float = 0.8
    plcc_delta_t: int = 2
    pecc_gamma: Optional[float] = None
    map_width: Optional[int] = None
    map_height: Optional[int] = None
    device: str = 'cpu'


class RePlan:
    def __init__(self, cfg: RePlanConfig = RePlanConfig()):
        self.cfg = cfg
        self.agent = None
        self.fix_nones = cfg.fix_nones
        self.no_path_random = cfg.no_path_random
        self.env = None

    def act(self, observations, rewards=None, dones=None, info=None, skip_agents=None):
        return self.agent.act(observations, skip_agents)

    def after_step(self, dones):
        if all(dones):
            self.agent = None

    def after_reset(self):
        self.reset_states()

    def get_path(self):
        x = self.agent.get_path()
        return x

    def reset_states(self, ):
        self.agent = RePlanBase(
            seed=self.cfg.seed,
            ignore_other_agents=self.cfg.ignore_other_agents,
            cost_penalty_coefficient=self.cfg.cost_penalty_coefficient,
            gamma=self._resolve_pecc_gamma(),
            delta_t=self.cfg.plcc_delta_t,
            alpha=self.cfg.plcc_alpha,
            beta=self.cfg.plcc_beta,
            lambda_=self.cfg.plcc_lambda,
            map_width=self._resolve_map_width(),
            map_height=self._resolve_map_height(),
        )
        if self.no_path_random:
            self.agent = NoPathSoRandomOrStayWrapper(self.agent)
        elif self.fix_nones:
            self.agent = FixNonesWrapper(self.agent)

    def _resolve_map_width(self):
        if self.cfg.map_width is not None:
            return int(self.cfg.map_width)
        if self.env is None:
            return None
        grid = getattr(self.env, 'grid', None)
        if grid is not None and getattr(grid, 'config', None) is not None:
            size = getattr(grid.config, 'size', None)
            if size is not None:
                return int(size)
        if hasattr(self.env, 'get_obstacles'):
            obstacles = self.env.get_obstacles(ignore_borders=True)
            if hasattr(obstacles, 'shape') and len(obstacles.shape) >= 2:
                return int(obstacles.shape[2] if len(obstacles.shape) == 3 else obstacles.shape[1])
        return None

    def _resolve_map_height(self):
        if self.cfg.map_height is not None:
            return int(self.cfg.map_height)
        if self.env is None:
            return None
        grid = getattr(self.env, 'grid', None)
        if grid is not None and getattr(grid, 'config', None) is not None:
            size = getattr(grid.config, 'size', None)
            if size is not None:
                return int(size)
        if hasattr(self.env, 'get_obstacles'):
            obstacles = self.env.get_obstacles(ignore_borders=True)
            if hasattr(obstacles, 'shape') and len(obstacles.shape) >= 2:
                return int(obstacles.shape[1] if len(obstacles.shape) == 3 else obstacles.shape[0])
        return None

    def _resolve_pecc_gamma(self):
        if self.cfg.pecc_gamma is not None:
            return float(self.cfg.pecc_gamma)

        map_width = self._resolve_map_width()
        map_height = self._resolve_map_height()
        if map_width is not None and map_height is not None:
            return 0.5 / float(map_width + map_height)

        return None

    @staticmethod
    def get_additional_info():
        return {"rl_used": 0.0}
