<template>
  <section class="ops-integrated-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, embedded: isEmbedded }">
    <aside v-if="!isEmbedded" class="panel ops-sidebar-panel" :class="{ collapsed: sidebarCollapsed }">
      <div class="ops-sidebar-head">
        <h2>{{ isAdmin ? "任务参数" : "任务概览" }}</h2>
        <button class="btn secondary" @click="toggleSidebar">{{ sidebarCollapsed ? "展开" : "收起" }}</button>
      </div>

      <div v-if="!sidebarCollapsed && isAdmin" class="field-grid">
        <label>参数模板
          <select v-model="selectedTemplateId" :disabled="!isAdmin" @change="applySavedTemplate">
            <option value="">未选择（手动配置）</option>
            <option v-for="item in savedTemplates" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </label>
        <label>任务模板
          <select v-model="selectedTemplate" :disabled="!isAdmin" @change="applyTemplate">
            <option value="warehouse">仓储巡检</option>
            <option value="campus">园区配送</option>
            <option value="emergency">应急调度</option>
          </select>
        </label>
        <label>执行数据源
          <select v-model="executionSource" :disabled="!isAdmin">
            <option value="sample">后端样例仿真</option>
            <option value="model">模型推理回放</option>
          </select>
        </label>
        <label>任务批次名称 <input v-model="missionName" :disabled="!isAdmin" placeholder="如：night_shift_batch_03" /></label>
        <label>无人机数量 <input v-model.number="taskConfig.num_agents" :disabled="!isAdmin" min="1" type="number" /></label>
        <label>最大帧数 <input v-model.number="taskConfig.max_frames" :disabled="!isAdmin" min="4" type="number" /></label>
        <label>节拍(ms) <input v-model.number="taskConfig.tick_ms" :disabled="!isAdmin" min="120" step="20" type="number" /></label>

        <label>3D镜头
          <select v-model="cameraMode">
            <option value="orbit">环绕观察</option>
            <option value="overview">俯视全局</option>
            <option value="follow">跟随选中无人机</option>
          </select>
        </label>
        <label>3D放大 x{{ zoomScale.toFixed(2) }}
          <input v-model.number="zoomScale" max="2.5" min="0.6" step="0.05" type="range" />
        </label>
        <label v-if="cameraMode === 'orbit'">环绕速度 {{ orbitSpeed.toFixed(2) }} rad/s
          <input v-model.number="orbitSpeed" max="0.35" min="0.02" step="0.01" type="range" />
        </label>

        <div class="btn-row" style="margin-top: 10px">
          <button class="btn" @click="startOpsRun">开始任务</button>
          <button class="btn secondary" @click="pauseOpsRun">暂停</button>
          <button class="btn secondary" @click="resumeOpsRun">继续</button>
          <button class="btn secondary" @click="stopOpsRun">停止</button>
          <button v-if="isAdmin" class="btn secondary" @click="saveCurrentAsTemplate">保存为模板</button>
          <button v-if="isAdmin" class="btn secondary" @click="deleteCurrentTemplate">删除当前模板</button>
        </div>
      </div>

      <div v-else-if="!sidebarCollapsed" class="ops-executor-summary">
        <div class="status-chip ops-mode-chip">参数已锁定</div>
        <div class="admin-highlight-card compact">
          <p>当前任务</p>
          <strong>{{ runtime.task?.mission_name || "未载入任务" }}</strong>
          <span>任务ID：{{ currentTaskId || "-" }}</span>
          <span>阶段：{{ runtime.task?.status || "待命" }}</span>
        </div>
        <div class="admin-highlight-card compact">
          <p>席位状态</p>
          <strong>观察与值守</strong>
          <span>启动、延期和异常上报在任务中心处理。</span>
        </div>
      </div>
    </aside>

    <article class="panel ops-main-panel" :class="{ 'ops-main-panel-embedded': isEmbedded }">
      <div class="ops-main-head">
        <div>
          <p class="section-kicker">{{ isEmbedded ? "MISSION STAGE" : "LIVE EXECUTION" }}</p>
          <h2>{{ isEmbedded ? "实时任务舞台" : "实时联合运行" }}</h2>
        </div>
        <button v-if="sidebarCollapsed && !isEmbedded" class="btn secondary" @click="toggleSidebar">显示参数侧栏</button>
      </div>
      <div class="status-chip ops-status-banner">{{ opsStatus }}</div>
      <div class="ops-inline-meta">
        <span>任务ID: {{ currentTaskId || "未创建" }}</span>
        <span>状态: {{ runtime.task?.status || "待命" }}</span>
        <span>当前步: {{ runtime.metrics.step || activeFrame.step || 0 }}</span>
      </div>

      <div class="status-cards" style="margin-top: 10px">
        <div class="status-card"><p>在线无人机数</p><strong>{{ statusCards.online }}</strong></div>
        <div class="status-card"><p>累计完成任务</p><strong>{{ statusCards.completed }}</strong></div>
        <div v-if="!isEmbedded" class="status-card"><p>冲突告警数</p><strong>{{ statusCards.conflicts }}</strong></div>
        <div v-if="!isEmbedded" class="status-card"><p>平均任务时延(步)</p><strong>{{ statusCards.latency }}</strong></div>
      </div>

      <div class="ops-dual-view-grid">
        <section class="ops-view-card">
          <h3>2D 俯视运行状态</h3>
          <div class="ops-inline-meta ops-card-meta">
            <span>选中无人机 {{ selectedDroneId + 1 }}</span>
            <span>{{ currentTaskId && !isTerminalStatus(runtime.task?.status) ? "运行锁定" : "待命可编辑" }}</span>
          </div>
          <div class="canvas-wrap" style="margin-top: 8px">
            <canvas ref="opsCanvasRef" width="880" height="500" @click="onOpsCanvasClick"></canvas>
          </div>
        </section>

        <section class="ops-view-card">
          <h3>3D 运行状态</h3>
          <div class="ops-inline-meta ops-card-meta">
            <span>镜头 {{ cameraModeLabel }}</span>
            <span>放大 x{{ zoomScale.toFixed(2) }}</span>
          </div>
          <div class="canvas-wrap" style="margin-top: 8px">
            <canvas ref="ops3dCanvasRef" width="880" height="500"></canvas>
          </div>
        </section>
      </div>

      <div v-if="!isEmbedded" class="field-grid" style="margin-top: 10px; max-width: 280px">
        <label>当前选中无人机
          <select v-model.number="selectedDroneId">
            <option v-for="d in fleetRows" :key="d.id" :value="d.id">无人机 {{ d.id + 1 }}</option>
          </select>
        </label>
      </div>

      <table v-if="!isEmbedded" class="fleet-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>当前位置</th>
            <th>目标点</th>
            <th>状态</th>
            <th>剩余距离</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in fleetRows" :key="row.id">
            <td>{{ row.id + 1 }}</td>
            <td>({{ row.x }}, {{ row.y }})</td>
            <td>({{ row.tx }}, {{ row.ty }})</td>
            <td>{{ row.state }}</td>
            <td>{{ row.dist }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="!isEmbedded" class="ops-alerts">
        <h3>实时告警</h3>
        <div v-if="alerts.length === 0" class="ops-alert-empty">当前无告警</div>
        <div v-for="alert in alerts" :key="`${alert.ts}-${alert.code}`" class="ops-alert-item" :class="`level-${alert.level}`">
          <span class="ops-alert-code">[{{ alert.code }}]</span>
          <span>{{ alert.message }}</span>
          <span class="ops-alert-step">step {{ alert.frame_step }}</span>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { buildSampleRun, createRenderer } from "../shared/renderer";
import { connectOpsTaskEvents, controlOpsTask, createOpsTask, getOpsTask } from "../../services/api";
import { deleteOpsTemplate, loadOpsTemplates, upsertOpsTemplate } from "../shared/templateStore";

const props = defineProps({
  role: {
    type: String,
    default: "executor",
  },
  currentUser: {
    type: Object,
    default: null,
  },
  embedded: {
    type: Boolean,
    default: false,
  },
  focusTaskId: {
    type: String,
    default: "",
  },
});

const CELL_SIZE = 1.2;
const DRONE_COLORS = ["#7ec8ff", "#68f2ca", "#ffd774", "#ff9191", "#8da9ff", "#d99eff"];

const renderer = createRenderer();
const opsCanvasRef = ref(null);
const ops3dCanvasRef = ref(null);
const selectedTemplate = ref("warehouse");
const missionName = ref("enterprise_batch_demo");
const selectedDroneId = ref(0);
const executionSource = ref("sample");
const selectedTemplateId = ref("");
const savedTemplates = ref(loadOpsTemplates());
const sidebarCollapsed = ref(false);
const cameraMode = ref("orbit");
const zoomScale = ref(1.0);
const orbitSpeed = ref(0.12);
const DEFAULT_TASK_TICK_MS = 600;

const taskConfig = reactive({
  num_agents: 16,
  max_frames: 64,
  tick_ms: DEFAULT_TASK_TICK_MS,
  device: "cpu",
});

const opsStatus = ref("待命");
const currentTaskId = ref("");
const eventSeq = ref(0);
const eventSource = ref(null);
let reconnectTimer = null;

const samplePlayback = ref(buildSampleRun(selectedTemplate.value));
const runtime = reactive({
  task: null,
  environment: null,
  frame: null,
  metrics: {
    online: 0,
    tasks_completed: 0,
    throughput: 0,
    avg_latency: 0,
    frame_conflicts: 0,
    cumulative_conflicts: 0,
    alerts: 0,
    step: 0,
    status: "IDLE",
  },
  alerts: [],
});

let rafId = null;
let lastTs = 0;
let orbitAngle = 0;
let resizeTimer = null;

const activeEnvironment = computed(() => runtime.environment || samplePlayback.value.environment);
const activeFrame = computed(() => runtime.frame || samplePlayback.value.frames[0] || { agents: [], vertex_conflicts: 0, step: 0 });
const alerts = computed(() => runtime.alerts || []);
const cameraModeLabel = computed(() => {
  if (cameraMode.value === "overview") return "俯视全局";
  if (cameraMode.value === "follow") return "跟随选中无人机";
  return "环绕观察";
});
const isAdmin = computed(() => props.role === "admin");
const isEmbedded = computed(() => !!props.embedded);

const statusCards = computed(() => {
  const frame = activeFrame.value;
  const online = runtime.metrics.online || frame.agents.length;
  const completed = runtime.metrics.tasks_completed || frame.agents.filter((a) => a.done).length;
  const conflicts = runtime.metrics.cumulative_conflicts || frame.vertex_conflicts || 0;
  const latency = runtime.metrics.avg_latency ? Number(runtime.metrics.avg_latency).toFixed(1) : "0.0";
  return { online, completed, conflicts, latency };
});

const fleetRows = computed(() => {
  const frame = activeFrame.value;
  return frame.agents.map((a) => ({
    id: a.id,
    x: a.x,
    y: a.y,
    tx: a.target_x,
    ty: a.target_y,
    state: a.done ? "已完成" : "执行中",
    dist: Math.abs(a.x - a.target_x) + Math.abs(a.y - a.target_y),
  }));
});

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
}

