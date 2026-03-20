<template>
  <section class="sim3d-grid">
    <article class="panel">
      <h2>3D 仿真配置</h2>
      <p>将现有 2D 地图与模型回放结果映射到 3D 视角中展示。</p>

      <div class="field-grid">
        <label>示例模板（仅前端示例）
          <select v-model="scenario">
            <option value="warehouse">仓储巡检 2D</option>
            <option value="campus">园区配送 2D</option>
            <option value="emergency">应急调度 2D</option>
          </select>
        </label>
        <label>镜头模式
          <select v-model="cameraMode">
            <option value="orbit">环绕观察</option>
            <option value="follow">跟随 1 号机</option>
            <option value="overview">全局俯视</option>
          </select>
        </label>
        <label>回放速度 x{{ speed.toFixed(1) }}
          <input v-model.number="speed" max="2.5" min="0.2" step="0.1" type="range" />
        </label>
        <label v-if="cameraMode === 'orbit'">环绕速度 {{ orbitSpeed.toFixed(2) }} rad/s
          <input v-model.number="orbitSpeed" max="0.35" min="0.02" step="0.01" type="range" />
        </label>
      </div>

      <div class="field-grid" style="margin-top: 10px">
        <label>map_name <input v-model="form.map_name" /></label>
        <label>num_agents <input v-model.number="form.num_agents" min="1" type="number" /></label>
        <label>max_frames <input v-model.number="form.max_frames" min="1" type="number" /></label>
        <label>device
          <select v-model="form.device">
            <option value="cpu">cpu</option>
            <option value="gpu">gpu</option>
          </select>
        </label>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="runModelPlayback">运行当前模型并加载3D</button>
        <button class="btn secondary" @click="loadSamplePlayback">加载2D示例</button>
        <button class="btn secondary" @click="startPreview">播放</button>
        <button class="btn secondary" @click="pausePreview">暂停</button>
        <button class="btn secondary" @click="resetPreview">重置</button>
      </div>
      <div class="status-chip">{{ statusText }}</div>

      <div class="metrics">
        <div class="metric"><span>数据来源</span><strong style="font-size: 18px">{{ sourceLabel }}</strong></div>
        <div class="metric"><span>地图尺寸</span><strong style="font-size: 18px">{{ mapSizeText }}</strong></div>
        <div class="metric"><span>当前步</span><strong>{{ currentStep }}</strong></div>
        <div class="metric"><span>总帧数</span><strong>{{ frameCount }}</strong></div>
        <div class="metric"><span>帧率估计</span><strong>{{ fps }}</strong></div>
        <div class="metric"><span>环绕周期(秒)</span><strong>{{ orbitPeriodText }}</strong></div>
      </div>
    </article>

    <article class="panel">
      <h2>3D 回放窗口</h2>
      <p>无人机和障碍均来自当前 2D 回放数据，按网格坐标转换为 3D 空间。</p>
      <div class="canvas-wrap sim3d-canvas-wrap">
        <canvas ref="previewCanvasRef" height="560" width="960"></canvas>
      </div>
      <div class="canvas-overlay">
        <span class="chip">Source: {{ sourceLabel }}</span>
        <span class="chip">Map: {{ playback.meta?.map_name || "-" }}</span>
        <span class="chip">Camera: {{ cameraLabel }}</span>
        <span class="chip">Step: {{ currentStep }}</span>
        <span class="chip">Speed: x{{ speed.toFixed(1) }}</span>
      </div>
    </article>

    <article class="panel">
      <h2>3D 技术路线建议</h2>
      <p>目前已实现“2D 推理结果 -> 3D 展示层”桥接，后续可替换为真实引擎。</p>
      <div class="sim3d-stack">
        <div class="sim3d-card recommend">
          <h3>推荐：Three.js + glTF + WebSocket</h3>
          <p>保留当前数据接口，替换渲染层即可升级到真实 3D 模型与材质。</p>
        </div>
        <div class="sim3d-card">
          <h3>当前已打通</h3>
          <p>可调用 `/api/run-demo`，读取后端 `environment` 和 `frames`，并在 3D 中回放。</p>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { fetchDefaults, runInference } from "../../services/api";
import { buildSampleRun } from "../shared/renderer";

const CELL_SIZE = 1.2;
const DRONE_COLORS = ["#7ec8ff", "#68f2ca", "#ffd774", "#ff9191", "#8da9ff", "#d99eff"];

const previewCanvasRef = ref(null);
const scenario = ref("warehouse");
const cameraMode = ref("orbit");
const speed = ref(1.0);
const orbitSpeed = ref(0.12);
const statusText = ref("3D预览待命");
const runtimeSec = ref(0);
const fps = ref(0);
const running = ref(false);
const dataSource = ref("sample");
const frameIndex = ref(0);
const playback = ref(buildSampleRun("warehouse"));

