import string
import sys
from contextlib import closing
from copy import deepcopy
import warnings

import numpy as np
from gym import utils
from io import StringIO

from pogema.generator import generate_obstacles, generate_positions_and_targets_fast, \
    get_components, generate_new_target
from .grid_config import GridConfig


class Grid:
    def __init__(self, grid_config: GridConfig, add_artificial_border: bool = True, num_retries=10):

        self.config = grid_config
        self.layered = self.config.is_layered()
        self.native_3d_obstacles = self.config.is_native_3d_obstacles()
        self.conflict = 0
        self.rnd = np.random.default_rng(grid_config.seed)
        if self.config.map is None:
            obstacles = generate_obstacles(self.config)
        else:
            obstacles = np.asarray(self.config.map, dtype=np.int32)
        obstacles = obstacles.astype(np.int32)
        if grid_config.targets_xy and grid_config.agents_xy:
            starts_xy, finishes_xy = grid_config.agents_xy, grid_config.targets_xy
            if len(starts_xy) != len(finishes_xy):
                raise IndexError("Can't create task. Please provide agents_xy and targets_xy of the same size.")
            grid_config.num_agents = len(starts_xy)
            for start_xy, finish_xy in zip(starts_xy, finishes_xy):
                s_x, s_y = start_xy[:2]
                f_x, f_y = finish_xy[:2]
                start_z = int(start_xy[2]) if len(start_xy) >= 3 else None
                finish_z = int(finish_xy[2]) if len(finish_xy) >= 3 else None
                if self.config.map is not None and self._obstacle_at(obstacles, s_x, s_y, start_z) == grid_config.OBSTACLE:
                    warnings.warn(f"There is an obstacle on a start point ({s_x}, {s_y}), replacing with free cell",
                                  Warning, stacklevel=2)
                self._clear_obstacle_cell(obstacles, s_x, s_y, start_z)
                if self.config.map is not None and self._obstacle_at(obstacles, f_x, f_y, finish_z) == grid_config.OBSTACLE:
                    warnings.warn(f"There is an obstacle on a finish point ({s_x}, {s_y}), replacing with free cell",
                                  Warning, stacklevel=2)
                self._clear_obstacle_cell(obstacles, f_x, f_y, finish_z)
        else:
            starts_xy, finishes_xy = generate_positions_and_targets_fast(obstacles, self.config)

        if len(starts_xy) != len(finishes_xy):
            for attempt in range(num_retries):
                if len(starts_xy) == len(finishes_xy):
                    warnings.warn(f'Created valid configuration only with {attempt} attempts.', Warning, stacklevel=2)
                    break
                if self.config.map is None:
                    obstacles = generate_obstacles(self.config)
                starts_xy, finishes_xy = generate_positions_and_targets_fast(obstacles, self.config)

        if not starts_xy or not finishes_xy or len(starts_xy) != len(finishes_xy):
            raise OverflowError("Can't create task. Please check grid grid_config, especially density, num_agent and map.")

        if add_artificial_border:
            r = self.config.obs_radius
            if obstacles.ndim == 3:
                levels, inner_height, inner_width = obstacles.shape
                filled_shape = (levels, inner_height + r * 2, inner_width + r * 2)
                if grid_config.empty_outside:
                    filled_obstacles = np.zeros(filled_shape, dtype=np.int32)
                else:
                    filled_obstacles = self.rnd.binomial(1, grid_config.density, filled_shape).astype(np.int32)

                height, width = filled_obstacles.shape[1:]
                filled_obstacles[:, r - 1, r - 1:width - r + 1] = grid_config.OBSTACLE
                filled_obstacles[:, r - 1:height - r + 1, r - 1] = grid_config.OBSTACLE
                filled_obstacles[:, height - r, r - 1:width - r + 1] = grid_config.OBSTACLE
                filled_obstacles[:, r - 1:height - r + 1, width - r] = grid_config.OBSTACLE
                filled_obstacles[:, r:height - r, r:width - r] = obstacles
            else:
                if grid_config.empty_outside:
                    filled_obstacles = np.zeros(np.array(obstacles.shape) + r * 2, dtype=np.int32)
                else:
                    filled_obstacles = self.rnd.binomial(1, grid_config.density, np.array(obstacles.shape) + r * 2).astype(np.int32)

                height, width = filled_obstacles.shape
                filled_obstacles[r - 1, r - 1:width - r + 1] = grid_config.OBSTACLE
                filled_obstacles[r - 1:height - r + 1, r - 1] = grid_config.OBSTACLE
                filled_obstacles[height - r, r - 1:width - r + 1] = grid_config.OBSTACLE
                filled_obstacles[r - 1:height - r + 1, width - r] = grid_config.OBSTACLE
                filled_obstacles[r:height - r, r:width - r] = obstacles

            obstacles = filled_obstacles

            starts_xy = [self._add_border_xy(pos, r) for pos in starts_xy]
            finishes_xy = [self._add_border_xy(pos, r) for pos in finishes_xy]

        starts_xy = self._lift_positions_to_layers(starts_xy)
        finishes_xy = self._lift_positions_to_layers(finishes_xy)

        if self.layered:
            filled_positions = np.zeros((self.config.height_levels,) + obstacles.shape[-2:], dtype=np.int32)
            for x, y, z in starts_xy:
                filled_positions[z, x, y] = 1
        else:
            filled_positions = np.zeros(obstacles.shape, dtype=np.int32)
            for x, y in starts_xy:
                filled_positions[x, y] = 1

        self.obstacles = obstacles
        self.positions = filled_positions
        self.finishes_xy = finishes_xy
        self.positions_xy = starts_xy
        self._initial_xy = deepcopy(starts_xy)
        self.is_active = {agent_id: True for agent_id in range(self.config.num_agents)}

    @staticmethod
    def _obstacle_at(obstacles, x, y, z=None):
        if obstacles.ndim == 3:
            if z is None:
                return obstacles[:, x, y].max()
            return obstacles[z, x, y]
        return obstacles[x, y]

    @staticmethod
    def _clear_obstacle_cell(obstacles, x, y, z=None):
        if obstacles.ndim == 3:
            if z is None:
                obstacles[:, x, y] = 0
            else:
                obstacles[z, x, y] = 0
            return
        obstacles[x, y] = 0

    def _add_border_xy(self, pos, radius):
        if len(pos) >= 3:
            x, y, z = pos
            return (x + radius, y + radius, z)
        x, y = pos
        return (x + radius, y + radius)

    def _lift_positions_to_layers(self, positions):
        if not self.layered:
            return [tuple(pos[:2]) if len(pos) >= 2 else tuple(pos) for pos in positions]

        layered_positions = []
        for pos in positions:
            if len(pos) >= 3:
                x, y, z = pos[:3]
            else:
                x, y = pos[:2]
                z = int(self.rnd.integers(self.config.height_levels))
            layered_positions.append((int(x), int(y), int(np.clip(z, 0, self.config.height_levels - 1))))
        return layered_positions

    def _split_position(self, pos):
        if self.layered:
            x, y, z = pos
            return int(x), int(y), int(z)
        x, y = pos
        return int(x), int(y), 0

    def get_obstacles(self, ignore_borders=False):
        gc = self.config
        if ignore_borders:
            if self.obstacles.ndim == 3:
                return self.obstacles[:, gc.obs_radius:-gc.obs_radius, gc.obs_radius:-gc.obs_radius].copy()
            return self.obstacles[gc.obs_radius:-gc.obs_radius, gc.obs_radius:-gc.obs_radius].copy()
        return self.obstacles.copy()

    @staticmethod
    def _cut_borders_xy(positions, obs_radius):
        result = []
        for pos in positions:
            if len(pos) >= 3:
                x, y, z = pos
                result.append([x - obs_radius, y - obs_radius, z])
            else:
                x, y = pos
                result.append([x - obs_radius, y - obs_radius])
        return result

    @staticmethod
    def _filter_inactive(pos, active_flags):
        return [pos for idx, pos in enumerate(pos) if active_flags[idx]]

    def get_grid_config(self):
        return deepcopy(self.config)

    def _prepare_positions(self, positions, only_active, ignore_borders):
        gc = self.config

        if only_active:
            positions = self._filter_inactive(positions, [idx for idx, active in self.is_active.items() if active])

        if ignore_borders:
            positions = self._cut_borders_xy(positions, gc.obs_radius)

        return positions

    def get_agents_xy(self, only_active=False, ignore_borders=False):
        return self._prepare_positions(deepcopy(self.positions_xy), only_active, ignore_borders)

    @staticmethod
    def to_relative(coordinates, offset):
        result = deepcopy(coordinates)
        for idx, _ in enumerate(result):
            if len(result[idx]) >= 3:
                x, y, z = result[idx]
                dx, dy, dz = offset[idx]
                result[idx] = x - dx, y - dy, z - dz
            else:
                x, y = result[idx]
                dx, dy = offset[idx]
                result[idx] = x - dx, y - dy
        return result

    def get_agents_xy_relative(self):
        return self.to_relative(self.positions_xy, self._initial_xy)

    def get_targets_xy_relative(self):
        return self.to_relative(self.finishes_xy, self._initial_xy)

    def get_targets_xy(self, only_active=False, ignore_borders=False):
        return self._prepare_positions(deepcopy(self.finishes_xy), only_active, ignore_borders)

    def _normalize_coordinates(self, coordinates):
        gc = self.config

        x, y = coordinates[:2]

        x -= gc.obs_radius
        y -= gc.obs_radius

        x /= gc.size - 1
        y /= gc.size - 1

        if len(coordinates) >= 3:
            z = coordinates[2]
            denom = max(gc.height_levels - 1, 1)
            return x, y, z / denom
        return x, y

    def get_state(self, ignore_borders=False, as_dict=False):
        agents_xy = list(map(self._normalize_coordinates, self.get_agents_xy(ignore_borders)))
        targets_xy = list(map(self._normalize_coordinates, self.get_targets_xy(ignore_borders)))

        obstacles = self.get_obstacles(ignore_borders)

        if as_dict:
            return {"obstacles": obstacles, "agents_xy": agents_xy, "targets_xy": targets_xy}

        return np.concatenate(list(map(lambda x: np.array(x).flatten(), [agents_xy, targets_xy, obstacles])))

    def get_observation_shape(self):
        full_radius = self.config.obs_radius * 2 + 1
        if self.layered:
            return self.config.height_levels * 2, full_radius, full_radius
        return 2, full_radius, full_radius

    def get_num_actions(self):
        return len(self.config.get_action_deltas())

    def get_obstacles_for_agent(self, agent_id):
        x, y, _ = self._split_position(self.positions_xy[agent_id])
        r = self.config.obs_radius
        if self.obstacles.ndim == 3:
            return self.obstacles[:, x - r:x + r + 1, y - r:y + r + 1].astype(np.float32)
        window = self.obstacles[x - r:x + r + 1, y - r:y + r + 1].astype(np.float32)
        if self.layered:
            return np.repeat(window[None], self.config.height_levels, axis=0)
        return window

    def get_positions(self, agent_id):
        x, y, _ = self._split_position(self.positions_xy[agent_id])
        r = self.config.obs_radius
        if self.layered:
            return self.positions[:, x - r:x + r + 1, y - r:y + r + 1].astype(np.float32)
        return self.positions[x - r:x + r + 1, y - r:y + r + 1].astype(np.float32)

    def get_target(self, agent_id):

        x, y, z = self._split_position(self.positions_xy[agent_id])
        fx, fy, fz = self._split_position(self.finishes_xy[agent_id])
        if x == fx and y == fy and z == fz:
            return (0.0, 0.0, 0.0) if self.layered else (0.0, 0.0)
        rx, ry, rz = fx - x, fy - y, fz - z
        dist = np.sqrt(rx ** 2 + ry ** 2 + rz ** 2) if self.layered else np.sqrt(rx ** 2 + ry ** 2)
        if self.layered:
            return rx / dist, ry / dist, rz / dist
        return rx / dist, ry / dist

    def get_square_target(self, agent_id):
        c = self.config
        full_size = self.config.obs_radius * 2 + 1
        if self.layered:
            result = np.zeros((c.height_levels, full_size, full_size))
            x, y, z = self._split_position(self.positions_xy[agent_id])
            fx, fy, fz = self._split_position(self.finishes_xy[agent_id])
            dx, dy = x - fx, y - fy
            dx = min(dx, c.obs_radius) if dx >= 0 else max(dx, -c.obs_radius)
            dy = min(dy, c.obs_radius) if dy >= 0 else max(dy, -c.obs_radius)
            target_layer = int(np.clip(fz, 0, c.height_levels - 1))
            result[target_layer, c.obs_radius - dx, c.obs_radius - dy] = 1
            return result.astype(np.float32)

        result = np.zeros((full_size, full_size))
        x, y, _ = self._split_position(self.positions_xy[agent_id])
        fx, fy, _ = self._split_position(self.finishes_xy[agent_id])
        dx, dy = x - fx, y - fy

        dx = min(dx, c.obs_radius) if dx >= 0 else max(dx, -c.obs_radius)
        dy = min(dy, c.obs_radius) if dy >= 0 else max(dy, -c.obs_radius)
        result[c.obs_radius - dx, c.obs_radius - dy] = 1
        return result.astype(np.float32)

    def render(self, mode='human'):
        outfile = StringIO() if mode == 'ansi' else sys.stdout
        chars = string.digits + string.ascii_letters + string.punctuation
        obstacle_projection = self.obstacles.max(axis=0) if self.obstacles.ndim == 3 else self.obstacles
        positions_map = {}
        finishes_map = {}
        for id_, pos in enumerate(self.positions_xy):
            if not self.is_active[id_]:
                continue
            x, y, _ = self._split_position(pos)
            positions_map[(x, y)] = id_
        for id_, pos in enumerate(self.finishes_xy):
            if not self.is_active[id_]:
                continue
            x, y, _ = self._split_position(pos)
            finishes_map[(x, y)] = id_
        for line_index, line in enumerate(obstacle_projection):
            out = ''
            for cell_index, cell in enumerate(line):
                if cell == self.config.FREE:
                    agent_id = positions_map.get((line_index, cell_index), None)
                    finish_id = finishes_map.get((line_index, cell_index), None)

                    if agent_id is not None:
                        out += str(utils.colorize(' ' + chars[agent_id % len(chars)] + ' ', color='red', bold=True,
                                                  highlight=False))
                    elif finish_id is not None:
                        out += str(
                            utils.colorize('|' + chars[finish_id % len(chars)] + '|', 'white', highlight=False))
                    else:
                        out += str(utils.colorize(str(' . '), 'white', highlight=False))
                else:
                    out += str(utils.colorize(str('   '), 'cyan', bold=False, highlight=True))
            out += '\n'
            outfile.write(out)

        if mode != 'human':
            with closing(outfile):
                return outfile.getvalue()

    def move_agent_to_cell(self, agent_id, x, y):
        pos = self.positions_xy[agent_id]
        if self.layered:
            z = pos[2]
            if self.positions[z, pos[0], pos[1]] == self.config.FREE:
                raise KeyError("Agent {} is not in the map".format(agent_id))
            self.positions[z, pos[0], pos[1]] = self.config.FREE
            if self._obstacle_at(self.obstacles, x, y, z if self.obstacles.ndim == 3 else None) != self.config.FREE or self.positions[z, x, y] != self.config.FREE:
                raise ValueError(f"Can't force agent to blocked position {x} {y} on layer {z}")
            self.positions_xy[agent_id] = (x, y, z)
            self.positions[z, x, y] = self.config.OBSTACLE
            return
        if self.positions[self.positions_xy[agent_id]] == self.config.FREE:
            raise KeyError("Agent {} is not in the map".format(agent_id))
        self.positions[self.positions_xy[agent_id]] = self.config.FREE
        if self.obstacles[x, y] != self.config.FREE or self.positions[x, y] != self.config.FREE:
            raise ValueError(f"Can't force agent to blocked position {x} {y}")
        self.positions_xy[agent_id] = x, y
        self.positions[self.positions_xy[agent_id]] = self.config.OBSTACLE

    def move(self, agent_id, action):
        # if collision: keep still
        if self.layered:
            x, y, z = self.positions_xy[agent_id]
            self.positions[z, x, y] = self.config.FREE

            dx, dy, dz = self.config.get_action_deltas()[action]
            nx, ny, nz = x + dx, y + dy, z + dz
            max_x = self.obstacles.shape[-2]
            max_y = self.obstacles.shape[-1]
            can_move = (
                0 <= nz < self.config.height_levels
                and 0 <= nx < max_x
                and 0 <= ny < max_y
                and self._obstacle_at(self.obstacles, nx, ny, nz if self.obstacles.ndim == 3 else None) == self.config.FREE
                and self.positions[nz, nx, ny] == self.config.FREE
            )
            if can_move:
                x, y, z = nx, ny, nz
            else:
                self.conflict += 1

            self.positions_xy[agent_id] = (x, y, z)
            self.positions[z, x, y] = self.config.OBSTACLE
            return

        x, y = self.positions_xy[agent_id]

        self.positions[x, y] = self.config.FREE

        dx, dy = self.config.get_action_deltas()[action]

        if self.obstacles[x + dx, y + dy] == self.config.FREE and self.positions[x + dx, y + dy] == self.config.FREE:
            x += dx
            y += dy
        else:
            self.conflict += 1

        self.positions_xy[agent_id] = (x, y)
        self.positions[x, y] = self.config.OBSTACLE

    def on_goal(self, agent_id):
        return self.positions_xy[agent_id] == self.finishes_xy[agent_id]

    def is_active(self, agent_id):
        return self.is_active[agent_id]

    def hide_agent(self, agent_id):
        if not self.is_active[agent_id]:
            return False
        self.is_active[agent_id] = False

        pos = self.positions_xy[agent_id]
        if self.layered:
            x, y, z = pos
            self.positions[z, x, y] = self.config.FREE
        else:
            self.positions[pos] = self.config.FREE

        return True

    def show_agent(self, agent_id):
        if self.is_active[agent_id]:
            return False

        self.is_active[agent_id] = True
        pos = self.positions_xy[agent_id]
        if self.layered:
            x, y, z = pos
            if self.positions[z, x, y] == self.config.OBSTACLE:
                raise KeyError("The cell is already occupied")
            self.positions[z, x, y] = self.config.OBSTACLE
        else:
            if self.positions[pos] == self.config.OBSTACLE:
                raise KeyError("The cell is already occupied")
            self.positions[pos] = self.config.OBSTACLE
        return True


