<template>
  <div>
    <header class="topbar editorial-topbar">
      <div class="brand">
        <span class="eyebrow">无人机协同调度系统</span>
        <div class="brand-headline">
          <h1>{{ pageTitle }}</h1>
          <span class="workspace-badge">{{ workspaceBadge }}</span>
        </div>
        <p v-if="pageIntro" class="brand-intro">{{ pageIntro }}</p>
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
  { path: "/admin/overview", label: "总览" },
  { path: "/admin/pending", label: "审核" },
  { path: "/admin/active", label: "执行" },
  { path: "/admin/completed", label: "归档" },
];
const requesterTabs = [
  { path: "/requester", label: "任务申请" },
];
const executorTabs = [
  { path: "/executor/overview", label: "总览" },
  { path: "/executor/tasks", label: "任务中心" },
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
  if (route.path.startsWith("/task/")) return "任务详情";
  if (currentRole.value === "admin") {
    if (route.path.startsWith("/admin/overview")) return "总览";
    if (route.path.startsWith("/admin/active")) return "执行调度";
    if (route.path.startsWith("/admin/completed")) return "任务归档";
    return "审核申请";
  }
  if (currentRole.value === "requester") {
    if (route.path.startsWith("/requester/history")) return "我的申请";
    return "提交任务申请";
  }
  if (route.path.startsWith("/executor/overview")) return "总览";
  return "任务中心";
});

const pageIntro = computed(() => {
  if (currentRole.value === "requester" && route.path.startsWith("/requester/create")) {
    return "提交后可在我的申请中查看审批和分配进展。";
  }
  return "";
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
