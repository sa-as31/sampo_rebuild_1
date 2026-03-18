const form = document.getElementById("inference-form");
const runBtn = document.getElementById("run-btn");
const sampleBtn = document.getElementById("sample-btn");
const playBtn = document.getElementById("play-btn");
const slider = document.getElementById("frame-slider");
const statusText = document.getElementById("status-text");
const logOutput = document.getElementById("log-output");
const mapOptions = document.getElementById("map-options");
const stepChip = document.getElementById("step-chip");
const deviceChip = document.getElementById("device-chip");
const checkpointChip = document.getElementById("checkpoint-chip");
const metricReward = document.getElementById("metric-reward");
const metricTasks = document.getElementById("metric-tasks");
const metricThroughput = document.getElementById("metric-throughput");
const metricConflicts = document.getElementById("metric-conflicts");
const canvas = document.getElementById("grid-canvas");
const ctx = canvas.getContext("2d");

const palette = [
  "#6ad5ff",
  "#59f0c2",
  "#ffd36c",
  "#ff7d7d",
  "#8ec5ff",
  "#df8cff",
  "#72d5c8",
  "#f5abff",
];

const agentIcon = {
  image: new Image(),
  loaded: false,
  failed: false,
  spriteCache: new Map(),
};

agentIcon.image.addEventListener("load", () => {
  agentIcon.loaded = true;
  agentIcon.failed = false;
  agentIcon.spriteCache.clear();
  if (playback.frames.length) renderFrame();
});

agentIcon.image.addEventListener("error", () => {
  agentIcon.loaded = false;
  agentIcon.failed = true;
});

agentIcon.image.src = "/uav-icon-384.png?v=20260318c";

let playback = {
  frames: [],
  environment: null,
  metrics: null,
  meta: null,
  frameIndex: 0,
  playing: false,
  timer: null,
};

const presets = {
  maze: {
    map_name: "mazes-s0_wc8_od55",
    num_agents: 16,
    max_episode_steps: 64,
    max_frames: 48,
    seed: 7,
  },
  dense: {
    map_name: "mazes-s1_wc3_od70",
    num_agents: 32,
    max_episode_steps: 96,
    max_frames: 72,
    seed: 11,
  },
};

document.querySelectorAll("[data-preset]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const key = btn.dataset.preset;
    if (key === "sample") {
      loadSampleRun();
      return;
    }
    applyPreset(presets[key]);
  });
});

runBtn.addEventListener("click", runInference);
sampleBtn.addEventListener("click", loadSampleRun);
playBtn.addEventListener("click", togglePlayback);
slider.addEventListener("input", () => {
  playback.frameIndex = Number(slider.value);
  renderFrame();
});

boot();

async function boot() {
  try {
    const response = await fetch("/api/defaults");
    const data = await response.json();
    setFormValues(data.defaults);
    fillMapSuggestions(data.map_suggestions || []);
    setStatus("默认参数已加载，可直接执行推理。");
  } catch (error) {
    setStatus("默认参数接口不可用，已切换为前端示例模式。");
    setFormValues(sampleDefaults());
  }
  loadSampleRun();
}

function sampleDefaults() {
  return {
    cfg_dir: "results/train_dir/0001/exp",
    checkpoint_path: "results/train_dir/0001/exp/checkpoint_p0/best/best_model_obj_+0000000.000000_step_000921600_1772213120.pth",
    device: "cpu",
    render: false,
    save_svg: "results/mac_eval/web-demo.svg",
    max_frames: 48,
    fps: 0,
    seed: 7,
    map_name: "mazes-s0_wc8_od55",
    num_agents: 16,
    max_episode_steps: 64,
    policy_index: 0,
  };
}

function setFormValues(values) {
  Object.entries(values).forEach(([key, value]) => {
    const field = form.elements.namedItem(key);
    if (!field) return;
    if (field.type === "checkbox") {
      field.checked = Boolean(value);
    } else {
      field.value = value ?? "";
    }
  });
}

function collectFormValues() {
  const data = Object.fromEntries(new FormData(form).entries());
  data.render = form.elements.namedItem("render").checked;
  return data;
}

function fillMapSuggestions(names) {
  mapOptions.innerHTML = "";
  names.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    mapOptions.appendChild(option);
  });
}

function applyPreset(preset) {
  setFormValues({ ...collectFormValues(), ...preset });
  setStatus(`已应用预设场景: ${preset.map_name}`);
}

