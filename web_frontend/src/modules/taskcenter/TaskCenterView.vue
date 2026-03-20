<template>
  <section class="task-center-grid">
    <article class="panel">
      <h2>任务中心</h2>

      <div class="field-grid">
        <label>状态筛选
          <select v-model="filters.status">
            <option value="ALL">全部</option>
            <option value="PREPARING">PREPARING</option>
            <option value="READY">READY</option>
            <option value="RUNNING">RUNNING</option>
            <option value="PAUSED">PAUSED</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="FAILED">FAILED</option>
            <option value="STOPPED">STOPPED</option>
          </select>
        </label>
        <label>模板筛选
          <select v-model="filters.template">
            <option value="ALL">全部</option>
            <option value="warehouse">仓储巡检</option>
            <option value="campus">园区配送</option>
            <option value="emergency">应急调度</option>
          </select>
        </label>
        <label>关键词
          <input v-model="filters.keyword" placeholder="任务名 / task_id" />
        </label>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="refreshTasks">刷新列表</button>
        <button class="btn secondary" @click="openOpsWithSelected">进入运营中心</button>
        <button class="btn secondary" @click="exportReport">导出任务报告</button>
      </div>
      <div class="status-chip">{{ status }}</div>

      <table class="fleet-table" style="margin-top: 8px">
        <thead>
          <tr>
            <th>任务ID</th>
            <th>任务名</th>
            <th>模板</th>
            <th>状态</th>
            <th>吞吐量</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="task in filteredTasks"
            :key="task.task_id"
            :class="{ 'task-row-active': task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <td>{{ task.task_id }}</td>
            <td>{{ task.mission_name }}</td>
            <td>{{ templateLabel(task.template) }}</td>
            <td>{{ task.status }}</td>
            <td>{{ fmtNumber(task.metrics?.throughput, 4) }}</td>
            <td>{{ fmtTime(task.updated_at) }}</td>
          </tr>
        </tbody>
      </table>
    </article>

    <article class="panel">
      <h2>任务详情与回放</h2>

      <div class="task-meta-grid">
        <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
        <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
        <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? "-" }}</strong></div>
        <div class="task-meta"><span>告警数</span><strong>{{ selectedSnapshot?.metrics?.alerts ?? "-" }}</strong></div>
      </div>

      <div class="btn-row" style="margin-top: 10px">
        <button class="btn secondary" @click="loadReplay">加载历史回放</button>
        <button class="btn secondary" @click="togglePlayback">{{ replay.playing ? "暂停回放" : "播放回放" }}</button>
        <input
          v-model.number="replay.frameIndex"
          :max="Math.max(0, replay.frames.length - 1)"
          min="0"
          type="range"
          @input="drawReplayFrame"
        />
      </div>

      <div class="canvas-wrap" style="margin-top: 10px">
        <canvas ref="canvasRef" width="920" height="460"></canvas>
      </div>

      <div class="ops-alerts" style="margin-top: 10px">
        <h3>任务告警</h3>
        <div v-if="selectedAlerts.length === 0" class="ops-alert-empty">无告警记录</div>
        <div
          v-for="alert in selectedAlerts"
          :key="`${alert.ts}-${alert.code}`"
          class="ops-alert-item"
          :class="`level-${alert.level}`"
        >
          <span class="ops-alert-code">[{{ alert.code }}]</span>
          <span>{{ alert.message }}</span>
          <span class="ops-alert-step">step {{ alert.frame_step }}</span>
        </div>
      </div>
    </article>

    <article class="panel">
      <h2>参数模板库</h2>
      <div class="field-grid">
        <label>模板名称 <input v-model="templateForm.name" placeholder="如：仓储夜班-16机" /></label>
        <label>模板场景
          <select v-model="templateForm.template">
            <option value="warehouse">仓储巡检</option>
            <option value="campus">园区配送</option>
            <option value="emergency">应急调度</option>
          </select>
        </label>
        <label>数据源
          <select v-model="templateForm.source">
            <option value="sample">sample</option>
            <option value="model">model</option>
          </select>
        </label>
        <label>默认任务名 <input v-model="templateForm.mission_name" /></label>
        <label>无人机数量 <input v-model.number="templateForm.num_agents" min="1" type="number" /></label>
        <label>最大帧数 <input v-model.number="templateForm.max_frames" min="4" type="number" /></label>
        <label>节拍(ms) <input v-model.number="templateForm.tick_ms" min="120" step="20" type="number" /></label>
      </div>
      <div class="btn-row" style="margin-top: 10px">
        <button class="btn" @click="saveTemplate">保存模板</button>
        <button class="btn secondary" @click="fillTemplateFromTask">从当前任务填充</button>
      </div>

      <table class="fleet-table" style="margin-top: 8px">
        <thead>
          <tr>
            <th>模板名</th>
            <th>场景</th>
            <th>源</th>
            <th>参数</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in templates" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ templateLabel(item.template) }}</td>
            <td>{{ item.source }}</td>
            <td>{{ item.num_agents }}机 / {{ item.max_frames }}帧 / {{ item.tick_ms }}ms</td>
            <td>
              <div class="btn-row">
                <button class="btn secondary" @click="applyTemplate(item)">应用到运营中心</button>
                <button class="btn secondary" @click="removeTemplate(item.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { fetchOpsTasks, fetchOpsAlerts, getOpsTask, fetchTaskReplay } from "../../services/api";
