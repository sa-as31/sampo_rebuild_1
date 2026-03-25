<template>
  <div class="app-shell">
    <section v-if="authBooting" class="login-shell">
      <div class="login-stage login-stage-loading">
        <div class="login-card editorial-card">
          <span class="eyebrow">System Access</span>
          <h2>正在加载账户信息...</h2>
        </div>
      </div>
    </section>

    <section v-else-if="!loggedIn" class="login-shell">
      <div class="login-stage">
        <article class="login-hero">
          <span class="eyebrow">UAV Coordination Research System</span>
          <h1>让任务申请、审核分配与飞行执行形成一条清晰可见的链路。</h1>
          <p class="login-hero-copy">
            该系统围绕申请人、管理员与飞手的协作流程展开，用统一的任务视图串联申请、审批、调度、执行和回放，适合毕业设计演示与过程展示。
          </p>
          <div class="login-hero-grid">
            <div class="login-hero-note">
              <strong>任务申请</strong>
              <span>提交时间、地点与任务类别，进入待审核流程。</span>
            </div>
            <div class="login-hero-note">
              <strong>审核调度</strong>
              <span>管理员审批申请并指定飞手与执行地图。</span>
            </div>
            <div class="login-hero-note">
              <strong>联合执行</strong>
              <span>2D 与 3D 运行状态、回放与反馈在同一链路闭环。</span>
            </div>
          </div>
        </article>

        <article class="login-card editorial-card">
          <span class="eyebrow">System Access</span>
          <h2>进入系统</h2>
          <p class="login-sub">请选择身份并输入账号密码。</p>
          <div class="login-role-row">
            <button class="role-toggle" :class="{ active: loginRole === 'requester' }" @click="setLoginRole('requester')">申请人</button>
            <button class="role-toggle" :class="{ active: loginRole === 'admin' }" @click="setLoginRole('admin')">管理员</button>
            <button class="role-toggle" :class="{ active: loginRole === 'executor' }" @click="setLoginRole('executor')">飞手</button>
          </div>
          <p class="login-sub login-meta-line">{{ roleHintText }}</p>
          <p class="login-sub login-meta-line">当前演示环境默认密码统一为 1。</p>

          <label class="login-label">
            账号
            <input v-model="loginUsername" type="text" autocomplete="username" placeholder="请输入账号" />
          </label>
          <label class="login-label">
            密码
            <input v-model="loginPassword" type="password" autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submitLogin" />
          </label>
          <p v-if="authError" class="role-error">{{ authError }}</p>
          <div class="btn-row login-actions">
            <button class="btn btn-dark" :disabled="authBusy" @click="submitLogin">{{ authBusy ? "登录中..." : "登录系统" }}</button>
          </div>
        </article>
      </div>
    </section>

    <template v-else>
      <header class="topbar editorial-topbar">
        <div class="brand">
          <span class="eyebrow">无人机协同调度系统</span>
          <h1>{{ pageTitle }}</h1>
          <p class="brand-intro">{{ pageIntro }}</p>
        </div>
        <div class="role-entry">
          <div class="account-chip">
            <span class="account-avatar">{{ currentUserInitial }}</span>
            <span class="account-meta">
              <strong>{{ currentUserName }}</strong>
              <small>{{ roleLabel }} · {{ currentUserDept }}</small>
            </span>
          </div>
          <button class="switch-trigger" :disabled="authBusy" @click="submitLogout">
            {{ authBusy ? "退出中..." : "退出登录" }}
          </button>
        </div>
      </header>

      <nav class="mode-tabs editorial-tabs">
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

      <main class="app-main">
        <TaskCenterView v-if="activeMode === 'taskCenter'" :current-user="currentUser" :role="currentRole" />
        <OpsDashboardView v-else-if="activeMode === 'dashboard'" />
      </main>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import TaskCenterView from "./modules/taskcenter/TaskCenterView.vue";
import OpsDashboardView from "./modules/dashboard/OpsDashboardView.vue";
import { fetchAuthOptions, fetchAuthState, fetchIdentity, loginWithPassword, logoutCurrentUser } from "./services/api";

const adminTabs = [
  { key: "taskCenter", label: "审核与调度" },
];
const requesterTabs = [
  { key: "taskCenter", label: "任务申请" },
];
const executorTabs = [
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营观测" },
];

const authBooting = ref(true);
const loggedIn = ref(false);
const authBusy = ref(false);
const authError = ref("");

const currentUser = ref(null);
const authAccounts = ref([]);
const loginRole = ref("requester");
const loginUsername = ref("");
const loginPassword = ref("");
const activeMode = ref("taskCenter");