async function runInference() {
  stopPlayback();
  setStatus("正在执行模型推理，请稍候...");
  logOutput.textContent = "请求已发送，等待后端返回轨迹数据。";
  try {
    const response = await fetch("/api/run-demo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectFormValues()),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "推理接口失败");
    }
    setPlaybackData(payload, "真实模型推理已完成。");
  } catch (error) {
    setStatus(`推理失败: ${error.message}`);
    logOutput.textContent = `后端运行失败。\n\n${error.message}\n\n已保留当前画面，你也可以点击“加载示例动画”。`;
  }
}

function loadSampleRun() {
  stopPlayback();
  const sample = buildSampleRun();
  setPlaybackData(sample, "已加载前端示例动画，可直接查看界面与回放逻辑。");
}

function setPlaybackData(payload, status) {
  playback = {
    frames: payload.frames,
    environment: payload.environment,
    metrics: payload.metrics,
    meta: payload.meta,
    frameIndex: 0,
    playing: false,
    timer: null,
  };

  slider.max = Math.max(0, playback.frames.length - 1);
  slider.value = 0;
  updateMetrics();
  updateChips();
  renderFrame();
  logOutput.textContent = buildLog(payload);
  setStatus(status);
}

function updateMetrics() {
  const metrics = playback.metrics || {};
  metricReward.textContent = fmt(metrics.mean_reward);
  metricTasks.textContent = fmt(metrics.tasks_completed);
  metricThroughput.textContent = fmt(metrics.throughput);
  metricConflicts.textContent = fmt(metrics.vertex_conflicts);
}

function updateChips() {
  const meta = playback.meta || {};
  stepChip.textContent = `Step ${playback.frameIndex}`;
  deviceChip.textContent = `Device: ${meta.actual_device || "sample"}`;
  checkpointChip.textContent = meta.checkpoint_path ? `Checkpoint: ${shorten(meta.checkpoint_path, 56)}` : "Checkpoint: sample";
}

function renderFrame() {
  const frame = playback.frames[playback.frameIndex];
  const environment = playback.environment;
  if (!frame || !environment) return;

  stepChip.textContent = `Step ${frame.step}`;
  drawScene(environment, frame);
}

function drawScene(environment, frame) {
  const { width, height, obstacles } = environment;
  const padding = 34;
  const cell = Math.min((canvas.width - padding * 2) / width, (canvas.height - padding * 2) / height);
  const gridWidth = cell * width;
  const gridHeight = cell * height;
  const left = (canvas.width - gridWidth) / 2;
  const top = (canvas.height - gridHeight) / 2;

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.save();
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
        roundRect(ctx, x + 2, y + 2, cell - 4, cell - 4, 8, true, false);
      }
    }
  }

  frame.agents.forEach((agent) => {
    const color = palette[agent.id % palette.length];
    const targetX = left + agent.target_y * cell + cell / 2;
    const targetY = top + agent.target_x * cell + cell / 2;

    ctx.lineWidth = 4;
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.arc(targetX, targetY, cell * 0.24, 0, Math.PI * 2);
    ctx.stroke();
  });

  frame.agents.forEach((agent) => {
    const color = palette[agent.id % palette.length];
    const agentX = left + agent.y * cell + cell / 2;
    const agentY = top + agent.x * cell + cell / 2;
    const iconSize = Math.max(16, Math.floor(cell * 0.62));

    ctx.lineWidth = Math.max(1.5, cell * 0.05);
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.arc(agentX, agentY, iconSize * 0.58, 0, Math.PI * 2);
    ctx.stroke();

    const sprite = getAgentSprite(iconSize);
    if (sprite) {
      ctx.drawImage(sprite, agentX - iconSize / 2, agentY - iconSize / 2, iconSize, iconSize);
    } else {
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(agentX, agentY, cell * 0.22, 0, Math.PI * 2);
      ctx.fill();
    }

    const badgeRadius = Math.max(8, cell * 0.13);
    const badgeX = agentX + iconSize * 0.27;
    const badgeY = agentY + iconSize * 0.27;
    ctx.fillStyle = "rgba(2, 16, 29, 0.86)";
    ctx.beginPath();
    ctx.arc(badgeX, badgeY, badgeRadius, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#f1f5ff";
    ctx.font = `${Math.max(9, cell * 0.17)}px "SFMono-Regular", monospace`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(String(agent.id + 1), badgeX, badgeY);
  });

  ctx.restore();
}

