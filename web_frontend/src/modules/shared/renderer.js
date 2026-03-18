const palette = ["#6ad5ff", "#59f0c2", "#ffd36c", "#ff7d7d", "#8ec5ff", "#df8cff", "#72d5c8", "#f5abff"];

export function createRenderer() {
  const icon = new Image();
  icon.src = "/uav-icon-local-384.png";
  icon.onerror = () => {
    icon.src = "/uav-icon.png";
  };
  const cache = new Map();

  function getSprite(size) {
    const key = Math.round(size);
    if (cache.has(key)) return cache.get(key);
    if (!icon.complete || !icon.naturalWidth) return null;

    const off = document.createElement("canvas");
    off.width = key;
    off.height = key;
    const c = off.getContext("2d");
    const fit = key * 0.86;
    const scale = Math.min(fit / icon.naturalWidth, fit / icon.naturalHeight);
    const dw = icon.naturalWidth * scale;
    const dh = icon.naturalHeight * scale;
    c.drawImage(icon, (key - dw) / 2, (key - dh) / 2, dw, dh);
    cache.set(key, off);
    return off;
  }

  // Shared renderer for both research mode and operations mode.
  function draw(canvas, environment, frame) {
    if (!canvas || !environment || !frame) return;
    const ctx = canvas.getContext("2d");
    const { width, height, obstacles } = environment;
    const padding = 34;
    const cell = Math.min((canvas.width - padding * 2) / width, (canvas.height - padding * 2) / height);
    const gridWidth = cell * width;
    const gridHeight = cell * height;
    const left = (canvas.width - gridWidth) / 2;
    const top = (canvas.height - gridHeight) / 2;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#07101f";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    for (let row = 0; row < height; row += 1) {
      for (let col = 0; col < width; col += 1) {
        const x = left + col * cell;
        const y = top + row * cell;
        ctx.strokeStyle = "rgba(255,255,255,0.08)";
        ctx.strokeRect(x, y, cell, cell);
        if (obstacles[row][col] === 1) {
          ctx.fillStyle = "rgba(128, 148, 170, 0.86)";
          ctx.fillRect(x + 2, y + 2, cell - 4, cell - 4);
        }
      }
    }

    frame.agents.forEach((agent) => {
      const color = palette[agent.id % palette.length];
      const tx = left + agent.target_y * cell + cell / 2;
      const ty = top + agent.target_x * cell + cell / 2;
      ctx.lineWidth = 4;
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.arc(tx, ty, cell * 0.24, 0, Math.PI * 2);
      ctx.stroke();
    });

    frame.agents.forEach((agent) => {
      const color = palette[agent.id % palette.length];
      const x = left + agent.y * cell + cell / 2;
      const y = top + agent.x * cell + cell / 2;
      const iconSize = Math.max(16, Math.floor(cell * 0.62));
      const sprite = getSprite(iconSize);

      ctx.lineWidth = Math.max(1.5, cell * 0.05);
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, iconSize * 0.58, 0, Math.PI * 2);
      ctx.stroke();

      if (sprite) {
        ctx.drawImage(sprite, x - iconSize / 2, y - iconSize / 2, iconSize, iconSize);
      } else {
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, cell * 0.22, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  return { draw };
}

export function buildSampleRun() {
  const environment = {
    width: 12,
    height: 12,
    obstacles: buildSampleObstacles(12, 12),
  };

  const starts = [
    [1, 1, 9, 9],
    [10, 1, 2, 9],
    [1, 10, 10, 3],
    [10, 10, 2, 2],
  ];

  const plans = starts.map(([sx, sy, tx, ty]) => {
    const path = findPathAStar(environment.obstacles, [sx, sy], [tx, ty]);
    return {
      start_x: sx,
      start_y: sy,
      target_x: tx,
      target_y: ty,
      path: path || [[sx, sy]],
      reachable: Boolean(path),
    };
  });

  const frames = [];
  const maxFrames = Math.max(...plans.map((p) => p.path.length - 1), 0);
  for (let step = 0; step <= maxFrames; step += 1) {
    const agents = plans.map((plan, idx) => {
      const last = plan.path.length - 1;
      const cursor = Math.min(step, last);
      const [x, y] = plan.path[cursor];
      return {
        id: idx,
        x,
        y,
        target_x: plan.target_x,
        target_y: plan.target_y,
        reward: plan.reachable && cursor === last ? 1 : 0,
        done: plan.reachable && cursor === last,
      };
    });
    frames.push({ step, vertex_conflicts: countVertexConflicts(agents), agents });
  }

  const tasksCompleted = plans.filter((p) => p.reachable).length;
  const totalSteps = Math.max(maxFrames, 1);

  return {
    meta: {
      actual_device: "sample",
      checkpoint_path: "sample/demo",
      cfg_dir: "sample",
      frames: frames.length,
      map_name: "sample-city-grid",
      num_agents: 4,
      save_svg: null,
      warnings: ["frontend sample mode"],
    },
    environment,
    frames,
    metrics: {
      mean_reward: tasksCompleted ? 1 : 0,
      tasks_completed: tasksCompleted,
      throughput: Number((tasksCompleted / totalSteps).toFixed(4)),
      total_steps: maxFrames,
      vertex_conflicts: Math.max(...frames.map((f) => f.vertex_conflicts), 0),
    },
  };
}

function buildSampleObstacles(height, width) {
  const obstacles = Array.from({ length: height }, () => Array(width).fill(0));
  for (let row = 3; row < 9; row += 1) obstacles[row][5] = 1;
  for (let col = 2; col < 10; col += 1) obstacles[6][col] = 1;
  obstacles[6][5] = 0;
  obstacles[2][8] = 1;
  obstacles[9][3] = 1;
  return obstacles;
}

function findPathAStar(obstacles, start, goal) {
  const [sx, sy] = start;
  const [gx, gy] = goal;
  if (!isWalkable(obstacles, sx, sy) || !isWalkable(obstacles, gx, gy)) return null;
  if (sx === gx && sy === gy) return [[sx, sy]];

  const open = [{ x: sx, y: sy, g: 0, f: manhattan(sx, sy, gx, gy) }];
  const parents = new Map();
  const gScore = new Map([[toKey(sx, sy), 0]]);
  const closed = new Set();

  while (open.length) {
    open.sort((a, b) => a.f - b.f || a.g - b.g);
    const current = open.shift();
    const cKey = toKey(current.x, current.y);
    if (closed.has(cKey)) continue;
    if (current.x === gx && current.y === gy) return rebuildPath(parents, cKey);
    closed.add(cKey);

    for (const [dx, dy] of [
      [-1, 0],
      [1, 0],
      [0, -1],
      [0, 1],
    ]) {
      const nx = current.x + dx;
      const ny = current.y + dy;
      if (!isWalkable(obstacles, nx, ny)) continue;
      const nKey = toKey(nx, ny);
      if (closed.has(nKey)) continue;

      const tentativeG = current.g + 1;
      if (tentativeG >= (gScore.get(nKey) ?? Number.POSITIVE_INFINITY)) continue;
      gScore.set(nKey, tentativeG);
      parents.set(nKey, cKey);
      open.push({
        x: nx,
        y: ny,
        g: tentativeG,
        f: tentativeG + manhattan(nx, ny, gx, gy),
      });
    }
  }

  return null;
}

function rebuildPath(parents, endKey) {
  const chain = [];
  let cursor = endKey;
  while (cursor) {
    const [x, y] = fromKey(cursor);
    chain.push([x, y]);
    cursor = parents.get(cursor);
  }
  chain.reverse();
  return chain;
}

function countVertexConflicts(agents) {
  const occupied = new Map();
  for (const agent of agents) {
    const key = toKey(agent.x, agent.y);
    occupied.set(key, (occupied.get(key) || 0) + 1);
  }
  let conflicts = 0;
  occupied.forEach((count) => {
    if (count > 1) conflicts += count - 1;
  });
  return conflicts;
}

function isWalkable(obstacles, x, y) {
  if (x < 0 || y < 0 || x >= obstacles.length || y >= obstacles[0].length) return false;
  return obstacles[x][y] === 0;
}

function manhattan(x1, y1, x2, y2) {
  return Math.abs(x1 - x2) + Math.abs(y1 - y2);
}

function toKey(x, y) {
  return `${x},${y}`;
}

function fromKey(key) {
  return key.split(",").map((v) => Number(v));
}