const currentRole = computed(() => {
  if (currentUser.value?.role === "admin") return "admin";
  if (currentUser.value?.role === "requester") return "requester";
  return "executor";
});
const tabs = computed(() => {
  if (currentRole.value === "admin") return adminTabs;
  if (currentRole.value === "requester") return requesterTabs;
  return executorTabs;
});
const roleLabel = computed(() => {
  if (currentRole.value === "admin") return "管理员";
  if (currentRole.value === "requester") return "申请人";
  return "飞手";
});
const pageTitle = computed(() => {
  if (currentRole.value === "admin") return "审核申请并调度飞手执行";
  if (currentRole.value === "requester") return "提交无人机任务并追踪审核进展";
  return "接收任务、执行飞行并回看运行过程";
});
const pageIntro = computed(() => {
  if (currentRole.value === "admin") return "聚焦待审核、执行中与已完成三条工作流，将审批、分配与回放整理为更清晰的调度工作台。";
  if (currentRole.value === "requester") return "在统一的任务申请界面中提交时间、地点与任务类别，并查看管理员审核和飞手分配结果。";
  return "围绕单个任务完成执行、反馈与回放观察，让飞手在同一页面中掌握当前飞行状态。";
});
const currentUserName = computed(() => currentUser.value?.display_name || "未登录账户");
const currentUserDept = computed(() => currentUser.value?.department || "未分配部门");
const currentUserInitial = computed(() => userInitial(currentUser.value));
const roleHintText = computed(() => {
  if (loginRole.value === "admin") return "管理员账号示例：admin（可手动输入其他管理员账号）";
  if (loginRole.value === "requester") return "申请人账号示例：requester01";
  return "飞手账号示例：executor01（可手动输入其他飞手账号）";
});

function normalizeUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  return {
    user_id: String(raw.user_id || ""),
    username: String(raw.username || ""),
    display_name: String(raw.display_name || "未命名用户"),
    role: raw.role === "admin" || raw.role === "requester" ? raw.role : "executor",
    department: String(raw.department || "未分配部门"),
    title: String(raw.title || ""),
    last_login_at: raw.last_login_at ?? null,
  };
}

function ensureActiveModeVisible() {
  const visible = tabs.value.map((tab) => tab.key);
  if (!visible.includes(activeMode.value)) activeMode.value = visible[0];
}

async function loadAuthOptions() {
  const payload = await fetchAuthOptions();
  authAccounts.value = Array.isArray(payload?.accounts) ? payload.accounts.map(normalizeUser).filter(Boolean) : [];
}

async function loadIdentity() {
  const payload = await fetchIdentity();
  currentUser.value = normalizeUser(payload?.current_user);
  ensureActiveModeVisible();
}

async function bootstrapAuth() {
  authBooting.value = true;
  authError.value = "";
  try {
    await loadAuthOptions();
    const state = await fetchAuthState();
    loggedIn.value = !!state?.logged_in;
    currentUser.value = normalizeUser(state?.current_user);
    if (loggedIn.value) await loadIdentity();
    ensureActiveModeVisible();
    prefillByRole(loginRole.value);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    authError.value = `认证服务不可用：${message}`;
    loggedIn.value = false;
  } finally {
    authBooting.value = false;
  }
}

function setLoginRole(role) {
  loginRole.value = role === "admin" || role === "requester" ? role : "executor";
  prefillByRole(loginRole.value);
}

function prefillByRole(role) {
  const first = authAccounts.value.find((item) => item.role === role);
  if (first) loginUsername.value = first.username;
}

async function submitLogin() {
  authBusy.value = true;
  authError.value = "";
  try {
    const payload = await loginWithPassword({
      role: loginRole.value,
      username: loginUsername.value,
      password: loginPassword.value,
    });
    loggedIn.value = !!payload?.logged_in;
    currentUser.value = normalizeUser(payload?.current_user);
    loginPassword.value = "";
    await loadIdentity();
    ensureActiveModeVisible();
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    authError.value = `登录失败：${message}`;
  } finally {
    authBusy.value = false;
  }
}

async function submitLogout() {
  authBusy.value = true;
  authError.value = "";
  try {
    await logoutCurrentUser();
    loggedIn.value = false;
    currentUser.value = null;
    activeMode.value = "taskCenter";
    loginPassword.value = "";
    prefillByRole(loginRole.value);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    authError.value = `退出失败：${message}`;
  } finally {
    authBusy.value = false;
  }
}

function userInitial(user) {
  const source = user?.display_name || user?.username || "U";
  return source.slice(0, 1).toUpperCase();
}

function handleModeSwitch(event) {
  if (!loggedIn.value) return;
  const mode = event?.detail?.mode;
  if (!mode) return;
  const visible = tabs.value.map((tab) => tab.key);
  if (visible.includes(mode)) activeMode.value = mode;
}

onMounted(async () => {
  window.addEventListener("app-switch-mode", handleModeSwitch);
  await bootstrapAuth();
});

onUnmounted(() => {
  window.removeEventListener("app-switch-mode", handleModeSwitch);
});
</script>
