import sys
from pathlib import Path
from typing import Optional, Union

import numpy as np
from pydantic import BaseModel, validator

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

try:
    import pyoctomap
except ImportError:  # pragma: no cover - optional dependency
    pyoctomap = None


class GridConfig(BaseModel, ):
    FREE: Literal[0] = 0
    OBSTACLE: Literal[1] = 1
    MOVES: list = [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1], ]
    MOVES_2P5D: list = [[0, 0, 0], [-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0], [0, 0, 1], [0, 0, -1]]
    on_target: Literal['finish', 'nothing', 'restart'] = 'finish'
    seed: Optional[int] = None
    size: int = 8
    density: float = 0.3
    num_agents: int = 1
    obs_radius: int = 5
    height_levels: int = 1
    native_3d_obstacles: bool = False
    obstacle_backend: Literal['numpy', 'pyoctomap'] = 'numpy'
    octomap_resolution: float = 1.0
    agents_xy: Optional[list] = None
    targets_xy: Optional[list] = None
    collision_system: Literal['block_both', 'priority'] = 'priority'
    persistent: bool = False
    observation_type: Literal['POMAPF', 'MAPF', 'default'] = 'default'
    map: Union[list, str, dict] = None

    empty_outside: bool = True

    map_name: str = None

    integration: Literal['SampleFactory', 'PyMARL', 'rllib', 'gym', 'PettingZoo'] = None
    max_episode_steps: int = 64
    auto_reset: Optional[bool] = None

    @validator('seed')
    def seed_initialization(cls, v):
        assert v is None or (0 <= v < sys.maxsize), "seed must be in [0, " + str(sys.maxsize) + ']'
        return v

    @validator('size')
    def size_restrictions(cls, v):
        assert 2 <= v <= 1024, "size must be in [2, 1024]"
        return v

    @validator('density')
    def density_restrictions(cls, v):
        assert 0.0 <= v <= 1, "density must be in [0, 1]"
        return v

    @validator('num_agents')
    def num_agents_must_be_positive(cls, v):
        assert 1 <= v <= 10000, "num_agents must be in [1, 10000]"
        return v

    @validator('obs_radius')
    def obs_radius_must_be_positive(cls, v):
        assert 1 <= v <= 128, "obs_radius must be in [1, 128]"
        return v

    @validator('height_levels')
    def height_levels_must_be_positive(cls, v):
        assert 1 <= v <= 32, "height_levels must be in [1, 32]"
        return v

    @validator('octomap_resolution')
    def octomap_resolution_must_be_positive(cls, v):
        assert float(v) > 0.0, "octomap_resolution must be positive"
        return float(v)

    @validator('map', always=True)
    def map_validation(cls, v, values, ):
        if v is None:
            return None
        agents_xy = None
        targets_xy = None
        if isinstance(v, (str, dict)):
            v, agents_xy, targets_xy = cls.parse_map_to_list(v, values['FREE'], values['OBSTACLE'])
        elif cls.is_3d_map(v):
            cls.validate_layer_shapes(v)
        if agents_xy and targets_xy and values['agents_xy'] is not None and values['targets_xy'] is not None:
            raise KeyError("""Can't create task. Please provide agents_xy and targets_xy only ones.
                Either with parameters or with a map.""")
        elif agents_xy and targets_xy:
            values['agents_xy'] = agents_xy
            values['targets_xy'] = targets_xy
            values['num_agents'] = len(agents_xy)
        size, area, obstacle_sum, height_levels = cls.get_map_stats(v)
        values['size'] = size
        values['density'] = obstacle_sum / area if area else 0.0
        if height_levels > 1:
            configured_height_levels = int(values.get('height_levels', 1))
            if configured_height_levels not in (1, height_levels):
                raise ValueError(
                    f"3D map has {height_levels} layers, but height_levels={configured_height_levels} was requested."
                )
            values['height_levels'] = height_levels
            values['native_3d_obstacles'] = True
        if agents_xy is not None:
            cls.check_positions(agents_xy, values['size'], values.get('height_levels', 1))
        if targets_xy is not None:
            cls.check_positions(targets_xy, values['size'], values.get('height_levels', 1))
        return v

    @validator('agents_xy')
    def agents_xy_validation(cls, v, values):
        if v is not None:
            cls.check_positions(v, values['size'], values.get('height_levels', 1))
            values['num_agents'] = len(v)
        return v

    @validator('targets_xy')
    def targets_xy_validation(cls, v, values):
        if v is not None:
            cls.check_positions(v, values['size'], values.get('height_levels', 1))
            values['num_agents'] = len(v)
        return v

    @staticmethod
    def check_positions(v, size, height_levels=1):
        for position in v:
            if len(position) not in (2, 3):
                raise IndexError("Position must contain either 2 or 3 coordinates!")
            x, y = position[:2]
            if not (0 <= x < size and 0 <= y < size):
                raise IndexError("Position is out of bounds!")
            if len(position) == 3:
                z = position[2]
                if not (0 <= z < height_levels):
                    raise IndexError("Layer index is out of bounds!")

    @staticmethod
    def str_map_to_list(str_map, free, obstacle):
        obstacles = []
        agents = {}
        targets = {}
        for idx, line in enumerate(str_map.split()):
            row = []
            for char in line:
                if char == '.':
                    row.append(free)
                elif char == '#':
                    row.append(obstacle)
                elif 'A' <= char <= 'Z':
                    targets[char.lower()] = len(obstacles), len(row)
                    row.append(free)
                elif 'a' <= char <= 'z':
                    agents[char.lower()] = len(obstacles), len(row)
                    row.append(free)
                else:
                    raise KeyError(f"Unsupported symbol '{char}' at line {idx}")
            if row:
                if obstacles:
                    assert len(obstacles[-1]) == len(row), f"Wrong string size for row {idx};"
                obstacles.append(row)

        targets_xy = []
        agents_xy = []
        for _, (x, y) in sorted(agents.items()):
            agents_xy.append([x, y])
        for _, (x, y) in sorted(targets.items()):
            targets_xy.append([x, y])

        assert len(targets_xy) == len(agents_xy)
        return obstacles, agents_xy, targets_xy

    @classmethod
    def parse_map_to_list(cls, map_definition, free, obstacle):
        if isinstance(map_definition, str):
            return cls.str_map_to_list(map_definition, free, obstacle)
        if isinstance(map_definition, dict):
            return cls.dict_map_to_list(map_definition, free, obstacle)
        raise TypeError(f"Unsupported map definition type: {type(map_definition).__name__}")

    @classmethod
    def dict_map_to_list(cls, map_definition, free, obstacle):
        if map_definition.get('octomap_file'):
            return cls.octomap_file_to_list(map_definition, free, obstacle)

        layers = map_definition.get('layers')
        if not layers:
            raise KeyError("3D map definitions must include a non-empty 'layers' field.")

        parsed_layers = []
        embedded_agents_xy = []
        embedded_targets_xy = []
        used_embedded_positions = False

        for z, layer in enumerate(layers):
            layer_grid, layer_agents_xy, layer_targets_xy = cls.parse_layer_to_list(layer, free, obstacle)
            parsed_layers.append(layer_grid)
            if layer_agents_xy or layer_targets_xy:
                used_embedded_positions = True
            embedded_agents_xy.extend([[x, y, z] for x, y in layer_agents_xy])
            embedded_targets_xy.extend([[x, y, z] for x, y in layer_targets_xy])

        cls.validate_layer_shapes(parsed_layers)

        explicit_agents_xy = map_definition.get('agents_xy')
        explicit_targets_xy = map_definition.get('targets_xy')
        if explicit_agents_xy is not None or explicit_targets_xy is not None:
            if used_embedded_positions:
                raise KeyError("3D map definitions cannot mix embedded agent markers with explicit agents_xy/targets_xy.")
            if explicit_agents_xy is None or explicit_targets_xy is None:
                raise KeyError("3D map definitions must provide both agents_xy and targets_xy together.")
            if len(explicit_agents_xy) != len(explicit_targets_xy):
                raise KeyError("3D map definitions must provide the same number of agents_xy and targets_xy.")
            embedded_agents_xy = [list(position[:3]) for position in explicit_agents_xy]
            embedded_targets_xy = [list(position[:3]) for position in explicit_targets_xy]

        if len(embedded_agents_xy) != len(embedded_targets_xy):
            raise KeyError("3D map definitions must provide the same number of agent and target positions.")

        return parsed_layers, embedded_agents_xy, embedded_targets_xy

    @classmethod
    def octomap_file_to_list(cls, map_definition, free, obstacle):
        if pyoctomap is None:
            raise ImportError("pyoctomap is required to load octomap_file-based 3D maps.")

        octomap_file = cls.resolve_octomap_path(map_definition['octomap_file'])
        if not octomap_file.exists():
            raise FileNotFoundError(f"OctoMap asset not found: {octomap_file}")

        initial_resolution = float(map_definition.get('tree_resolution', 0.1))
        tree = pyoctomap.OcTree(initial_resolution)

        if octomap_file.suffix == '.bt':
            loaded = tree.readBinary(str(octomap_file))
        else:
            loaded = tree.read(str(octomap_file))
        if not loaded:
            raise RuntimeError(f"Failed to load OctoMap asset from {octomap_file}")

        metric_min = np.array(map_definition.get('metric_min', tree.getMetricMin()), dtype=np.float32)
        metric_max = np.array(map_definition.get('metric_max', tree.getMetricMax()), dtype=np.float32)
        voxel_size = float(map_definition.get('voxel_size', tree.getResolution()))

        extents = np.maximum(metric_max - metric_min, voxel_size)
        width = int(map_definition.get('width', int(np.ceil(extents[0] / voxel_size))))
        height = int(map_definition.get('height', int(np.ceil(extents[1] / voxel_size))))
        levels = int(map_definition.get('height_levels', int(np.ceil(extents[2] / voxel_size))))
        if width <= 0 or height <= 0 or levels <= 0:
            raise ValueError("Resolved OctoMap grid dimensions must all be positive.")

        dense = np.zeros((levels, height, width), dtype=np.int32)
        for z in range(levels):
            metric_z = float(metric_min[2] + (z + 0.5) * voxel_size)
            for x in range(height):
                metric_x = float(metric_min[0] + (x + 0.5) * voxel_size)
                for y in range(width):
                    metric_y = float(metric_min[1] + (y + 0.5) * voxel_size)
                    node = tree.search([metric_x, metric_y, metric_z])
                    if node is not None and tree.isNodeOccupied(node):
                        dense[z, x, y] = int(obstacle)

        return dense.tolist(), map_definition.get('agents_xy', []), map_definition.get('targets_xy', [])

    @staticmethod
    def resolve_octomap_path(octomap_path):
        path = Path(octomap_path)
        if path.is_absolute():
            return path
        return Path(__file__).resolve().parents[1] / path

    @classmethod
    def parse_layer_to_list(cls, layer_definition, free, obstacle):
        if isinstance(layer_definition, str):
            return cls.str_map_to_list(layer_definition, free, obstacle)
        if not isinstance(layer_definition, list):
            raise TypeError(
                f"Unsupported 3D map layer type: {type(layer_definition).__name__}. "
                "Expected string or list."
            )

        normalized_layer = []
        width = None
        for row_idx, row in enumerate(layer_definition):
            if not isinstance(row, list):
                raise TypeError("List-based 3D map layers must be lists of rows.")
            if width is None:
                width = len(row)
            elif width != len(row):
                raise ValueError(f"All rows inside a 3D map layer must have equal width; row {row_idx} mismatched.")
            normalized_row = []
            for cell in row:
                if cell not in (free, obstacle):
                    raise ValueError("Numeric 3D map layers may only contain FREE/OBSTACLE values.")
                normalized_row.append(int(cell))
            normalized_layer.append(normalized_row)
        return normalized_layer, [], []

    @staticmethod
    def validate_layer_shapes(layers):
        if not layers:
            raise ValueError("3D maps must contain at least one layer.")
        reference_height = len(layers[0])
        reference_width = len(layers[0][0]) if reference_height else 0
        for layer_idx, layer in enumerate(layers):
            if len(layer) != reference_height:
                raise ValueError(
                    f"3D map layers must share the same height; layer 0 has {reference_height}, "
                    f"layer {layer_idx} has {len(layer)}."
                )
            for row_idx, row in enumerate(layer):
                if len(row) != reference_width:
                    raise ValueError(
                        f"3D map layers must share the same width; layer {layer_idx}, row {row_idx} mismatched."
                    )

    @classmethod
    def get_map_stats(cls, map_definition):
        if cls.is_3d_map(map_definition):
            height_levels = len(map_definition)
            height = len(map_definition[0]) if height_levels else 0
            width = len(map_definition[0][0]) if height else 0
            area = max(height_levels * height * width, 1)
            obstacle_sum = sum(sum(sum(row) for row in layer) for layer in map_definition)
            return max(height, width), area, obstacle_sum, height_levels

        size = len(map_definition)
        area = 0
        obstacle_sum = 0
        for line in map_definition:
            size = max(size, len(line))
            area += len(line)
            obstacle_sum += sum(line)
        return size, max(area, 1), obstacle_sum, 1

    @staticmethod
    def is_3d_map(map_definition):
        return (
            isinstance(map_definition, list)
            and len(map_definition) > 0
            and isinstance(map_definition[0], list)
            and len(map_definition[0]) > 0
            and isinstance(map_definition[0][0], list)
        )

    def is_layered(self):
        return int(self.height_levels) > 1

    def is_native_3d_obstacles(self):
        return self.is_layered() and bool(self.native_3d_obstacles)

    def get_action_deltas(self):
        if self.is_layered():
            return self.MOVES_2P5D
        return self.MOVES


