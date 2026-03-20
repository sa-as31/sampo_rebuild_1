from pogema import GridConfig
from planner.LB_A.planner import planner
from pydantic import BaseModel
from typing import Optional
import heapq
import math
import numpy as np

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
        normalized_obstacles = np.asarray(obstacles, dtype=np.int32)
        if normalized_obstacles.ndim != 2:
            raise ValueError("Planner expects a 2D obstacle grid.")
        self.obstacles = normalized_obstacles.tolist()
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


class LayeredPlanner:
    def __init__(self, cfg: PlannerConfig):
        self.cfg = cfg
        self.obstacles = None
        self.starts = None
        self.paths = []
        self.height_levels = 1
        self.action_deltas = GridConfig().MOVES_2P5D

    def add_grid_obstacles(self, obstacles, starts):
        self.obstacles = np.asarray(obstacles, dtype=np.int32)
        self.starts = starts
        if self.obstacles.ndim == 3:
            self.height_levels = int(self.obstacles.shape[0])
        if starts and len(starts[0]) >= 3:
            self.height_levels = max(self.height_levels, max(int(pos[2]) for pos in starts) + 1)

    def _in_bounds(self, x, y, z):
        if self.obstacles.ndim == 3:
            _, height, width = self.obstacles.shape
            return 0 <= x < height and 0 <= y < width and 0 <= z < self.height_levels
        return (
            0 <= x < len(self.obstacles)
            and 0 <= y < len(self.obstacles[0])
            and 0 <= z < self.height_levels
        )

    def _is_free(self, x, y, z, blocked):
        if not self._in_bounds(x, y, z):
            return False
        if self.obstacles.ndim == 3:
            if self.obstacles[z][x][y] != 0:
                return False
        elif self.obstacles[x][y] != 0:
            return False
        return (x, y, z) not in blocked

    @staticmethod
    def _manhattan(a, b):
        return sum(abs(int(x) - int(y)) for x, y in zip(a, b))

    def _register_path(self, path, planned_occupancy):
        for t, pos in enumerate(path[1:], start=1):
            planned_occupancy[(pos[0], pos[1], pos[2], t)] = planned_occupancy.get((pos[0], pos[1], pos[2], t), 0) + 1

    def _plan_single(self, start, goal, blocked, planned_occupancy, max_depth=96):
        if start == goal:
            return [start]

        open_heap = [(self._manhattan(start, goal), 0.0, start, 0)]
        g_score = {(start, 0): 0.0}
        parent = {}
        best = (start, 0)
        best_h = self._manhattan(start, goal)

        while open_heap:
            _, cur_g, pos, t = heapq.heappop(open_heap)
            if cur_g > g_score.get((pos, t), math.inf):
                continue
            h = self._manhattan(pos, goal)
            if h < best_h:
                best_h = h
                best = (pos, t)
            if pos == goal:
                best = (pos, t)
                break
            if t >= max_depth:
                continue

            for dx, dy, dz in self.action_deltas:
                nxt = (pos[0] + dx, pos[1] + dy, pos[2] + dz)
                if not self._is_free(*nxt, blocked):
                    continue
                penalty = planned_occupancy.get((nxt[0], nxt[1], nxt[2], t + 1), 0)
                new_g = cur_g + 1.0 + self.cfg.plcc_alpha * penalty
                key = (nxt, t + 1)
                if new_g >= g_score.get(key, math.inf):
                    continue
                g_score[key] = new_g
                parent[key] = (pos, t)
                heapq.heappush(open_heap, (new_g + self._manhattan(nxt, goal), new_g, nxt, t + 1))

        states = [best]
        while states[-1][0] != start:
            states.append(parent[states[-1]])
        states.reverse()
        return [state[0] for state in states]

    def update(self, obs):
        num_agents = len(obs)
        if self.starts is None:
            raise RuntimeError("LayeredPlanner must be initialized with add_grid_obstacles before update().")
        if obs and hasattr(obs[0].get('agents'), 'shape') and len(obs[0]['agents'].shape) == 3:
            self.height_levels = int(obs[0]['agents'].shape[0])

        current_positions = [tuple(int(v) for v in obs[i]['xy']) for i in range(num_agents)]
        target_positions = [tuple(int(v) for v in obs[i]['target_xy']) for i in range(num_agents)]
        blocked_now = set(current_positions)
        planned_occupancy = {}
        self.paths = []

        for i in range(num_agents):
            if current_positions[i] == target_positions[i]:
                self.paths.append([current_positions[i]])
                continue
            blocked = blocked_now - {current_positions[i]}
            path = self._plan_single(current_positions[i], target_positions[i], blocked, planned_occupancy)
            self.paths.append(path)
            self._register_path(path, planned_occupancy)

    def get_path(self):
        return self.paths


class ResettablePlanner:
    def __init__(self, cfg: PlannerConfig):
        self._cfg = cfg
        self._agent = None
        self._starts = None

    def update(self, observations):
        return self._agent.update(observations)

    def get_path(self):
        return self._agent.get_path()

    def reset_states(self, ):
        self._agent = Planner(self._cfg)

    def add_grid_obstacles(self, obstacles, starts):
        self._starts = starts
        if starts and len(starts[0]) >= 3:
            self._agent = LayeredPlanner(self._cfg)
        elif self._agent is None:
            self._agent = Planner(self._cfg)
        self._agent.add_grid_obstacles(obstacles, starts)
