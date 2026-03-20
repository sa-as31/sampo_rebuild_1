import time
from collections import defaultdict, deque

import numpy as np

from pogema import GridConfig

try:
    import pyoctomap
except ImportError:  # pragma: no cover - optional dependency
    pyoctomap = None


def _is_3d_grid(grid):
    return len(grid.shape) == 3


def _iter_free_cells(grid):
    if _is_3d_grid(grid):
        levels, height, width = grid.shape
        for z in range(levels):
            for x in range(height):
                for y in range(width):
                    yield x, y, z
        return
    height, width = grid.shape
    for x in range(height):
        for y in range(width):
            yield x, y


def _grid_get(grid, position):
    if _is_3d_grid(grid):
        x, y, z = position
        return grid[z, x, y]
    x, y = position
    return grid[x, y]


def _grid_set(grid, position, value):
    if _is_3d_grid(grid):
        x, y, z = position
        grid[z, x, y] = value
        return
    x, y = position
    grid[x, y] = value


def _grid_shape_xy(grid):
    if _is_3d_grid(grid):
        _, height, width = grid.shape
        return height, width
    return grid.shape


def _grid_levels(grid):
    return int(grid.shape[0]) if _is_3d_grid(grid) else 1


def _in_bounds(grid, position):
    height, width = _grid_shape_xy(grid)
    if _is_3d_grid(grid):
        x, y, z = position
        return 0 <= z < _grid_levels(grid) and 0 <= x < height and 0 <= y < width
    x, y = position
    return 0 <= x < height and 0 <= y < width


def _neighbor_positions(position, moves):
    if len(position) == 3:
        x, y, z = position
        for dx, dy, dz in moves:
            if dx == dy == dz == 0:
                continue
            yield x + dx, y + dy, z + dz
        return
    x, y = position
    for dx, dy in moves:
        if dx == dy == 0:
            continue
        yield x + dx, y + dy


def _get_connectivity_moves(grid, grid_config):
    if _is_3d_grid(grid):
        return tuple(tuple(int(v) for v in move) for move in grid_config.get_action_deltas())
    return tuple(tuple(int(v) for v in move[:2]) for move in grid_config.MOVES)


def _label_connected_components(grid, moves, start_id, free_cell):
    q = deque()
    current_id = start_id
    components = [0 for _ in range(start_id)]

    for position in _iter_free_cells(grid):
        if _grid_get(grid, position) != free_cell:
            continue
        _grid_set(grid, position, current_id)
        components.append(1)
        q.append(position)

        while q:
            pos = q.popleft()
            for nxt in _neighbor_positions(pos, moves):
                if not _in_bounds(grid, nxt):
                    continue
                if _grid_get(grid, nxt) != free_cell:
                    continue
                _grid_set(grid, nxt, current_id)
                components[current_id] += 1
                q.append(nxt)

        current_id += 1
    return components


def generate_obstacles_pyoctomap(grid_config: GridConfig, rnd=None):
    if pyoctomap is None:
        raise ImportError("pyoctomap is not installed. Install it or switch obstacle_backend back to 'numpy'.")

    if rnd is None:
        rnd = np.random.default_rng(grid_config.seed)

    occupancy = rnd.binomial(
        1,
        grid_config.density,
        (grid_config.height_levels, grid_config.size, grid_config.size),
    ).astype(np.int32)

    resolution = float(grid_config.octomap_resolution)
    tree = pyoctomap.OcTree(resolution)
    for z, x, y in np.argwhere(occupancy == grid_config.OBSTACLE):
        point = [
            (float(x) + 0.5) * resolution,
            (float(y) + 0.5) * resolution,
            (float(z) + 0.5) * resolution,
        ]
        tree.updateNode(point, True)

    dense = np.zeros_like(occupancy, dtype=np.int32)
    for z in range(grid_config.height_levels):
        for x in range(grid_config.size):
            for y in range(grid_config.size):
                point = [
                    (float(x) + 0.5) * resolution,
                    (float(y) + 0.5) * resolution,
                    (float(z) + 0.5) * resolution,
                ]
                node = tree.search(point)
                if node is not None and tree.isNodeOccupied(node):
                    dense[z, x, y] = grid_config.OBSTACLE
    return dense