const form = reactive({
  cfg_dir: "results/train_dir/0001/exp",
  checkpoint_path: "results/train_dir/0001/exp/checkpoint_p0/best/best_model_obj_+0000000.000000_step_000921600_1772213120.pth",
  device: "cpu",
  map_name: "mazes-s0_wc8_od55",
  num_agents: 16,
  max_episode_steps: 64,
  max_frames: 64,
  seed: 7,
  save_svg: "results/mac_eval/web-3d.svg",
  render: false,
});

let rafId = null;
let lastTs = 0;
let fpsTs = 0;
let frameCounter = 0;
let orbitAngle = 0;
let frameCursor = 0;

const frameCount = computed(() => playback.value?.frames?.length || 0);
const currentStep = computed(() => playback.value?.frames?.[frameIndex.value]?.step ?? 0);
const sourceLabel = computed(() => (dataSource.value === "model" ? "模型推理" : "前端示例"));
const cameraLabel = computed(() => {
  if (cameraMode.value === "follow") return "跟随 1 号机";
  if (cameraMode.value === "overview") return "全局俯视";
  return "环绕观察";
});
const mapSizeText = computed(() => {
  const env = playback.value?.environment;
  if (!env) return "-";
  return `${env.height} x ${env.width}`;
});
const orbitPeriodText = computed(() => (cameraMode.value === "orbit" ? (Math.PI * 2 / orbitSpeed.value).toFixed(1) : "--"));

function resetPlaybackCursor() {
  frameCursor = 0;
  frameIndex.value = 0;
  runtimeSec.value = 0;
  orbitAngle = 0;
  drawFrame();
}

function startPreview() {
  if (running.value) return;
  running.value = true;
  statusText.value = `${sourceLabel.value}回放运行中`;
  lastTs = 0;
  fpsTs = 0;
  frameCounter = 0;
  rafId = window.requestAnimationFrame(tick);
}

function pausePreview() {
  running.value = false;
  if (rafId) window.cancelAnimationFrame(rafId);
  rafId = null;
  statusText.value = `${sourceLabel.value}回放已暂停`;
}

function resetPreview() {
  resetPlaybackCursor();
  statusText.value = `${sourceLabel.value}回放已重置`;
}

async function runModelPlayback() {
  const shouldResume = running.value;
  pausePreview();
  statusText.value = "正在请求后端推理并映射到3D...";
  try {
    const payload = await runInference({ ...form });
    playback.value = payload;
    dataSource.value = "model";
    resetPlaybackCursor();
    statusText.value = `模型推理回放已加载：${payload.meta?.map_name || form.map_name}`;
    if (shouldResume) startPreview();
  } catch (error) {
    statusText.value = `模型推理失败：${error.message}`;
  }
}

function loadSamplePlayback() {
  const shouldResume = running.value;
  pausePreview();
  playback.value = buildSampleRun(scenario.value);
  dataSource.value = "sample";
  resetPlaybackCursor();
  statusText.value = `已加载示例2D地图：${scenario.value}`;
  if (shouldResume) startPreview();
}

function tick(ts) {
  if (!running.value) return;
  if (!lastTs) lastTs = ts;
  if (!fpsTs) fpsTs = ts;

  const dt = Math.max((ts - lastTs) / 1000, 0);
  lastTs = ts;
  runtimeSec.value += dt;
  if (cameraMode.value === "orbit") orbitAngle += dt * orbitSpeed.value;
  advanceFrame(dt);
  drawFrame();

  frameCounter += 1;
  if (ts - fpsTs >= 1000) {
    fps.value = frameCounter;
    frameCounter = 0;
    fpsTs = ts;
  }

  rafId = window.requestAnimationFrame(tick);
}

function advanceFrame(dt) {
  const max = frameCount.value - 1;
  if (max <= 0) return;
  frameCursor += dt * speed.value * 5;
  if (frameCursor >= max) {
    frameCursor = max;
    frameIndex.value = max;
    pausePreview();
    statusText.value = `${sourceLabel.value}回放完成`;
    return;
  }
  frameIndex.value = Math.floor(frameCursor);
}

