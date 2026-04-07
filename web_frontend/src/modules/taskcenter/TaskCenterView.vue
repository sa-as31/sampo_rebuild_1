<template>
  <section v-if="isAdmin" class="admin-task-shell">
    <section v-if="adminSection === 'overview'" class="admin-workspace-grid admin-overview-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">ADMIN OVERVIEW</p>
            <h2>调度总览</h2>
          </div>
          <button class="btn" @click="refreshTasks">同步数据</button>
        </div>

        <div class="status-cards admin-overview-status-cards">
          <div class="status-card">
            <p>总任务</p>
            <strong>{{ adminTaskStats.total }}</strong>
          </div>
          <div class="status-card">
            <p>执行中</p>
            <strong>{{ adminTaskStats.active }}</strong>
          </div>
          <div class="status-card">
            <p>已归档</p>
            <strong>{{ adminTaskStats.completed }}</strong>
          </div>
          <div class="status-card">
            <p>待审核</p>
            <strong>{{ adminTaskStats.pending }}</strong>
          </div>
        </div>

        <div class="admin-overview-list admin-overview-route-list">
          <button class="admin-task-card" @click="$router.push('/admin/pending')">
            <span class="admin-task-card-top">
              <strong>审核队列</strong>
              <em>{{ pendingReviewTasks.length }} 条</em>
            </span>
            <span class="admin-task-card-meta">查看新申请、审批结论与任务分配。</span>
          </button>
          <button class="admin-task-card" @click="$router.push('/admin/active')">
            <span class="admin-task-card-top">
              <strong>执行调度</strong>
              <em>{{ activeTasks.length }} 条</em>
            </span>
            <span class="admin-task-card-meta">跟进待执行、执行中与暂停任务。</span>
          </button>
          <button class="admin-task-card" @click="$router.push('/admin/completed')">
            <span class="admin-task-card-top">
              <strong>任务归档</strong>
              <em>{{ completedTasks.length }} 条</em>
            </span>
            <span class="admin-task-card-meta">查看回放、告警与任务闭环结果。</span>
          </button>
        </div>

        <div class="admin-highlight-card compact">
          <p>最新状态</p>
          <strong>{{ latestAdminTask?.mission_name || "当前暂无任务" }}</strong>
          <span v-if="latestAdminTask">
            {{ taskStageLabel(latestAdminTask.status) }} · {{ fmtDateTime(latestAdminTask.updated_at || latestAdminTask.created_at) }}
          </span>
          <span v-else>任务队列更新后会在这里显示最近变更。</span>
        </div>
      </article>
    </section>

    <section v-else-if="adminSection === 'create'" class="admin-workspace-grid admin-dispatch-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">REVIEW QUEUE</p>
            <h2>待审核申请</h2>
          </div>
          <button class="btn" @click="refreshTasks">同步队列</button>
        </div>

        <div class="admin-subheadline">
          <span>当前待审核 {{ pendingReviewTasks.length }} 条</span>
          <span v-if="status">{{ status }}</span>
        </div>

        <div class="admin-overview-list" style="grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));">
          <button
            v-for="task in pendingReviewTasks"
            :key="task.task_id"
            class="admin-task-card"
            @click="$router.push(`/task/${task.task_id}?role=admin&section=create`)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskCategoryLabel(task.params?.task_category) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ requesterLabel(task) }} · {{ task.params?.requested_location || task.params?.map_name || "-" }}</span>
            <span class="admin-task-card-meta">申请 {{ fmtDateTime(task.created_at) }} · 执行窗口 {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          </button>
          <div v-if="pendingReviewTasks.length === 0" class="ops-alert-empty">当前没有待审核申请。</div>
        </div>
      </article>
    </section>

    <section v-else-if="adminSection === 'active'" class="admin-workspace-grid admin-active-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">ACTIVE OPS</p>
            <h2>执行中任务</h2>
          </div>
          <button class="btn" @click="refreshTasks">刷新列表</button>
        </div>

        <div class="admin-subheadline">
          <span>待执行 {{ activeTasks.filter((task) => ['PREPARING','READY'].includes(task.status)).length }} 条</span>
          <span>运行或暂停 {{ activeTasks.filter((task) => ['RUNNING','PAUSED'].includes(task.status)).length }} 条</span>
          <span v-if="status">{{ status }}</span>
        </div>

        <div class="admin-toolbar-row">
          <label class="admin-search">
            <span>搜索任务</span>
            <input v-model="adminFilters.activeKeyword" placeholder="任务名 / task_id / 飞手" />
          </label>
          <label class="admin-search">
            <span>按日期筛选</span>
            <div class="date-picker-trigger" @click="openDatePicker(adminActiveDateInputRef)">
              <input
                ref="adminActiveDateInputRef"
                v-model="adminFilters.activeDate"
                class="date-picker-input"
                type="date"
                @keydown.prevent
                @beforeinput.prevent
              />
              <button class="date-picker-button" type="button" @click.stop="openDatePicker(adminActiveDateInputRef)">选择日期</button>
            </div>
          </label>
        </div>

        <div class="admin-overview-list" style="grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));">
          <button
            v-for="task in filteredActiveTasks"
            :key="task.task_id"
            class="admin-task-card"
            @click="$router.push(`/task/${task.task_id}?role=admin&section=active`)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ templateLabel(task.template) }} · {{ assigneeLabel(task) }}</span>
            <span class="admin-task-card-meta">计划开始 {{ fmtDateTime(task.params?.scheduled_start_at) }} · 状态 {{ task.status }}</span>
          </button>
          <div v-if="filteredActiveTasks.length === 0" class="ops-alert-empty">当前没有执行中任务。</div>
        </div>
      </article>
    </section>

    <section v-else class="admin-workspace-grid admin-completed-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">ARCHIVE</p>
            <h2>任务归档</h2>
          </div>
          <button class="btn" @click="refreshTasks">刷新历史</button>
        </div>

        <div class="admin-subheadline">
          <span>已归档 {{ completedTasks.length }} 条</span>
          <span v-if="status">{{ status }}</span>
        </div>

        <div class="admin-toolbar-row">
          <label class="admin-search">
            <span>搜索任务</span>
            <input v-model="adminFilters.completedKeyword" placeholder="任务名 / task_id / 飞手" />
          </label>
          <label class="admin-search">
            <span>按日期筛选</span>
            <div class="date-picker-trigger" @click="openDatePicker(adminCompletedDateInputRef)">
              <input
                ref="adminCompletedDateInputRef"
                v-model="adminFilters.completedDate"
                class="date-picker-input"
                type="date"
                @keydown.prevent
                @beforeinput.prevent
              />
              <button class="date-picker-button" type="button" @click.stop="openDatePicker(adminCompletedDateInputRef)">选择日期</button>
            </div>
          </label>
        </div>

        <div class="admin-overview-list" style="grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));">
          <button
            v-for="task in filteredCompletedTasks"
            :key="task.task_id"
            class="admin-task-card"
            @click="$router.push(`/task/${task.task_id}?role=admin&section=completed`)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ assigneeLabel(task) }} · 归档于 {{ fmtDateTime(task.ended_at || task.updated_at) }}</span>
            <span class="admin-task-card-meta">系统告警 {{ selectedTaskId === task.task_id ? selectedAlerts.length : Number(task.metrics?.alerts || 0) }} · 状态 {{ task.status }}</span>
          </button>
          <div v-if="filteredCompletedTasks.length === 0" class="ops-alert-empty">当前没有已完成任务。</div>
        </div>
      </article>
    </section>
  </section>

  <section v-else-if="isRequester" class="admin-task-shell">
    <nav class="admin-workspace-tabs">
      <button class="tab-btn" :class="{ active: requesterSection === 'create' }" @click="router.push('/requester/create')">发起申请</button>
      <button class="tab-btn" :class="{ active: requesterSection === 'history' }" @click="router.push('/requester/history')">我的申请</button>
    </nav>

    <section v-if="requesterSection === 'create'" class="admin-workspace-grid requester-create-grid requester-create-grid-single">
      <article class="panel requester-form-panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">NEW REQUEST</p>
            <h2>新建任务申请</h2>
          </div>
        </div>

        <div class="field-grid requester-form-grid">
          <label>任务名称
            <input v-model="requestForm.mission_name" placeholder="如：north_zone_patrol_request" />
          </label>
          <label>任务类别
            <select v-model="requestForm.task_category">
              <option value="patrol">巡逻</option>
              <option value="show">表演</option>
              <option value="transport">运输</option>
            </select>
          </label>
          <label>执行地点
            <input v-model="requestForm.requested_location" placeholder="如：北区 3 号楼天台 / 仓库 A 区" />
          </label>
          <label>申请执行时间
            <input v-model="requestForm.scheduled_start_input" type="datetime-local" />
          </label>
        </div>

        <div class="admin-highlight-card">
          <p>提交预览</p>
          <strong>{{ requestForm.mission_name }}</strong>
          <span>{{ taskCategoryLabel(requestForm.task_category) }} · {{ requestForm.requested_location || "未填写地点" }}</span>
          <span>执行窗口：{{ requesterScheduledPreview }}</span>
        </div>

        <div class="btn-row" style="margin-top: 12px">
          <button class="btn" @click="submitTaskRequest">提交任务申请</button>
        </div>
        <div v-if="requestStatus" class="status-chip">{{ requestStatus }}</div>
      </article>
    </section>

    <section v-else class="admin-workspace-grid requester-history-grid">
      <article class="panel">
        <div class="admin-panel-head">
          <div>
            <p class="section-kicker">REQUEST HISTORY</p>
            <h2>我的申请记录</h2>
          </div>
          <button class="btn" @click="refreshTasks">刷新列表</button>
        </div>

        <div class="admin-subheadline">
          <span>待审核 {{ requesterTaskStats.pending }} 条</span>
          <span>已通过 {{ requesterTaskStats.approved }} 条</span>
        </div>

        <div class="status-cards requester-status-grid">
          <div class="status-card"><p>申请总数</p><strong>{{ requesterTaskStats.total }}</strong></div>
          <div class="status-card"><p>待审核</p><strong>{{ requesterTaskStats.pending }}</strong></div>
          <div class="status-card"><p>已通过</p><strong>{{ requesterTaskStats.approved }}</strong></div>
          <div class="status-card"><p>已驳回</p><strong>{{ requesterTaskStats.rejected }}</strong></div>
        </div>

        <div class="admin-highlight-card compact">
          <p>最近申请</p>
          <strong>{{ latestRequesterTask?.mission_name || "暂无申请记录" }}</strong>
          <span v-if="latestRequesterTask">
            {{ taskStageLabel(latestRequesterTask.status) }} · {{ fmtDateTime(latestRequesterTask.updated_at || latestRequesterTask.created_at) }}
          </span>
          <span v-else>提交后会在这里看到最新处理进展。</span>
        </div>

        <div class="admin-overview-list">
          <button
            v-for="task in requesterTasks"
            :key="task.task_id"
            class="admin-task-card"
            @click="openTaskDetail(task.task_id)"
          >
            <span class="admin-task-card-top">
              <strong>{{ task.mission_name }}</strong>
              <em>{{ taskStageLabel(task.status) }}</em>
            </span>
            <span class="admin-task-card-meta">{{ taskCategoryLabel(task.params?.task_category) }} · {{ task.params?.requested_location || "-" }}</span>
            <span class="admin-task-card-meta">飞手 {{ assigneeLabel(task) }} · 执行窗口 {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          </button>
          <div v-if="requesterTasks.length === 0" class="ops-alert-empty">当前还没有提交任务申请。</div>
        </div>
      </article>
    </section>
  </section>

  <section v-else class="executor-task-shell">
    <article class="panel executor-task-list">
      <div class="admin-panel-head">
        <div>
          <p class="section-kicker">TASK FILTERS</p>
          <h2>分配给我的任务</h2>
        </div>
        <button class="btn" @click="refreshTasks">刷新列表</button>
      </div>

      <div class="admin-subheadline">
        <span>待执行 {{ filteredTasks.filter((task) => ['PREPARING', 'READY'].includes(task.status)).length }} 条</span>
        <span>执行中 {{ filteredTasks.filter((task) => ['RUNNING', 'PAUSED'].includes(task.status)).length }} 条</span>
        <span>已结束 {{ filteredTasks.filter((task) => FINAL_STATUSES.has(task.status)).length }} 条</span>
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
        <label>按日期筛选
          <div class="date-picker-trigger" @click="openDatePicker(executorDateInputRef)">
            <input
              ref="executorDateInputRef"
              v-model="filters.date"
              class="date-picker-input"
              type="date"
              @keydown.prevent
              @beforeinput.prevent
            />
            <button class="date-picker-button" type="button" @click.stop="openDatePicker(executorDateInputRef)">选择日期</button>
          </div>
        </label>
      </div>

      <div v-if="status" class="status-chip">{{ status }}</div>

      <div class="executor-task-stack">
        <button
          v-for="task in filteredTasks"
          :key="task.task_id"
          class="admin-task-card"
          @click="openTaskDetail(task.task_id)"
        >
          <span class="admin-task-card-top">
            <strong>{{ task.mission_name }}</strong>
            <em>{{ taskStageLabel(task.status) }}</em>
          </span>
          <span class="admin-task-card-meta">{{ templateLabel(task.template) }} · {{ fmtDateTime(task.params?.scheduled_start_at) }}</span>
          <span class="admin-task-card-meta">任务ID {{ task.task_id }} · 状态 {{ task.status }}</span>
        </button>
        <div v-if="filteredTasks.length === 0" class="ops-alert-empty">当前没有分配给你的任务。</div>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import OperationsModeView from "../operations/OperationsModeView.vue";
import { useAuthStore } from "../../stores/auth";
import {
  controlOpsTask,
  createOpsTask,
  fetchAuthOptions,
  fetchOpsAlerts,
  fetchOpsTasks,
  fetchTaskFeedback,
  fetchTaskReplay,
  getOpsTask,
  submitTaskFeedback,
} from "../../services/api";
import { createRenderer, drawScene3D, resizeCanvasToDisplaySize } from "../shared/renderer";

const TEMPLATE_MAP_OPTIONS = [
  { value: "warehouse-grid-v1", label: "仓储巡检默认地图", source: "template" },
  { value: "campus-road-v1", label: "园区配送默认地图", source: "template" },
  { value: "emergency-block-v1", label: "应急调度默认地图", source: "template" },
];

const ACTIVE_STATUSES = new Set(["PREPARING", "READY", "RUNNING", "PAUSED"]);
const FINAL_STATUSES = new Set(["COMPLETED", "FAILED", "STOPPED", "REJECTED"]);
const DEFAULT_TASK_TICK_MS = 600;

const props = defineProps({
  role: {
    type: String,
    default: "executor",
  },
  section: {
    type: String,
    default: "",
  },
  currentUser: {
    type: Object,
    default: null,
  },
});

const router = useRouter();
const authStore = useAuthStore();
const renderer = createRenderer();
const liveCanvasRef = ref(null);
const historyCanvasRef = ref(null);
const history3dCanvasRef = ref(null);
const executorHistoryCanvasRef = ref(null);
const executorHistory3dCanvasRef = ref(null);
const executorDateInputRef = ref(null);
const adminActiveDateInputRef = ref(null);
const adminCompletedDateInputRef = ref(null);
const status = ref("任务中心初始化中...");
const assignStatus = ref("");
const feedbackStatus = ref("");
const requestStatus = ref("");
const tasks = ref([]);
const selectedTaskId = ref("");
const selectedTask = ref(null);
const selectedSnapshot = ref(null);
const selectedAlerts = ref([]);
const selectedFeedback = ref([]);
const assignees = ref([]);
const importedMaps = ref(loadImportedMaps());
const replayTimer = ref(null);
const replayVisualTimer = ref(null);
const adminSection = ref("overview");
let pollTimer = null;

const filters = reactive({
  status: "ALL",
  template: "ALL",
  keyword: "",
  date: "",
});

const adminFilters = reactive({
  activeKeyword: "",
  completedKeyword: "",
  activeDate: "",
  completedDate: "",
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
  tick_ms: DEFAULT_TASK_TICK_MS,
  scheduled_start_input: buildDefaultScheduleInput(),
  review_note: "",
});

const requestForm = reactive({
  mission_name: "north_zone_patrol_request",
  task_category: "patrol",
  requested_location: "北区 3 号楼天台",
  scheduled_start_input: buildDefaultScheduleInput(),
});

const feedbackForm = reactive({
  category: "issue",
  message: "",
});
const executorView = ref("execute");
const requesterSection = ref("create");
const reviewFormTaskId = ref("");
const pilotSpeedInput = ref(1200);
const replaySpeedInput = ref(220);

const replay = reactive({
  available: false,
  frames: [],
  environment: null,
  frameIndex: 0,
  playing: false,
  reason: "",
});

const replayViewState = reactive({
  selectedDroneId: 0,
});

const isAdmin = computed(() => props.role === "admin");
const isRequester = computed(() => props.role === "requester");
const resolvedCurrentUser = computed(() => props.currentUser || authStore.state.currentUser || null);
const currentUserId = computed(() => resolvedCurrentUser.value?.user_id || "");
const currentUser = computed(() => resolvedCurrentUser.value);
const hasExecutorSelection = computed(() => !isAdmin.value && !!selectedTaskId.value && !!selectedTask.value);
const executorAssignedTasks = computed(() =>
  tasks.value.filter((task) => String(task?.params?.assignee_user_id || "") === currentUserId.value),
);

const filteredTasks = computed(() => {
  const keyword = filters.keyword.trim().toLowerCase();
  return executorAssignedTasks.value.filter((task) => {
    if (filters.status !== "ALL" && task.status !== filters.status) return false;
    if (filters.template !== "ALL" && task.template !== filters.template) return false;
    if (filters.date && !matchTaskDate(task, filters.date)) return false;
    if (!keyword) return true;
    return matchTaskKeyword(task, keyword);
  });
});

const availableMapChoices = computed(() => {
  const imported = importedMaps.value.map((item) => ({
    value: item.map_name,
    label: `${item.map_name}（已导入）`,
    source: "imported",
  }));
  const unique = new Map();
  [...imported, ...TEMPLATE_MAP_OPTIONS].forEach((item) => {
    if (!unique.has(item.value)) unique.set(item.value, item);
  });
  return Array.from(unique.values());
});

const selectedAssigneeLabel = computed(() => {
  const target = assignees.value.find((item) => item.user_id === assignForm.assignee_user_id);
  return target ? `${target.display_name}（${target.username}）` : "未指定飞手";
});

const scheduledPreviewText = computed(() => {
  const ts = parseScheduledInput(assignForm.scheduled_start_input);
  return ts ? fmtDateTime(ts) : "未设置";
});
const requesterScheduledPreview = computed(() => {
  const ts = parseScheduledInput(requestForm.scheduled_start_input);
  return ts ? fmtDateTime(ts) : "未设置";
});

const pendingReviewTasks = computed(() => tasks.value.filter((task) => task.status === "PENDING_REVIEW"));
const activeTasks = computed(() => tasks.value.filter((task) => ACTIVE_STATUSES.has(task.status)));
const completedTasks = computed(() => tasks.value.filter((task) => FINAL_STATUSES.has(task.status)));
const requesterTasks = computed(() =>
  tasks.value.filter((task) => String(task?.params?.requester_user_id || "") === currentUserId.value),
);

const filteredActiveTasks = computed(() => filterAdminTasks(activeTasks.value, adminFilters.activeKeyword, adminFilters.activeDate));
const filteredCompletedTasks = computed(() => filterAdminTasks(completedTasks.value, adminFilters.completedKeyword, adminFilters.completedDate));

const adminTaskStats = computed(() => ({
  total: tasks.value.length,
  active: activeTasks.value.length,
  completed: completedTasks.value.length,
  pending: pendingReviewTasks.value.length,
}));
const latestAdminTask = computed(() =>
  tasks.value
    .slice()
    .sort((a, b) => Number(b.updated_at || b.created_at || 0) - Number(a.updated_at || a.created_at || 0))[0] || null,
);
const requesterTaskStats = computed(() => ({
  total: requesterTasks.value.length,
  pending: requesterTasks.value.filter((task) => task.status === "PENDING_REVIEW").length,
  approved: requesterTasks.value.filter((task) => ACTIVE_STATUSES.has(task.status) || task.status === "COMPLETED").length,
  rejected: requesterTasks.value.filter((task) => task.status === "REJECTED").length,
}));
const latestRequesterTask = computed(() =>
  requesterTasks.value
    .slice()
    .sort((a, b) => Number(b.updated_at || b.created_at || 0) - Number(a.updated_at || a.created_at || 0))[0] || null,
);
const executorTaskStats = computed(() => ({
  total: executorAssignedTasks.value.length,
  queued: executorAssignedTasks.value.filter((task) => ["PREPARING", "READY"].includes(task.status)).length,
  active: executorAssignedTasks.value.filter((task) => ["RUNNING", "PAUSED"].includes(task.status)).length,
  finished: executorAssignedTasks.value.filter((task) => FINAL_STATUSES.has(task.status)).length,
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

function fmtDateTime(ts) {
  if (!ts) return "-";
  const d = new Date(Number(ts) * 1000);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function buildDefaultScheduleInput() {
  const d = new Date(Date.now() + 10 * 60 * 1000);
  d.setSeconds(0, 0);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function parseScheduledInput(value) {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return Math.floor(parsed.getTime() / 1000);
}

function buildDateTimeLocalInput(ts) {
  if (!ts) return "";
  const d = new Date(Number(ts) * 1000);
  if (Number.isNaN(d.getTime())) return "";
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}T${hh}:${mi}`;
}

function templateLabel(key) {
  if (key === "campus") return "园区配送";
  if (key === "emergency") return "应急调度";
  return "仓储巡检";
}

function taskCategoryLabel(value) {
  if (value === "show") return "表演";
  if (value === "transport") return "运输";
  return "巡逻";
}

function assigneeLabel(task) {
  const params = task?.params || {};
  return params.assignee_display_name || params.assignee_user_id || "待分配";
}

function requesterLabel(task) {
  const params = task?.params || {};
  return params.requester_display_name || params.requester_username || "-";
}

function feedbackCategoryLabel(category) {
  if (category === "delay_request") return "延期申请";
  if (category === "anomaly") return "异常上报";
  if (category === "risk") return "风险";
  if (category === "note") return "备注";
  return "问题";
}

function taskStageLabel(status) {
  const value = String(status || "").toUpperCase();
  if (value === "PENDING_REVIEW") return "待审核";
  if (value === "REJECTED") return "已驳回";
  if (["PREPARING", "READY"].includes(value)) return "待执行";
  if (["RUNNING", "PAUSED"].includes(value)) return "执行中";
  return "已完成";
}

function matchTaskKeyword(task, keyword) {
  return [
    task.task_id,
    task.mission_name,
    assigneeLabel(task),
    task.params?.map_name,
  ]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(keyword));
}

function filterAdminTasks(list, keyword, dateValue) {
  const normalized = String(keyword || "").trim().toLowerCase();
  return list.filter((task) => {
    if (dateValue && !matchTaskDate(task, dateValue)) return false;
    if (!normalized) return true;
    return matchTaskKeyword(task, normalized);
  });
}

function matchTaskDate(task, dateValue) {
  if (!dateValue) return true;
  const candidates = collectTaskDateCandidates(task);
  return candidates.some((candidate) => formatDateOnly(candidate) === dateValue);
}

function collectTaskDateCandidates(task) {
  const status = String(task?.status || "").toUpperCase();
  const params = task?.params || {};
  const rawCandidates = [];

  if (["COMPLETED", "FAILED", "STOPPED"].includes(status)) {
    rawCandidates.push(task?.ended_at, task?.updated_at, params?.scheduled_start_at, task?.created_at);
  } else if (["RUNNING", "PAUSED"].includes(status)) {
    rawCandidates.push(params?.scheduled_start_at, task?.started_at, task?.created_at, task?.updated_at);
  } else {
    rawCandidates.push(params?.scheduled_start_at, task?.created_at, task?.updated_at);
  }

  return rawCandidates
    .map((value) => Number(value || 0))
    .filter((value, index, list) => value > 0 && list.indexOf(value) === index);
}

function formatDateOnly(ts) {
  if (!ts) return "";
  const d = new Date(Number(ts) * 1000);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function openDatePicker(inputRef) {
  const input = inputRef?.value;
  if (!input) return;
  if (typeof input.showPicker === "function") {
    input.showPicker();
    return;
  }
  input.focus();
  input.click();
}

function ensureVersionedMapName(baseName) {
  const normalized = String(baseName || "imported-map").trim() || "imported-map";
  const existing = new Set(importedMaps.value.map((item) => item.map_name));
  if (!existing.has(normalized)) return normalized;
  let version = 2;
  while (existing.has(`${normalized}-v${version}`)) version += 1;
  return `${normalized}-v${version}`;
}

function loadImportedMaps() {
  try {
    const raw = window.localStorage.getItem("OPS_IMPORTED_MAPS");
    const parsed = JSON.parse(raw || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveImportedMaps() {
  window.localStorage.setItem("OPS_IMPORTED_MAPS", JSON.stringify(importedMaps.value.slice(-20)));
}

function drawEmptyCanvas(canvas, message) {
  if (!canvas) return;
  resizeCanvasToDisplaySize(canvas);
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#061327";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "rgba(205,225,255,0.84)";
  ctx.font = '15px "PingFang SC", "Noto Sans SC", sans-serif';
  ctx.textAlign = "center";
  ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

function drawTaskSnapshotTo(canvas) {
  if (selectedSnapshot.value?.environment && selectedSnapshot.value?.frame && canvas) {
    resizeCanvasToDisplaySize(canvas);
    renderer.draw(canvas, selectedSnapshot.value.environment, selectedSnapshot.value.frame);
    return;
  }
  drawEmptyCanvas(canvas, "暂无实时任务画面");
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
    assignStatus.value = `飞手列表加载失败：${error.message}`;
  }
}

async function refreshTasks() {
  try {
    const data = await fetchOpsTasks(100);
    tasks.value = data.tasks || [];
    ensureSelectedTask();
    if (selectedTaskId.value) {
      await loadTaskDetail(selectedTaskId.value, false);
    } else {
      selectedTask.value = null;
      selectedSnapshot.value = null;
      selectedAlerts.value = [];
      selectedFeedback.value = [];
    }
    if (isAdmin.value) {
      status.value = `任务已刷新：待审核 ${pendingReviewTasks.value.length}，执行中 ${activeTasks.value.length}，已完成 ${completedTasks.value.length}`;
    } else if (isRequester.value) {
      status.value = "";
    } else {
      status.value = "";
    }
  } catch (error) {
    status.value = `刷新失败：${error.message}`;
  }
}

function ensureSelectedTask() {
  const pool = isAdmin.value ? tasks.value : isRequester.value ? requesterTasks.value : filteredTasks.value;
  if (pool.some((task) => task.task_id === selectedTaskId.value)) return;
  if (isAdmin.value) {
    selectedTaskId.value =
      pendingReviewTasks.value[0]?.task_id ||
      activeTasks.value[0]?.task_id ||
      completedTasks.value[0]?.task_id ||
      tasks.value[0]?.task_id ||
      "";
    return;
  }
  if (isRequester.value) {
    selectedTaskId.value = requesterTasks.value[0]?.task_id || "";
    return;
  }
  selectedTaskId.value = "";
  selectedTask.value = null;
  selectedSnapshot.value = null;
  selectedAlerts.value = [];
  selectedFeedback.value = [];
  stopReplayTimer();
  stopReplayVisualTimer();
  drawEmptyCanvas(liveCanvasRef.value, "请选择左侧任务以展开执行详情");
}

async function selectTask(taskId) {
  stopReplayTimer();
  replay.available = false;
  replay.frames = [];
  replay.environment = null;
  replay.frameIndex = 0;
  replay.reason = "";
  selectedTaskId.value = taskId;
  if (!isAdmin.value) executorView.value = "execute";
  await loadTaskDetail(taskId, true);
}

function openTaskDetail(taskId) {
  if (!taskId) return;
  if (isRequester.value) {
    router.push(`/task/${taskId}?role=requester&section=history`);
    return;
  }
  if (!isAdmin.value) {
    router.push(`/task/${taskId}?role=executor&section=tasks`);
  }
}

function closeExecutorDetail() {
  if (isAdmin.value) return;
  selectedTaskId.value = "";
  selectedTask.value = null;
  selectedSnapshot.value = null;
  selectedAlerts.value = [];
  selectedFeedback.value = [];
  stopReplayTimer();
  stopReplayVisualTimer();
  drawEmptyCanvas(liveCanvasRef.value, "请选择左侧任务以展开执行详情");
  drawEmptyCanvas(executorHistoryCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(executorHistory3dCanvasRef.value, "请选择左侧任务以查看历史回放");
  status.value = "";
}

async function loadTaskDetail(taskId, withStatusText) {
  try {
    const [detail, alerts, feedback] = await Promise.all([
      getOpsTask(taskId),
      fetchOpsAlerts(taskId, 30),
      fetchTaskFeedback(taskId, 30),
    ]);
    selectedTask.value = detail.task || null;
    selectedSnapshot.value = detail.snapshot || null;
    selectedAlerts.value = alerts.alerts || [];
    selectedFeedback.value = feedback.feedback || [];
    pilotSpeedInput.value = Number(detail.task?.tick_ms || detail.task?.params?.tick_ms || DEFAULT_TASK_TICK_MS);
    if (isAdmin.value && adminSection.value === "create" && selectedTask.value?.status === "PENDING_REVIEW") {
      syncReviewFormFromTask(selectedTask.value);
    }
    if (withStatusText) status.value = `已加载任务：${taskId}`;
    await nextTick();
    drawTaskSnapshotTo(liveCanvasRef.value);
    if (isAdmin.value && adminSection.value === "completed") {
      await loadReplay({ silent: true });
      drawReplayFrame();
    }
  } catch (error) {
    status.value = `加载任务失败：${error.message}`;
  }
}

async function loadReplay(options = {}) {
  const { silent = false } = options;
  if (!selectedTaskId.value) {
    if (!silent) status.value = "请先选择一个任务";
    return;
  }
  stopReplayTimer();
  try {
    const payload = await fetchTaskReplay(selectedTaskId.value);
    replay.available = Boolean(payload.available);
    replay.frames = payload.frames || [];
    replay.environment = payload.environment || null;
    replay.frameIndex = 0;
    replay.reason = payload.reason || "";
    await nextTick();
    if (!replay.available || !replay.frames.length || !replay.environment) {
      if (!silent) status.value = replay.reason || "当前任务无法提供历史回放";
      drawReplayFrame();
      ensureReplayVisualTimer();
      return;
    }
    if (!silent) status.value = `历史回放已加载，帧数 ${replay.frames.length}`;
    drawReplayFrame();
    ensureReplayVisualTimer();
  } catch (error) {
    if (!silent) status.value = `加载回放失败：${error.message}`;
  }
}

function drawReplayFrame() {
  const canvases = getReplayCanvasTargets();
  if (replay.available && replay.environment && replay.frames.length) {
    const frame = replay.frames[Math.min(replay.frameIndex, replay.frames.length - 1)];
    syncReplaySelectedDrone(frame);
    if (canvases.canvas2d) {
      resizeCanvasToDisplaySize(canvases.canvas2d);
      renderer.draw(canvases.canvas2d, replay.environment, frame);
    }
    if (canvases.canvas3d) {
      drawScene3D(canvases.canvas3d, replay.environment, frame, {
        cameraMode: "orbit",
        zoomScale: 1,
        orbitAngle: replay.frameIndex * 0.14,
        selectedDroneId: replayViewState.selectedDroneId,
      });
    }
    return;
  }
  if (selectedSnapshot.value?.environment && selectedSnapshot.value?.frame) {
    syncReplaySelectedDrone(selectedSnapshot.value.frame);
    if (canvases.canvas2d) {
      resizeCanvasToDisplaySize(canvases.canvas2d);
      renderer.draw(canvases.canvas2d, selectedSnapshot.value.environment, selectedSnapshot.value.frame);
    }
    if (canvases.canvas3d) {
      drawScene3D(canvases.canvas3d, selectedSnapshot.value.environment, selectedSnapshot.value.frame, {
        cameraMode: "orbit",
        zoomScale: 1,
        orbitAngle: 0.2,
        selectedDroneId: replayViewState.selectedDroneId,
      });
    }
    return;
  }
  if (canvases.canvas2d) drawEmptyCanvas(canvases.canvas2d, "暂无可展示回放");
  if (canvases.canvas3d) drawEmptyCanvas(canvases.canvas3d, "暂无可展示回放");
}

function getReplayCanvasTargets() {
  if (isAdmin.value) {
    return {
      canvas2d: historyCanvasRef.value || liveCanvasRef.value,
      canvas3d: history3dCanvasRef.value || null,
    };
  }
  return {
    canvas2d: executorHistoryCanvasRef.value || liveCanvasRef.value,
    canvas3d: executorHistory3dCanvasRef.value || null,
  };
}

function syncReplaySelectedDrone(frame) {
  const agents = frame?.agents || [];
  if (!agents.length) {
    replayViewState.selectedDroneId = 0;
    return;
  }
  if (!agents.some((agent) => agent.id === replayViewState.selectedDroneId)) {
    replayViewState.selectedDroneId = agents[0].id;
  }
}

async function togglePlayback() {
  if (replay.playing) {
    stopReplayTimer();
    return;
  }
  if (!replay.available || !replay.frames.length) {
    await loadReplay({ silent: true });
    if (!replay.available || !replay.frames.length) {
      status.value = replay.reason || "请先加载历史回放";
      return;
    }
  }
  replay.playing = true;
  replayTimer.value = window.setInterval(() => {
    if (replay.frameIndex >= replay.frames.length - 1) {
      stopReplayTimer();
      return;
    }
    replay.frameIndex += 1;
    drawReplayFrame();
  }, replaySpeedInput.value);
}

function applyReplaySpeed() {
  const parsedSpeed = Number(replaySpeedInput.value);
  if (!Number.isFinite(parsedSpeed) || parsedSpeed < 80 || parsedSpeed > 2000) {
    status.value = "请输入 80 到 2000 之间的回放节拍。";
    return;
  }
  replaySpeedInput.value = parsedSpeed;
  status.value = `回放节拍已调整为 ${parsedSpeed} ms/帧`;
  if (replay.playing) {
    stopReplayTimer();
    togglePlayback();
  }
}

function stopReplayTimer() {
  replay.playing = false;
  if (replayTimer.value) {
    window.clearInterval(replayTimer.value);
    replayTimer.value = null;
  }
}

function shouldAnimateReplayCanvas() {
  if (isAdmin.value) return adminSection.value === "completed" && !!selectedTaskId.value;
  if (isRequester.value) return false;
  return executorView.value === "history" && !!selectedTaskId.value;
}

function ensureReplayVisualTimer() {
  if (!shouldAnimateReplayCanvas()) {
    stopReplayVisualTimer();
    return;
  }
  if (replayVisualTimer.value) return;
  replayVisualTimer.value = window.setInterval(() => {
    drawReplayFrame();
  }, 140);
}

function stopReplayVisualTimer() {
  if (replayVisualTimer.value) {
    window.clearInterval(replayVisualTimer.value);
    replayVisualTimer.value = null;
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
    `- 飞手: ${assigneeLabel(task)}`,
    `- 地图: ${task.params?.map_name || "-"}`,
    `- 计划开始: ${fmtDateTime(task.params?.scheduled_start_at)}`,
    `- 创建时间: ${fmtDateTime(task.created_at)}`,
    `- 更新时间: ${fmtDateTime(task.updated_at)}`,
    ``,
    `## 核心指标`,
    `- 在线无人机数: ${metrics.online ?? "-"}`,
    `- 累计完成任务数: ${metrics.tasks_completed ?? "-"}`,
    `- 吞吐量: ${fmtNumber(metrics.throughput, 4)}`,
    `- 累计冲突数: ${metrics.cumulative_conflicts ?? metrics.vertex_conflicts ?? "-"}`,
    `- 平均时延(步): ${metrics.avg_latency ?? "-"}`,
    ``,
    `## 系统告警`,
  ];
  if (!selectedAlerts.value.length) {
    lines.push("- 无告警");
  } else {
    selectedAlerts.value.forEach((alert) => {
      lines.push(`- [${alert.level}] ${alert.code} | step ${alert.frame_step} | ${alert.message}`);
    });
  }
  lines.push("", "## 飞手反馈");
  if (!selectedFeedback.value.length) {
    lines.push("- 无反馈");
  } else {
    selectedFeedback.value.forEach((item) => {
      lines.push(`- [${feedbackCategoryLabel(item.category)}] ${item.display_name || item.username} | ${fmtDateTime(item.created_at)} | ${item.message}`);
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

function syncReviewFormFromTask(task) {
  const taskId = String(task?.task_id || "");
  if (!taskId) return;
  if (reviewFormTaskId.value === taskId) return;
  const params = task?.params || {};
  reviewFormTaskId.value = taskId;
  assignForm.assignee_user_id = String(params.assignee_user_id || "");
  syncAssigneeDisplayName();
  assignForm.source = task?.source || "sample";
  assignForm.map_name = String(params.map_name || params.requested_location || "warehouse-grid-v1");
  assignForm.num_agents = Number(params.num_agents || 16);
  assignForm.max_frames = Number(params.max_frames || 64);
  assignForm.tick_ms = Number(task?.tick_ms || DEFAULT_TASK_TICK_MS);
  assignForm.scheduled_start_input = buildDateTimeLocalInput(params.scheduled_start_at) || buildDefaultScheduleInput();
  assignForm.review_note = String(params.review_note || "");
}

async function createAndAssignTask() {
  if (!isAdmin.value) {
    assignStatus.value = "仅管理员可创建和分配任务";
    return;
  }
  if (!assignForm.assignee_user_id) {
    assignStatus.value = "请先选择飞手";
    return;
  }
  const scheduledStartAt = parseScheduledInput(assignForm.scheduled_start_input);
  if (!scheduledStartAt) {
    assignStatus.value = "请设置有效的计划执行时间";
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
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: fmtDateTime(scheduledStartAt),
    });
    selectedTaskId.value = created?.task?.task_id || "";
    await refreshTasks();
    assignStatus.value = `任务已分配给 ${assignForm.assignee_display_name}，计划于 ${fmtDateTime(scheduledStartAt)} 执行`;
  } catch (error) {
    assignStatus.value = `任务创建失败：${error.message}`;
  }
}

async function approveTaskRequest() {
  if (!selectedTaskId.value || selectedTask.value?.status !== "PENDING_REVIEW") {
    assignStatus.value = "请先选择待审核申请";
    return;
  }
  if (!assignForm.assignee_user_id) {
    assignStatus.value = "请先选择飞手";
    return;
  }
  const scheduledStartAt = parseScheduledInput(assignForm.scheduled_start_input);
  syncAssigneeDisplayName();
  try {
    await controlOpsTask(selectedTaskId.value, "approve", {
      assignee_user_id: assignForm.assignee_user_id,
      assignee_display_name: assignForm.assignee_display_name,
      source: assignForm.source,
      map_name: assignForm.map_name,
      num_agents: assignForm.num_agents,
      max_frames: assignForm.max_frames,
      tick_ms: assignForm.tick_ms,
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: scheduledStartAt ? fmtDateTime(scheduledStartAt) : "",
      review_note: assignForm.review_note,
    });
    reviewFormTaskId.value = "";
    await refreshTasks();
    assignStatus.value = `审核通过，已为 ${selectedTask.value?.mission_name || "该任务"} 指派飞手 ${assignForm.assignee_display_name}`;
    adminSection.value = "active";
  } catch (error) {
    assignStatus.value = `审核通过失败：${error.message}`;
  }
}

async function rejectTaskRequest() {
  if (!selectedTaskId.value || selectedTask.value?.status !== "PENDING_REVIEW") {
    assignStatus.value = "请先选择待审核申请";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "reject", {
      review_note: assignForm.review_note,
    });
    reviewFormTaskId.value = "";
    await refreshTasks();
    assignStatus.value = "申请已驳回。";
  } catch (error) {
    assignStatus.value = `驳回失败：${error.message}`;
  }
}

async function runTaskAction(action) {
  if (!selectedTaskId.value) {
    status.value = "请先选择任务";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, action);
    await refreshTasks();
    status.value = `任务操作已执行：${action}`;
  } catch (error) {
    status.value = `任务操作失败：${error.message}`;
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
      const rawMapName = String(parsed.map_name || file.name.replace(/\.[^.]+$/, "") || "imported-map");
      const mapName = ensureVersionedMapName(rawMapName);
      const item = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        map_name: mapName,
        file_name: file.name,
        ts: Date.now() / 1000,
      };
      importedMaps.value = [item, ...importedMaps.value].slice(0, 20);
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

async function submitExecutorFeedback() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  if (!feedbackForm.message.trim()) {
    feedbackStatus.value = "请先填写反馈内容";
    return;
  }
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: feedbackForm.category,
      message: feedbackForm.message.trim(),
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "反馈已提交，管理员可在已完成任务中查看。";
  } catch (error) {
    feedbackStatus.value = `提交失败：${error.message}`;
  }
}

async function requestTaskDelay() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  const message = feedbackForm.message.trim() || "申请延期，请管理员确认新的执行时间。";
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: "delay_request",
      message,
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "延期申请已提交，等待管理员处理。";
  } catch (error) {
    feedbackStatus.value = `提交延期申请失败：${error.message}`;
  }
}

async function reportTaskAnomaly() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  const message = feedbackForm.message.trim() || "发现执行异常，请管理员关注。";
  try {
    await submitTaskFeedback(selectedTaskId.value, {
      category: "anomaly",
      message,
    });
    feedbackForm.message = "";
    await loadTaskDetail(selectedTaskId.value, false);
    feedbackStatus.value = "异常已上报，管理员可在复盘界面查看。";
  } catch (error) {
    feedbackStatus.value = `异常上报失败：${error.message}`;
  }
}

async function startAssignedTask() {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "start");
    await refreshTasks();
    feedbackStatus.value = "任务已开始执行。";
  } catch (error) {
    feedbackStatus.value = `开始执行失败：${error.message}`;
  }
}