function applyTemplate() {
  selectedTemplateId.value = "";
  samplePlayback.value = buildSampleRun(selectedTemplate.value);
  selectedDroneId.value = 0;
  drawAll();
  opsStatus.value = `已切换模板：${templateLabel(selectedTemplate.value)}`;
}

function applySavedTemplate() {
  const template = savedTemplates.value.find((item) => item.id === selectedTemplateId.value);
  if (!template) return;
  selectedTemplate.value = template.template;
  executionSource.value = template.source;
  missionName.value = template.mission_name || missionName.value;
  taskConfig.num_agents = Number(template.num_agents || taskConfig.num_agents);
  taskConfig.max_frames = Number(template.max_frames || taskConfig.max_frames);
  taskConfig.tick_ms = Number(template.tick_ms || taskConfig.tick_ms);
  samplePlayback.value = buildSampleRun(selectedTemplate.value);
  selectedDroneId.value = 0;
  drawAll();
  opsStatus.value = `已应用模板：${template.name}`;
}

function saveCurrentAsTemplate() {
  const name = window.prompt("请输入模板名称", `${templateLabel(selectedTemplate.value)}-${taskConfig.num_agents}机`);
  if (!name) return;
  const saved = upsertOpsTemplate({
    name: name.trim(),
    template: selectedTemplate.value,
    source: executionSource.value,
    mission_name: missionName.value,
    num_agents: taskConfig.num_agents,
    max_frames: taskConfig.max_frames,
    tick_ms: taskConfig.tick_ms,
  });
  refreshSavedTemplates();
  selectedTemplateId.value = saved.id;
  opsStatus.value = `模板已保存：${saved.name}`;
}