class PredefinedDifficultyConfig(GridConfig):
    density: float = 0.3
    collision_system: Literal['priority'] = 'priority'
    obs_radius: Literal[5] = 5
    observation_type: Literal['default'] = 'default'

    @validator('density', always=True)
    def density_restrictions(cls, v):
        assert 0.299999 <= v <= 0.3000001, "density for that predefined configuration must be equal to 0.3"
        return v


class Easy8x8(PredefinedDifficultyConfig):
    size: Literal[8] = 8
    max_episode_steps: Literal[64] = 64
    num_agents: Literal[1] = 1
    map_name: Literal['Easy8x8'] = 'Easy8x8'


class Normal8x8(PredefinedDifficultyConfig):
    size: Literal[8] = 8
    max_episode_steps: Literal[64] = 64
    num_agents: Literal[2] = 2
    map_name: Literal['Normal8x8'] = 'Normal8x8'


class Hard8x8(PredefinedDifficultyConfig):
    size: Literal[8] = 8
    max_episode_steps: Literal[64] = 64
    num_agents: Literal[4] = 4
    map_name: Literal['Hard8x8'] = 'Hard8x8'


class ExtraHard8x8(PredefinedDifficultyConfig):
    size: Literal[8] = 8
    max_episode_steps: Literal[64] = 64
    num_agents: Literal[8] = 8
    map_name: Literal['ExtraHard8x8'] = 'ExtraHard8x8'


