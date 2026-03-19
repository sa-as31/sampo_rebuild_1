<template>
  <section class="sim3d-grid">
    <article class="panel">
      <h2>3D 仿真配置</h2>
      <p>作为后续真实 3D 引擎接入前的页面骨架，先验证交互流程与展示信息。</p>

      <div class="field-grid">
        <label>仿真场景模板
          <select v-model="scenario">
            <option value="warehouse">仓储巡检 3D</option>
            <option value="campus">园区配送 3D</option>
            <option value="emergency">应急调度 3D</option>
          </select>
        </label>
        <label>镜头模式
          <select v-model="cameraMode">
            <option value="orbit">环绕观察</option>
            <option value="follow">跟随 1 号机</option>
            <option value="overview">全局俯视</option>
          </select>
        </label>
        <label>仿真速度 x{{ speed.toFixed(1) }}
          <input v-model.number="speed" max="2.5" min="0.2" step="0.1" type="range" />
        </label>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="startPreview">开始</button>
        <button class="btn secondary" @click="pausePreview">暂停</button>
        <button class="btn secondary" @click="resetPreview">重置</button>
      </div>
      <div class="status-chip">{{ statusText }}</div>

      <div class="metrics">
        <div class="metric"><span>场景无人机数</span><strong>{{ droneCount }}</strong></div>
        <div class="metric"><span>运行时长(秒)</span><strong>{{ runtimeSec.toFixed(1) }}</strong></div>
        <div class="metric"><span>帧率估计</span><strong>{{ fps }}</strong></div>
        <div class="metric"><span>引擎状态</span><strong style="font-size: 18px">{{ engineTag }}</strong></div>
      </div>
    </article>

    <article class="panel">
      <h2>3D 预览窗口</h2>
      <p>当前为轻量占位渲染层，后续可平滑替换为 Three.js/Cesium 实时渲染。</p>
      <div class="canvas-wrap sim3d-canvas-wrap">
        <canvas ref="previewCanvasRef" height="560" width="960"></canvas>
      </div>
      <div class="canvas-overlay">
        <span class="chip">Scenario: {{ scenarioLabel }}</span>
        <span class="chip">Camera: {{ cameraLabel }}</span>
        <span class="chip">Speed: x{{ speed.toFixed(1) }}</span>
      </div>
    </article>

    <article class="panel">
      <h2>3D 技术路线建议</h2>
      <p>毕业设计场景下，建议优先选择可控、可演示、可扩展的方案。</p>
      <div class="sim3d-stack">
        <div class="sim3d-card recommend">
          <h3>推荐：Three.js + glTF + WebSocket</h3>
          <p>与当前前端集成成本低，能快速实现可交互 3D 地图、无人机模型、轨迹回放和状态面板。</p>
        </div>
        <div class="sim3d-card">
          <h3>备选：CesiumJS（地理场景）</h3>
          <p>适合真实经纬度与大范围地图，但工程复杂度更高，前期投入更大。</p>
        </div>
        <div class="sim3d-card">
          <h3>备选：Unity WebGL</h3>
          <p>视觉效果强，但与现有 Web 业务页面耦合较重，不利于快速论文迭代。</p>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

const previewCanvasRef = ref(null);
const scenario = ref("warehouse");
const cameraMode = ref("orbit");
const speed = ref(1.0);
const statusText = ref("3D预览待命");
const runtimeSec = ref(0);
const fps = ref(0);
const running = ref(false);

let rafId = null;
let lastTs = 0;
let fpsTs = 0;
let frameCounter = 0;

const scenarioLabel = computed(() => {
  if (scenario.value === "campus") return "园区配送 3D";
  if (scenario.value === "emergency") return "应急调度 3D";
  return "仓储巡检 3D";
});

const cameraLabel = computed(() => {
  if (cameraMode.value === "follow") return "跟随 1 号机";
  if (cameraMode.value === "overview") return "全局俯视";
  return "环绕观察";
});

const droneCount = computed(() => {
  if (scenario.value === "campus") return 10;
  if (scenario.value === "emergency") return 12;
  return 8;
});

const engineTag = computed(() => "Prototype");

function startPreview() {
  if (running.value) return;
  running.value = true;
  statusText.value = `3D预览运行中：${scenarioLabel.value}`;
  lastTs = 0;
  fpsTs = 0;
  frameCounter = 0;
  rafId = window.requestAnimationFrame(tick);
}

function pausePreview() {
  running.value = false;
  if (rafId) window.cancelAnimationFrame(rafId);
  rafId = null;
  statusText.value = "3D预览已暂停";
}

function resetPreview() {
  runtimeSec.value = 0;
  drawFrame();
  statusText.value = "3D预览已重置";
}

function tick(ts) {
  if (!running.value) return;
  if (!lastTs) lastTs = ts;
  if (!fpsTs) fpsTs = ts;

  const dt = Math.max((ts - lastTs) / 1000, 0);
  lastTs = ts;
  runtimeSec.value += dt * speed.value;
  drawFrame();

  frameCounter += 1;
  if (ts - fpsTs >= 1000) {
    fps.value = frameCounter;
    frameCounter = 0;
    fpsTs = ts;
  }

  rafId = window.requestAnimationFrame(tick);
}