def generate_obstacles(grid_config: GridConfig, rnd=None):
    if rnd is None:
        rnd = np.random.default_rng(grid_config.seed)
    if grid_config.is_native_3d_obstacles():
        if grid_config.obstacle_backend == 'pyoctomap':
            return generate_obstacles_pyoctomap(grid_config, rnd)
        return rnd.binomial(1, grid_config.density, (grid_config.height_levels, grid_config.size, grid_config.size))
    return rnd.binomial(1, grid_config.density, (grid_config.size, grid_config.size))


def generate_positions_and_targets(obstacles, grid_config: GridConfig):
    if _is_3d_grid(obstacles):
        return generate_positions_and_targets_fast(obstacles, grid_config)
    c = grid_config
    grid = obstacles.copy()
    q = []
    current_id = max(int(c.FREE), int(c.OBSTACLE)) + 1

    for x in range(c.size):
        for y in range(c.size):
            if grid[x, y] != c.FREE:
                continue
            grid[x, y] = current_id
            q.append((x, y))
            while len(q):
                cx, cy = q.pop(0)

                for dx, dy in c.MOVES:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < c.size and 0 <= ny < c.size:
                        if grid[nx, ny] == c.FREE:
                            grid[nx, ny] = current_id
                            q.append((nx, ny))

            current_id += 1
    xy_to_id = dict()
    id_to_xy = defaultdict(set)
    for x in range(len(grid)):
        for y in range(len(grid[x])):
            if grid[x, y] != c.OBSTACLE:
                xy_to_id[x, y] = grid[x, y]
                id_to_xy[grid[x, y]].add((x, y))
    order = list(xy_to_id.keys())
    np.random.default_rng(c.seed).shuffle(order)

    requests = defaultdict(set)
    done_requests = 0
    positions_xy = []
    finishes_xy = [(-1, -1) for _ in range(c.num_agents)]
    for x, y in order:
        if (x, y) not in xy_to_id:
            continue

        # remove cell
        id_ = xy_to_id.pop((x, y))
        id_to_xy[id_].remove((x, y))

        # deal with requests first
        if requests[id_]:
            finishes_xy[requests[id_].pop()] = x, y
            done_requests += 1
            continue

        # no empty space so skip
        if not len(id_to_xy[id_]):
            continue

        if len(positions_xy) >= c.num_agents:
            if done_requests >= c.num_agents:
                break
            continue

        # add start position and request finish for it
        requests[id_].add(len(positions_xy))
        positions_xy.append((x, y))
    return positions_xy, finishes_xy


def bfs(grid, moves, size, start_id, free_cell):
    if _is_3d_grid(grid):
        return _label_connected_components(grid, moves, start_id, free_cell)
    q = []
    current_id = start_id

    components = [0 for _ in range(start_id)]

    size_x = len(grid)
    size_y = len(grid[0])

    for x in range(size_x):
        for y in range(size_y):
            if grid[x, y] != free_cell:
                continue
            grid[x, y] = current_id
            components.append(1)
            q.append((x, y))

            while len(q):
                cx, cy = q.pop(0)

                for dx, dy in moves:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < size_x and 0 <= ny < size_y:
                        if grid[nx, ny] == free_cell:
                            grid[nx, ny] = current_id
                            components[current_id] += 1
                            q.append((nx, ny))

            current_id += 1
    return components


def placing_fast(order, components, grid, start_id, num_agents):
    link_to_next = [-1 for _ in range(len(order))]
    colors = [-1 for _ in range(len(components))]
    size = len(order)
    for index in range(size):
        reversed_index = len(order) - index - 1
        color = _grid_get(grid, order[reversed_index])
        link_to_next[reversed_index] = colors[color]
        colors[color] = reversed_index

    positions_xy = []
    finishes_xy = []

    for index in range(len(order)):
        next_index = link_to_next[index]
        if next_index == -1:
            continue

        positions_xy.append(order[index])
        finishes_xy.append(order[next_index])

        link_to_next[next_index] = -1
        if len(finishes_xy) >= num_agents:
            break
    return positions_xy, finishes_xy

