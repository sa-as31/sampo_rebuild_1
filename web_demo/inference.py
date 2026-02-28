import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning.encoder_residual import ResnetEncoder
from sample_factory.algorithms.appo.actor_worker import transform_dict_observations
from sample_factory.algorithms.appo.model import create_actor_critic
from sample_factory.algorithms.appo.model_utils import get_hidden_size, register_custom_encoder
from sample_factory.utils.utils import AttrDict
from scripts.eval_checkpoint import load_cfg, make_env, resolve_checkpoint, maybe_build_planner
from utils.training_tools import register_custom_components


DEFAULT_PAYLOAD = {
    "cfg_dir": "results/train_dir/0001/exp",
    "checkpoint_path": "results/train_dir/0001/exp/checkpoint_p0/best/best_model_obj_+0000000.000000_step_000921600_1772213120.pth",
    "device": "cpu",
    "render": False,
    "save_svg": "results/mac_eval/web-demo.svg",
    "max_frames": 48,
    "fps": 0,
    "seed": 7,
    "map_name": "mazes-s0_wc8_od55",
    "num_agents": 16,
    "max_episode_steps": 64,
    "policy_index": 0,
}

MAP_SUGGESTIONS = [
    "mazes-s0_wc8_od55",
    "mazes-s1_wc3_od70",
]

_RUNTIME_READY = False


def ensure_runtime_ready():
    global _RUNTIME_READY
    if _RUNTIME_READY:
        return

    maybe_build_planner()
    register_custom_components()
    register_custom_encoder("pogema_residual", ResnetEncoder)
    _RUNTIME_READY = True


def normalize_payload(payload):
    merged = dict(DEFAULT_PAYLOAD)
    merged.update(payload or {})

    merged["cfg_dir"] = str(_resolve_repo_path(merged["cfg_dir"]))
    merged["checkpoint_path"] = str(_resolve_repo_path(merged["checkpoint_path"]))

    save_svg = merged.get("save_svg")
    if save_svg:
        merged["save_svg"] = str(_resolve_repo_path(save_svg))

    merged["render"] = bool(merged.get("render", False))
    merged["max_frames"] = int(merged.get("max_frames", DEFAULT_PAYLOAD["max_frames"]))
    merged["fps"] = int(merged.get("fps", DEFAULT_PAYLOAD["fps"]))
    merged["num_agents"] = int(merged.get("num_agents", DEFAULT_PAYLOAD["num_agents"]))
    merged["max_episode_steps"] = int(merged.get("max_episode_steps", DEFAULT_PAYLOAD["max_episode_steps"]))
    merged["policy_index"] = int(merged.get("policy_index", DEFAULT_PAYLOAD["policy_index"]))

    seed = merged.get("seed")
    merged["seed"] = None if seed in (None, "", "null") else int(seed)

    return merged


