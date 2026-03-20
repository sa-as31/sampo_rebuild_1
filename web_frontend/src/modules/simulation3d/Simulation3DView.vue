<template>
  <section class="sim3d-grid">
    <article class="panel">
      <h2>3D 仿真配置</h2>

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
            <option value="drone">无人机视角</option>
          </select>
        </label>
        <label v-if="cameraMode === 'drone'">视角无人机
          <select v-model.number="selectedDroneId">
            <option v-for="agent in activeAgents" :key="agent.id" :value="agent.id">无人机 {{ agent.id + 1 }}</option>
          </select>
        </label>
        <label>回放速度 x{{ speed.toFixed(1) }}
          <input v-model.number="speed" max="2.5" min="0.2" step="0.1" type="range" />
        </label>
        <label>视图放大 x{{ zoomScale.toFixed(2) }}
          <input v-model.number="zoomScale" max="2.5" min="0.6" step="0.05" type="range" />
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
        <div class="metric"><span>放大倍率</span><strong>{{ zoomScale.toFixed(2) }}x</strong></div>
        <div class="metric"><span>视角无人机</span><strong>{{ selectedDroneText }}</strong></div>
        <div class="metric"><span>环绕周期(秒)</span><strong>{{ orbitPeriodText }}</strong></div>
      </div>
    </article>

    <article class="panel">
      <h2>3D 回放窗口</h2>
      <div class="canvas-wrap sim3d-canvas-wrap">
        <canvas
          ref="previewCanvasRef"
          height="560"
          width="960"
          @pointerdown="onCanvasPointerDown"
          @pointermove="onCanvasPointerMove"
          @pointerup="onCanvasPointerUp"
          @pointerleave="onCanvasPointerUp"
          @pointercancel="onCanvasPointerUp"
        ></canvas>
      </div>
      <div class="canvas-overlay">
        <span class="chip">Source: {{ sourceLabel }}</span>
        <span class="chip">Map: {{ playback.meta?.map_name || "-" }}</span>
        <span class="chip">Camera: {{ cameraLabel }}</span>
        <span class="chip">Step: {{ currentStep }}</span>
        <span class="chip">Speed: x{{ speed.toFixed(1) }}</span>
        <span class="chip">Zoom: x{{ zoomScale.toFixed(2) }}</span>
        <span class="chip">拖拽: 左键旋转视角</span>
        <span v-if="cameraMode === 'drone'" class="chip">局部视野: 11 x 11</span>
      </div>
    </article>

    <article class="panel">
      <h2>系统摘要</h2>
      <div class="sim3d-stack">
        <div class="sim3d-card recommend">
          <h3>渲染链路</h3>
          <p>2D 地图与回放数据实时映射到 3D 视图。</p>
        </div>
        <div class="sim3d-card">
          <h3>模型接口</h3>
          <p>支持直接调用 `/api/run-demo` 并加载回放。</p>
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
const LOCAL_VIEW_RADIUS = 5;
const DRONE_COLORS = ["#7ec8ff", "#68f2ca", "#ffd774", "#ff9191", "#8da9ff", "#d99eff"];

const previewCanvasRef = ref(null);
const scenario = ref("warehouse");
const cameraMode = ref("orbit");
const speed = ref(1.0);
const zoomScale = ref(1.0);
const orbitSpeed = ref(0.12);
const statusText = ref("3D预览待命");
const runtimeSec = ref(0);
const fps = ref(0);
const running = ref(false);
const dataSource = ref("sample");
const frameIndex = ref(0);
const playback = ref(buildSampleRun("warehouse"));
const selectedDroneId = ref(0);

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
let orbitHeightFactor = 0.48;
let frameCursor = 0;
let dragPointerId = null;
let lastDragX = 0;
let lastDragY = 0;
let viewYawOffset = 0;
let viewPitchOffset = 0;
let dragging = false;
let droneForward = { x: 1, z: 0 };
let droneCameraPos = null;

