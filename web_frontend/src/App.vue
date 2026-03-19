<template>
  <div class="app-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Graduation Design Prototype / Vue3</p>
        <h1>无人机动态路径规划系统</h1>
        <p class="hero-copy">
          这版前端按毕业设计常见交付方式，拆为“研究模式”“运营模式”和“3D仿真预览”，兼顾算法实验、企业操作与可视化演示。
        </p>
      </div>
      <div class="hero-tags">
        <span>LB-A*</span>
        <span>MARL</span>
        <span>3D Simulation</span>
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
import { ref } from "vue";
import ResearchModeView from "./modules/research/ResearchModeView.vue";
import OperationsModeView from "./modules/operations/OperationsModeView.vue";
import Simulation3DView from "./modules/simulation3d/Simulation3DView.vue";

const tabs = [
  { key: "research", label: "研究模式（推理实验）" },
  { key: "ops", label: "运营模式（企业操作）" },
  { key: "sim3d", label: "3D仿真预览（演示）" },
];

const activeMode = ref("research");
</script>
