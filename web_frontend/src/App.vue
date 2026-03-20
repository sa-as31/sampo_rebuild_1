<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <h1>无人机协同调度系统</h1>
        <span>Control Console</span>
      </div>
      <div class="role-entry">
        <button class="account-chip" @click="openRoleDialog">
          <span class="account-avatar">{{ currentUserInitial }}</span>
          <span class="account-meta">
            <strong>{{ currentUserName }}</strong>
            <small>{{ roleLabel }} · {{ currentUserDept }}</small>
          </span>
        </button>
        <button class="switch-trigger" :disabled="identityLoading" @click="openRoleDialog">
          {{ identityLoading ? "同步中..." : "切换账户" }}
        </button>
      </div>
    </header>

    <nav class="mode-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeMode === tab.key }"
        @click="activeMode = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <main>
      <ResearchModeView v-if="activeMode === 'research'" />
      <TaskCenterView v-else-if="activeMode === 'taskCenter'" />
      <OpsDashboardView v-else-if="activeMode === 'dashboard'" />
      <OperationsModeView v-else />
    </main>

    <div v-if="showRoleDialog" class="role-modal-mask" @click.self="closeRoleDialog">
      <section class="role-modal role-modal-real">
        <div class="role-modal-head">
          <h3>账户切换</h3>
          <span class="role-pill">当前：{{ currentUserName }}</span>
        </div>
        <p class="role-modal-sub">账号状态由后端数据库维护，切换后会同步角色权限。</p>
        <p v-if="identityError" class="role-error">{{ identityError }}</p>
        <div class="role-card-grid">
          <button
            v-for="user in identityUsers"
            :key="user.user_id"
            class="role-card role-user-card"
            :class="{ active: selectedUserId === user.user_id }"
            :disabled="switchingUserId !== ''"
            @click="selectedUserId = user.user_id"
          >
            <span class="user-avatar">{{ userInitial(user) }}</span>
            <span class="user-content">
              <strong>{{ user.display_name }}</strong>
              <span class="user-sub">{{ user.username }} · {{ roleText(user.role) }}</span>
              <span class="user-sub">{{ user.department }} · {{ user.title || "未设置岗位" }}</span>
            </span>
            <span class="user-state">
              <span class="role-pill role-badge" :class="user.role">{{ roleText(user.role) }}</span>
              <small>最近登录：{{ formatTs(user.last_login_at) }}</small>
            </span>
          </button>
          <div v-if="!identityUsers.length" class="role-empty">暂无可切换账户</div>
        </div>
        <div class="btn-row" style="margin-top: 12px">
          <button class="btn" :disabled="!selectedUserId || switchingUserId !== ''" @click="applyRoleSwitch">
            {{ switchingUserId ? "切换中..." : "确认切换" }}
          </button>
          <button class="btn secondary" @click="closeRoleDialog">取消</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import ResearchModeView from "./modules/research/ResearchModeView.vue";
import OperationsModeView from "./modules/operations/OperationsModeView.vue";
import TaskCenterView from "./modules/taskcenter/TaskCenterView.vue";
import OpsDashboardView from "./modules/dashboard/OpsDashboardView.vue";
import { fetchIdentity, switchIdentity } from "./services/api";

const adminTabs = [
  { key: "ops", label: "联合运行" },
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营大屏" },
  { key: "research", label: "研究模式" },
];
const executorTabs = [
  { key: "ops", label: "联合运行" },
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营大屏" },
];

const currentUser = ref(null);
const identityUsers = ref([]);
const activeMode = ref("ops");
const showRoleDialog = ref(false);
const selectedUserId = ref("");
const identityLoading = ref(false);
const switchingUserId = ref("");
const identityError = ref("");

const currentRole = computed(() => (currentUser.value?.role === "admin" ? "admin" : "executor"));
const tabs = computed(() => (currentRole.value === "admin" ? adminTabs : executorTabs));
const roleLabel = computed(() => (currentRole.value === "admin" ? "管理员" : "执行者"));
const currentUserName = computed(() => currentUser.value?.display_name || "未登录账户");
const currentUserDept = computed(() => currentUser.value?.department || "未分配部门");
const currentUserInitial = computed(() => userInitial(currentUser.value));

function ensureActiveModeVisible() {
  const visible = tabs.value.map((tab) => tab.key);
  if (!visible.includes(activeMode.value)) activeMode.value = visible[0];
}

function normalizeUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  const role = raw.role === "admin" ? "admin" : "executor";
  return {
    user_id: String(raw.user_id || ""),
    username: String(raw.username || ""),
    display_name: String(raw.display_name || "未命名用户"),
    role,
    department: String(raw.department || "未分配部门"),
    title: String(raw.title || ""),
    last_login_at: raw.last_login_at ?? null,
  };
}

function applyIdentityPayload(payload) {
  const users = Array.isArray(payload?.users) ? payload.users.map(normalizeUser).filter(Boolean) : [];
  identityUsers.value = users;

  const preferred = normalizeUser(payload?.current_user);
  currentUser.value = preferred || users[0] || null;
  selectedUserId.value = currentUser.value?.user_id || "";
  ensureActiveModeVisible();
}

async function loadIdentity({ silent = false } = {}) {
  if (!silent) identityError.value = "";
  identityLoading.value = true;
  try {
    const payload = await fetchIdentity();
    applyIdentityPayload(payload);
    identityError.value = "";
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    identityError.value = `身份服务不可用：${message}`;
    if (!currentUser.value) {
      const fallback = {
        user_id: "local_executor",
        username: "local.executor",
        display_name: "本地执行者",
        role: "executor",
        department: "本地模式",
        title: "离线账户",
        last_login_at: null,
      };
      currentUser.value = fallback;
      identityUsers.value = [fallback];
      selectedUserId.value = fallback.user_id;
      ensureActiveModeVisible();
    }
  } finally {
    identityLoading.value = false;
  }
}

async function openRoleDialog() {
  selectedUserId.value = currentUser.value?.user_id || selectedUserId.value;
  showRoleDialog.value = true;
  await loadIdentity({ silent: true });
}

function closeRoleDialog() {
  showRoleDialog.value = false;
}

async function applyRoleSwitch() {
  if (!selectedUserId.value) return;
  switchingUserId.value = selectedUserId.value;
  identityError.value = "";
  try {
    const payload = await switchIdentity(selectedUserId.value);
    applyIdentityPayload(payload);
    closeRoleDialog();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    identityError.value = `切换失败：${message}`;
  } finally {
    switchingUserId.value = "";
  }
}

function roleText(role) {
  return role === "admin" ? "管理员" : "执行者";
}

function userInitial(user) {
  const source = user?.display_name || user?.username || "U";
  return source.slice(0, 1).toUpperCase();
}

function formatTs(ts) {
  if (ts === null || ts === undefined) return "从未登录";
  const parsed = Number(ts);
  if (!Number.isFinite(parsed) || parsed <= 0) return "从未登录";
  return new Date(parsed * 1000).toLocaleString("zh-CN", { hour12: false });
}

function handleModeSwitch(event) {
  const mode = event?.detail?.mode;
  if (!mode) return;
  const visible = tabs.value.map((tab) => tab.key);
  if (visible.includes(mode)) {
    activeMode.value = mode;
  }
}

onMounted(() => {
  window.addEventListener("app-switch-mode", handleModeSwitch);
  loadIdentity();
});

onUnmounted(() => {
  window.removeEventListener("app-switch-mode", handleModeSwitch);
});
</script>