async function setPilotTaskSpeed(tickMs) {
  if (!selectedTaskId.value) {
    feedbackStatus.value = "请先选择一个任务";
    return;
  }
  const parsedTickMs = Number(tickMs);
  if (!Number.isFinite(parsedTickMs) || parsedTickMs < 120 || parsedTickMs > 2400) {
    feedbackStatus.value = "请输入 120 到 2400 之间的节拍值。";
    return;
  }
  try {
    await controlOpsTask(selectedTaskId.value, "set_speed", {
      tick_ms: parsedTickMs,
    });
    await refreshTasks();
    feedbackStatus.value = `已将飞行节拍调整为 ${parsedTickMs} ms/步。`;
  } catch (error) {
    feedbackStatus.value = `调整速度失败：${error.message}`;
  }
}

async function submitTaskRequest() {
  const scheduledStartAt = parseScheduledInput(requestForm.scheduled_start_input);
  if (!requestForm.mission_name.trim()) {
    requestStatus.value = "请填写任务名称";
    return;
  }
  if (!requestForm.requested_location.trim()) {
    requestStatus.value = "请填写执行地点";
    return;
  }
  if (!scheduledStartAt) {
    requestStatus.value = "请填写有效的执行时间";
    return;
  }
  try {
    const created = await createOpsTask({
      mission_name: requestForm.mission_name.trim(),
      task_category: requestForm.task_category,
      requested_location: requestForm.requested_location.trim(),
      scheduled_start_at: scheduledStartAt,
      scheduled_start_label: fmtDateTime(scheduledStartAt),
    });
    const createdTaskId = created?.task?.task_id || "";
    selectedTaskId.value = createdTaskId;
    await refreshTasks();
    requesterSection.value = "history";
    router.push("/requester/history");
    requestStatus.value = createdTaskId
      ? `申请已提交，已切换到“我的申请”。申请编号 ${createdTaskId}`
      : "申请已提交，已切换到“我的申请”。";
  } catch (error) {
    requestStatus.value = `提交申请失败：${error.message}`;
  }
}