function deleteCurrentTemplate() {
  if (!selectedTemplateId.value) {
    opsStatus.value = "请先选择模板";
    return;
  }
  deleteOpsTemplate(selectedTemplateId.value);
  refreshSavedTemplates();
  selectedTemplateId.value = "";
  opsStatus.value = "模板已删除";
}

function refreshSavedTemplates() {
  savedTemplates.value = loadOpsTemplates();
}

async function startOpsRun() {
  try {
    if (isEmbedded.value && !currentTaskId.value) {
      opsStatus.value = "请先从任务中心选择任务";
      return;
    }
    if (!isAdmin.value && (!currentTaskId.value || isTerminalStatus(runtime.task?.status))) {
      opsStatus.value = "飞手不能新建任务，请在任务中心选择管理员分配的任务后再启动。";
      return;
    }
    if (!currentTaskId.value || isTerminalStatus(runtime.task?.status)) {
      const created = await createOpsTask({
        mission_name: missionName.value,
        template: selectedTemplate.value,
        source: executionSource.value,
        num_agents: taskConfig.num_agents,
        max_frames: taskConfig.max_frames,
        tick_ms: taskConfig.tick_ms,
        device: taskConfig.device,
      });
      currentTaskId.value = created.task.task_id;
      eventSeq.value = Number(created.last_event_seq || 0);
      await syncTaskDetail();
      connectEvents();
    } else if (!eventSource.value) {
      connectEvents();
    }

    await controlOpsTask(currentTaskId.value, "start");
    opsStatus.value = `任务启动：${missionName.value}`;
  } catch (error) {
    opsStatus.value = `启动失败：${error.message}`;
  }
}