const frameCount = computed(() => playback.value?.frames?.length || 0);
const currentStep = computed(() => playback.value?.frames?.[frameIndex.value]?.step ?? 0);
const activeAgents = computed(() => playback.value?.frames?.[frameIndex.value]?.agents || []);
const sourceLabel = computed(() => (dataSource.value === "model" ? "模型推理" : "前端示例"));
const cameraLabel = computed(() => {
  if (cameraMode.value === "follow") return "跟随 1 号机";
  if (cameraMode.value === "overview") return "全局俯视";
  if (cameraMode.value === "drone") return "无人机视角";
  return "环绕观察";
});
const selectedDroneText = computed(() => {
  const focused = activeAgents.value.find((a) => a.id === selectedDroneId.value);
  return focused ? String(focused.id + 1) : "-";
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
  orbitHeightFactor = 0.48;
  viewYawOffset = 0;
  viewPitchOffset = 0;
  droneForward = { x: 1, z: 0 };
  droneCameraPos = null;
  drawFrame();
}

function startPreview() {
  if (running.value) return;
  const max = frameCount.value - 1;
  if (max >= 0 && frameIndex.value >= max) {
    resetPlaybackCursor();
  }
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
  if (cameraMode.value === "orbit" && !dragging) orbitAngle += dt * orbitSpeed.value;
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

  if (!env.width || !env.height) {
    drawEmptyHint(ctx, canvas, "无可绘制地图数据");
    return;
  }

  const focusAgent = cameraMode.value === "drone" ? resolveFocusedAgent(frame) : null;
  const prevFocusAgent = cameraMode.value === "drone" ? resolveFocusedAgent(playback.value?.frames?.[Math.max(frameIndex.value - 1, 0)]) : null;
  const leadSource = focusAgent || frame.agents?.[0];
  const lead = leadSource ? gridToWorld(leadSource.x, leadSource.y, env) : { x: 0, z: 0 };
  const sceneRadius = Math.max((env.height - 1) * CELL_SIZE, (env.width - 1) * CELL_SIZE) * 0.95 + 6;
  const camera = buildCamera(
    cameraMode.value,
    lead,
    orbitAngle,
    sceneRadius,
    orbitHeightFactor,
    viewYawOffset,
    viewPitchOffset,
    focusAgent,
    prevFocusAgent,
    env
  );

  drawGrid(ctx, canvas, camera, env, focusAgent);
  drawObstacles(ctx, canvas, camera, env, focusAgent);
  drawAgents(ctx, canvas, camera, env, frame, focusAgent);
}

function drawGrid(ctx, canvas, camera, env, focusAgent) {
  const halfX = ((env.height - 1) * CELL_SIZE) / 2;
  const halfZ = ((env.width - 1) * CELL_SIZE) / 2;
  for (let row = 0; row < env.height; row += 1) {
    if (focusAgent && !isInsideLocalWindow(row, focusAgent.y, focusAgent, LOCAL_VIEW_RADIUS)) continue;
    const x = row * CELL_SIZE - halfX;
    drawLine3D(ctx, canvas, camera, { x, y: 0, z: -halfZ }, { x, y: 0, z: halfZ }, "rgba(145,180,230,0.16)", 1);
  }
  for (let col = 0; col < env.width; col += 1) {
    if (focusAgent && !isInsideLocalWindow(focusAgent.x, col, focusAgent, LOCAL_VIEW_RADIUS)) continue;
    const z = col * CELL_SIZE - halfZ;
    drawLine3D(ctx, canvas, camera, { x: -halfX, y: 0, z }, { x: halfX, y: 0, z }, "rgba(145,180,230,0.16)", 1);
  }
}

function drawObstacles(ctx, canvas, camera, env, focusAgent) {
  const solidMode = cameraMode.value === "drone";
  for (let row = 0; row < env.height; row += 1) {
    for (let col = 0; col < env.width; col += 1) {
      if (focusAgent && !isInsideLocalWindow(row, col, focusAgent, LOCAL_VIEW_RADIUS)) continue;
      if (env.obstacles?.[row]?.[col] !== 1) continue;
      const p = gridToWorld(row, col, env);
      const block = { x: p.x - CELL_SIZE * 0.45, z: p.z - CELL_SIZE * 0.45, w: CELL_SIZE * 0.9, d: CELL_SIZE * 0.9, h: 0.9 };
      if (solidMode) {
        drawBoxSolid(ctx, canvas, camera, block);
      } else {
        drawBoxWire(ctx, canvas, camera, block, "rgba(145,160,182,0.95)");
      }
    }
  }
}

function drawAgents(ctx, canvas, camera, env, frame, focusAgent) {
  frame.agents?.forEach((agent) => {
    if (focusAgent && !isInsideLocalWindow(agent.x, agent.y, focusAgent, LOCAL_VIEW_RADIUS)) return;
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

    if (focusAgent && agent.id === focusAgent.id) {
      ctx.strokeStyle = "rgba(255,255,255,0.92)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(body.x, body.y, Math.max(5.5, body.scale * 6.8), 0, Math.PI * 2);
      ctx.stroke();
    }
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

function drawBoxSolid(ctx, canvas, camera, block) {
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
  const projected = corners.map(([x, y, z]) => projectPoint(canvas, camera, x, y, z));
  if (projected.some((p) => !p)) {
    drawBoxWire(ctx, canvas, camera, block, "rgba(145,160,182,0.95)");
    return;
  }

  const cx = x1 + block.w / 2;
  const cz = z1 + block.d / 2;
  const xFace = camera.x <= cx ? [0, 3, 7, 4] : [1, 2, 6, 5];
  const zFace = camera.z <= cz ? [0, 1, 5, 4] : [3, 2, 6, 7];
  const topFace = [4, 5, 6, 7];
  const faces = [
    { indices: xFace, fill: "#6e7d90", stroke: "#7f8ea2" },
    { indices: zFace, fill: "#5f6f84", stroke: "#73839a" },
    { indices: topFace, fill: "#8a9aae", stroke: "#99a9be" },
  ]
    .map((face) => ({
      ...face,
      pts: face.indices.map((idx) => projected[idx]),
      depth: face.indices.reduce((sum, idx) => sum + projected[idx].depth, 0) / face.indices.length,
    }))
    .sort((a, b) => b.depth - a.depth);

  faces.forEach((face) => {
    ctx.fillStyle = face.fill;
    ctx.strokeStyle = face.stroke;
    ctx.lineWidth = 1.1;
    ctx.beginPath();
    ctx.moveTo(face.pts[0].x, face.pts[0].y);
    for (let i = 1; i < face.pts.length; i += 1) {
      ctx.lineTo(face.pts[i].x, face.pts[i].y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
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

  const focal = 630 * zoomScale.value;
  const scale = focal / z2;
  return {
    x: canvas.width * 0.5 + x1 * scale,
    y: canvas.height * 0.58 - y2 * scale,
    scale: Math.max(0.3, Math.min(2.2, scale / 120)),
    depth: z2,
  };
}

function buildCamera(mode, lead, angle, radius, heightFactor, yawOffset, pitchOffset, focusAgent, prevFocusAgent, env) {
  let baseCamera = null;
  if (mode === "follow") {
    baseCamera = lookAtCamera(
      { x: lead.x - radius * 0.16, y: radius * 0.28, z: lead.z + radius * 0.24 },
      { x: lead.x, y: 0.4, z: lead.z }
    );
  } else if (mode === "overview") {
    baseCamera = lookAtCamera({ x: 0, y: radius * 0.9, z: radius * 0.52 }, { x: 0, y: 0, z: 0 });
  } else if (mode === "drone" && focusAgent && env) {
    const current = gridToWorld(focusAgent.x, focusAgent.y, env);
    const prev = prevFocusAgent ? gridToWorld(prevFocusAgent.x, prevFocusAgent.y, env) : null;
    const target = gridToWorld(focusAgent.target_x, focusAgent.target_y, env);
    const dir = resolveAgentDirection(current, prev, target);
    droneForward = dir;

    const viewDir = rotate2D(dir, yawOffset);
    const followDistance = CELL_SIZE * 2.6;
    const desiredPos = {
      x: current.x - viewDir.x * followDistance,
      y: 1.25 + pitchOffset * 1.2,
      z: current.z - viewDir.z * followDistance,
    };

    if (!droneCameraPos) {
      droneCameraPos = desiredPos;
    } else {
      const smoothing = running.value ? 0.18 : 0.35;
      droneCameraPos = {
        x: lerp(droneCameraPos.x, desiredPos.x, smoothing),
        y: lerp(droneCameraPos.y, desiredPos.y, smoothing),
        z: lerp(droneCameraPos.z, desiredPos.z, smoothing),
      };
    }

    const lookTarget = {
      x: current.x + viewDir.x * 3.0,
      y: 0.82 + pitchOffset * 0.35,
      z: current.z + viewDir.z * 3.0,
    };
    baseCamera = lookAtCamera(droneCameraPos, lookTarget);
  } else {
    baseCamera = lookAtCamera(
      { x: Math.cos(angle) * radius, y: radius * heightFactor, z: Math.sin(angle) * radius },
      { x: 0, y: 0.4, z: 0 }
    );
  }
  if (mode === "drone") {
    return {
      ...baseCamera,
      pitch: clamp(baseCamera.pitch, -1.0, 0.65),
    };
  }
  return {
    ...baseCamera,
    yaw: baseCamera.yaw + yawOffset,
    pitch: clamp(baseCamera.pitch + pitchOffset, -1.2, 1.2),
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

function onCanvasPointerDown(event) {
  if (event.button !== 0) return;
  const canvas = previewCanvasRef.value;
  if (!canvas) return;
  dragging = true;
  dragPointerId = event.pointerId;
  lastDragX = event.clientX;
  lastDragY = event.clientY;
  canvas.setPointerCapture(event.pointerId);
}

function onCanvasPointerMove(event) {
  if (!dragging || event.pointerId !== dragPointerId) return;
  const dx = event.clientX - lastDragX;
  const dy = event.clientY - lastDragY;
  lastDragX = event.clientX;
  lastDragY = event.clientY;

  if (cameraMode.value === "orbit") {
    orbitAngle += dx * 0.01;
    orbitHeightFactor = clamp(orbitHeightFactor - dy * 0.0025, 0.2, 0.92);
  } else {
    viewYawOffset = normalizeAngle(viewYawOffset + dx * 0.006);
    if (cameraMode.value === "drone") {
      viewPitchOffset = clamp(viewPitchOffset + dy * 0.003, -0.35, 0.65);
    } else {
      viewPitchOffset = clamp(viewPitchOffset + dy * 0.003, -0.5, 0.5);
    }
  }
  drawFrame();
}

function onCanvasPointerUp(event) {
  if (!dragging || event.pointerId !== dragPointerId) return;
  dragging = false;
  dragPointerId = null;
  const canvas = previewCanvasRef.value;
  if (canvas?.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function resolveAgentDirection(current, prev, target) {
  let dx = current.x - (prev?.x ?? current.x);
  let dz = current.z - (prev?.z ?? current.z);
  if (Math.hypot(dx, dz) < 0.001) {
    dx = target.x - current.x;
    dz = target.z - current.z;
  }
  if (Math.hypot(dx, dz) < 0.001) {
    dx = droneForward.x;
    dz = droneForward.z;
  }
  const len = Math.hypot(dx, dz) || 1;
  return { x: dx / len, z: dz / len };
}

function rotate2D(vector, radians) {
  const c = Math.cos(radians);
  const s = Math.sin(radians);
  return {
    x: vector.x * c - vector.z * s,
    z: vector.x * s + vector.z * c,
  };
}

function normalizeAngle(value) {
  let angle = value;
  while (angle > Math.PI) angle -= Math.PI * 2;
  while (angle < -Math.PI) angle += Math.PI * 2;
  return angle;
}

function drawEmptyHint(ctx, canvas, text) {
  ctx.fillStyle = "rgba(205,225,255,0.86)";
  ctx.font = '16px "PingFang SC", "Noto Sans SC", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);
}

function resolveFocusedAgent(frame) {
  const agents = frame?.agents || [];
  if (!agents.length) return null;
  return agents.find((agent) => agent.id === selectedDroneId.value) || agents[0];
}

function isInsideLocalWindow(row, col, focusAgent, radius) {
  return Math.abs(row - focusAgent.x) <= radius && Math.abs(col - focusAgent.y) <= radius;
}

watch(scenario, () => {
  if (dataSource.value === "sample") loadSamplePlayback();
});

watch(cameraMode, () => {
  if (cameraMode.value === "drone") {
    droneCameraPos = null;
    droneForward = { x: 1, z: 0 };
  }
  drawFrame();
});
watch(zoomScale, () => drawFrame());
watch(activeAgents, (agents) => {
  if (!agents.length) return;
  if (!agents.some((agent) => agent.id === selectedDroneId.value)) {
    selectedDroneId.value = agents[0].id;
  }
  drawFrame();
});
watch(selectedDroneId, () => drawFrame());

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