class Easy16x16(PredefinedDifficultyConfig):
    size: Literal[16] = 16
    max_episode_steps: Literal[128] = 128
    num_agents: Literal[4] = 4
    map_name: Literal['Easy16x16'] = 'Easy16x16'


class Normal16x16(PredefinedDifficultyConfig):
    size: Literal[16] = 16
    max_episode_steps: Literal[128] = 128
    num_agents: Literal[8] = 8
    map_name: Literal['Normal16x16'] = 'Normal16x16'


class Hard16x16(PredefinedDifficultyConfig):
    size: Literal[16] = 16
    max_episode_steps: Literal[128] = 128
    num_agents: Literal[16] = 16
    map_name: Literal['Hard16x16'] = 'Hard16x16'


class ExtraHard16x16(PredefinedDifficultyConfig):
    size: Literal[16] = 16
    max_episode_steps: Literal[128] = 128
    num_agents: Literal[32] = 32
    map_name: Literal['ExtraHard16x16'] = 'ExtraHard16x16'


class Easy32x32(PredefinedDifficultyConfig):
    size: Literal[32] = 32
    max_episode_steps: Literal[256] = 256
    num_agents: Literal[16] = 16
    map_name: Literal['Easy32x32'] = 'Easy32x32'


class Normal32x32(PredefinedDifficultyConfig):
    size: Literal[32] = 32
    max_episode_steps: Literal[256] = 256
    num_agents: Literal[32] = 32
    map_name: Literal['Normal32x32'] = 'Normal32x32'