async function pauseOpsRun() {
  if (!currentTaskId.value) return;
  try {
    await controlOpsTask(currentTaskId.value, "pause");
    opsStatus.value = "任务已暂停";
  } catch (error) {
    opsStatus.value = `暂停失败：${error.message}`;
  }
}

async function resumeOpsRun() {
  if (!currentTaskId.value) return;
  try {
    await controlOpsTask(currentTaskId.value, "resume");
    opsStatus.value = "任务继续执行";
  } catch (error) {
    opsStatus.value = `继续失败：${error.message}`;
  }
}

async function stopOpsRun() {
  if (!currentTaskId.value) {
    resetRuntimeView();
    drawAll();
    opsStatus.value = "任务已停止";
    return;
  }
  try {
    await controlOpsTask(currentTaskId.value, "stop");
    opsStatus.value = "任务已停止";
  } catch (error) {
    opsStatus.value = `停止失败：${error.message}`;
  }
}

function isTerminalStatus(status) {
  return ["COMPLETED", "FAILED", "STOPPED"].includes(String(status || "").toUpperCase());
}

function connectEvents() {
  disconnectEvents();
  if (!currentTaskId.value) return;

  const es = connectOpsTaskEvents(currentTaskId.value, eventSeq.value);
  eventSource.value = es;
  es.onmessage = (event) => {
    if (!event?.data) return;
    try {
      const message = JSON.parse(event.data);
      handleTaskEvent(message);
    } catch {
      // Ignore heartbeat.
    }
  };
  es.onerror = () => {
    if (eventSource.value !== es) return;
    es.close();
    eventSource.value = null;
    if (isTerminalStatus(runtime.task?.status)) return;
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(() => connectEvents(), 1200);
  };
}

