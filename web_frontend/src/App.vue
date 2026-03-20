<template>
  <div class="app-shell">
    <section v-if="authBooting" class="login-shell">
      <div class="login-card">
        <h2>正在加载账户信息...</h2>
      </div>
    </section>

    <section v-else-if="!loggedIn" class="login-shell">
      <div class="login-card">
        <h2>系统登录</h2>
        <p class="login-sub">请选择身份并输入账号密码。</p>
        <div class="login-role-row">
          <button class="role-toggle" :class="{ active: loginRole === 'executor' }" @click="setLoginRole('executor')">执行者</button>
          <button class="role-toggle" :class="{ active: loginRole === 'admin' }" @click="setLoginRole('admin')">管理员</button>
        </div>
        <p class="login-sub" style="margin-top: 8px">{{ roleHintText }}</p>

        <label class="login-label">
          账号
          <input v-model="loginUsername" type="text" autocomplete="username" placeholder="请输入账号" />
        </label>
        <label class="login-label">
          密码
          <input v-model="loginPassword" type="password" autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submitLogin" />
        </label>
        <p v-if="authError" class="role-error">{{ authError }}</p>
        <div class="btn-row" style="margin-top: 12px">
          <button class="btn" :disabled="authBusy" @click="submitLogin">{{ authBusy ? "登录中..." : "登录" }}</button>
        </div>
      </div>
    </section>

    <template v-else>
      <header class="topbar">
        <div class="brand">
          <h1>无人机协同调度系统</h1>
          <span>Control Console</span>
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
        <TaskCenterView v-if="activeMode === 'taskCenter'" :current-user="currentUser" :role="currentRole" />
        <OpsDashboardView v-else-if="activeMode === 'dashboard'" />
        <OperationsModeView v-else :current-user="currentUser" :role="currentRole" />
      </main>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import OperationsModeView from "./modules/operations/OperationsModeView.vue";
import TaskCenterView from "./modules/taskcenter/TaskCenterView.vue";
import OpsDashboardView from "./modules/dashboard/OpsDashboardView.vue";
import { fetchAuthOptions, fetchAuthState, fetchIdentity, loginWithPassword, logoutCurrentUser } from "./services/api";

const adminTabs = [
  { key: "taskCenter", label: "任务分配" },
];
const executorTabs = [
  { key: "ops", label: "联合运行" },
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营大屏" },
];

const authBooting = ref(true);
const loggedIn = ref(false);
const authBusy = ref(false);
const authError = ref("");

const currentUser = ref(null);
const authAccounts = ref([]);
const loginRole = ref("executor");
const loginUsername = ref("");
const loginPassword = ref("");
const activeMode = ref("ops");

const currentRole = computed(() => (currentUser.value?.role === "admin" ? "admin" : "executor"));
const tabs = computed(() => (currentRole.value === "admin" ? adminTabs : executorTabs));
const roleLabel = computed(() => (currentRole.value === "admin" ? "管理员" : "执行者"));
const currentUserName = computed(() => currentUser.value?.display_name || "未登录账户");
const currentUserDept = computed(() => currentUser.value?.department || "未分配部门");
const currentUserInitial = computed(() => userInitial(currentUser.value));
const roleHintText = computed(() => {
  if (loginRole.value === "admin") return "管理员账号示例：admin（可手动输入其他管理员账号）";
  return "执行者账号示例：executor01（可手动输入其他执行者账号）";
});

function normalizeUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  return {
    user_id: String(raw.user_id || ""),
    username: String(raw.username || ""),
    display_name: String(raw.display_name || "未命名用户"),
    role: raw.role === "admin" ? "admin" : "executor",
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
  loginRole.value = role === "admin" ? "admin" : "executor";
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
    activeMode.value = "ops";
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
