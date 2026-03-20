<template>
  <section v-if="isAdmin" class="admin-task-shell">
    <article class="panel admin-task-hero">
      <div>
        <p class="section-kicker">ADMIN WORKSPACE</p>
        <h2>任务调度台</h2>
        <p class="legend">把任务筛选、历史回放、创建分配与地图导入拆成独立工作界面，避免管理员在一个页面里同时处理所有事情。</p>
      </div>
      <div class="admin-summary-row">
        <div class="status-card">
          <p>任务总数</p>
          <strong>{{ adminTaskStats.total }}</strong>
        </div>
        <div class="status-card">
          <p>执行中任务</p>
          <strong>{{ adminTaskStats.running }}</strong>
        </div>
        <div class="status-card">
          <p>执行者账号</p>
          <strong>{{ assignees.length }}</strong>
        </div>
        <div class="status-card">
          <p>已导入地图</p>
          <strong>{{ importedMaps.length }}</strong>
        </div>
      </div>
    </article>

    <nav class="admin-workspace-tabs">
      <button class="tab-btn" :class="{ active: adminView === 'overview' }" @click="adminView = 'overview'">总览</button>
      <button class="tab-btn" :class="{ active: adminView === 'tasks' }" @click="adminView = 'tasks'">任务列表</button>
      <button class="tab-btn" :class="{ active: adminView === 'replay' }" @click="adminView = 'replay'">任务回放</button>
      <button class="tab-btn" :class="{ active: adminView === 'dispatch' }" @click="adminView = 'dispatch'">创建与地图</button>
    </nav>

    <section v-if="adminView === 'overview'" class="admin-workspace-grid admin-overview-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务总览</h2>
            <p class="legend">先看当前任务状态，再决定进入列表、回放还是创建流程。</p>
          </div>
          <div class="btn-row">
            <button class="btn" @click="refreshTasks">刷新列表</button>
            <button class="btn secondary" @click="adminView = 'dispatch'">创建新任务</button>
          </div>
        </div>
        <div class="status-chip">{{ status }}</div>

        <div class="admin-overview-list">
          <button
            v-for="task in adminRecentTasks"
            :key="task.task_id"
            class="admin-task-card"
            :class="{ active: task.task_id === selectedTaskId }"
            @click="selectTask(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ task.status }}</em>
            </span>
            <span class="admin-task-card-meta">{{ templateLabel(task.template) }} · {{ assigneeLabel(task) }}</span>
            <span class="admin-task-card-meta">更新时间 {{ fmtTime(task.updated_at) }} · 吞吐量 {{ fmtNumber(task.metrics?.throughput, 4) }}</span>
          </button>
          <div v-if="adminRecentTasks.length === 0" class="ops-alert-empty">当前没有可展示任务。</div>
        </div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>当前选中任务</h2>
            <p class="legend">聚焦一个任务的关键信息与后续操作。</p>
          </div>
          <div class="btn-row">
            <button class="btn secondary" @click="adminView = 'tasks'">进入任务列表</button>
            <button class="btn secondary" @click="adminView = 'replay'">查看回放</button>
          </div>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
          <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? "-" }}</strong></div>
          <div class="task-meta"><span>吞吐量</span><strong>{{ fmtNumber(selectedSnapshot?.metrics?.throughput, 4) }}</strong></div>
        </div>

        <div class="admin-highlight-card">
          <p>任务名称</p>
          <strong>{{ selectedTask?.mission_name || "未选择任务" }}</strong>
          <span>{{ selectedTask ? `${templateLabel(selectedTask.template)} · ${assigneeLabel(selectedTask)}` : "请先从左侧选择任务" }}</span>
        </div>

        <div class="btn-row">
          <button class="btn secondary" @click="openOpsWithSelected">进入运营中心</button>
          <button class="btn secondary" @click="exportReport">导出任务报告</button>
          <button class="btn secondary" @click="loadReplay">加载历史回放</button>
        </div>
      </article>
    </section>

    <section v-else-if="adminView === 'tasks'" class="admin-workspace-grid admin-list-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务列表</h2>
            <p class="legend">先筛选，再定位到要处理的任务。</p>
          </div>
          <div class="btn-row">
            <button class="btn" @click="refreshTasks">刷新列表</button>
            <button class="btn secondary" @click="exportReport">导出任务报告</button>
          </div>
        </div>

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

        <table class="fleet-table admin-fleet-table" style="margin-top: 8px">
          <thead>
            <tr>
              <th>任务ID</th>
              <th>任务名</th>
              <th>模板</th>
              <th>执行者</th>
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
              <td>{{ assigneeLabel(task) }}</td>
              <td>{{ task.status }}</td>
              <td>{{ fmtNumber(task.metrics?.throughput, 4) }}</td>
              <td>{{ fmtTime(task.updated_at) }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务摘要</h2>
            <p class="legend">展示当前所选任务的核心状态和快捷入口。</p>
          </div>
          <button class="btn secondary" @click="adminView = 'replay'">切到回放界面</button>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
          <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? "-" }}</strong></div>
          <div class="task-meta"><span>告警数</span><strong>{{ selectedSnapshot?.metrics?.alerts ?? "-" }}</strong></div>
        </div>

        <div class="admin-highlight-card compact">
          <p>当前任务</p>
          <strong>{{ selectedTask?.mission_name || "未选择任务" }}</strong>
          <span>{{ selectedTask ? `${templateLabel(selectedTask.template)} · ${selectedTask.source} · ${assigneeLabel(selectedTask)}` : "从左侧表格中选择一个任务" }}</span>
        </div>

        <div class="btn-row">
          <button class="btn secondary" @click="openOpsWithSelected">进入运营中心</button>
          <button class="btn secondary" @click="loadReplay">加载历史回放</button>
        </div>
      </article>
    </section>

    <section v-else-if="adminView === 'replay'" class="admin-workspace-grid admin-replay-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务详情与回放</h2>
            <p class="legend">单独处理回放与告警，避免和任务创建表单混在一起。</p>
          </div>
          <div class="btn-row">
            <button class="btn secondary" @click="loadReplay">加载历史回放</button>
            <button class="btn secondary" @click="togglePlayback">{{ replay.playing ? "暂停回放" : "播放回放" }}</button>
          </div>
        </div>

        <div class="task-meta-grid">
          <div class="task-meta"><span>任务ID</span><strong>{{ selectedTask?.task_id || "-" }}</strong></div>
          <div class="task-meta"><span>任务状态</span><strong>{{ selectedTask?.status || "-" }}</strong></div>
          <div class="task-meta"><span>累计任务数</span><strong>{{ selectedSnapshot?.metrics?.tasks_completed ?? "-" }}</strong></div>
          <div class="task-meta"><span>告警数</span><strong>{{ selectedSnapshot?.metrics?.alerts ?? "-" }}</strong></div>
        </div>

        <div class="admin-slider-row">
          <span>回放进度</span>
          <input
            v-model.number="replay.frameIndex"
            :max="Math.max(0, replay.frames.length - 1)"
            min="0"
            type="range"
            @input="drawReplayFrame"
          />
          <strong>{{ replay.frameIndex }}/{{ Math.max(0, replay.frames.length - 1) }}</strong>
        </div>

        <div class="canvas-wrap" style="margin-top: 10px">
          <canvas ref="canvasRef" width="920" height="460"></canvas>
        </div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>任务告警</h2>
            <p class="legend">告警列表和当前任务信息分开展示，便于阅读。</p>
          </div>
          <button class="btn secondary" @click="adminView = 'tasks'">返回任务列表</button>
        </div>

        <div class="admin-highlight-card compact">
          <p>当前任务</p>
          <strong>{{ selectedTask?.mission_name || "未选择任务" }}</strong>
          <span>{{ selectedTask ? `${templateLabel(selectedTask.template)} · ${assigneeLabel(selectedTask)}` : "请先在任务列表中选择任务" }}</span>
        </div>

        <div class="ops-alerts" style="margin-top: 10px">
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
    </section>

    <section v-else class="admin-workspace-grid admin-dispatch-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>创建并分配任务</h2>
            <p class="legend">这里专门处理任务创建，不再和历史回放混排。</p>
          </div>
          <button class="btn secondary" @click="syncAssigneeDisplayName">同步执行者名称</button>
        </div>

        <div class="field-grid">
          <label>任务名称 <input v-model="assignForm.mission_name" placeholder="如：night_shift_assign_01" /></label>
          <label>任务模板
            <select v-model="assignForm.template">
              <option value="warehouse">仓储巡检</option>
              <option value="campus">园区配送</option>
              <option value="emergency">应急调度</option>
            </select>
          </label>
          <label>执行数据源
            <select v-model="assignForm.source">
              <option value="sample">sample</option>
              <option value="model">model</option>
            </select>
          </label>
          <label>分配执行者
            <select v-model="assignForm.assignee_user_id" @change="syncAssigneeDisplayName">
              <option v-for="user in assignees" :key="user.user_id" :value="user.user_id">{{ user.display_name }} ({{ user.username }})</option>
            </select>
          </label>
          <label>地图名称 <input v-model="assignForm.map_name" placeholder="如：warehouse-grid-v1" /></label>
          <label>无人机数量 <input v-model.number="assignForm.num_agents" min="1" type="number" /></label>
          <label>最大帧数 <input v-model.number="assignForm.max_frames" min="4" type="number" /></label>
          <label>节拍(ms) <input v-model.number="assignForm.tick_ms" min="120" step="20" type="number" /></label>
        </div>

        <div class="btn-row" style="margin-top: 10px">
          <button class="btn" @click="createAndAssignTask">创建并分配任务</button>
        </div>
        <div class="status-chip">{{ assignStatus }}</div>
      </article>

      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <h2>地图管理</h2>
            <p class="legend">导入地图、查看最近导入记录，并一键设为当前任务地图。</p>
          </div>
        </div>

        <div class="field-grid admin-map-import-grid">
          <label>导入地图(JSON)
            <input accept=".json,application/json" type="file" @change="onImportMapFile" />
          </label>
        </div>

        <table class="fleet-table" style="margin-top: 8px">
          <thead>
            <tr>
              <th>地图名</th>
              <th>来源文件</th>
              <th>导入时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in importedMaps" :key="item.id">
              <td>{{ item.map_name }}</td>
              <td>{{ item.file_name }}</td>
              <td>{{ fmtTime(item.ts) }}</td>
              <td>
                <button class="btn secondary" @click="applyImportedMap(item)">设为任务地图</button>
              </td>
            </tr>
          </tbody>
        </table>
      </article>
    </section>
  </section>

  <section v-else class="task-center-grid executor-task-grid">
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
            <th>执行者</th>
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
            <td>{{ assigneeLabel(task) }}</td>
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
      <h2>执行者工作台</h2>
      <p class="legend">执行者仅可执行管理员分配的任务，不能创建任务或导入地图。</p>
      <div class="status-chip">当前账号：{{ currentUser?.display_name || "-" }}</div>
      <div class="admin-highlight-card compact" style="margin-top: 12px">
        <p>当前权限</p>
        <strong>仅查看与执行</strong>
        <span>可以查看分配给自己的任务、载入回放并跳转到运营中心。</span>
      </div>
      <div class="btn-row" style="margin-top: 12px">
        <button class="btn secondary" @click="openOpsWithSelected">进入运营中心</button>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { createOpsTask, fetchAuthOptions, fetchOpsTasks, fetchOpsAlerts, getOpsTask, fetchTaskReplay } from "../../services/api";
