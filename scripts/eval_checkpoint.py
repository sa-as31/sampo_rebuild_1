import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning.encoder_residual import ResnetEncoder
from pogema.animation import AnimationConfig, AnimationMonitor
from sample_factory.algorithms.appo.actor_worker import transform_dict_observations
from sample_factory.algorithms.appo.learner import LearnerWorker
from sample_factory.algorithms.appo.model import create_actor_critic
from sample_factory.algorithms.appo.model_utils import get_hidden_size, register_custom_encoder
from sample_factory.envs.create_env import create_env
from sample_factory.utils.utils import AttrDict
from utils.training_tools import register_custom_components, validate_config


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate a trained SMAPO checkpoint on CPU/Mac-friendly path.")
    parser.add_argument("--cfg_dir", required=True, help="Experiment directory containing cfg.json and checkpoint_p*/")
    parser.add_argument("--checkpoint_path", default=None, help="Explicit checkpoint path. Defaults to latest checkpoint under checkpoint_p{policy_index}.")
    parser.add_argument("--device", default="cpu", choices=["cpu", "gpu"], help="Inference device. CPU is recommended for Mac.")
    parser.add_argument("--render", action="store_true", help="Render the environment during rollout.")
    parser.add_argument("--save_svg", default=None, help="Optional SVG output path for the rollout animation.")
    parser.add_argument("--max_frames", type=int, default=512, help="Maximum environment steps to run.")
    parser.add_argument("--fps", type=int, default=0, help="Render FPS limit. 0 means no delay.")
    parser.add_argument("--seed", type=int, default=None, help="Optional evaluation seed override.")
    parser.add_argument("--map_name", default=None, help="Optional map name override for the evaluation environment.")
    parser.add_argument("--num_agents", type=int, default=None, help="Optional agent count override for the evaluation environment.")
    parser.add_argument("--max_episode_steps", type=int, default=None, help="Optional episode length override.")
    parser.add_argument("--policy_index", type=int, default=None, help="Optional policy index override.")
    return parser.parse_args()


def maybe_build_planner():
    import cppimport

    cppimport.imp("planner.LB_A.planner")


def load_cfg(cfg_dir: Path, args):
    with open(cfg_dir / "cfg.json", "r") as f:
        raw_cfg = json.load(f)

    full_config = raw_cfg["full_config"]
    _, cfg = validate_config(full_config)

    cfg.train_dir = str(cfg_dir.parent.parent)
    cfg.experiments_root = cfg_dir.parent.name
    cfg.experiment = cfg_dir.name
    cfg.device = args.device
    cfg.no_render = not args.render
    cfg.fps = args.fps

    if args.policy_index is not None:
        cfg.policy_index = args.policy_index
        cfg.full_config["evaluation"]["policy_index"] = args.policy_index

    if args.seed is not None:
        cfg.seed = args.seed
        cfg.full_config["global_settings"]["seed"] = args.seed
        cfg.grid_config["seed"] = args.seed
        cfg.full_config["environment"]["grid_config"]["seed"] = args.seed

    if args.map_name is not None:
        cfg.grid_config["map_name"] = args.map_name
        cfg.full_config["environment"]["grid_config"]["map_name"] = args.map_name

    if args.num_agents is not None:
        cfg.grid_config["num_agents"] = args.num_agents
        cfg.full_config["environment"]["grid_config"]["num_agents"] = args.num_agents
        cfg.target_num_agents = None
        cfg.full_config["environment"]["target_num_agents"] = None
        cfg.agent_bins = None
        cfg.full_config["environment"]["agent_bins"] = None

    if args.max_episode_steps is not None:
        cfg.grid_config["max_episode_steps"] = args.max_episode_steps
        cfg.full_config["environment"]["grid_config"]["max_episode_steps"] = args.max_episode_steps

    return cfg


def resolve_checkpoint(cfg, cfg_dir: Path, checkpoint_path: Optional[str]):
    if checkpoint_path is not None:
        return Path(checkpoint_path)

    checkpoint_dir = Path(LearnerWorker.checkpoint_dir(cfg, cfg.policy_index))
    checkpoints = LearnerWorker.get_checkpoints(str(checkpoint_dir))
    if not checkpoints:
        raise FileNotFoundError(f"No checkpoints found under {checkpoint_dir}")
    return Path(checkpoints[-1])


def make_env(cfg, save_svg: Optional[str]):
    env = create_env(cfg.env, cfg=cfg, env_config={"worker_index": 0, "vector_index": 0})
    if save_svg:
        env = AnimationMonitor(
            env,
            AnimationConfig(directory=str(Path(save_svg).parent), save_every_idx_episode=None),
        )
    return env


def main():
    args = parse_args()
    cfg_dir = Path(args.cfg_dir).resolve()

    maybe_build_planner()
    register_custom_components()
    register_custom_encoder("pogema_residual", ResnetEncoder)

    cfg = load_cfg(cfg_dir, args)
    checkpoint_path = resolve_checkpoint(cfg, cfg_dir, args.checkpoint_path)

    device = torch.device("cuda" if args.device == "gpu" and torch.cuda.is_available() else "cpu")

    env = make_env(cfg, args.save_svg)
    actor_critic = create_actor_critic(cfg, env.observation_space, env.action_space)
    actor_critic.model_to_device(device)

    checkpoint = torch.load(checkpoint_path, map_location=device)
    actor_critic.load_state_dict(checkpoint["model"])

    obs = env.reset()
    rnn_states = torch.zeros([env.num_agents, get_hidden_size(cfg)], dtype=torch.float32, device=device)

    episode_reward = np.zeros(env.num_agents, dtype=np.float32)
    num_frames = 0
    done = [False] * env.num_agents
    render_start = time.time()

    with torch.no_grad():
        while num_frames < args.max_frames and not all(done):
            obs_torch = AttrDict(transform_dict_observations(obs))
            for key, value in obs_torch.items():
                obs_torch[key] = torch.from_numpy(value).to(device).float()

            policy_outputs = actor_critic(obs_torch, rnn_states, with_action_distribution=True)
            actions = policy_outputs.actions.cpu().numpy()
            rnn_states = policy_outputs.rnn_states

            if args.render:
                target_delay = 1.0 / args.fps if args.fps > 0 else 0
                elapsed = time.time() - render_start
                if target_delay > elapsed:
                    time.sleep(target_delay - elapsed)
                render_start = time.time()
                env.render()

            obs, rewards, done, info = env.step(actions)
            episode_reward += np.asarray(rewards, dtype=np.float32)
            num_frames += 1

    if args.save_svg:
        save_path = Path(args.save_svg).resolve()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        env.save_animation(str(save_path))
        print(f"Saved SVG to {save_path}")

    print(f"Checkpoint: {checkpoint_path}")
    print(f"Frames: {num_frames}")
    print(f"Mean reward: {float(np.mean(episode_reward)):.4f}")
    print(f"Done flags: {done}")

    env.close()


if __name__ == "__main__":
    main()