class Hard32x32(PredefinedDifficultyConfig):
    size: Literal[32] = 32
    max_episode_steps: Literal[256] = 256
    num_agents: Literal[64] = 64
    map_name: Literal['Hard32x32'] = 'Hard32x32'


class ExtraHard32x32(PredefinedDifficultyConfig):
    size: Literal[32] = 32
    max_episode_steps: Literal[256] = 256
    num_agents: Literal[128] = 128
    map_name: Literal['ExtraHard32x32'] = 'ExtraHard32x32'


class Easy64x64(PredefinedDifficultyConfig):
    size: Literal[32] = 64
    max_episode_steps: Literal[512] = 512
    num_agents: Literal[16] = 64
    map_name: Literal['Easy64x64'] = 'Easy64x64'


class Normal64x64(PredefinedDifficultyConfig):
    size: Literal[32] = 64
    max_episode_steps: Literal[512] = 512
    num_agents: Literal[16] = 128
    map_name: Literal['Normal64x64'] = 'Normal64x64'


class Hard64x64(PredefinedDifficultyConfig):
    size: Literal[32] = 64
    max_episode_steps: Literal[512] = 512
    num_agents: Literal[16] = 256
    map_name: Literal['Hard64x64'] = 'Hard64x64'


class ExtraHard64x64(PredefinedDifficultyConfig):
    size: Literal[32] = 64
    max_episode_steps: Literal[512] = 512
    num_agents: Literal[16] = 512
    map_name: Literal['ExtraHard64x64'] = 'ExtraHard64x64'