import { createRenderer } from "../shared/renderer";

const props = defineProps({
  role: {
    type: String,
    default: "executor",
  },
  currentUser: {
    type: Object,
    default: null,
  },
});

const renderer = createRenderer();
const canvasRef = ref(null);
const status = ref("任务中心初始化中...");
const assignStatus = ref("管理员可创建任务并分配给执行者。");
const tasks = ref([]);
const selectedTaskId = ref("");
const selectedTask = ref(null);
const selectedSnapshot = ref(null);
const selectedAlerts = ref([]);
const assignees = ref([]);
const importedMaps = ref(loadImportedMaps());
const replayTimer = ref(null);
let pollTimer = null;
const adminView = ref("overview");

const filters = reactive({
  status: "ALL",
  template: "ALL",
  keyword: "",
});

const assignForm = reactive({
  mission_name: "dispatch_batch_001",
  template: "warehouse",
  source: "sample",
  assignee_user_id: "",
  assignee_display_name: "",
  map_name: "warehouse-grid-v1",
  num_agents: 16,
  max_frames: 64,
  tick_ms: 320,
});

const isAdmin = computed(() => props.role === "admin");
const currentUserId = computed(() => props.currentUser?.user_id || "");
const currentUser = computed(() => props.currentUser);

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
    if (!isAdmin.value) {
      const assignee = String(task?.params?.assignee_user_id || "");
      if (!assignee || assignee !== currentUserId.value) return false;
    }
    if (filters.status !== "ALL" && task.status !== filters.status) return false;
    if (filters.template !== "ALL" && task.template !== filters.template) return false;
    if (!keyword) return true;
    return task.task_id.toLowerCase().includes(keyword) || String(task.mission_name || "").toLowerCase().includes(keyword);
  });
});

