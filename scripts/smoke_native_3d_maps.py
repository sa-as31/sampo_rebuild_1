import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.SMAPO import SMAPOWrapper
from env.create_env import create_env
from env.custom_maps import MAPS_REGISTRY
from learning.learning_config import DMAPFConfig, Environment


def unwrap_wrapper(env, wrapper_type):
    current = env
    while current is not None:
        if isinstance(current, wrapper_type):
            return current
        current = getattr(current, "env", None)
    raise RuntimeError(f"Could not find wrapper {wrapper_type.__name__}")


def validate_map(map_name, map_definition):
    layer_rows = map_definition["layers"][0].splitlines()
    expected_size = len(layer_rows)
    expected_levels = len(map_definition["layers"])

    env_cfg = Environment(
        use_maps=True,
        target_num_agents=None,
        grid_config=DMAPFConfig(
            num_agents=12,
            obs_radius=5,
            max_episode_steps=64,
            map_name=map_name,
        ),
    )

    env = create_env(env_cfg, auto_reset=False)
    obs = env.reset()
    smapo = unwrap_wrapper(env, SMAPOWrapper)
    planner_agent = smapo.re_plan._agent
    global_obstacles = np.asarray(env.get_obstacles(ignore_borders=True))
    positions = env.get_agents_xy()

    assert global_obstacles.shape == (expected_levels, expected_size, expected_size), global_obstacles.shape
    assert isinstance(planner_agent.obstacles, np.ndarray), type(planner_agent.obstacles)
    assert planner_agent.obstacles.shape == (
        expected_levels,
        expected_size + 10,
        expected_size + 10,
    ), planner_agent.obstacles.shape
    assert len(positions[0]) == 3, positions[0]
    assert env.grid.config.height_levels == expected_levels, env.grid.config.height_levels
    assert env.grid.config.native_3d_obstacles is True
    assert np.any(global_obstacles[0] != global_obstacles[-1]), "3D map layers should differ"
    assert np.sum(global_obstacles) > 0, "Expected occupied cells in native 3D map"
    assert sum(len(path) > 1 for path in smapo.re_plan.get_path()) > 0
    assert obs[0]["obs"].shape[1:] == (11, 11), obs[0]["obs"].shape

    return {
        "map_name": map_name,
        "shape": tuple(int(v) for v in global_obstacles.shape),
        "occupied_cells": int(np.sum(global_obstacles)),
        "agent_position_example": positions[0],
    }


def main():
    native_map_names = sorted(name for name in MAPS_REGISTRY if name.startswith("native3d-demo-"))
    assert len(native_map_names) == 9, native_map_names

    summaries = []
    for map_name in native_map_names:
        summaries.append(validate_map(map_name, MAPS_REGISTRY[map_name]))

    print("native_3d_maps_smoke_ok")
    print(f"native_map_count={len(summaries)}")
    for summary in summaries:
        print(
            f"{summary['map_name']}: shape={summary['shape']}, "
            f"occupied_cells={summary['occupied_cells']}, "
            f"agent_position_example={summary['agent_position_example']}"
        )


if __name__ == "__main__":
    main()
