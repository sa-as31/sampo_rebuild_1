<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <h1>无人机协同调度系统</h1>
        <span>Control Console</span>
      </div>
      <div class="role-entry">
        <span class="role-pill">当前身份：{{ roleLabel }}</span>
        <button class="switch-trigger" @click="openRoleDialog">切换身份</button>
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
      <OperationsModeView v-else-if="activeMode === 'ops'" />
      <Simulation3DView v-else />
    </main>

    <div v-if="showRoleDialog" class="role-modal-mask" @click.self="closeRoleDialog">
      <section class="role-modal">
        <h3>身份切换</h3>
        <p>选择要进入的工作界面。</p>
        <div class="role-card-grid">
          <button class="role-card" :class="{ active: pendingRole === 'executor' }" @click="pendingRole = 'executor'">
            <strong>执行者</strong>
            <span>任务下发、状态回放、3D 观察</span>
          </button>
          <button class="role-card" :class="{ active: pendingRole === 'admin' }" @click="pendingRole = 'admin'">
            <strong>管理员</strong>
            <span>包含执行者能力 + 研究模式与参数调试</span>
          </button>
        </div>
        <div class="btn-row" style="margin-top: 12px">
          <button class="btn" @click="applyRoleSwitch">确认切换</button>
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
import Simulation3DView from "./modules/simulation3d/Simulation3DView.vue";
import TaskCenterView from "./modules/taskcenter/TaskCenterView.vue";
import OpsDashboardView from "./modules/dashboard/OpsDashboardView.vue";

const adminTabs = [
  { key: "ops", label: "运营中心" },
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营大屏" },
  { key: "sim3d", label: "3D回放" },
  { key: "research", label: "研究模式" },
];
const executorTabs = [
  { key: "ops", label: "运营中心" },
  { key: "taskCenter", label: "任务中心" },
  { key: "dashboard", label: "运营大屏" },
  { key: "sim3d", label: "3D回放" },
];

const userRole = ref("executor");
const activeMode = ref("ops");
const showRoleDialog = ref(false);
const pendingRole = ref(userRole.value);
const tabs = computed(() => (userRole.value === "admin" ? adminTabs : executorTabs));
const roleLabel = computed(() => (userRole.value === "admin" ? "管理员" : "执行者"));

function switchRole(nextRole) {
  userRole.value = nextRole;
  const visible = tabs.value.map((tab) => tab.key);
  if (!visible.includes(activeMode.value)) activeMode.value = visible[0];
}

function openRoleDialog() {
  pendingRole.value = userRole.value;
  showRoleDialog.value = true;
}

function closeRoleDialog() {
  showRoleDialog.value = false;
}

function applyRoleSwitch() {
  switchRole(pendingRole.value);
  closeRoleDialog();
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
});

onUnmounted(() => {
  window.removeEventListener("app-switch-mode", handleModeSwitch);
});
</script>
