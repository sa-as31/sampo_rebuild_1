const palette = ["#6ad5ff", "#59f0c2", "#ffd36c", "#ff7d7d", "#8ec5ff", "#df8cff", "#72d5c8", "#f5abff"];
const CELL_SIZE_3D = 1.2;

const TEMPLATE_CONFIGS = {
  warehouse: {
    mapName: "warehouse-grid-v1",
    starts: [
      [1, 1, 10, 10],
      [10, 1, 2, 10],
      [1, 10, 10, 2],
      [10, 10, 2, 2],
    ],
  },
  campus: {
    mapName: "campus-road-v1",
    starts: [
      [1, 2, 10, 9],
      [10, 2, 2, 9],
      [2, 10, 9, 2],
      [9, 10, 2, 2],
    ],
  },
  emergency: {
    mapName: "emergency-block-v1",
    starts: [
      [1, 1, 10, 10],
      [10, 1, 1, 10],
      [1, 10, 10, 1],
      [10, 10, 1, 1],
    ],
  },
};

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

    const pulse = performance.now() / 1000;
    frame.agents.forEach((agent) => {
      const color = palette[agent.id % palette.length];
      const path = findPathAStar(obstacles, [agent.x, agent.y], [agent.target_x, agent.target_y]) || [[agent.x, agent.y]];
      if (path.length < 2) return;

      ctx.save();
      ctx.strokeStyle = `${color}${Math.round((0.56 + 0.2 * Math.sin(pulse * 3 + agent.id)) * 255)
        .toString(16)
        .padStart(2, "0")}`;
      ctx.lineWidth = Math.max(1.8, cell * 0.13);
      ctx.setLineDash([cell * 0.34, cell * 0.22]);
      ctx.lineDashOffset = -(pulse * cell * 2.4 + agent.id * cell * 0.45);
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      path.forEach(([row, col], index) => {
        const px = left + col * cell + cell / 2;
        const py = top + row * cell + cell / 2;
        if (index === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.restore();
    });

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

export function drawScene3D(canvas, environment, frame, options = {}) {
  if (!canvas || !environment || !frame) return;
  resizeCanvasToDisplaySize(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#091a33");
  gradient.addColorStop(1, "#050d1d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!environment.width || !environment.height) return;

  const selectedDroneId = Number(options.selectedDroneId || 0);
  const leadAgent = frame.agents?.find((agent) => agent.id === selectedDroneId) || frame.agents?.[0];
  const lead = leadAgent ? gridToWorld(leadAgent.x, leadAgent.y, environment) : { x: 0, z: 0 };
  const radius = Math.max((environment.height - 1) * CELL_SIZE_3D, (environment.width - 1) * CELL_SIZE_3D) * 0.95 + 6;
  const camera = build3DCamera(
    String(options.cameraMode || "orbit"),
    lead,
    radius,
    Number(options.orbitAngle || 0)
  );
  const zoomScale = Number(options.zoomScale || 1);

  drawGrid3D(ctx, canvas, camera, environment, zoomScale);
  drawObstacles3D(ctx, canvas, camera, environment, zoomScale);
  drawAgents3D(ctx, canvas, camera, environment, frame, zoomScale);
}

export function resizeCanvasToDisplaySize(canvas) {
  if (!canvas) return false;
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const targetWidth = Math.max(1, Math.round(rect.width * dpr));
  const targetHeight = Math.max(1, Math.round(rect.height * dpr));
  if (canvas.width === targetWidth && canvas.height === targetHeight) return false;
  canvas.width = targetWidth;
  canvas.height = targetHeight;
  return true;
}

export function buildSampleRun(template = "warehouse") {
  const config = TEMPLATE_CONFIGS[template] || TEMPLATE_CONFIGS.warehouse;
  const environment = {
    width: 12,
    height: 12,
    obstacles: buildTemplateObstacles(template, 12, 12),
  };
  const starts = config.starts;

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
      map_name: config.mapName,
      num_agents: 4,
      save_svg: null,
      warnings: [`frontend sample mode: ${template}`],
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

function buildTemplateObstacles(template, height, width) {
  if (template === "campus") return buildCampusObstacles(height, width);
  if (template === "emergency") return buildEmergencyObstacles(height, width);
  return buildWarehouseObstacles(height, width);
}

function buildWarehouseObstacles(height, width) {
  const obstacles = Array.from({ length: height }, () => Array(width).fill(0));
  for (let col = 2; col < width - 2; col += 1) {
    if (col !== 5 && col !== 8) obstacles[3][col] = 1;
    if (col !== 3 && col !== 9) obstacles[6][col] = 1;
    if (col !== 4 && col !== 7) obstacles[9][col] = 1;
  }
  for (let row = 1; row < height - 1; row += 1) {
    if (row !== 4 && row !== 8) obstacles[row][5] = 1;
    if (row !== 2 && row !== 7) obstacles[row][8] = 1;
  }
  return obstacles;
}

function buildCampusObstacles(height, width) {
  const obstacles = Array.from({ length: height }, () => Array(width).fill(0));
  for (let row = 2; row < height - 2; row += 1) {
    for (let col = 2; col < width - 2; col += 1) {
      const inCentralBlock = row >= 4 && row <= 7 && col >= 4 && col <= 7;
      if (inCentralBlock) obstacles[row][col] = 1;
    }
  }
  for (let row = 1; row < height - 1; row += 1) {
    if (row !== 5) obstacles[row][2] = obstacles[row][9] = 1;
  }
  for (let col = 1; col < width - 1; col += 1) {
    if (col !== 6) obstacles[2][col] = obstacles[9][col] = 1;
  }
  // Keep main roads open.
  for (let col = 0; col < width; col += 1) obstacles[5][col] = 0;
  for (let row = 0; row < height; row += 1) obstacles[row][6] = 0;
  return obstacles;
}

function buildEmergencyObstacles(height, width) {
  const obstacles = Array.from({ length: height }, () => Array(width).fill(0));
  for (let row = 2; row < height - 2; row += 1) {
    obstacles[row][Math.floor(width / 2)] = 1;
  }
  for (let col = 2; col < width - 2; col += 1) {
    obstacles[Math.floor(height / 2)][col] = 1;
  }
  for (let i = 2; i < height - 2; i += 1) {
    if (i !== 4 && i !== 7) obstacles[i][i] = 1;
    const mirrorCol = width - 1 - i;
    if (i !== 4 && i !== 7) obstacles[i][mirrorCol] = 1;
  }
  // Open emergency corridors.
  obstacles[4][Math.floor(width / 2)] = 0;
  obstacles[7][Math.floor(width / 2)] = 0;
  obstacles[Math.floor(height / 2)][4] = 0;
  obstacles[Math.floor(height / 2)][7] = 0;
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

function build3DCamera(mode, lead, radius, orbitAngle) {
  if (mode === "overview") {
    return lookAtCamera({ x: 0, y: radius * 0.9, z: radius * 0.5 }, { x: 0, y: 0.3, z: 0 });
  }
  if (mode === "follow") {
    return lookAtCamera(
      { x: lead.x - radius * 0.16, y: radius * 0.28, z: lead.z + radius * 0.23 },
      { x: lead.x, y: 0.4, z: lead.z }
    );
  }
  return lookAtCamera(
    { x: Math.cos(orbitAngle) * radius, y: radius * 0.45, z: Math.sin(orbitAngle) * radius },
    { x: 0, y: 0.3, z: 0 }
  );
}

function drawGrid3D(ctx, canvas, camera, environment, zoomScale) {
  const halfX = ((environment.height - 1) * CELL_SIZE_3D) / 2;
  const halfZ = ((environment.width - 1) * CELL_SIZE_3D) / 2;
  for (let row = 0; row < environment.height; row += 1) {
    const x = row * CELL_SIZE_3D - halfX;
    drawLine3D(ctx, canvas, camera, { x, y: 0, z: -halfZ }, { x, y: 0, z: halfZ }, "rgba(145,180,230,0.16)", 1, zoomScale);
  }
  for (let col = 0; col < environment.width; col += 1) {
    const z = col * CELL_SIZE_3D - halfZ;
    drawLine3D(ctx, canvas, camera, { x: -halfX, y: 0, z }, { x: halfX, y: 0, z }, "rgba(145,180,230,0.16)", 1, zoomScale);
  }
}

function drawObstacles3D(ctx, canvas, camera, environment, zoomScale) {
  for (let row = 0; row < environment.height; row += 1) {
    for (let col = 0; col < environment.width; col += 1) {
      if (environment.obstacles?.[row]?.[col] !== 1) continue;
      const p = gridToWorld(row, col, environment);
      const block = { x: p.x - CELL_SIZE_3D * 0.45, z: p.z - CELL_SIZE_3D * 0.45, w: CELL_SIZE_3D * 0.9, d: CELL_SIZE_3D * 0.9, h: 0.9 };
      drawBoxWire(ctx, canvas, camera, block, "rgba(145,160,182,0.95)", zoomScale);
    }
  }
}

function drawAgents3D(ctx, canvas, camera, environment, frame, zoomScale) {
  frame.agents?.forEach((agent) => {
    const color = palette[agent.id % palette.length];
    const bodyPos = gridToWorld(agent.x, agent.y, environment);
    const targetPos = gridToWorld(agent.target_x, agent.target_y, environment);
    const body = projectPoint(canvas, camera, bodyPos.x, 0.72, bodyPos.z, zoomScale);
    const ground = projectPoint(canvas, camera, bodyPos.x, 0.03, bodyPos.z, zoomScale);
    const target = projectPoint(canvas, camera, targetPos.x, 0.08, targetPos.z, zoomScale);
    if (!body || !ground) return;

    if (target) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(target.x, target.y, Math.max(5, target.scale * 7), 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.strokeStyle = "rgba(175,209,255,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(body.x, body.y);
    ctx.lineTo(ground.x, ground.y);
    ctx.stroke();

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(body.x, body.y, Math.max(3.2, body.scale * 4.6), 0, Math.PI * 2);
    ctx.fill();
  });
}

function gridToWorld(row, col, environment) {
  const halfX = ((environment.height - 1) * CELL_SIZE_3D) / 2;
  const halfZ = ((environment.width - 1) * CELL_SIZE_3D) / 2;
  return { x: row * CELL_SIZE_3D - halfX, z: col * CELL_SIZE_3D - halfZ };
}

function drawBoxWire(ctx, canvas, camera, block, color, zoomScale) {
  const x1 = block.x;
  const x2 = block.x + block.w;
  const y1 = 0;
  const y2 = block.h;
  const z1 = block.z;
  const z2 = block.z + block.d;
  const corners = [
    [x1, y1, z1],
    [x2, y1, z1],
    [x2, y1, z2],
    [x1, y1, z2],
    [x1, y2, z1],
    [x2, y2, z1],
    [x2, y2, z2],
    [x1, y2, z2],
  ];
  const edges = [
    [0, 1], [1, 2], [2, 3], [3, 0],
    [4, 5], [5, 6], [6, 7], [7, 4],
    [0, 4], [1, 5], [2, 6], [3, 7],
  ];
  edges.forEach(([a, b]) => {
    const pa = corners[a];
    const pb = corners[b];
    drawLine3D(
      ctx,
      canvas,
      camera,
      { x: pa[0], y: pa[1], z: pa[2] },
      { x: pb[0], y: pb[1], z: pb[2] },
      color,
      1.5,
      zoomScale
    );
  });
}

function drawLine3D(ctx, canvas, camera, a, b, color, width, zoomScale) {
  const pa = projectPoint(canvas, camera, a.x, a.y, a.z, zoomScale);
  const pb = projectPoint(canvas, camera, b.x, b.y, b.z, zoomScale);
  if (!pa || !pb) return;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.stroke();
}

function projectPoint(canvas, camera, x, y, z, zoomScale) {
  const dx = x - camera.x;
  const dy = y - camera.y;
  const dz = z - camera.z;

  const cosYaw = Math.cos(-camera.yaw);
  const sinYaw = Math.sin(-camera.yaw);
  const x1 = dx * cosYaw - dz * sinYaw;
  const z1 = dx * sinYaw + dz * cosYaw;

  const cosPitch = Math.cos(-camera.pitch);
  const sinPitch = Math.sin(-camera.pitch);
  const y2 = dy * cosPitch - z1 * sinPitch;
  const z2 = dy * sinPitch + z1 * cosPitch;
  if (z2 <= 0.25) return null;

  const focal = 620 * Number(zoomScale || 1);
  const scale = focal / z2;
  return {
    x: canvas.width * 0.5 + x1 * scale,
    y: canvas.height * 0.52 - y2 * scale,
    scale: Math.max(0.3, Math.min(2.2, scale / 120)),
  };
}

function lookAtCamera(position, target) {
  const dx = target.x - position.x;
  const dy = target.y - position.y;
  const dz = target.z - position.z;
  const yaw = -Math.atan2(dx, dz);
  const distXZ = Math.hypot(dx, dz);
  const pitch = -Math.atan2(dy, distXZ);
  return { x: position.x, y: position.y, z: position.z, yaw, pitch };
}
