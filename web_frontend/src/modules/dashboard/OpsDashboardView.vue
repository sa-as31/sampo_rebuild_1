<template>
  <section class="dashboard-grid">
    <article class="panel dashboard-panel-primary">
      <div class="admin-panel-head">
        <div>
          <p class="section-kicker">FLIGHT OVERVIEW</p>
          <h2>飞手总览</h2>
          <div class="admin-subheadline">
            <span>{{ status }}</span>
            <span>焦点任务 {{ focusTask?.mission_name || "未选定" }}</span>
          </div>
        </div>
        <div class="btn-row">
          <button class="btn secondary" @click="refreshDashboard">刷新</button>
          <button class="btn secondary" @click="goTaskCenter">返回任务中心</button>
        </div>
      </div>

      <div class="status-cards" style="margin-top: 14px">
        <div class="status-card"><p>任务总数</p><strong>{{ summary.total_tasks }}</strong></div>
        <div class="status-card"><p>待执行</p><strong>{{ summary.queued_tasks }}</strong></div>
        <div class="status-card"><p>执行中</p><strong>{{ summary.running_tasks }}</strong></div>
        <div class="status-card"><p>已结束</p><strong>{{ summary.completed_tasks }}</strong></div>
      </div>

      <div class="dashboard-task-stack">
        <button
          v-for="task in dashboardTaskCards"
          :key="task.task_id"
          class="admin-task-card"
          :class="{ active: task.task_id === focusTaskId }"
          @click="onFocusTask(task.task_id)"
        >
          <span class="admin-task-card-top">
            <strong>{{ task.mission_name }}</strong>
            <em>{{ stageLabel(task.status) }}</em>
          </span>
          <span class="admin-task-card-meta">{{ task.task_id }} · 当前步 {{ task.metrics?.step ?? "-" }}</span>
          <span class="admin-task-card-meta">更新于 {{ fmtTime(task.updated_at) }} · 吞吐量 {{ fmt(task.metrics?.throughput, 4) }}</span>
        </button>
        <div v-if="dashboardTaskCards.length === 0" class="ops-alert-empty">当前没有分配给你的任务。</div>
      </div>
    </article>

    <article class="panel">
      <p class="section-kicker">LIVE SNAPSHOT</p>
      <h2>{{ focusTask?.mission_name || "任务快照" }}</h2>
      <div class="ops-inline-meta" style="margin-top: 12px">
        <span>任务ID: {{ focusTask?.task_id || "-" }}</span>
        <span>阶段: {{ stageLabel(focusTask?.status) }}</span>
        <span>更新时间: {{ fmtTime(focusTask?.updated_at) }}</span>
      </div>
      <div class="canvas-wrap" style="margin-top: 10px">
        <canvas ref="canvasRef" width="980" height="520"></canvas>
      </div>

      <div class="metrics" style="margin-top: 10px">
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
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import { fetchOpsAlerts, fetchOpsTasks, getOpsTask } from "../../services/api";
import { createRenderer } from "../shared/renderer";

const router = useRouter();
const authStore = useAuthStore();
const renderer = createRenderer();
const canvasRef = ref(null);
const status = ref("总览初始化中...");
const tasks = ref([]);
const focusTaskId = ref("");
const focusTask = ref(null);
const snapshot = ref(null);
const alerts = ref([]);
let timer = null;

const currentUserId = computed(() => String(authStore.state.currentUser?.user_id || ""));
const assignedTasks = computed(() =>
  tasks.value.filter((task) => String(task?.params?.assignee_user_id || "") === currentUserId.value),
);

const summary = reactive({
  total_tasks: 0,
  queued_tasks: 0,
  running_tasks: 0,
  completed_tasks: 0,
});

const dashboardTaskCards = computed(() => {
  const rank = {
    RUNNING: 0,
    PAUSED: 1,
    READY: 2,
    PREPARING: 3,
    COMPLETED: 4,
    FAILED: 5,
    STOPPED: 6,
  };
  return assignedTasks.value
    .slice()
    .sort((a, b) => {
      const ra = rank[String(a.status || "").toUpperCase()] ?? 99;
      const rb = rank[String(b.status || "").toUpperCase()] ?? 99;
      if (ra !== rb) return ra - rb;
      return Number(b.updated_at || 0) - Number(a.updated_at || 0);
    })
    .slice(0, 6);
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

function stageLabel(statusValue) {
  const value = String(statusValue || "").toUpperCase();
  if (value === "PENDING_REVIEW") return "待审核";
  if (value === "REJECTED") return "已驳回";
  if (value === "PREPARING" || value === "READY") return "待执行";
  if (value === "RUNNING" || value === "PAUSED") return "执行中";
  return "已完成";
}

function goTaskCenter() {
  router.push("/executor/tasks");
}

async function refreshDashboard() {
  try {
    const taskData = await fetchOpsTasks(80);
    tasks.value = taskData.tasks || [];

    summary.total_tasks = assignedTasks.value.length;
    summary.queued_tasks = assignedTasks.value.filter((task) => ["PREPARING", "READY"].includes(task.status)).length;
    summary.running_tasks = assignedTasks.value.filter((task) => ["RUNNING", "PAUSED"].includes(task.status)).length;
    summary.completed_tasks = assignedTasks.value.filter((task) => ["COMPLETED", "FAILED", "STOPPED"].includes(task.status)).length;

    const running = assignedTasks.value.find((task) => task.status === "RUNNING");
    if (!focusTaskId.value || !assignedTasks.value.some((task) => task.task_id === focusTaskId.value)) {
      focusTaskId.value = (running || assignedTasks.value[0] || {}).task_id || "";
    } else if (running && focusTask?.value?.status !== "RUNNING") {
      focusTaskId.value = running.task_id;
    }

    if (focusTaskId.value) {
      await loadFocusTask(focusTaskId.value);
    } else {
      clearCanvas();
    }

    status.value = `总览已更新（我的任务 ${assignedTasks.value.length} 条）`;
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
