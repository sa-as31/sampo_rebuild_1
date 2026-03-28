<template>
  <section class="dashboard-page">
    <article class="dashboard-hero card-panel">
      <div class="dashboard-hero__copy">
        <p class="section-kicker">Mission Overview</p>
        <h2 class="section-title">先讲当前任务，再讲系统能力。</h2>
        <p class="section-copy">
          这一版首页不再堆大量小卡片，而是先把今天最值得展示的调度状态压缩成一条叙事:
          任务量、舰队在线率、当前执行焦点，以及此刻是否存在需要处理的风险。
        </p>
        <div class="dashboard-hero__actions">
          <button class="app-btn app-btn--primary" @click="$router.push('/tasks')">查看任务看板</button>
          <button class="app-btn app-btn--ghost" @click="$router.push('/fleet')">切到舰队观测</button>
        </div>
      </div>

      <div class="dashboard-hero__aside">
        <div class="dashboard-focus-card dark-stage">
          <div class="dashboard-focus-card__head">
            <span>今日焦点任务</span>
            <strong>{{ focusTask.name }}</strong>
          </div>
          <p>{{ focusTask.summary }}</p>
          <div class="dashboard-focus-card__meta">
            <span>{{ focusTask.location }}</span>
            <span>{{ focusTask.operator }}</span>
            <span>{{ focusTask.throughput }}</span>
          </div>
        </div>
      </div>
    </article>

    <div class="metric-strip">
      <article v-for="metric in dashboardMetrics" :key="metric.label" class="metric-card">
        <p>{{ metric.label }}</p>
        <strong>{{ metric.value }}</strong>
        <span>{{ metric.note }}</span>
      </article>
    </div>

    <section class="dashboard-grid">
      <article class="dashboard-stage dark-stage">
        <div class="dashboard-stage__head">
          <div>
            <p class="section-kicker">Live Stage</p>
            <h3>活跃任务分布</h3>
          </div>
          <button class="eyebrow-link" @click="$router.push(`/tasks/${focusTask.id}`)">进入任务详情</button>
        </div>

        <div class="dashboard-stage__map">
          <div class="dashboard-stage__grid"></div>
          <div v-for="(task, index) in highlightedTasks" :key="task.id" class="dashboard-stage__node" :style="nodeStyle(index)">
            <span>{{ task.name }}</span>
            <small>{{ task.stage }} · {{ task.drones }} 架</small>
          </div>
        </div>
      </article>

      <article class="dashboard-feed card-panel">
        <div class="dashboard-feed__head">
          <div>
            <p class="section-kicker">Activity Feed</p>
            <h3>最新动态</h3>
          </div>
        </div>

        <div class="dashboard-feed__list">
          <article v-for="item in dashboardActivities" :key="item.title" class="dashboard-feed__item">
            <span class="tone-badge" :class="`tone-${item.tone}`">{{ item.time }}</span>
            <strong>{{ item.title }}</strong>
          </article>
        </div>
      </article>
    </section>

    <section class="dashboard-lower">
      <article class="dashboard-capacity card-panel">
        <div>
          <p class="section-kicker">System Rhythm</p>
          <h3>当前系统节拍</h3>
        </div>

        <div class="dashboard-capacity__list">
          <div v-for="lane in capacityLanes" :key="lane.label" class="dashboard-capacity__item">
            <div class="dashboard-capacity__meta">
              <strong>{{ lane.label }}</strong>
              <span>{{ lane.value }}</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${lane.percent}%` }"></div>
            </div>
            <p>{{ lane.detail }}</p>
          </div>
        </div>
      </article>

      <article class="dashboard-summary card-panel">
        <div>
          <p class="section-kicker">Fleet Snapshot</p>
          <h3>舰队状态摘要</h3>
        </div>

        <div class="dashboard-summary__list">
          <article v-for="item in fleetSummary" :key="item.label" class="dashboard-summary__item">
            <span class="tone-badge" :class="`tone-${item.tone}`">{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.note }}</p>
          </article>
        </div>
      </article>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import {
  dashboardMetrics,
  dashboardActivities,
  capacityLanes,
  fleetSummary,
  tasks,
} from '../data/mockMissionData';

const highlightedTasks = computed(() => tasks.filter((item) => ['ready', 'running'].includes(item.stageKey)).slice(0, 4));
const focusTask = computed(() => tasks.find((item) => item.stageKey === 'running') || tasks[0]);

function nodeStyle(index) {
  const positions = [
    { left: '18%', top: '62%' },
    { left: '36%', top: '38%' },
    { left: '58%', top: '52%' },
    { left: '74%', top: '30%' },
  ];

  return positions[index] || positions[0];
}
</script>

<style scoped>
.dashboard-page {
  display: grid;
  gap: 26px;
}

.dashboard-hero {
  padding: 30px;
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.78fr);
}

.dashboard-hero__actions {
  display: flex;
  gap: 12px;
  margin-top: 28px;
}

.dashboard-hero__aside {
  display: flex;
  align-items: stretch;
}

.dashboard-focus-card {
  width: 100%;
  padding: 22px;
  border-radius: 28px;
}

.dashboard-focus-card__head span,
.dashboard-focus-card__head strong {
  display: block;
}

.dashboard-focus-card__head span {
  color: rgba(245, 242, 235, 0.62);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-focus-card__head strong {
  margin-top: 14px;
  font-family: var(--font-display);
  font-size: 34px;
  line-height: 1;
}

.dashboard-focus-card p {
  margin: 18px 0 0;
  color: rgba(245, 242, 235, 0.78);
  line-height: 1.8;
}

.dashboard-focus-card__meta {
  display: grid;
  gap: 10px;
  margin-top: 20px;
}

.dashboard-focus-card__meta span {
  display: inline-flex;
  width: fit-content;
  padding: 8px 12px;
  border-radius: 999px;
  color: rgba(245, 242, 235, 0.84);
  background: rgba(255, 255, 255, 0.08);
}

.dashboard-grid {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.7fr);
}

.dashboard-stage {
  padding: 26px;
  border-radius: 32px;
}

.dashboard-stage__head,
.dashboard-feed__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dashboard-stage__head h3,
.dashboard-feed__head h3,
.dashboard-capacity h3,
.dashboard-summary h3 {
  margin: 14px 0 0;
  font-size: 30px;
  line-height: 1.1;
}

.dashboard-stage__map {
  position: relative;
  min-height: 380px;
  margin-top: 24px;
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02)),
    rgba(0, 0, 0, 0.14);
}

.dashboard-stage__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 48px 48px;
  opacity: 0.35;
}

.dashboard-stage__node {
  position: absolute;
  display: grid;
  gap: 6px;
  min-width: 170px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  transform: translate(-50%, -50%);
  box-shadow: 0 16px 34px rgba(0, 0, 0, 0.2);
}

.dashboard-stage__node span {
  font-size: 16px;
  font-weight: 600;
}

.dashboard-stage__node small {
  color: rgba(245, 242, 235, 0.72);
}

.dashboard-feed {
  padding: 24px;
}

.dashboard-feed__list {
  display: grid;
  gap: 18px;
  margin-top: 24px;
}

.dashboard-feed__item {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.52);
}

.dashboard-feed__item strong {
  font-size: 16px;
  line-height: 1.6;
}

.dashboard-lower {
  display: grid;
  gap: 24px;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
}

.dashboard-capacity,
.dashboard-summary {
  padding: 24px;
}

.dashboard-capacity__list,
.dashboard-summary__list {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}

.dashboard-capacity__item {
  display: grid;
  gap: 12px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.48);
}

.dashboard-capacity__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.dashboard-capacity__meta span,
.dashboard-capacity__item p,
.dashboard-summary__item p {
  color: var(--color-copy);
}

.dashboard-capacity__item p,
.dashboard-summary__item p {
  margin: 0;
  line-height: 1.7;
}

.dashboard-summary__item {
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.48);
}

.dashboard-summary__item strong {
  display: block;
  margin-top: 14px;
  font-size: 34px;
  line-height: 1;
}

@media (max-width: 1100px) {
  .dashboard-hero,
  .dashboard-grid,
  .dashboard-lower {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .dashboard-hero,
  .dashboard-stage,
  .dashboard-feed,
  .dashboard-capacity,
  .dashboard-summary {
    padding: 20px;
  }

  .dashboard-hero__actions {
    flex-direction: column;
  }
}
</style>