class GridLifeLong(Grid):
    def __init__(self, grid_config: GridConfig, add_artificial_border: bool = True, num_retries=10):

        super().__init__(grid_config, add_artificial_border, num_retries)

        self.component_to_points, self.point_to_component = get_components(grid_config, self.obstacles,
                                                                           self.positions_xy, self.finishes_xy)

        for i in range(len(self.positions_xy)):
            position, target = self.positions_xy[i], self.finishes_xy[i]
            if self.obstacles.ndim == 3:
                position_key = tuple(position[:3])
                target_key = tuple(target[:3])
            else:
                position_key = tuple(position[:2])
                target_key = tuple(target[:2])
            if self.point_to_component[position_key] != self.point_to_component[target_key]:
                warnings.warn(f"The start point ({position[0]}, {position[1]}) and the goal"
                              f" ({target[0]}, {target[1]}) are in different components. The goal is changed.",
                              Warning, stacklevel=2)
                new_target_xy = generate_new_target(grid_config, self.point_to_component,
                                                    self.component_to_points, position_key)
                if self.obstacles.ndim == 3:
                    self.finishes_xy[i] = new_target_xy
                elif self.layered:
                    self.finishes_xy[i] = (new_target_xy[0], new_target_xy[1], target[2])
                else:
                    self.finishes_xy[i] = new_target_xy


class CooperativeGrid(Grid):
    def __init__(self, grid_config: GridConfig, add_artificial_border: bool = True, num_retries=10):
        super().__init__(grid_config, add_artificial_border, num_retries)

    def move(self, agent_id, action):
        if self.layered:
            return super().move(agent_id, action)
        x, y = self.positions_xy[agent_id]
        dx, dy = self.config.get_action_deltas()[action]
        if self.obstacles[x + dx, y + dy] == self.config.FREE:
            if self.positions[x + dx, y + dy] == self.config.FREE:
                self.positions[x, y] = self.config.FREE
                x += dx
                y += dy
                self.positions[x, y] = self.config.OBSTACLE
        self.positions_xy[agent_id] = (x, y)