def build_rollout(payload):
    ensure_runtime_ready()
    normalized = normalize_payload(payload)
    args = SimpleNamespace(**normalized)
    cfg_dir = Path(normalized["cfg_dir"])
    cfg = load_cfg(cfg_dir, args)
    checkpoint_path = resolve_checkpoint(cfg, cfg_dir, normalized["checkpoint_path"])

    device = torch.device("cuda" if normalized["device"] == "gpu" and torch.cuda.is_available() else "cpu")
    warnings = []
    if normalized["device"] == "gpu" and device.type != "cuda":
        warnings.append("GPU unavailable at runtime. Fallback to CPU.")
    if normalized["render"]:
        warnings.append("Native env.render() is not used here. The web canvas is the render target.")

    env = make_env(cfg, normalized.get("save_svg"))
    actor_critic = create_actor_critic(cfg, env.observation_space, env.action_space)
    actor_critic.model_to_device(device)

    checkpoint = torch.load(checkpoint_path, map_location=device)
    actor_critic.load_state_dict(checkpoint["model"])

    obs = env.reset()
    obstacles = np.asarray(env.grid.get_obstacles(ignore_borders=True)).astype(int).tolist()
    height = int(len(obstacles))
    width = int(len(obstacles[0])) if obstacles else 0
    rnn_states = torch.zeros([env.num_agents, get_hidden_size(cfg)], dtype=torch.float32, device=device)
    episode_reward = np.zeros(env.num_agents, dtype=np.float32)
    frames = [_frame_from_env(env, 0, np.zeros(env.num_agents), np.zeros(env.num_agents, dtype=bool))]
    tasks_completed = 0

    done = np.zeros(env.num_agents, dtype=bool)
    for step in range(1, normalized["max_frames"] + 1):
        previous_targets = env.get_targets_xy(ignore_borders=True)
        with torch.no_grad():
            obs_torch = AttrDict(transform_dict_observations(obs))
            for key, value in obs_torch.items():
                obs_torch[key] = torch.from_numpy(value).to(device).float()

            policy_outputs = actor_critic(obs_torch, rnn_states, with_action_distribution=True)
            actions = policy_outputs.actions.cpu().numpy()
            rnn_states = policy_outputs.rnn_states

        obs, rewards, done_list, _info = env.step(actions)
        rewards_np = np.asarray(rewards, dtype=np.float32)
        done = np.asarray(done_list, dtype=bool)
        episode_reward += rewards_np
        completed_this_step = _count_completed_tasks(env, previous_targets)
        tasks_completed += completed_this_step
        frames.append(_frame_from_env(env, step, rewards_np, done, completed_this_step, tasks_completed))
        if bool(done.all()):
            break

    svg_path = normalized.get("save_svg")
    if svg_path:
        save_path = Path(svg_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        env.save_animation(str(save_path))

    env.close()

    metrics = _build_metrics(frames, episode_reward, tasks_completed)
    return {
        "meta": {
            "actual_device": device.type,
            "checkpoint_path": str(checkpoint_path),
            "cfg_dir": str(cfg_dir),
            "frames": len(frames),
            "map_name": normalized["map_name"],
            "num_agents": len(frames[0]["agents"]) if frames else 0,
            "save_svg": svg_path,
            "warnings": warnings,
        },
        "environment": {
            "width": width,
            "height": height,
            "obstacles": obstacles,
        },
        "metrics": metrics,
        "frames": frames,
    }


def _frame_from_env(env, step, rewards, done, completed_this_step=0, tasks_completed=0):
    positions = env.get_agents_xy(ignore_borders=True)
    targets = env.get_targets_xy(ignore_borders=True)
    agents = []
    for idx, (position, target) in enumerate(zip(positions, targets)):
        x, y = [int(v) for v in position]
        tx, ty = [int(v) for v in target]
        agents.append(
            {
                "id": idx,
                "x": x,
                "y": y,
                "target_x": tx,
                "target_y": ty,
                "reward": float(rewards[idx]),
                "done": bool(done[idx]),
            }
        )

    positions = [(agent["x"], agent["y"]) for agent in agents]
    vertex_conflicts = len(positions) - len(set(positions))
    return {
        "step": step,
        "vertex_conflicts": vertex_conflicts,
        "completed_this_step": int(completed_this_step),
        "tasks_completed": int(tasks_completed),
        "agents": agents,
    }


def _build_metrics(frames, episode_reward, tasks_completed):
    total_conflicts = sum(frame["vertex_conflicts"] for frame in frames)
    movement_steps = 0
    for left, right in zip(frames, frames[1:]):
        for before, after in zip(left["agents"], right["agents"]):
            movement_steps += int(before["x"] != after["x"] or before["y"] != after["y"])

    total_steps = len(frames) - 1
    throughput = float(tasks_completed / total_steps) if total_steps > 0 else 0.0

    return {
        "mean_reward": round(float(np.mean(episode_reward)), 4),
        "tasks_completed": int(tasks_completed),
        "throughput": round(throughput, 4),
        "total_steps": total_steps,
        "vertex_conflicts": int(total_conflicts),
        "movement_steps": int(movement_steps),
    }


def _count_completed_tasks(env, previous_targets):
    current_positions = env.get_agents_xy(ignore_borders=True)
    completed = 0
    for position, target in zip(current_positions, previous_targets):
        if tuple(position) == tuple(target):
            completed += 1
    return completed


def _resolve_repo_path(value):
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def defaults_response():
    return {
        "defaults": DEFAULT_PAYLOAD,
        "map_suggestions": MAP_SUGGESTIONS,
        "project_title": "无人机动态路径规划系统",
    }