function drawFrame() {
  const canvas = previewCanvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const env = playback.value?.environment;
  const frame = playback.value?.frames?.[frameIndex.value];
  if (!env || !frame) return;

  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#091a33");
  gradient.addColorStop(1, "#050d1d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const lead = frame.agents?.[0] ? gridToWorld(frame.agents[0].x, frame.agents[0].y, env) : { x: 0, z: 0 };
  const sceneRadius = Math.max((env.height - 1) * CELL_SIZE, (env.width - 1) * CELL_SIZE) * 0.95 + 6;
  const camera = buildCamera(cameraMode.value, lead, orbitAngle, sceneRadius);

  drawGrid(ctx, canvas, camera, env);
  drawObstacles(ctx, canvas, camera, env);
  drawAgents(ctx, canvas, camera, env, frame);
}

function drawGrid(ctx, canvas, camera, env) {
  const halfX = ((env.height - 1) * CELL_SIZE) / 2;
  const halfZ = ((env.width - 1) * CELL_SIZE) / 2;
  for (let row = 0; row < env.height; row += 1) {
    const x = row * CELL_SIZE - halfX;
    drawLine3D(ctx, canvas, camera, { x, y: 0, z: -halfZ }, { x, y: 0, z: halfZ }, "rgba(145,180,230,0.16)", 1);
  }
  for (let col = 0; col < env.width; col += 1) {
    const z = col * CELL_SIZE - halfZ;
    drawLine3D(ctx, canvas, camera, { x: -halfX, y: 0, z }, { x: halfX, y: 0, z }, "rgba(145,180,230,0.16)", 1);
  }
}

function drawObstacles(ctx, canvas, camera, env) {
  for (let row = 0; row < env.height; row += 1) {
    for (let col = 0; col < env.width; col += 1) {
      if (env.obstacles?.[row]?.[col] !== 1) continue;
      const p = gridToWorld(row, col, env);
      drawBoxWire(
        ctx,
        canvas,
        camera,
        { x: p.x - CELL_SIZE * 0.45, z: p.z - CELL_SIZE * 0.45, w: CELL_SIZE * 0.9, d: CELL_SIZE * 0.9, h: 0.9 },
        "rgba(145,160,182,0.95)"
      );
    }
  }
}

function drawAgents(ctx, canvas, camera, env, frame) {
  frame.agents?.forEach((agent) => {
    const c = DRONE_COLORS[agent.id % DRONE_COLORS.length];
    const bodyPos = gridToWorld(agent.x, agent.y, env);
    const targetPos = gridToWorld(agent.target_x, agent.target_y, env);

    const body = projectPoint(canvas, camera, bodyPos.x, 0.72, bodyPos.z);
    const ground = projectPoint(canvas, camera, bodyPos.x, 0.03, bodyPos.z);
    const target = projectPoint(canvas, camera, targetPos.x, 0.08, targetPos.z);
    if (!body || !ground) return;

    if (target) {
      ctx.strokeStyle = c;
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

    ctx.fillStyle = c;
    ctx.beginPath();
    ctx.arc(body.x, body.y, Math.max(3.2, body.scale * 4.6), 0, Math.PI * 2);
    ctx.fill();
  });
}

function gridToWorld(row, col, env) {
  const halfX = ((env.height - 1) * CELL_SIZE) / 2;
  const halfZ = ((env.width - 1) * CELL_SIZE) / 2;
  return {
    x: row * CELL_SIZE - halfX,
    z: col * CELL_SIZE - halfZ,
  };
}

function drawBoxWire(ctx, canvas, camera, block, color) {
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
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 0],
    [4, 5],
    [5, 6],
    [6, 7],
    [7, 4],
    [0, 4],
    [1, 5],
    [2, 6],
    [3, 7],
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
      1.5
    );
  });
}

function drawLine3D(ctx, canvas, camera, a, b, color, width) {
  const pa = projectPoint(canvas, camera, a.x, a.y, a.z);
  const pb = projectPoint(canvas, camera, b.x, b.y, b.z);
  if (!pa || !pb) return;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.stroke();
}

function projectPoint(canvas, camera, x, y, z) {
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

  const focal = 630;
  const scale = focal / z2;
  return {
    x: canvas.width * 0.5 + x1 * scale,
    y: canvas.height * 0.58 - y2 * scale,
    scale: Math.max(0.3, Math.min(2.2, scale / 120)),
  };
}

function buildCamera(mode, lead, angle, radius) {
  if (mode === "follow") {
    return lookAtCamera(
      { x: lead.x - radius * 0.16, y: radius * 0.28, z: lead.z + radius * 0.24 },
      { x: lead.x, y: 0.4, z: lead.z }
    );
  }
  if (mode === "overview") {
    return lookAtCamera({ x: 0, y: radius * 0.9, z: radius * 0.52 }, { x: 0, y: 0, z: 0 });
  }
  return lookAtCamera(
    { x: Math.cos(angle) * radius, y: radius * 0.48, z: Math.sin(angle) * radius },
    { x: 0, y: 0.4, z: 0 }
  );
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

watch(scenario, () => {
  if (dataSource.value === "sample") loadSamplePlayback();
});

watch(cameraMode, () => drawFrame());

onMounted(async () => {
  try {
    const defaults = await fetchDefaults();
    Object.assign(form, defaults.defaults || {});
  } catch {
    // Keep local defaults when backend defaults are unavailable.
  }
  loadSamplePlayback();
  startPreview();
});

onUnmounted(() => pausePreview());
</script>