watch(
  () => props.section,
  (section) => {
    if (isAdmin.value) {
      adminSection.value = section || "overview";
      return;
    }
    if (isRequester.value) {
      requesterSection.value = section || "create";
    }
  },
  { immediate: true },
);

watch(adminSection, async (section) => {
  if (!isAdmin.value) return;
  stopReplayTimer();
  if (section !== "completed") stopReplayVisualTimer();
  if (section !== "create") reviewFormTaskId.value = "";
  if (section === "create" && !pendingReviewTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = pendingReviewTasks.value[0]?.task_id || "";
  }
  if (section === "active" && !filteredActiveTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = filteredActiveTasks.value[0]?.task_id || "";
  }
  if (section === "completed" && !filteredCompletedTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = filteredCompletedTasks.value[0]?.task_id || "";
  }
  await nextTick();
  if (selectedTaskId.value) {
    await loadTaskDetail(selectedTaskId.value, false);
    ensureReplayVisualTimer();
    return;
  }
  drawEmptyCanvas(liveCanvasRef.value, "暂无实时任务画面");
  drawEmptyCanvas(historyCanvasRef.value, "暂无可展示回放");
  drawEmptyCanvas(history3dCanvasRef.value, "暂无可展示回放");
});

watch(requesterSection, async (section) => {
  if (!isRequester.value) return;
  if (section !== "history") return;
  if (!requesterTasks.value.some((task) => task.task_id === selectedTaskId.value)) {
    selectedTaskId.value = requesterTasks.value[0]?.task_id || "";
  }
  await nextTick();
  if (selectedTaskId.value) {
    await loadTaskDetail(selectedTaskId.value, false);
  }
});

watch(executorView, async (view) => {
  if (isAdmin.value || isRequester.value) return;
  if (view !== "history") {
    stopReplayVisualTimer();
    return;
  }
  await loadReplay({ silent: true });
  await nextTick();
  drawReplayFrame();
  ensureReplayVisualTimer();
});

onMounted(async () => {
  await refreshAssignees();
  await refreshTasks();
  pollTimer = window.setInterval(() => refreshTasks(), 3200);
  drawEmptyCanvas(executorHistoryCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(executorHistory3dCanvasRef.value, "请选择左侧任务以查看历史回放");
  drawEmptyCanvas(history3dCanvasRef.value, "暂无可展示回放");
  ensureReplayVisualTimer();
});

onUnmounted(() => {
  stopReplayTimer();
  stopReplayVisualTimer();
  if (pollTimer) window.clearInterval(pollTimer);
});
</script>