function disconnectEvents() {
  if (eventSource.value) {
    eventSource.value.close();
    eventSource.value = null;
  }
  if (reconnectTimer) {
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
}

async function syncTaskDetail() {
  if (!currentTaskId.value) return;
  const data = await getOpsTask(currentTaskId.value);
  if (data.task) runtime.task = data.task;
  if (data.snapshot) applySnapshot(data.snapshot);
  if (Array.isArray(data.alerts)) runtime.alerts = data.alerts;
}

function handleTaskEvent(event) {
  if (!event || typeof event !== "object") return;
  const seq = Number(event.seq || 0);
  if (seq > 0) eventSeq.value = Math.max(eventSeq.value, seq);

  const payload = event.payload || {};
  if (payload.task) runtime.task = payload.task;
  if (payload.snapshot) applySnapshot(payload.snapshot);

  if (event.type === "alert" && payload.alert) {
    runtime.alerts = [payload.alert, ...runtime.alerts].slice(0, 30);
  }
  if (event.type === "task_failed") {
    opsStatus.value = `任务失败：${payload.error || "未知错误"}`;
  } else if (event.type === "task_completed") {
    opsStatus.value = "任务已完成";
  } else if (event.type === "task_stopped") {
    opsStatus.value = "任务已停止";
  } else if (event.type === "task_ready") {
    opsStatus.value = "任务就绪，等待启动";
  } else if (event.type === "task_status" && payload.status) {
    opsStatus.value = `任务状态：${payload.status}`;
  }
}

function applySnapshot(snapshot) {
  if (snapshot.environment) runtime.environment = snapshot.environment;
  if (snapshot.frame) runtime.frame = snapshot.frame;
  if (snapshot.metrics) runtime.metrics = snapshot.metrics;
  if (Array.isArray(snapshot.alerts)) runtime.alerts = snapshot.alerts;
  if (snapshot.task) runtime.task = snapshot.task;

  if (runtime.frame?.agents?.length && !runtime.frame.agents.some((a) => a.id === selectedDroneId.value)) {
    selectedDroneId.value = runtime.frame.agents[0].id;
  }
  drawAll();
}

function resetRuntimeView() {
  runtime.task = null;
  runtime.environment = null;
  runtime.frame = null;
  runtime.metrics = {
    online: 0,
    tasks_completed: 0,
    throughput: 0,
    avg_latency: 0,
    frame_conflicts: 0,
    cumulative_conflicts: 0,
    alerts: 0,
    step: 0,
    status: "IDLE",
  };
  runtime.alerts = [];
  currentTaskId.value = "";
  eventSeq.value = 0;
}

function onOpsCanvasClick(event) {
  if (currentTaskId.value && !isTerminalStatus(runtime.task?.status)) {
    opsStatus.value = "运行中任务暂不支持在线改目标（可先暂停/停止后重建任务）";
    return;
  }
  const canvas = opsCanvasRef.value;
  const env = activeEnvironment.value;
  const frame = activeFrame.value;
  if (!canvas || !env || !frame) return;

  const rect = canvas.getBoundingClientRect();
  const px = ((event.clientX - rect.left) * canvas.width) / Math.max(rect.width, 1);
  const py = ((event.clientY - rect.top) * canvas.height) / Math.max(rect.height, 1);
  const padding = 34;
  const cell = Math.min((canvas.width - padding * 2) / env.width, (canvas.height - padding * 2) / env.height);
  const gridWidth = cell * env.width;
  const gridHeight = cell * env.height;
  const left = (canvas.width - gridWidth) / 2;
  const top = (canvas.height - gridHeight) / 2;
  const col = Math.floor((px - left) / cell);
  const row = Math.floor((py - top) / cell);

  if (row < 0 || col < 0 || row >= env.height || col >= env.width) return;
  if (env.obstacles[row][col] === 1) {
    opsStatus.value = "该位置是障碍物，不能设为目标";
    return;
  }

  const target = frame.agents.find((a) => a.id === selectedDroneId.value);
  if (!target) return;
  target.target_x = row;
  target.target_y = col;
  opsStatus.value = `已为无人机${target.id + 1}设置目标点(${row}, ${col})`;
  drawAll();
}

function drawAll() {
  draw2D();
  draw3D();
}

function draw2D() {
  const canvas = opsCanvasRef.value;
  resizeCanvasToDisplaySize(canvas);
  renderer.draw(canvas, activeEnvironment.value, activeFrame.value);
}

function draw3D() {
  const canvas = ops3dCanvasRef.value;
  const env = activeEnvironment.value;
  const frame = activeFrame.value;
  if (!canvas || !env || !frame) return;
  resizeCanvasToDisplaySize(canvas);

  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "#091a33");
  gradient.addColorStop(1, "#050d1d");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (!env.width || !env.height) return;

  const leadAgent = frame.agents.find((agent) => agent.id === selectedDroneId.value) || frame.agents[0];
  const lead = leadAgent ? gridToWorld(leadAgent.x, leadAgent.y, env) : { x: 0, z: 0 };
  const radius = Math.max((env.height - 1) * CELL_SIZE, (env.width - 1) * CELL_SIZE) * 0.95 + 6;
  const camera = buildCamera(lead, radius);

  drawGrid3D(ctx, canvas, camera, env);
  drawObstacles3D(ctx, canvas, camera, env);
  drawAgents3D(ctx, canvas, camera, env, frame);
}

