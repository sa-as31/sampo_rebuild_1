import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.SMAPO import SMAPOWrapper
from env.create_env import create_env
from learning.learning_config import DMAPFConfig, Environment


def unwrap_wrapper(env, wrapper_type):
    current = env
    while current is not None:
        if isinstance(current, wrapper_type):
            return current
        current = getattr(current, "env", None)
    raise RuntimeError(f"Could not find wrapper {wrapper_type.__name__}")


def main():
    env_cfg = Environment(
        use_maps=True,
        target_num_agents=None,
        grid_config=DMAPFConfig(
            num_agents=12,
            obs_radius=5,
            max_episode_steps=64,
            map_name=r"octomap-geb079-demo",
        ),
    )

    env = create_env(env_cfg, auto_reset=False)
    obs = env.reset()
    smapo = unwrap_wrapper(env, SMAPOWrapper)
    planner_agent = smapo.re_plan._agent
    global_obstacles = np.asarray(env.get_obstacles(ignore_borders=True))
    positions = env.get_agents_xy()

    assert global_obstacles.shape == (7, 30, 78), global_obstacles.shape
    assert isinstance(planner_agent.obstacles, np.ndarray), type(planner_agent.obstacles)
    assert planner_agent.obstacles.shape == (7, 40, 88), planner_agent.obstacles.shape
    assert env.grid.config.height_levels == 7, env.grid.config.height_levels
    assert env.grid.config.native_3d_obstacles is True
    assert len(positions[0]) == 3, positions[0]
    assert np.sum(global_obstacles) > 0, "Expected occupied cells from OctoMap asset"
    assert sum(len(path) > 1 for path in smapo.re_plan.get_path()) > 0
    assert obs[0]["obs"].shape[1:] == (11, 11), obs[0]["obs"].shape

    print("octomap_asset_smoke_ok")
    print(f"map_name={env.grid.config.map_name}")
    print(f"global_obstacles_shape={tuple(int(v) for v in global_obstacles.shape)}")
    print(f"planner_obstacles_shape={tuple(int(v) for v in planner_agent.obstacles.shape)}")
    print(f"occupied_cells={int(np.sum(global_obstacles))}")
    print(f"agent_position_example={positions[0]}")


if __name__ == "__main__":
    main()
