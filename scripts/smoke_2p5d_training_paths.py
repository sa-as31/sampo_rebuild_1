import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env.SMAPO import SMAPOWrapper
from env.create_env import create_env
from learning.learning_config import DMAPFConfig, Environment, EnvironmentMazes


def unwrap_wrapper(env, wrapper_type):
    current = env
    while current is not None:
        if isinstance(current, wrapper_type):
            return current
        current = getattr(current, "env", None)
    raise RuntimeError(f"Could not find wrapper {wrapper_type.__name__}")


def summarize_paths(paths):
    lengths = [len(path) for path in paths]
    return {
        "min": int(min(lengths)) if lengths else 0,
        "max": int(max(lengths)) if lengths else 0,
        "num_nontrivial": int(sum(length > 1 for length in lengths)),
    }


def random_native_3d_smoke():
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
            on_target="restart",
            max_episode_steps=32,
        ),
    )

    env = create_env(env_cfg, auto_reset=False)
    obs = env.reset()
    smapo = unwrap_wrapper(env, SMAPOWrapper)
    planner_agent = smapo.re_plan._agent

    assert planner_agent.__class__.__name__ == "LayeredPlanner"
    assert isinstance(planner_agent.obstacles, np.ndarray)
    assert planner_agent.obstacles.shape[0] == 4, planner_agent.obstacles.shape
    assert obs[0]["obs"].shape[1:] == (11, 11), obs[0]["obs"].shape

    return {
        "planner_type": planner_agent.__class__.__name__,
        "planner_obstacles_shape": tuple(int(v) for v in planner_agent.obstacles.shape),
        "path_stats": summarize_paths(smapo.re_plan.get_path()),
    }


def mazes_layered_smoke():
    env_cfg = EnvironmentMazes(
        target_num_agents=None,
        grid_config=DMAPFConfig(
            num_agents=16,
            obs_radius=5,
            height_levels=4,
            native_3d_obstacles=True,
            obstacle_backend="pyoctomap",
            on_target="restart",
            max_episode_steps=64,
            map_name=r"mazes-.+",
        ),
    )

    env = create_env(env_cfg, auto_reset=False)
    obs = env.reset()
    smapo = unwrap_wrapper(env, SMAPOWrapper)
    planner_agent = smapo.re_plan._agent
    global_obstacles = np.asarray(env.get_obstacles(ignore_borders=True))

    assert planner_agent.__class__.__name__ == "LayeredPlanner"
    assert isinstance(planner_agent.obstacles, np.ndarray)
    assert planner_agent.obstacles.ndim == 2, planner_agent.obstacles.shape
    assert obs[0]["obs"].shape[1:] == (11, 11), obs[0]["obs"].shape
    assert len(env.get_agents_xy()[0]) == 3, env.get_agents_xy()[0]

    return {
        "planner_type": planner_agent.__class__.__name__,
        "planner_obstacles_shape": tuple(int(v) for v in planner_agent.obstacles.shape),
        "global_obstacles_shape": tuple(int(v) for v in global_obstacles.shape),
        "path_stats": summarize_paths(smapo.re_plan.get_path()),
    }


def main():
    random_summary = random_native_3d_smoke()
    mazes_summary = mazes_layered_smoke()

    print("training_paths_smoke_ok")
    print(f"random_native_3d={random_summary}")
    print(f"mazes_layered={mazes_summary}")


if __name__ == "__main__":
    main()