function getAgentSprite(size) {
  if (!agentIcon.loaded || !agentIcon.image.naturalWidth || !agentIcon.image.naturalHeight) return null;

  const key = Math.round(size);
  const cached = agentIcon.spriteCache.get(key);
  if (cached) return cached;

  const sprite = document.createElement("canvas");
  sprite.width = key;
  sprite.height = key;
  const spriteCtx = sprite.getContext("2d");
  if (!spriteCtx) return null;

  const fit = key * 0.86;
  const imgW = agentIcon.image.naturalWidth;
  const imgH = agentIcon.image.naturalHeight;
  const scale = Math.min(fit / imgW, fit / imgH);
  const drawW = imgW * scale;
  const drawH = imgH * scale;
  const dx = (key - drawW) / 2;
  const dy = (key - drawH) / 2;
  spriteCtx.drawImage(agentIcon.image, dx, dy, drawW, drawH);

  agentIcon.spriteCache.set(key, sprite);
  return sprite;
}

function togglePlayback() {
  if (!playback.frames.length) return;
  if (playback.playing) {
    stopPlayback();
  } else {
    startPlayback();
  }
}

function startPlayback() {
  stopPlayback();
  playback.playing = true;
  playBtn.textContent = "暂停";
  playback.timer = window.setInterval(() => {
    if (playback.frameIndex >= playback.frames.length - 1) {
      stopPlayback();
      return;
    }
    playback.frameIndex += 1;
    slider.value = playback.frameIndex;
    renderFrame();
  }, 240);
}

function stopPlayback() {
  playback.playing = false;
  playBtn.textContent = "播放";
  if (playback.timer) {
    window.clearInterval(playback.timer);
    playback.timer = null;
  }
}

function buildLog(payload) {
  const meta = payload.meta || {};
  const metrics = payload.metrics || {};
  const warnings = meta.warnings && meta.warnings.length ? meta.warnings.join("\n- ") : "无";
  return [
    `cfg_dir: ${meta.cfg_dir || "sample"}`,
    `checkpoint: ${meta.checkpoint_path || "sample"}`,
    `device: ${meta.actual_device || "sample"}`,
    `map_name: ${meta.map_name || "sample"}`,
    `frames: ${meta.frames || 0}`,
    `svg: ${meta.save_svg || "未输出"}`,
    "",
    `mean_reward: ${fmt(metrics.mean_reward)}`,
    `tasks_completed: ${fmt(metrics.tasks_completed)}`,
    `throughput: ${fmt(metrics.throughput)}`,
    `total_steps: ${fmt(metrics.total_steps)}`,
    `vertex_conflicts: ${fmt(metrics.vertex_conflicts)}`,
    "",
    `warnings:\n- ${warnings}`,
  ].join("\n");
}

function buildSampleRun() {
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

  const frames = [];
  const maxFrames = 18;
  for (let step = 0; step <= maxFrames; step += 1) {
    const agents = starts.map(([sx, sy, tx, ty], idx) => {
      const t = Math.min(step / maxFrames, 1);
      const x = Math.round(sx + (tx - sx) * t);
      const y = Math.round(sy + (ty - sy) * t);
      return {
        id: idx,
        x,
        y,
        target_x: tx,
        target_y: ty,
        reward: step === maxFrames ? 1 : 0,
        done: step === maxFrames,
      };
    });
    frames.push({ step, vertex_conflicts: 0, agents });
  }

  return {
    meta: {
      actual_device: "sample",
      checkpoint_path: "sample/demo",
      cfg_dir: "sample",
      frames: frames.length,
      map_name: "sample-city-grid",
      num_agents: 4,
      save_svg: null,
      warnings: ["This playback is generated in the browser for UI preview."],
    },
    environment,
    frames,
    metrics: {
      mean_reward: 1,
      tasks_completed: 4,
      throughput: 0.2222,
      total_steps: maxFrames,
      vertex_conflicts: 0,
      movement_steps: 68,
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

function setStatus(message) {
  statusText.textContent = message;
}

function fmt(value) {
  return value == null || Number.isNaN(Number(value)) ? "-" : String(value);
}

function shorten(text, maxLength) {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}...`;
}

function roundRect(context, x, y, width, height, radius, fill, stroke) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + radius);
  context.lineTo(x + width, y + height - radius);
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  context.lineTo(x + radius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - radius);
  context.lineTo(x, y + radius);
  context.quadraticCurveTo(x, y, x + radius, y);
  context.closePath();
  if (fill) context.fill();
  if (stroke) context.stroke();
}
