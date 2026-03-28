<template>
  <div class="login-stage">
    <article class="login-hero">
      <span class="eyebrow">Operations Access</span>
      <h1>让申请、调度与执行落在同一套运营工作台里。</h1>
      <p class="login-hero-copy">
        面向申请人、调度管理员与飞手的统一入口，聚焦任务排队、审批分发、联合执行与回放归档四条主链路。
      </p>
      <div class="login-hero-grid">
        <div class="login-hero-note">
          <strong>申请排队</strong>
          <span>提交任务名称、地点与时间，立即进入审核队列。</span>
        </div>
        <div class="login-hero-note">
          <strong>调度审批</strong>
          <span>按地图、飞手与执行窗口完成分发与调度。</span>
        </div>
        <div class="login-hero-note">
          <strong>执行归档</strong>
          <span>实时状态、现场记录与历史回放统一归档。</span>
        </div>
      </div>
    </article>

    <article class="login-card editorial-card">
      <span class="eyebrow">System Access</span>
      <h2>进入系统</h2>
      <p class="login-sub">选择席位后登录当前工作台。</p>
      <div class="login-role-row">
        <button class="role-toggle" :class="{ active: loginRole === 'requester' }" @click="setLoginRole('requester')">申请人</button>
        <button class="role-toggle" :class="{ active: loginRole === 'admin' }" @click="setLoginRole('admin')">管理员</button>
        <button class="role-toggle" :class="{ active: loginRole === 'executor' }" @click="setLoginRole('executor')">飞手</button>
      </div>
      <div class="login-access-strip">
        <span class="login-access-chip">{{ roleHintText }}</span>
        <span class="login-access-chip">默认密码 1</span>
      </div>

      <label class="login-label">
        账号
        <input v-model="loginUsername" type="text" autocomplete="username" placeholder="请输入账号" />
      </label>
      <label class="login-label">
        密码
        <input v-model="loginPassword" type="password" autocomplete="current-password" placeholder="请输入密码" @keyup.enter="submitLogin" />
      </label>
      <p v-if="authStore.state.authError" class="role-error">{{ authStore.state.authError }}</p>
      <div class="btn-row login-actions">
        <button class="btn btn-dark" :disabled="authStore.state.authBusy" @click="submitLogin">
          {{ authStore.state.authBusy ? "登录中..." : "登录系统" }}
        </button>
      </div>
    </article>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const loginRole = ref("requester");
const loginUsername = ref("");
const loginPassword = ref("");

const roleHintText = computed(() => {
  if (loginRole.value === "admin") return "管理员示例：admin";
  if (loginRole.value === "requester") return "申请人示例：requester01";
  return "飞手示例：executor01";
});

function prefillByRole(role) {
  const first = authStore.state.authAccounts.find((item) => item.role === role);
  if (first) loginUsername.value = first.username;
}

function setLoginRole(role) {
  loginRole.value = role === "admin" || role === "requester" ? role : "executor";
  prefillByRole(loginRole.value);
}

async function submitLogin() {
  const success = await authStore.login(loginRole.value, loginUsername.value, loginPassword.value);
  if (success) {
    const role = authStore.state.currentUser?.role;
    if (role === 'admin') router.push('/admin');
    else if (role === 'requester') router.push('/requester');
    else router.push('/executor');
  }
}

onMounted(() => {
  if (authStore.state.authAccounts.length === 0) {
    authStore.loadAuthOptions().then(() => {
      prefillByRole(loginRole.value);
    });
  } else {
    prefillByRole(loginRole.value);
  }
});
</script>