function start3DLoop() {
  stop3DLoop();
  lastTs = 0;
  rafId = window.requestAnimationFrame(tick3D);
}

function stop3DLoop() {
  if (rafId) window.cancelAnimationFrame(rafId);
  rafId = null;
}

function tick3D(ts) {
  if (!lastTs) lastTs = ts;
  const dt = Math.max((ts - lastTs) / 1000, 0);
  lastTs = ts;
  if (cameraMode.value === "orbit") orbitAngle += dt * orbitSpeed.value;
  draw3D();
  rafId = window.requestAnimationFrame(tick3D);
}

function buildCamera(lead, radius) {
  if (cameraMode.value === "overview") {
    return lookAtCamera({ x: 0, y: radius * 0.9, z: radius * 0.5 }, { x: 0, y: 0.3, z: 0 });
  }
  if (cameraMode.value === "follow") {
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

function drawGrid3D(ctx, canvas, camera, env) {
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

function drawObstacles3D(ctx, canvas, camera, env) {
  for (let row = 0; row < env.height; row += 1) {
    for (let col = 0; col < env.width; col += 1) {
      if (env.obstacles?.[row]?.[col] !== 1) continue;
      const p = gridToWorld(row, col, env);
      const block = { x: p.x - CELL_SIZE * 0.45, z: p.z - CELL_SIZE * 0.45, w: CELL_SIZE * 0.9, d: CELL_SIZE * 0.9, h: 0.9 };
      drawBoxWire(ctx, canvas, camera, block, "rgba(145,160,182,0.95)");
    }
  }
}

function drawAgents3D(ctx, canvas, camera, env, frame) {
  frame.agents?.forEach((agent) => {
    const color = DRONE_COLORS[agent.id % DRONE_COLORS.length];
    const bodyPos = gridToWorld(agent.x, agent.y, env);
    const targetPos = gridToWorld(agent.target_x, agent.target_y, env);
    const body = projectPoint(canvas, camera, bodyPos.x, 0.72, bodyPos.z);
    const ground = projectPoint(canvas, camera, bodyPos.x, 0.03, bodyPos.z);
    const target = projectPoint(canvas, camera, targetPos.x, 0.08, targetPos.z);
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

function gridToWorld(row, col, env) {
  const halfX = ((env.height - 1) * CELL_SIZE) / 2;
  const halfZ = ((env.width - 1) * CELL_SIZE) / 2;
  return { x: row * CELL_SIZE - halfX, z: col * CELL_SIZE - halfZ };
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

  const focal = 620 * zoomScale.value;
  const scale = focal / z2;
  return {
    x: canvas.width * 0.5 + x1 * scale,
    y: canvas.height * 0.52 - y2 * scale,
    scale: Math.max(0.3, Math.min(2.2, scale / 120)),
  };
}

function resizeCanvasToDisplaySize(canvas) {
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

function lookAtCamera(position, target) {
  const dx = target.x - position.x;
  const dy = target.y - position.y;
  const dz = target.z - position.z;
  const yaw = -Math.atan2(dx, dz);
  const distXZ = Math.hypot(dx, dz);
  const pitch = -Math.atan2(dy, distXZ);
  return { x: position.x, y: position.y, z: position.z, yaw, pitch };
}

function templateLabel(templateKey) {
  if (templateKey === "campus") return "园区配送";
  if (templateKey === "emergency") return "应急调度";
  return "仓储巡检";
}

function handleTemplateUpdate() {
  refreshSavedTemplates();
}

async function restorePrefillAndFocus() {
  if (isEmbedded.value) {
    if (props.focusTaskId) {
      await focusTaskById(props.focusTaskId);
    }
    return;
  }

  const rawTemplate = window.localStorage.getItem("OPS_TEMPLATE_PREFILL");
  if (rawTemplate) {
    try {
      const template = JSON.parse(rawTemplate);
      selectedTemplate.value = template.template || selectedTemplate.value;
      executionSource.value = template.source || executionSource.value;
      missionName.value = template.mission_name || missionName.value;
      taskConfig.num_agents = Number(template.num_agents || taskConfig.num_agents);
      taskConfig.max_frames = Number(template.max_frames || taskConfig.max_frames);
      taskConfig.tick_ms = Number(template.tick_ms || taskConfig.tick_ms);
      samplePlayback.value = buildSampleRun(selectedTemplate.value);
      selectedDroneId.value = 0;
      drawAll();
      opsStatus.value = `已载入模板：${template.name || "未命名模板"}`;
    } catch {
      // Ignore malformed prefill payload.
    }
    window.localStorage.removeItem("OPS_TEMPLATE_PREFILL");
  }

  const focusTaskId = window.localStorage.getItem("OPS_FOCUS_TASK_ID");
  if (!focusTaskId) return;
  window.localStorage.removeItem("OPS_FOCUS_TASK_ID");
  currentTaskId.value = focusTaskId;
  connectEvents();
  await syncTaskDetail();
  opsStatus.value = `已切换到任务：${focusTaskId}`;
}

async function focusTaskById(taskId) {
  const normalized = String(taskId || "").trim();
  if (!normalized) {
    disconnectEvents();
    resetRuntimeView();
    drawAll();
    return;
  }
  if (currentTaskId.value !== normalized) {
    currentTaskId.value = normalized;
    eventSeq.value = 0;
    connectEvents();
  }
  await syncTaskDetail();
  opsStatus.value = `已载入任务：${normalized}`;
}

watch([cameraMode, zoomScale], () => draw3D());
watch(selectedDroneId, () => drawAll());
watch(
  () => props.focusTaskId,
  async (taskId) => {
    if (!isEmbedded.value) return;
    await focusTaskById(taskId);
  }
);

onMounted(async () => {
  refreshSavedTemplates();
  if (!isEmbedded.value) window.addEventListener("ops-template-updated", handleTemplateUpdate);
  window.addEventListener("resize", handleWindowResize);
  drawAll();
  start3DLoop();
  await restorePrefillAndFocus();
});

onUnmounted(() => {
  disconnectEvents();
  stop3DLoop();
  if (!isEmbedded.value) window.removeEventListener("ops-template-updated", handleTemplateUpdate);
  window.removeEventListener("resize", handleWindowResize);
  if (resizeTimer) window.clearTimeout(resizeTimer);
});

function handleWindowResize() {
  if (resizeTimer) window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(() => drawAll(), 80);
}
</script>
