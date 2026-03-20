import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.create_env import create_env
from learning.learning_config import Environment, DMAPFConfig


def main():
    env_cfg = Environment(
        use_maps=False,
        target_num_agents=None,
        grid_config=DMAPFConfig(
            size=16,
            num_agents=8,
            obs_radius=5,
            height_levels=4,
            native_3d_obstacles=True,
            obstacle_backend="pyoctomap",
            octomap_resolution=1.0,
            density=0.18,
            on_target="finish",
            max_episode_steps=32,
        ),
    )

    env = create_env(env_cfg, auto_reset=False)
    obs = env.reset()
    global_obstacles = np.array(env.get_obstacles(ignore_borders=True))
    agent_positions = env.get_agents_xy()

    assert global_obstacles.shape == (4, 16, 16), global_obstacles.shape
    assert len(agent_positions[0]) == 3, agent_positions[0]
    assert np.any(global_obstacles[0] != global_obstacles[-1]), "native 3D layers should not all be identical"
    assert obs[0]["obs"].shape[1:] == (11, 11), obs[0]["obs"].shape

    actions = env.sample_actions()
    obs, rewards, dones, infos = env.step(actions)

    print("pyoctomap_smoke_ok")
    print(f"global_obstacles_shape={global_obstacles.shape}")
    print(f"single_obs_shape={obs[0]['obs'].shape}")
    print(f"agent_position_example={agent_positions[0]}")
    print(f"reward_sum={float(np.sum(rewards))}")
    print(f"all_done={all(dones)}")


if __name__ == "__main__":
    main()
