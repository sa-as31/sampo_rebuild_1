<template>
  <div>
    <header class="topbar editorial-topbar">
      <div class="brand">
        <span class="eyebrow">无人机协同调度系统</span>
        <div class="brand-headline">
          <h1>{{ pageTitle }}</h1>
          <span class="workspace-badge">{{ workspaceBadge }}</span>
        </div>
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
        <button class="switch-trigger" :disabled="authStore.state.authBusy" @click="submitLogout">
          {{ authStore.state.authBusy ? "退出中..." : "退出登录" }}
        </button>
      </div>
    </header>

    <nav v-if="tabs.length > 1" class="mode-tabs editorial-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.path"
        class="tab-btn"
        :class="{ active: $route.path.startsWith(tab.path) }"
        @click="$router.push(tab.path)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const adminTabs = [
  { path: "/admin", label: "审核与调度" },
];
const requesterTabs = [
  { path: "/requester", label: "任务申请" },
];
const executorTabs = [
  { path: "/executor/tasks", label: "任务中心" },
  { path: "/executor/dashboard", label: "运营观测" },
];

const currentRole = computed(() => {
  if (authStore.state.currentUser?.role === "admin") return "admin";
  if (authStore.state.currentUser?.role === "requester") return "requester";
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
  if (currentRole.value === "requester") return "提交任务申请并跟进审批结果";
  return "接收任务、执行飞行并完成值守记录";
});

const pageIntro = computed(() => {
  if (currentRole.value === "admin") return "围绕审核队列、执行调度和归档复盘组织统一运营工作台。";
  if (currentRole.value === "requester") return "用统一入口提交任务，并持续查看审批、分配和执行进展。";
  return "围绕单个任务完成执行观察、异常记录与历史回放。";
});

const workspaceBadge = computed(() => {
  if (currentRole.value === "admin") return "调度工作台";
  if (currentRole.value === "requester") return "申请工作台";
  return "飞行席位";
});

const currentUserName = computed(() => authStore.state.currentUser?.display_name || "未登录账户");
const currentUserDept = computed(() => authStore.state.currentUser?.department || "未分配部门");

const currentUserInitial = computed(() => {
  const source = authStore.state.currentUser?.display_name || authStore.state.currentUser?.username || "U";
  return source.slice(0, 1).toUpperCase();
});

async function submitLogout() {
  await authStore.logout();
  router.push('/login');
}
</script>