const adminRecentTasks = computed(() => filteredTasks.value.slice(0, 6));
const adminTaskStats = computed(() => ({
  total: tasks.value.length,
  running: tasks.value.filter((task) => task.status === "RUNNING").length,
}));

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

function assigneeLabel(task) {
  const params = task?.params || {};
  return params.assignee_display_name || params.assignee_user_id || "-";
}

function loadImportedMaps() {
  try {
    const raw = window.localStorage.getItem("OPS_IMPORTED_MAPS");
    const parsed = JSON.parse(raw || "[]");
    if (Array.isArray(parsed)) return parsed;
    return [];
  } catch {
    return [];
  }
}

function saveImportedMaps() {
  window.localStorage.setItem("OPS_IMPORTED_MAPS", JSON.stringify(importedMaps.value.slice(-20)));
}

async function refreshAssignees() {
  if (!isAdmin.value) return;
  try {
    const payload = await fetchAuthOptions();
    assignees.value = (payload?.accounts || []).filter((item) => item.role === "executor");
    if (!assignForm.assignee_user_id && assignees.value.length) {
      assignForm.assignee_user_id = assignees.value[0].user_id;
      assignForm.assignee_display_name = assignees.value[0].display_name;
    }
  } catch (error) {
    assignStatus.value = `执行者列表加载失败：${error.message}`;
  }
}

