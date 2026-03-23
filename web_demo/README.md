# UAV Inference Web Demo

This subproject provides the first web-based prototype for the graduation-design system:

- inference parameter form
- model checkpoint loading
- web animation for multi-agent rollout playback
- metric summary for the current run

## Run with the existing Docker image

```bash
docker run --rm \
  -p 8080:8080 \
  -v /Users/eller/Documents/codes/smapo_rebuild_1:/app \
  -w /app \
  smapo:local \
  python web_demo/server.py --host 0.0.0.0 --port 8080
```

Then open:

- `http://localhost:8080`

## Run locally with Django backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 0.0.0.0:8080 --noreload
```

Or keep using the previous compatible entrypoint:

```bash
python web_demo/server.py --host 0.0.0.0 --port 8080
```

## What it does

- `POST /api/run-demo` runs checkpoint inference and returns rollout frames as JSON
- the frontend draws obstacles, targets, agents, and animated playback on a canvas
- if runtime inference is not available, the UI can still load a built-in sample animation
- frontend Vue app continues to call the backend through the same `/api/...` paths

## Main parameters exposed in the UI

- `cfg_dir`
- `checkpoint_path`
- `device`
- `map_name`
- `num_agents`
- `max_episode_steps`
- `max_frames`
- `seed`
- `save_svg`

## Output

- optional SVG output is written to the path passed as `save_svg`
- playback data is returned directly to the frontend as JSON
