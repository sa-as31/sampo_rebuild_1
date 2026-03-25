<template>
  <section class="dashboard-grid">
    <article class="panel">
      <p class="section-kicker">OPS DASHBOARD</p>
      <h2>用更少的指标查看当前任务态势</h2>
      <div class="status-chip">{{ status }}</div>

      <div class="status-cards" style="margin-top: 10px">
        <div class="status-card"><p>任务总数</p><strong>{{ summary.total_tasks }}</strong></div>
        <div class="status-card"><p>运行中</p><strong>{{ summary.running_tasks }}</strong></div>
        <div class="status-card"><p>已完成</p><strong>{{ summary.completed_tasks }}</strong></div>
        <div class="status-card"><p>平均吞吐量</p><strong>{{ fmt(summary.avg_throughput, 4) }}</strong></div>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn secondary" @click="refreshDashboard">刷新</button>
        <button class="btn secondary" @click="goMode('taskCenter')">查看任务中心</button>
      </div>

      <table class="fleet-table" style="margin-top: 10px">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>任务名</th>
            <th>状态</th>
            <th>吞吐量</th>
            <th>更新</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="task in tasks"
            :key="task.task_id"
            :class="{ 'task-row-active': task.task_id === focusTaskId }"
            @click="onFocusTask(task.task_id)"
          >
            <td>{{ task.task_id }}</td>
            <td>{{ task.mission_name }}</td>
            <td>{{ task.status }}</td>
            <td>{{ fmt(task.metrics?.throughput, 4) }}</td>
            <td>{{ fmtTime(task.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </article>

    <article class="panel">
      <p class="section-kicker">LIVE SNAPSHOT</p>
      <h2>当前焦点任务的实时地图快照</h2>
      <div class="canvas-wrap" style="margin-top: 10px">
        <canvas ref="canvasRef" width="980" height="520"></canvas>
      </div>

      <div class="metrics" style="margin-top: 10px">
        <div class="metric"><span>焦点任务</span><strong style="font-size: 18px">{{ focusTask?.task_id || "-" }}</strong></div>
        <div class="metric"><span>状态</span><strong style="font-size: 18px">{{ focusTask?.status || "-" }}</strong></div>
        <div class="metric"><span>当前步</span><strong>{{ snapshot?.metrics?.step ?? "-" }}</strong></div>
        <div class="metric"><span>累计任务</span><strong>{{ snapshot?.metrics?.tasks_completed ?? "-" }}</strong></div>
        <div class="metric"><span>冲突累计</span><strong>{{ snapshot?.metrics?.cumulative_conflicts ?? "-" }}</strong></div>
        <div class="metric"><span>告警累计</span><strong>{{ snapshot?.metrics?.alerts ?? "-" }}</strong></div>
      </div>

      <div class="ops-alerts" style="margin-top: 10px">
        <h3>最近告警</h3>
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
import { onMounted, onUnmounted, reactive, ref } from "vue";
import { fetchDashboardSummary, fetchOpsAlerts, fetchOpsTasks, getOpsTask } from "../../services/api";
import { createRenderer } from "../shared/renderer";

const renderer = createRenderer();
const canvasRef = ref(null);
const status = ref("大屏初始化中...");
const tasks = ref([]);
const focusTaskId = ref("");
const focusTask = ref(null);
const snapshot = ref(null);
const alerts = ref([]);
let timer = null;

const summary = reactive({
  total_tasks: 0,
  running_tasks: 0,
  paused_tasks: 0,
  completed_tasks: 0,
  failed_tasks: 0,
  stopped_tasks: 0,
  avg_throughput: 0,
});

function fmt(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function fmtTime(ts) {
  if (!ts) return "-";
  const d = new Date(Number(ts) * 1000);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

function goMode(mode) {
  window.dispatchEvent(new CustomEvent("app-switch-mode", { detail: { mode } }));
}

async function refreshDashboard() {
  try {
    const [sumData, taskData] = await Promise.all([fetchDashboardSummary(), fetchOpsTasks(80)]);
    Object.assign(summary, sumData.summary || {});
    tasks.value = taskData.tasks || [];

    const running = tasks.value.find((task) => task.status === "RUNNING");
    if (!focusTaskId.value || !tasks.value.some((task) => task.task_id === focusTaskId.value)) {
      focusTaskId.value = (running || tasks.value[0] || {}).task_id || "";
    } else if (running && focusTask?.value?.status !== "RUNNING") {
      focusTaskId.value = running.task_id;
    }

    if (focusTaskId.value) {
      await loadFocusTask(focusTaskId.value);
    } else {
      clearCanvas();
    }

    status.value = `大屏已更新（${tasks.value.length}个任务）`;
  } catch (error) {
    status.value = `刷新失败：${error.message}`;
  }
}

async function onFocusTask(taskId) {
  focusTaskId.value = taskId;
  await loadFocusTask(taskId);
}

async function loadFocusTask(taskId) {
  try {
    const [detail, alertData] = await Promise.all([getOpsTask(taskId), fetchOpsAlerts(taskId, 12)]);
    focusTask.value = detail.task || null;
    snapshot.value = detail.snapshot || null;
    alerts.value = alertData.alerts || [];
    if (snapshot.value?.environment && snapshot.value?.frame) {
      renderer.draw(canvasRef.value, snapshot.value.environment, snapshot.value.frame);
    } else {
      clearCanvas();
    }
  } catch {
    // Keep previous successful data.
  }
}

function clearCanvas() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#061327";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(205,225,255,0.82)";
  ctx.font = '15px "PingFang SC", "Noto Sans SC", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText("暂无可展示任务快照", canvas.width / 2, canvas.height / 2);
}

onMounted(async () => {
  await refreshDashboard();
  timer = window.setInterval(() => refreshDashboard(), 2000);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
});
</script>
