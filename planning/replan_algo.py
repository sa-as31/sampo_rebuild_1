import heapq
import math
import random
from collections import defaultdict
from typing import Optional

import numpy as np


ACTION_TO_DELTA = {
    0: (0, 0),    # stay
    1: (-1, 0),   # up
    2: (1, 0),    # down
    3: (0, -1),   # left
    4: (0, 1),    # right
}
DELTA_TO_ACTION = {v: k for k, v in ACTION_TO_DELTA.items()}


class RePlanBase:
    """
    A lightweight randomized A* replanner used by inference utilities.
    It follows SMAPO paper ideas by combining:
    - Planned congestion cost (PlCC): temporal occupancy penalties on planned paths
    - Perceived congestion cost (PeCC): exponentially decayed local traffic estimates
    """

    def __init__(
        self,
        seed=0,
        ignore_other_agents=1.0,
        cost_penalty_coefficient=0.4,
        gamma: Optional[float] = None,
        delta_t=2,
        alpha=2.0,
        beta=0.5,
        lambda_=0.8,
        max_depth=64,
        map_width: Optional[int] = None,
        map_height: Optional[int] = None,
    ):
        self._rng = random.Random(seed)
        self.ignore_other_agents = float(np.clip(ignore_other_agents, 0.0, 1.0))
        self.cost_penalty_coefficient = float(cost_penalty_coefficient)

        # Prefer the paper-style gamma resolution instead of a hard-coded fallback.
        self.gamma = None if gamma is None else float(gamma)
        self.delta_t = int(delta_t)
        self.alpha = float(alpha)
        self.beta = float(beta)
        self.lambda_ = float(lambda_)
        self.max_depth = int(max_depth)
        self.map_width = None if map_width is None else int(map_width)
        self.map_height = None if map_height is None else int(map_height)

        self._pecc = {}
        self._paths = []

    def get_path(self):
        return self._paths

    def act(self, observations, skip_agents=None):
        skip_set = set(skip_agents or [])
        self._ensure_gamma(observations)

        self._decay_pecc()
        for obs in observations:
            self._update_pecc_from_observation(obs)

        planned_occupancy = defaultdict(int)
        actions = []
        paths = []

        for agent_idx, obs in enumerate(observations):
            if agent_idx in skip_set:
                actions.append(0)
                paths.append(None)
                continue

            path = self._plan_single_agent(obs, planned_occupancy)
            paths.append(path)
            actions.append(self._path_to_action(path, obs))
            self._register_planned_occupancy(path, planned_occupancy)

        self._paths = paths
        return actions

    def _plan_single_agent(self, obs, planned_occupancy):
        obstacles = np.asarray(obs["obstacles"])
        agents = np.asarray(obs.get("agents", np.zeros_like(obstacles)))
        center = obstacles.shape[0] // 2

        start_abs = (int(obs["xy"][0]), int(obs["xy"][1]))
        goal_abs = (int(obs["target_xy"][0]), int(obs["target_xy"][1]))
        start_local = (center, center)
        goal_local = (goal_abs[0] - start_abs[0] + center, goal_abs[1] - start_abs[1] + center)

        consider_agents_as_obstacles = self._rng.random() > self.ignore_other_agents
        target_local = self._pick_local_target(goal_local, start_abs, goal_abs, obstacles)
        if target_local is None:
            return None

        start_state = (start_local[0], start_local[1], 0)
        open_heap = [(self._manhattan(start_local, target_local), 0.0, start_state)]
        g_score = {start_state: 0.0}
        parent = {}
        best_state = None

        while open_heap:
            _, cur_g, state = heapq.heappop(open_heap)
            if cur_g > g_score.get(state, math.inf):
                continue

            x, y, t = state
            if (x, y) == target_local:
                best_state = state
                break
            if t >= self.max_depth:
                continue

            for dx, dy in ACTION_TO_DELTA.values():
                nx, ny = x + dx, y + dy
                if not self._is_local_free(nx, ny, obstacles):
                    continue

                if (nx, ny) != start_local and consider_agents_as_obstacles and agents[nx, ny] > 0:
                    continue

                abs_pos = (start_abs[0] + nx - center, start_abs[1] + ny - center)
                step_cost = self._planned_congestion_cost(abs_pos, t + 1, planned_occupancy)
                step_cost += self._perceived_congestion_cost(abs_pos)

                if (nx, ny) != start_local and agents[nx, ny] > 0:
                    # Keep a soft interaction penalty even when agents are not hard obstacles.
                    step_cost += self.cost_penalty_coefficient * (1.0 - self.ignore_other_agents)

                next_state = (nx, ny, t + 1)
                new_g = cur_g + step_cost
                if new_g >= g_score.get(next_state, math.inf):
                    continue

                g_score[next_state] = new_g
                parent[next_state] = state
                f = new_g + self._manhattan((nx, ny), target_local)
                heapq.heappush(open_heap, (f, new_g, next_state))

        if best_state is None:
            return self._fallback_path(obs, obstacles)

        states = [best_state]
        while states[-1] != start_state:
            states.append(parent[states[-1]])
        states.reverse()

        return [(start_abs[0] + x - center, start_abs[1] + y - center) for x, y, _ in states]

    def _fallback_path(self, obs, obstacles):
        center = obstacles.shape[0] // 2
        start_abs = (int(obs["xy"][0]), int(obs["xy"][1]))
        goal_abs = (int(obs["target_xy"][0]), int(obs["target_xy"][1]))
        best_action = None
        best_score = math.inf

        for action, (dx, dy) in ACTION_TO_DELTA.items():
            nx, ny = center + dx, center + dy
            if not self._is_local_free(nx, ny, obstacles):
                continue
            abs_pos = (start_abs[0] + dx, start_abs[1] + dy)
            score = self._manhattan(abs_pos, goal_abs)
            if score < best_score:
                best_score = score
                best_action = action

        if best_action is None:
            return None
        dx, dy = ACTION_TO_DELTA[best_action]
        return [start_abs, (start_abs[0] + dx, start_abs[1] + dy)]

    def _pick_local_target(self, goal_local, start_abs, goal_abs, obstacles):
        if self._is_local_free(goal_local[0], goal_local[1], obstacles):
            return goal_local

        best = None
        best_dist = math.inf
        size = obstacles.shape[0]
        center = size // 2

        for i in range(size):
            for j in range(size):
                if not self._is_local_free(i, j, obstacles):
                    continue
                abs_pos = (start_abs[0] + i - center, start_abs[1] + j - center)
                dist = self._manhattan(abs_pos, goal_abs)
                if dist < best_dist:
                    best_dist = dist
                    best = (i, j)
        return best

    def _register_planned_occupancy(self, path, planned_occupancy):
        if not path:
            return
        # Track near-future occupancies for temporal congestion penalties.
        for t, (x, y) in enumerate(path[1 : self.max_depth + 1], start=1):
            planned_occupancy[(x, y, t)] += 1

    def _planned_congestion_cost(self, pos, t, planned_occupancy):
        x, y = pos
        total = 1.0
        for k in range(-self.delta_t, self.delta_t + 1):
            count = planned_occupancy.get((x, y, t + k), 0)
            if count <= 0:
                continue
            if k == 0:
                total += self.alpha * (count ** 2)
            else:
                total += self.beta * count * (self.lambda_ ** abs(k))
        return total

    def _perceived_congestion_cost(self, pos):
        return self._pecc.get(pos, 0.0)

    def _decay_pecc(self):
        if self.gamma is None:
            return
        if not self._pecc:
            return
        to_drop = []
        for key, value in self._pecc.items():
            decayed = value * self.gamma
            if decayed < 1e-4:
                to_drop.append(key)
            else:
                self._pecc[key] = decayed
        for key in to_drop:
            self._pecc.pop(key, None)

    def _update_pecc_from_observation(self, obs):
        agents = np.asarray(obs.get("agents"))
        if agents.ndim != 2:
            return
        center = agents.shape[0] // 2
        x0, y0 = int(obs["xy"][0]), int(obs["xy"][1])
        idx = np.argwhere(agents > 0)
        for i, j in idx:
            pos = (x0 + int(i) - center, y0 + int(j) - center)
            self._pecc[pos] = self._pecc.get(pos, 0.0) + 1.0

    @staticmethod
    def _path_to_action(path, obs):
        if not path or len(path) < 2:
            return None
        sx, sy = int(obs["xy"][0]), int(obs["xy"][1])
        nx, ny = path[1]
        return DELTA_TO_ACTION.get((nx - sx, ny - sy), None)

    @staticmethod
    def _is_local_free(i, j, obstacles):
        if i < 0 or j < 0 or i >= obstacles.shape[0] or j >= obstacles.shape[1]:
            return False
        return float(obstacles[i, j]) <= 0.0

    @staticmethod
    def _manhattan(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _ensure_gamma(self, observations):
        if self.gamma is not None:
            return

        map_w = self.map_width
        map_h = self.map_height

        # Fallback for lightweight inference paths that do not attach the full env.
        if (map_w is None or map_h is None) and observations:
            obstacles = np.asarray(observations[0].get("obstacles"))
            if obstacles.ndim == 2:
                map_h = int(obstacles.shape[0])
                map_w = int(obstacles.shape[1])

        map_w = max(int(map_w or 1), 1)
        map_h = max(int(map_h or 1), 1)
        self.gamma = 0.5 / float(map_w + map_h)


class NoPathSoRandomOrStayWrapper:
    def __init__(self, agent):
        self._agent = agent
        self._rng = random.Random()

    def act(self, observations, skip_agents=None):
        actions = self._agent.act(observations, skip_agents=skip_agents)
        for i, action in enumerate(actions):
            if action is None:
                actions[i] = self._sample_feasible_action(observations[i])
        return actions

    def get_path(self):
        return self._agent.get_path()

    def _sample_feasible_action(self, obs):
        obstacles = np.asarray(obs["obstacles"])
        center = obstacles.shape[0] // 2
        feasible = [0]
        for action, (dx, dy) in ACTION_TO_DELTA.items():
            ni, nj = center + dx, center + dy
            if 0 <= ni < obstacles.shape[0] and 0 <= nj < obstacles.shape[1] and obstacles[ni, nj] <= 0:
                feasible.append(action)
        return self._rng.choice(feasible) if feasible else 0


class FixNonesWrapper:
    def __init__(self, agent):
        self._agent = agent
        self._last_actions = None

    def act(self, observations, skip_agents=None):
        actions = self._agent.act(observations, skip_agents=skip_agents)
        if self._last_actions is None or len(self._last_actions) != len(actions):
            self._last_actions = [0 for _ in actions]

        fixed = []
        for i, action in enumerate(actions):
            if action is None:
                action = self._last_actions[i]
            fixed.append(action)
            self._last_actions[i] = action
        return fixed

    def get_path(self):
        return self._agent.get_path()
