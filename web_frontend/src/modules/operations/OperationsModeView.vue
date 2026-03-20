<template>
  <section class="ops-grid">
    <article class="panel">
      <h2>任务下发</h2>

      <div class="field-grid">
        <label>任务模板
          <select v-model="selectedTemplate" @change="applyTemplate">
            <option value="warehouse">仓储巡检</option>
            <option value="campus">园区配送</option>
            <option value="emergency">应急调度</option>
          </select>
        </label>
        <label>执行数据源
          <select v-model="executionSource">
            <option value="sample">后端样例仿真</option>
            <option value="model">模型推理回放</option>
          </select>
        </label>
        <label>任务批次名称 <input v-model="missionName" placeholder="如：night_shift_batch_03" /></label>
        <label>无人机数量 <input v-model.number="taskConfig.num_agents" min="1" type="number" /></label>
        <label>最大帧数 <input v-model.number="taskConfig.max_frames" min="4" type="number" /></label>
        <label>节拍(ms) <input v-model.number="taskConfig.tick_ms" min="120" step="20" type="number" /></label>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="startOpsRun">开始任务</button>
        <button class="btn secondary" @click="pauseOpsRun">暂停</button>
        <button class="btn secondary" @click="resumeOpsRun">继续</button>
        <button class="btn secondary" @click="stopOpsRun">停止</button>
      </div>
      <div class="status-chip">{{ opsStatus }}</div>
      <div class="legend">任务ID: {{ currentTaskId || "未创建" }}</div>

      <div class="legend">点击地图空白网格可设置目标点</div>
      <div class="field-grid" style="margin-top: 8px">
        <label>当前选中无人机
          <select v-model.number="selectedDroneId">
            <option v-for="d in fleetRows" :key="d.id" :value="d.id">无人机 {{ d.id + 1 }}</option>
          </select>
        </label>
      </div>
    </article>

    <article class="panel">
      <h2>运行态势</h2>

      <div class="status-cards">
        <div class="status-card"><p>在线无人机数</p><strong>{{ statusCards.online }}</strong></div>
        <div class="status-card"><p>累计完成任务</p><strong>{{ statusCards.completed }}</strong></div>
        <div class="status-card"><p>冲突告警数</p><strong>{{ statusCards.conflicts }}</strong></div>
        <div class="status-card"><p>平均任务时延(步)</p><strong>{{ statusCards.latency }}</strong></div>
      </div>

      <div class="canvas-wrap" style="margin-top: 12px">
        <canvas ref="opsCanvasRef" width="920" height="520" @click="onOpsCanvasClick"></canvas>
      </div>

      <table class="fleet-table">
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

      <div class="ops-alerts">
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
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { buildSampleRun, createRenderer } from "../shared/renderer";
import { connectOpsTaskEvents, controlOpsTask, createOpsTask, getOpsTask } from "../../services/api";

const renderer = createRenderer();
const opsCanvasRef = ref(null);
const selectedTemplate = ref("warehouse");
const missionName = ref("enterprise_batch_demo");
const selectedDroneId = ref(0);
const executionSource = ref("sample");
const taskConfig = reactive({
  num_agents: 16,
  max_frames: 64,
  tick_ms: 320,
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

const activeEnvironment = computed(() => runtime.environment || samplePlayback.value.environment);
const activeFrame = computed(() => runtime.frame || samplePlayback.value.frames[0] || { agents: [], vertex_conflicts: 0, step: 0 });
const alerts = computed(() => runtime.alerts || []);

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

function applyTemplate() {
  samplePlayback.value = buildSampleRun(selectedTemplate.value);
  selectedDroneId.value = 0;
  drawOps();
  opsStatus.value = `已切换模板：${templateLabel(selectedTemplate.value)}`;
}

async function startOpsRun() {
  try {
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
    drawOps();
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
      // Ignore non-JSON heartbeat lines.
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
  drawOps();
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

// In backend-driven mode target editing is not applied to task runtime yet.
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
  const px = event.clientX - rect.left;
  const py = event.clientY - rect.top;
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
  drawOps();
}

function drawOps() {
  renderer.draw(opsCanvasRef.value, activeEnvironment.value, activeFrame.value);
}

function templateLabel(templateKey) {
  if (templateKey === "campus") return "园区配送";
  if (templateKey === "emergency") return "应急调度";
  return "仓储巡检";
}

onMounted(() => drawOps());
onUnmounted(() => disconnectEvents());
</script>