import { createRenderer } from "../shared/renderer";
import { deleteOpsTemplate, loadOpsTemplates, upsertOpsTemplate } from "../shared/templateStore";

const renderer = createRenderer();
const canvasRef = ref(null);
const status = ref("任务中心初始化中...");
const tasks = ref([]);
const selectedTaskId = ref("");
const selectedTask = ref(null);
const selectedSnapshot = ref(null);
const selectedAlerts = ref([]);
const templates = ref(loadOpsTemplates());
const replayTimer = ref(null);
let pollTimer = null;

const filters = reactive({
  status: "ALL",
  template: "ALL",
  keyword: "",
});

const templateForm = reactive({
  id: "",
  name: "",
  template: "warehouse",
  source: "sample",
  mission_name: "enterprise_batch_demo",
  num_agents: 16,
  max_frames: 64,
  tick_ms: 320,
});

const replay = reactive({
  available: false,
  frames: [],
  environment: null,
  frameIndex: 0,
  playing: false,
  reason: "",
});

const filteredTasks = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase();
  return tasks.value.filter((task) => {
    if (filters.status !== "ALL" && task.status !== filters.status) return false;
    if (filters.template !== "ALL" && task.template !== filters.template) return false;
    if (!keyword) return true;
    return task.task_id.toLowerCase().includes(keyword) || String(task.mission_name || "").toLowerCase().includes(keyword);
  });
});

