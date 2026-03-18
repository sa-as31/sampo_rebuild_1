from pogema import GridConfig
from planner.LB_A.planner import planner
from pydantic import BaseModel
from typing import Optional

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


class PlannerConfig(BaseModel):
    use_static_cost: bool = True
    use_dynamic_cost: bool = True
    reset_dynamic_cost: bool = False
    plcc_alpha: float = 2.0
    plcc_beta: float = 0.5
    plcc_lambda: float = 0.8
    plcc_delta_t: int = 2
    pecc_gamma: Optional[float] = None


class Planner:
    def __init__(self, cfg: PlannerConfig):
        self.planner = None
        self.obstacles = None
        self.starts = None
        self.cfg = cfg

    def add_grid_obstacles(self, obstacles, starts):
        self.obstacles = obstacles
        self.starts = starts
        self.planner = None

    def _resolve_pecc_gamma(self, obs_radius):
        if self.cfg.pecc_gamma is not None:
            return float(self.cfg.pecc_gamma)

        map_h = max(len(self.obstacles) - 2 * obs_radius, 1)
        map_w = max(len(self.obstacles[0]) - 2 * obs_radius, 1)
        return 0.5 / float(map_w + map_h)

    def update(self, obs):
        num_agents = len(obs)
        obs_radius = len(obs[0]['obstacles']) // 2
        if self.planner is None:
            pecc_gamma = self._resolve_pecc_gamma(obs_radius)
            self.planner = [
                planner(
                    self.obstacles,
                    self.cfg.use_static_cost,
                    self.cfg.use_dynamic_cost,
                    self.cfg.reset_dynamic_cost,
                    self.cfg.plcc_alpha,
                    self.cfg.plcc_beta,
                    self.cfg.plcc_lambda,
                    pecc_gamma,
                    self.cfg.plcc_delta_t,
                )
                for _ in range(num_agents)
            ]
            for i, p in enumerate(self.planner):
                p.set_abs_start(self.starts[i])
            if self.cfg.use_static_cost:
                pen_calc = planner(
                    self.obstacles,
                    self.cfg.use_static_cost,
                    self.cfg.use_dynamic_cost,
                    self.cfg.reset_dynamic_cost,
                    self.cfg.plcc_alpha,
                    self.cfg.plcc_beta,
                    self.cfg.plcc_lambda,
                    pecc_gamma,
                    self.cfg.plcc_delta_t,
                )
                penalties = pen_calc.precompute_penalty_matrix(obs_radius)
                for p in self.planner:
                    p.set_penalties(penalties)
        
        hash_map = dict()
        for k in range(num_agents):
            if obs[k]['xy'] == obs[k]['target_xy']:
                continue
            obs[k]['agents'][obs_radius][obs_radius] = 0
            self.planner[k].update_occupations(obs[k]['agents'], (obs[k]['xy'][0] - obs_radius, obs[k]['xy'][1] - obs_radius), obs[k]['target_xy'])
            obs[k]['agents'][obs_radius][obs_radius] = 1
            self.planner[k].update_path(obs[k]['xy'], obs[k]['target_xy'], hash_map)
            self.planner[k].update_cur_map(hash_map)
            

    def get_path(self):
        results = []
        for idx in range(len(self.planner)):
            results.append(self.planner[idx].get_path())
        return results


class ResettablePlanner:
    def __init__(self, cfg: PlannerConfig):
        self._cfg = cfg
        self._agent = None

    def update(self, observations):
        return self._agent.update(observations)

    def get_path(self):
        return self._agent.get_path()

    def reset_states(self, ):
        self._agent = Planner(self._cfg)