function drawFrame() {
  const canvas = previewCanvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#091a33");
  gradient.addColorStop(1, "#050d1d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const lead = getDronePosition(0, runtimeSec.value, scenario.value);
  const camera = buildCamera(cameraMode.value, runtimeSec.value, lead);
  drawGrid(ctx, canvas, camera);
  drawObstacles(ctx, canvas, camera, getObstacleBlocks(scenario.value));
  drawDrones(ctx, canvas, camera);
}

function drawGrid(ctx, canvas, camera) {
  for (let i = -10; i <= 10; i += 1) {
    drawLine3D(ctx, canvas, camera, { x: i, y: 0, z: -10 }, { x: i, y: 0, z: 10 }, "rgba(145,180,230,0.16)", 1);
    drawLine3D(ctx, canvas, camera, { x: -10, y: 0, z: i }, { x: 10, y: 0, z: i }, "rgba(145,180,230,0.16)", 1);
  }
}

function drawObstacles(ctx, canvas, camera, blocks) {
  blocks.forEach((block) => {
    drawBoxWire(ctx, canvas, camera, block, "rgba(145,160,182,0.95)");
  });
}

function drawDrones(ctx, canvas, camera) {
  for (let i = 0; i < droneCount.value; i += 1) {
    const p = getDronePosition(i, runtimeSec.value, scenario.value);
    const body = projectPoint(canvas, camera, p.x, p.y, p.z);
    const ground = projectPoint(canvas, camera, p.x, 0.05, p.z);
    if (!body || !ground) continue;

    const color = ["#7ec8ff", "#68f2ca", "#ffd774", "#ff9191"][i % 4];
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
  }
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
  const edgeIds = [
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

  edgeIds.forEach(([a, b]) => {
    const pa = corners[a];
    const pb = corners[b];
    drawLine3D(
      ctx,
      canvas,
      camera,
      { x: pa[0], y: pa[1], z: pa[2] },
      { x: pb[0], y: pb[1], z: pb[2] },
      color,
      1.8
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

// Minimal perspective projection for placeholder 3D preview.
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

function buildCamera(mode, t, lead) {
  if (mode === "follow") {
    return lookAtCamera(
      { x: lead.x - 3.2, y: 4.5, z: lead.z + 4.4 },
      { x: lead.x, y: 0.8, z: lead.z }
    );
  }
  if (mode === "overview") {
    return lookAtCamera({ x: 0, y: 15.5, z: 10.5 }, { x: 0, y: 0, z: 0 });
  }
  const angle = t * 0.26;
  return lookAtCamera(
    { x: Math.cos(angle) * 17, y: 8.6, z: Math.sin(angle) * 17 },
    { x: 0, y: 0.5, z: 0 }
  );
}

function lookAtCamera(position, target) {
  const dx = target.x - position.x;
  const dy = target.y - position.y;
  const dz = target.z - position.z;
  const yaw = Math.atan2(dx, dz);
  const distXZ = Math.hypot(dx, dz);
  const pitch = -Math.atan2(dy, distXZ);
  return { x: position.x, y: position.y, z: position.z, yaw, pitch };
}

function getDronePosition(index, t, template) {
  const seed = index * 0.68;
  if (template === "campus") {
    return {
      x: Math.sin(t * 0.55 + seed) * 7.2,
      y: 0.7 + Math.sin(t * 1.8 + seed) * 0.24,
      z: Math.cos(t * 0.45 + seed * 0.8) * 7.2,
    };
  }
  if (template === "emergency") {
    return {
      x: Math.sin(t * 0.9 + seed) * 6.5,
      y: 0.85 + Math.sin(t * 2.3 + seed) * 0.3,
      z: Math.sin((t * 0.7 + seed) * 2) * 3.8,
    };
  }
  return {
    x: Math.sin(t * 0.75 + seed) * 8.2,
    y: 0.72 + Math.cos(t * 2.2 + seed) * 0.22,
    z: Math.cos(t * 0.56 + seed) * 5.8,
  };
}

function getObstacleBlocks(template) {
  if (template === "campus") {
    return [
      { x: -6, z: -2, w: 3, d: 4, h: 1.6 },
      { x: 3, z: -7, w: 4, d: 3, h: 1.4 },
      { x: 2, z: 3, w: 5, d: 4, h: 1.8 },
    ];
  }
  if (template === "emergency") {
    return [
      { x: -7, z: -1, w: 5, d: 2, h: 1.5 },
      { x: 2, z: -1, w: 5, d: 2, h: 1.5 },
      { x: -1, z: -7, w: 2, d: 5, h: 1.5 },
      { x: -1, z: 2, w: 2, d: 5, h: 1.5 },
    ];
  }
  return [
    { x: -8, z: -6, w: 3, d: 11, h: 1.3 },
    { x: -2, z: -6, w: 3, d: 11, h: 1.3 },
    { x: 4, z: -6, w: 3, d: 11, h: 1.3 },
  ];
}

watch([scenario, cameraMode], () => {
  resetPreview();
  if (running.value) statusText.value = `3D预览运行中：${scenarioLabel.value}`;
});

onMounted(() => {
  drawFrame();
  startPreview();
});

onUnmounted(() => pausePreview());
</script>