def placing(order, components, grid, start_id, num_agents):
    requests = [[] for _ in range(len(components))]
    done_requests = 0
    positions_xy = []
    finishes_xy = [(-1, -1) for _ in range(num_agents)]
    sample_pos = order[0] if order else None
    if sample_pos is not None and len(sample_pos) == 3:
        finishes_xy = [(-1, -1, -1) for _ in range(num_agents)]

    for position in order:
        if _grid_get(grid, position) < start_id:
            continue

        id_ = _grid_get(grid, position)
        _grid_set(grid, position, 0)

        if requests[id_]:
            tt = requests[id_].pop()
            finishes_xy[tt] = position
            done_requests += 1
            continue

        if len(positions_xy) >= num_agents:
            if done_requests >= num_agents:
                break
            continue

        if components[id_] >= 2:
            components[id_] -= 2
            requests[id_].append(len(positions_xy))
            positions_xy.append(position)

    return positions_xy, finishes_xy


def generate_positions_and_targets_fast(obstacles, grid_config):
    c = grid_config
    grid = obstacles.copy()

    start_id = max(c.FREE, c.OBSTACLE) + 1

    moves = _get_connectivity_moves(grid, c)
    components = bfs(grid, moves, c.size, start_id, free_cell=c.FREE)
    if _is_3d_grid(obstacles):
        levels, height, width = obstacles.shape
        order = [(x, y, z) for z in range(levels) for x in range(height) for y in range(width)
                 if grid[z, x, y] >= start_id]
    else:
        height, width = obstacles.shape
        order = [(x, y) for x in range(height) for y in range(width) if grid[x, y] >= start_id]
    np.random.default_rng(c.seed).shuffle(order)
    return placing(order=order, components=components, grid=grid, start_id=start_id, num_agents=c.num_agents)


def generate_new_target(rnd_generator, point_to_component, component_to_points, position):

    component_id = point_to_component[position]
    component = component_to_points[component_id]
    new_target = tuple(*rnd_generator.choice(component, 1))

    return new_target


def get_components(grid_config, obstacles, positions_xy, target_xy):
    c = grid_config
    grid = obstacles.copy()

    start_id = max(c.FREE, c.OBSTACLE) + 1
    moves = _get_connectivity_moves(grid, c)
    components = bfs(grid, moves, c.size, start_id, free_cell=c.FREE)

    comp_to_points = defaultdict(list)
    point_to_comp = {}
    if _is_3d_grid(obstacles):
        levels, height, width = obstacles.shape
        for z in range(levels):
            for x in range(height):
                for y in range(width):
                    comp_to_points[grid[z, x, y]].append((x, y, z))
                    point_to_comp[(x, y, z)] = grid[z, x, y]
    else:
        height, width = obstacles.shape
        for x in range(height):
            for y in range(width):
                comp_to_points[grid[x, y]].append((x, y))
                point_to_comp[(x, y)] = grid[x, y]
    return comp_to_points, point_to_comp


def time_it(func, num_iterations):
    start = time.monotonic()
    for index in range(num_iterations):
        grid_config = GridConfig(num_agents=64, size=64, seed=index)
        obstacles = generate_obstacles(grid_config)
        result = func(obstacles, grid_config, )
        if index == 0 and num_iterations > 1:
            print(result)
    finish = time.monotonic()

    return finish - start


def main():
    num_iterations = 1000
    time_it(generate_positions_and_targets, num_iterations=1)
    time_it(generate_positions_and_targets_fast, num_iterations=1)
    print('fast:', time_it(generate_positions_and_targets_fast, num_iterations=num_iterations))
    print('slow:', time_it(generate_positions_and_targets, num_iterations=num_iterations))


if __name__ == '__main__':
    main()
