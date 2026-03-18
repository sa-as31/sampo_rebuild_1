<template>
  <div class="app-shell">
    <header class="hero">
      <div>
        <p class="eyebrow">Graduation Design Prototype / Vue3</p>
        <h1>无人机动态路径规划系统</h1>
        <p class="hero-copy">
          这版前端按毕业设计常见交付方式，拆为“研究模式”和“运营模式”，兼顾算法实验与企业侧操作流程。
        </p>
      </div>
      <div class="hero-tags">
        <span>LB-A*</span>
        <span>MARL</span>
        <span>Dual Mode UI</span>
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
      <OperationsModeView v-else />
    </main>
  </div>
</template>

<script setup>
import { ref } from "vue";
import ResearchModeView from "./modules/research/ResearchModeView.vue";
import OperationsModeView from "./modules/operations/OperationsModeView.vue";

const tabs = [
  { key: "research", label: "研究模式（推理实验）" },
  { key: "ops", label: "运营模式（企业操作）" },
];

const activeMode = ref("research");
</script>