async function refreshTasks() {
  try {
    const data = await fetchOpsTasks(100);
    tasks.value = data.tasks || [];
    const visibleList = filteredTasks.value;
    if ((!selectedTaskId.value || !visibleList.some((task) => task.task_id === selectedTaskId.value)) && visibleList.length) {
      selectedTaskId.value = visibleList[0].task_id;
    }
    if (selectedTaskId.value) {
      await loadTaskDetail(selectedTaskId.value, false);
    }
    status.value = `任务列表已更新，可见 ${visibleList.length} 条（总 ${tasks.value.length} 条）`;
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

function syncAssigneeDisplayName() {
  const target = assignees.value.find((item) => item.user_id === assignForm.assignee_user_id);
  assignForm.assignee_display_name = target?.display_name || "";
}

async function createAndAssignTask() {
  if (!isAdmin.value) {
    assignStatus.value = "仅管理员可创建和分配任务";
    return;
  }
  if (!assignForm.assignee_user_id) {
    assignStatus.value = "请先选择执行者";
    return;
  }
  syncAssigneeDisplayName();
  try {
    const created = await createOpsTask({
      mission_name: assignForm.mission_name,
      template: assignForm.template,
      source: assignForm.source,
      map_name: assignForm.map_name,
      num_agents: assignForm.num_agents,
      max_frames: assignForm.max_frames,
      tick_ms: assignForm.tick_ms,
      assignee_user_id: assignForm.assignee_user_id,
      assignee_display_name: assignForm.assignee_display_name,
    });
    selectedTaskId.value = created?.task?.task_id || "";
    await refreshTasks();
    assignStatus.value = `任务已创建并分配给 ${assignForm.assignee_display_name}`;
  } catch (error) {
    assignStatus.value = `任务创建失败：${error.message}`;
  }
}

function onImportMapFile(event) {
  if (!isAdmin.value) return;
  const file = event?.target?.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(String(reader.result || "{}"));
      const mapName = String(parsed.map_name || file.name.replace(/\.[^.]+$/, "") || "imported-map");
      const item = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        map_name: mapName,
        file_name: file.name,
        ts: Date.now() / 1000,
      };
      importedMaps.value = [item, ...importedMaps.value.filter((m) => m.map_name !== mapName)].slice(0, 20);
      saveImportedMaps();
      assignForm.map_name = mapName;
      assignStatus.value = `地图已导入：${mapName}`;
    } catch (error) {
      assignStatus.value = `地图导入失败：${error.message}`;
    }
  };
  reader.readAsText(file, "utf-8");
}

function applyImportedMap(item) {
  assignForm.map_name = item.map_name;
  assignStatus.value = `已选择地图：${item.map_name}`;
}

function openOpsWithSelected() {
  if (!selectedTaskId.value) {
    status.value = "请先选择任务";
    return;
  }
  if (!isAdmin.value) {
    const task = tasks.value.find((item) => item.task_id === selectedTaskId.value);
    const assignee = String(task?.params?.assignee_user_id || "");
    if (assignee !== currentUserId.value) {
      status.value = "该任务未分配给当前执行者";
      return;
    }
  }
  window.localStorage.setItem("OPS_FOCUS_TASK_ID", selectedTaskId.value);
  window.dispatchEvent(new CustomEvent("app-switch-mode", { detail: { mode: "ops" } }));
}

onMounted(async () => {
  await refreshAssignees();
  await refreshTasks();
  pollTimer = window.setInterval(() => refreshTasks(), 3200);
});

onUnmounted(() => {
  stopReplayTimer();
  if (pollTimer) window.clearInterval(pollTimer);
});
</script>
