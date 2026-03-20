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
        <label>任务批次名称 <input v-model="missionName" placeholder="如：night_shift_batch_03" /></label>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="startOpsRun">开始任务</button>
        <button class="btn secondary" @click="pauseOpsRun">暂停</button>
        <button class="btn secondary" @click="resumeOpsRun">继续</button>
        <button class="btn secondary" @click="stopOpsRun">停止</button>
      </div>
      <div class="status-chip">{{ opsStatus }}</div>

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
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { buildSampleRun, createRenderer } from "../shared/renderer";

const renderer = createRenderer();
const opsCanvasRef = ref(null);
const selectedTemplate = ref("warehouse");
const missionName = ref("enterprise_batch_demo");
const selectedDroneId = ref(0);
const opsStatus = ref("待命");
const running = ref(false);
const frameIndex = ref(0);
let timer = null;

const playback = ref(buildSampleRun(selectedTemplate.value));

const statusCards = computed(() => {
  const frame = playback.value.frames[frameIndex.value] || { agents: [], vertex_conflicts: 0 };
  const online = frame.agents.length;
  const completed = frame.agents.filter((a) => a.done).length;
  const conflicts = frame.vertex_conflicts || 0;
  const latency = online ? Math.round((frame.step + 1) * 0.7) : 0;
  return { online, completed, conflicts, latency };
});

const fleetRows = computed(() => {
  const frame = playback.value.frames[frameIndex.value] || { agents: [] };
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
  stopTimer();
  playback.value = buildSampleRun(selectedTemplate.value);
  frameIndex.value = 0;
  selectedDroneId.value = 0;
  drawOps();
  opsStatus.value = `已切换模板：${templateLabel(selectedTemplate.value)}`;
}

function startOpsRun() {
  stopTimer();
  const max = playback.value.frames.length - 1;
  frameIndex.value = 0;
  drawOps();
  if (max <= 0) {
    opsStatus.value = max === 0 ? "任务已完成" : "暂无可播放轨迹";
    return;
  }
  running.value = true;
  opsStatus.value = `任务启动：${missionName.value}`;
  timer = window.setInterval(tickOpsFrame, 320);
}

function pauseOpsRun() {
  if (!running.value) return;
  running.value = false;
  if (timer) window.clearInterval(timer);
  timer = null;
  opsStatus.value = "任务已暂停";
}

function resumeOpsRun() {
  if (running.value) return;
  const max = playback.value.frames.length - 1;
  if (max < 0) {
    opsStatus.value = "暂无可播放轨迹";
    return;
  }
  if (frameIndex.value >= max) {
    frameIndex.value = max;
    drawOps();
    opsStatus.value = "任务已完成";
    return;
  }
  running.value = true;
  opsStatus.value = "任务继续执行";
  timer = window.setInterval(tickOpsFrame, 320);
}

function stopOpsRun() {
  stopTimer();
  frameIndex.value = 0;
  drawOps();
  opsStatus.value = "任务已停止";
}

function stopTimer() {
  running.value = false;
  if (timer) window.clearInterval(timer);
  timer = null;
}

function tickOpsFrame() {
  const max = playback.value.frames.length - 1;
  if (max < 0) {
    stopTimer();
    opsStatus.value = "暂无可播放轨迹";
    return;
  }
  if (frameIndex.value >= max) {
    frameIndex.value = max;
    drawOps();
    stopTimer();
    opsStatus.value = "任务已完成";
    return;
  }
  frameIndex.value += 1;
  drawOps();
}

// For ops mode we keep target assignment fully visual.
function onOpsCanvasClick(event) {
  const canvas = opsCanvasRef.value;
  const env = playback.value.environment;
  const frame = playback.value.frames[frameIndex.value];
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
  const frame = playback.value.frames[frameIndex.value];
  renderer.draw(opsCanvasRef.value, playback.value.environment, frame);
}

function templateLabel(templateKey) {
  if (templateKey === "campus") return "园区配送";
  if (templateKey === "emergency") return "应急调度";
  return "仓储巡检";
}

onMounted(() => drawOps());
onUnmounted(() => stopTimer());
</script>