function fmtNumber(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function fmtTime(ts) {
  if (!ts) return "-";
  const d = new Date(Number(ts) * 1000);
  return `${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}:${d.getSeconds().toString().padStart(2, "0")}`;
}

function templateLabel(key) {
  if (key === "campus") return "园区配送";
  if (key === "emergency") return "应急调度";
  return "仓储巡检";
}

async function refreshTasks() {
  try {
    const data = await fetchOpsTasks(100);
    tasks.value = data.tasks || [];
    if (!selectedTaskId.value && tasks.value.length) {
      selectedTaskId.value = tasks.value[0].task_id;
    }
    if (selectedTaskId.value) {
      await loadTaskDetail(selectedTaskId.value, false);
    }
    status.value = `任务列表已更新，共 ${tasks.value.length} 条`;
  } catch (error) {
    status.value = `刷新失败：${error.message}`;
  }
}

async function selectTask(taskId) {
  selectedTaskId.value = taskId;
  await loadTaskDetail(taskId, true);
}

async function loadTaskDetail(taskId, withStatusText) {
  try {
    const [detail, alerts] = await Promise.all([getOpsTask(taskId), fetchOpsAlerts(taskId, 30)]);
    selectedTask.value = detail.task || null;
    selectedSnapshot.value = detail.snapshot || null;
    selectedAlerts.value = alerts.alerts || [];
    if (withStatusText) status.value = `已加载任务：${taskId}`;
    if (detail.snapshot?.frame && detail.snapshot?.environment) {
      renderer.draw(canvasRef.value, detail.snapshot.environment, detail.snapshot.frame);
    }
  } catch (error) {
    status.value = `加载任务失败：${error.message}`;
  }
}

async function loadReplay() {
  if (!selectedTaskId.value) return;
  stopReplayTimer();
  try {
    const payload = await fetchTaskReplay(selectedTaskId.value);
    replay.available = Boolean(payload.available);
    replay.frames = payload.frames || [];
    replay.environment = payload.environment || null;
    replay.frameIndex = 0;
    replay.reason = payload.reason || "";
    if (!replay.available || !replay.frames.length || !replay.environment) {
      status.value = replay.reason || "当前任务无法提供历史回放（可能是服务重启后历史任务）";
      drawReplayFrame();
      return;
    }
    status.value = `历史回放已加载，帧数 ${replay.frames.length}`;
    drawReplayFrame();
  } catch (error) {
    status.value = `加载回放失败：${error.message}`;
  }
}

function drawReplayFrame() {
  if (replay.available && replay.environment && replay.frames.length) {
    const frame = replay.frames[Math.min(replay.frameIndex, replay.frames.length - 1)];
    renderer.draw(canvasRef.value, replay.environment, frame);
    return;
  }
  const snapshot = selectedSnapshot.value;
  if (snapshot?.environment && snapshot?.frame) {
    renderer.draw(canvasRef.value, snapshot.environment, snapshot.frame);
    return;
  }
  const canvas = canvasRef.value;
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#061327";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(205,225,255,0.84)";
  ctx.font = '15px "PingFang SC", "Noto Sans SC", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText("暂无可展示回放", canvas.width / 2, canvas.height / 2);
}

function togglePlayback() {
  if (!replay.available || !replay.frames.length) {
    status.value = "请先加载历史回放";
    return;
  }
  if (replay.playing) {
    stopReplayTimer();
    return;
  }
  replay.playing = true;
  replayTimer.value = window.setInterval(() => {
    if (replay.frameIndex >= replay.frames.length - 1) {
      stopReplayTimer();
      return;
    }
    replay.frameIndex += 1;
    drawReplayFrame();
  }, 220);
}

function stopReplayTimer() {
  replay.playing = false;
  if (replayTimer.value) {
    window.clearInterval(replayTimer.value);
    replayTimer.value = null;
  }
}

function exportReport() {
  if (!selectedTask.value) {
    status.value = "请先选择一个任务";
    return;
  }
  const task = selectedTask.value;
  const metrics = selectedSnapshot.value?.metrics || task.metrics || {};
  const lines = [
    `# 任务报告`,
    ``,
    `- 任务ID: ${task.task_id}`,
    `- 任务名: ${task.mission_name}`,
    `- 模板: ${templateLabel(task.template)}`,
    `- 数据源: ${task.source}`,
    `- 状态: ${task.status}`,
    `- 创建时间: ${fmtTime(task.created_at)}`,
    `- 更新时间: ${fmtTime(task.updated_at)}`,
    ``,
    `## 核心指标`,
    `- 在线无人机数: ${metrics.online ?? "-"}`,
    `- 累计完成任务数: ${metrics.tasks_completed ?? "-"}`,
    `- 吞吐量: ${fmtNumber(metrics.throughput, 4)}`,
    `- 累计冲突数: ${metrics.cumulative_conflicts ?? metrics.vertex_conflicts ?? "-"}`,
    `- 平均时延(步): ${metrics.avg_latency ?? "-"}`,
    ``,
    `## 告警列表`,
  ];
  if (!selectedAlerts.value.length) {
    lines.push("- 无告警");
  } else {
    selectedAlerts.value.forEach((alert) => {
      lines.push(`- [${alert.level}] ${alert.code} | step ${alert.frame_step} | ${alert.message}`);
    });
  }

  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `task-report-${task.task_id}.md`;
  a.click();
  URL.revokeObjectURL(url);
  status.value = `已导出报告：task-report-${task.task_id}.md`;
}

function fillTemplateFromTask() {
  if (!selectedTask.value) {
    status.value = "请先选择任务，再填充模板";
    return;
  }
  const task = selectedTask.value;
  const params = task.params || {};
  templateForm.template = task.template || "warehouse";
  templateForm.source = task.source || "sample";
  templateForm.mission_name = task.mission_name || "enterprise_batch_demo";
  templateForm.num_agents = Number(params.num_agents || 16);
  templateForm.max_frames = Number(params.max_frames || 64);
  templateForm.tick_ms = Number(task.tick_ms || 320);
  if (!templateForm.name) templateForm.name = `${templateLabel(templateForm.template)}-${templateForm.num_agents}机`;
  status.value = "已从当前任务填充模板参数";
}

function saveTemplate() {
  if (!templateForm.name.trim()) {
    status.value = "请先填写模板名称";
    return;
  }
  const saved = upsertOpsTemplate({
    id: templateForm.id || undefined,
    name: templateForm.name.trim(),
    template: templateForm.template,
    source: templateForm.source,
    mission_name: templateForm.mission_name,
    num_agents: templateForm.num_agents,
    max_frames: templateForm.max_frames,
    tick_ms: templateForm.tick_ms,
  });
  templateForm.id = saved.id;
  templates.value = loadOpsTemplates();
  status.value = `模板已保存：${saved.name}`;
}

function removeTemplate(templateId) {
  deleteOpsTemplate(templateId);
  templates.value = loadOpsTemplates();
  status.value = "模板已删除";
}

function applyTemplate(item) {
  window.localStorage.setItem("OPS_TEMPLATE_PREFILL", JSON.stringify(item));
  window.dispatchEvent(new CustomEvent("app-switch-mode", { detail: { mode: "ops" } }));
  status.value = `已将模板“${item.name}”应用到运营中心`;
}

function openOpsWithSelected() {
  if (!selectedTaskId.value) {
    status.value = "请先选择任务";
    return;
  }
  window.localStorage.setItem("OPS_FOCUS_TASK_ID", selectedTaskId.value);
  window.dispatchEvent(new CustomEvent("app-switch-mode", { detail: { mode: "ops" } }));
}

function handleTemplateUpdate() {
  templates.value = loadOpsTemplates();
}

onMounted(async () => {
  window.addEventListener("ops-template-updated", handleTemplateUpdate);
  await refreshTasks();
  pollTimer = window.setInterval(() => refreshTasks(), 3200);
});

onUnmounted(() => {
  stopReplayTimer();
  if (pollTimer) window.clearInterval(pollTimer);
  window.removeEventListener("ops-template-updated", handleTemplateUpdate);
});
</script>
