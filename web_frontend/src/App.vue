<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <h1>无人机协同调度系统</h1>
        <span>Control Console</span>
      </div>
      <div class="role-switch">
        <button :class="{ active: userRole === 'executor' }" @click="switchRole('executor')">执行者</button>
        <button :class="{ active: userRole === 'admin' }" @click="switchRole('admin')">管理员</button>
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
      <OperationsModeView v-else-if="activeMode === 'ops'" />
      <Simulation3DView v-else />
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import ResearchModeView from "./modules/research/ResearchModeView.vue";
import OperationsModeView from "./modules/operations/OperationsModeView.vue";
import Simulation3DView from "./modules/simulation3d/Simulation3DView.vue";

const adminTabs = [
  { key: "ops", label: "运营中心" },
  { key: "sim3d", label: "3D回放" },
  { key: "research", label: "研究模式" },
];
const executorTabs = [
  { key: "ops", label: "运营中心" },
  { key: "sim3d", label: "3D回放" },
];

const userRole = ref("executor");
const activeMode = ref("ops");
const tabs = computed(() => (userRole.value === "admin" ? adminTabs : executorTabs));

function switchRole(nextRole) {
  userRole.value = nextRole;
  const visible = tabs.value.map((tab) => tab.key);
  if (!visible.includes(activeMode.value)) activeMode.value = visible[0];
}
</script>
