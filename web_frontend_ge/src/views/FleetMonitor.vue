<template>
  <section class="fleet-page">
    <article class="fleet-hero card-panel">
      <div>
        <p class="section-kicker">Fleet Monitor</p>
        <h2 class="section-title">从机组健康、覆盖扇区和维护队列解释系统整体能力。</h2>
        <p class="section-copy">
          这一页不和任务看板抢信息，而是专门回答“我们的无人机群现在状态怎么样”。
          对答辩展示来说，它更像是系统层面的运营总台。
        </p>
      </div>
      <div class="fleet-hero__actions">
        <button class="app-btn app-btn--ghost" @click="$router.push('/dashboard')">回到总览首页</button>
        <button class="app-btn app-btn--primary" @click="$router.push('/tasks')">查看任务看板</button>
      </div>
    </article>

    <div class="metric-strip">
      <article v-for="item in fleetSummary" :key="item.label" class="metric-card">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ item.note }}</span>
      </article>
    </div>

    <section class="fleet-grid">
      <article class="fleet-stage dark-stage">
        <div class="fleet-stage__head">
          <div>
            <p class="section-kicker">Coverage Stage</p>
            <h3>扇区覆盖与链路状态</h3>
          </div>
        </div>

        <div class="fleet-stage__list">
          <article v-for="sector in sectorCoverage" :key="sector.name" class="fleet-stage__item">
            <div class="fleet-stage__item-head">
              <span class="tone-badge" :class="`tone-${sector.tone}`">{{ sector.status }}</span>
              <strong>{{ sector.name }}</strong>
            </div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${sector.coverage}%` }"></div>
            </div>
            <div class="fleet-stage__item-meta">
              <span>覆盖率 {{ sector.coverage }}%</span>
              <span>{{ sector.latency }}</span>
            </div>
          </article>
        </div>
      </article>

      <article class="fleet-roster card-panel">
        <div>
          <p class="section-kicker">Live Roster</p>
          <h3>在线机组</h3>
        </div>

        <div class="fleet-roster__list">
          <article v-for="unit in fleetRoster" :key="unit.id" class="fleet-roster__item">
            <div class="fleet-roster__head">
              <div>
                <strong>{{ unit.name }}</strong>
                <span>{{ unit.mission }}</span>
              </div>
              <span class="tone-badge" :class="`tone-${unit.tone}`">{{ unit.pilot }}</span>
            </div>
            <p>{{ unit.stage }}</p>
            <div class="fleet-roster__bars">
              <div>
                <small>电量 {{ unit.battery }}%</small>
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: `${unit.battery}%` }"></div>
                </div>
              </div>
              <div>
                <small>链路 {{ unit.link }}%</small>
                <div class="progress-track">
                  <div class="progress-fill" :style="{ width: `${unit.link}%` }"></div>
                </div>
              </div>
            </div>
          </article>
        </div>
      </article>
    </section>

    <section class="fleet-lower">
      <article class="fleet-maintenance card-panel">
        <div>
          <p class="section-kicker">Maintenance Queue</p>
          <h3>维护与保养</h3>
        </div>
        <div class="fleet-maintenance__list">
          <article v-for="item in maintenanceQueue" :key="item.name" class="fleet-maintenance__item">
            <strong>{{ item.name }}</strong>
            <p>{{ item.issue }}</p>
            <span>{{ item.eta }}</span>
          </article>
        </div>
      </article>

      <article class="fleet-upnext card-panel">
        <div>
          <p class="section-kicker">Up Next</p>
          <h3>即将进入执行窗口</h3>
        </div>
        <div class="fleet-upnext__list">
          <button v-for="task in upcomingTasks" :key="task.id" class="fleet-upnext__item" @click="$router.push(`/tasks/${task.id}`)">
            <span class="tone-badge" :class="`tone-${task.tone}`">{{ task.stage }}</span>
            <strong>{{ task.name }}</strong>
            <p>{{ task.location }}</p>
          </button>
        </div>
      </article>
    </section>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import {
  fleetSummary,
  fleetRoster,
  maintenanceQueue,
  sectorCoverage,
  tasks,
} from '../data/mockMissionData';

const upcomingTasks = computed(() => tasks.filter((task) => ['pending', 'ready'].includes(task.stageKey)).slice(0, 3));
</script>

<style scoped>
.fleet-page {
  display: grid;
  gap: 24px;
}

.fleet-hero {
  padding: 28px 30px;
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1.1fr) auto;
  align-items: center;
}

.fleet-hero__actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.fleet-grid,
.fleet-lower {
  display: grid;
  gap: 22px;
  grid-template-columns: minmax(0, 1.15fr) minmax(340px, 0.85fr);
}

.fleet-stage {
  padding: 24px;
  border-radius: 32px;
}

.fleet-stage__head h3,
.fleet-roster h3,
.fleet-maintenance h3,
.fleet-upnext h3 {
  margin: 14px 0 0;
  font-size: 30px;
}

.fleet-stage__list,
.fleet-roster__list,
.fleet-maintenance__list,
.fleet-upnext__list {
  display: grid;
  gap: 16px;
  margin-top: 22px;
}

.fleet-stage__item {
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.08);
}

.fleet-stage__item-head {
  display: grid;
  gap: 12px;
}

.fleet-stage__item-head strong {
  font-size: 22px;
}

.fleet-stage__item-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  color: rgba(245, 242, 235, 0.72);
}

.fleet-roster,
.fleet-maintenance,
.fleet-upnext {
  padding: 24px;
}

.fleet-roster__item,
.fleet-maintenance__item,
.fleet-upnext__item {
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.56);
}

.fleet-roster__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.fleet-roster__head strong,
.fleet-roster__head span {
  display: block;
}

.fleet-roster__head span:last-child {
  color: var(--color-copy);
  margin-top: 8px;
}

.fleet-roster__item > p,
.fleet-maintenance__item p,
.fleet-upnext__item p {
  margin: 14px 0 0;
  color: var(--color-copy);
  line-height: 1.75;
}

.fleet-roster__bars {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.fleet-roster__bars small {
  display: block;
  margin-bottom: 8px;
  color: var(--color-muted);
}

.fleet-maintenance__item strong,
.fleet-upnext__item strong {
  display: block;
  font-size: 20px;
  text-align: left;
}

.fleet-maintenance__item span {
  display: block;
  margin-top: 12px;
  color: var(--color-muted);
}

.fleet-upnext__item {
  text-align: left;
  transition:
    transform 0.22s ease,
    border-color 0.22s ease,
    box-shadow 0.22s ease;
}

.fleet-upnext__item:hover {
  transform: translateY(-2px);
  border-color: var(--color-line-strong);
  box-shadow: 0 14px 34px rgba(17, 17, 17, 0.08);
}

@media (max-width: 1180px) {
  .fleet-hero,
  .fleet-grid,
  .fleet-lower {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .fleet-hero,
  .fleet-stage,
  .fleet-roster,
  .fleet-maintenance,
  .fleet-upnext {
    padding: 20px;
  }

  .fleet-hero__actions {
    flex-direction: column;
  }
}
</style>
