<template>
  <section class="detail-page">
    <button class="eyebrow-link detail-back" @click="router.push('/tasks')">
      <ArrowLeftIcon class="detail-back__icon" />
      返回任务看板
    </button>

    <article class="detail-hero card-panel">
      <div>
        <div class="detail-hero__top">
          <span class="tone-badge" :class="`tone-${selectedTask.tone}`">{{ selectedTask.stage }}</span>
          <span class="tone-badge" :class="`tone-${categoryTone(selectedTask.category)}`">{{ selectedTask.category }}</span>
        </div>
        <h2>{{ selectedTask.name }}</h2>
        <p>{{ selectedTask.summary }}</p>
      </div>

      <div class="detail-hero__actions">
        <button class="app-btn app-btn--ghost" @click="router.push('/fleet')">查看舰队态势</button>
        <button class="app-btn app-btn--primary" @click="activeTab = '参数'">查看执行参数</button>
      </div>
    </article>

    <div class="detail-metrics">
      <article v-for="item in selectedTask.kpis" :key="item.label" class="metric-card">
        <p>{{ item.label }}</p>
        <strong>{{ item.value }}</strong>
        <span>{{ selectedTask.code }}</span>
      </article>
    </div>

    <section class="detail-grid">
      <article class="detail-stage dark-stage">
        <div class="detail-stage__head">
          <div>
            <p class="section-kicker">Mission Stage</p>
            <h3>{{ viewMode === '3D' ? '联合运行舞台' : '二维俯视路径' }}</h3>
          </div>

          <div class="segmented detail-stage__switcher">
            <button :class="{ 'is-active': viewMode === '3D' }" @click="viewMode = '3D'">3D 视图</button>
            <button :class="{ 'is-active': viewMode === '2D' }" @click="viewMode = '2D'">2D 俯视</button>
          </div>
        </div>

        <div class="detail-stage__map">
          <div class="detail-stage__grid"></div>
          <div v-for="segment in pathSegments" :key="segment.key" class="detail-stage__line" :style="segment.style"></div>
          <div v-for="point in selectedTask.checkpoints" :key="point.label" class="detail-stage__point" :style="checkpointStyle(point)">
            <strong>{{ point.label }}</strong>
            <span>{{ point.altitude }}</span>
          </div>
          <div class="detail-stage__legend">
            <span>地图 {{ selectedTask.map }}</span>
            <span>飞手 {{ selectedTask.operator }}</span>
            <span>{{ selectedTask.drones }} 架协同</span>
          </div>
        </div>

        <div class="detail-stage__footer">
          <button class="detail-stage__play">
            <PlayIcon />
          </button>
          <div class="detail-stage__progress">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${selectedTask.progress}%` }"></div>
            </div>
          </div>
          <span>{{ selectedTask.progress }}%</span>
        </div>
      </article>

      <aside class="detail-side card-panel">
        <div class="segmented detail-side__tabs">
          <button v-for="tab in tabs" :key="tab" :class="{ 'is-active': activeTab === tab }" @click="activeTab = tab">
            {{ tab }}
          </button>
        </div>

        <section v-if="activeTab === '概览'" class="detail-pane">
          <article class="detail-pane__block">
            <p class="section-kicker">Mission Brief</p>
            <h3>任务说明</h3>
            <p>{{ selectedTask.note }}</p>
          </article>

          <article class="detail-pane__block">
            <p class="section-kicker">Timeline</p>
            <h3>流程进度</h3>
            <div class="detail-timeline">
              <div v-for="item in selectedTask.timeline" :key="item.label" class="detail-timeline__item">
                <span :class="{ 'is-done': item.done }"></span>
                <div>
                  <strong>{{ item.label }}</strong>
                  <p>{{ item.detail }}</p>
                </div>
              </div>
            </div>
          </article>
        </section>

        <section v-else-if="activeTab === '参数'" class="detail-pane">
          <div class="detail-params">
            <article class="detail-param">
              <span>任务编号</span>
              <strong>{{ selectedTask.code }}</strong>
            </article>
            <article class="detail-param">
              <span>执行地图</span>
              <strong>{{ selectedTask.map }}</strong>
            </article>
            <article class="detail-param">
              <span>算法后端</span>
              <strong>{{ selectedTask.algorithm }}</strong>
            </article>
            <article class="detail-param">
              <span>计划时间</span>
              <strong>{{ selectedTask.schedule }}</strong>
            </article>
            <article class="detail-param">
              <span>申请部门</span>
              <strong>{{ selectedTask.requester }}</strong>
            </article>
            <article class="detail-param">
              <span>执行飞手</span>
              <strong>{{ selectedTask.operator }}</strong>
            </article>
          </div>
        </section>

        <section v-else-if="activeTab === '告警'" class="detail-pane">
          <article v-if="selectedTask.alerts.length === 0" class="detail-empty">
            当前任务没有额外告警，适合在答辩时作为“稳定运行”的示例页面。
          </article>
          <article v-for="alert in selectedTask.alerts" :key="alert.title" class="detail-alert" :class="alert.level">
            <strong>{{ alert.title }}</strong>
            <p>{{ alert.detail }}</p>
          </article>
        </section>

        <section v-else class="detail-pane">
          <article class="detail-pane__block">
            <p class="section-kicker">Replay Log</p>
            <h3>运行日志</h3>
            <div class="detail-log">
              <div v-for="line in selectedTask.logs" :key="line">{{ line }}</div>
            </div>
          </article>

          <article class="detail-pane__block">
            <p class="section-kicker">Checkpoints</p>
            <h3>路径锚点</h3>
            <div class="detail-checkpoints">
              <div v-for="point in selectedTask.checkpoints" :key="point.label" class="detail-checkpoints__item">
                <strong>{{ point.label }}</strong>
                <span>{{ point.altitude }}</span>
              </div>
            </div>
          </article>
        </section>
      </aside>
    </section>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ArrowLeftIcon, PlayIcon } from '@heroicons/vue/24/outline';
import { getTaskById } from '../data/mockMissionData';

const route = useRoute();
const router = useRouter();

const tabs = ['概览', '参数', '告警', '回放'];
const activeTab = ref('概览');
const viewMode = ref('3D');

const selectedTask = computed(() => getTaskById(route.params.id));

const pathSegments = computed(() => {
  const points = selectedTask.value.checkpoints;
  return points.slice(0, -1).map((point, index) => {
    const next = points[index + 1];
    const dx = next.x - point.x;
    const dy = next.y - point.y;
    const length = Math.sqrt(dx * dx + dy * dy);
    const angle = (Math.atan2(dy, dx) * 180) / Math.PI;

    return {
      key: `${point.label}-${next.label}`,
      style: {
        left: `${point.x}%`,
        top: `${point.y}%`,
        width: `${length}%`,
        transform: `rotate(${angle}deg)`,
      },
    };
  });
});

function checkpointStyle(point) {
  return {
    left: `${point.x}%`,
    top: `${point.y}%`,
  };
}

function categoryTone(category) {
  return (
    {
      巡检: 'teal',
      测绘: 'ink',
      运输: 'amber',
      演示: 'rose',
    }[category] || 'slate'
  );
}
</script>

<style scoped>
.detail-page {
  display: grid;
  gap: 22px;
}

.detail-back {
  width: fit-content;
  border: none;
  padding: 0;
  background: transparent;
}

.detail-back__icon {
  width: 16px;
  height: 16px;
}

.detail-hero {
  padding: 24px 28px;
  display: grid;
  gap: 18px;
  grid-template-columns: minmax(0, 1.1fr) auto;
  align-items: center;
}

.detail-hero__top,
.detail-hero__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-hero h2 {
  margin: 18px 0 0;
  font-family: var(--font-display);
  font-size: clamp(34px, 4vw, 54px);
  line-height: 0.98;
  letter-spacing: -0.04em;
}

.detail-hero p {
  margin: 16px 0 0;
  color: var(--color-copy);
  line-height: 1.8;
}

.detail-metrics {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.detail-grid {
  display: grid;
  gap: 22px;
  grid-template-columns: minmax(0, 1.45fr) minmax(360px, 0.78fr);
}

.detail-stage {
  padding: 24px;
  border-radius: 32px;
}

.detail-stage__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.detail-stage__head h3 {
  margin: 14px 0 0;
  font-size: 30px;
}

.detail-stage__switcher {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.12);
}

.detail-stage__switcher button {
  color: rgba(245, 242, 235, 0.7);
}

.detail-stage__switcher button.is-active {
  color: var(--color-ink);
  background: #f5f2eb;
}

.detail-stage__map {
  position: relative;
  min-height: 520px;
  margin-top: 20px;
  overflow: hidden;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at top left, rgba(92, 132, 183, 0.14), transparent 36%),
    rgba(0, 0, 0, 0.14);
}

.detail-stage__grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.08) 1px, transparent 1px);
  background-size: 52px 52px;
  opacity: 0.35;
}

.detail-stage__line {
  position: absolute;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(245, 242, 235, 0.25), rgba(245, 242, 235, 0.8));
  transform-origin: left center;
}

.detail-stage__point {
  position: absolute;
  min-width: 84px;
  padding: 12px 12px 10px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
  transform: translate(-50%, -50%);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.22);
}

.detail-stage__point strong,
.detail-stage__point span {
  display: block;
}

.detail-stage__point span {
  margin-top: 6px;
  color: rgba(245, 242, 235, 0.7);
  font-size: 12px;
}

.detail-stage__legend {
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 18px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.detail-stage__legend span {
  display: inline-flex;
  padding: 8px 12px;
  border-radius: 999px;
  color: rgba(245, 242, 235, 0.82);
  background: rgba(255, 255, 255, 0.08);
}

.detail-stage__footer {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 18px;
}

.detail-stage__play {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  color: #f5f2eb;
  background: rgba(255, 255, 255, 0.08);
}

.detail-stage__play :deep(svg) {
  width: 18px;
  height: 18px;
}

.detail-stage__progress {
  flex: 1;
}

.detail-side {
  padding: 20px;
}

.detail-side__tabs {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.detail-pane {
  display: grid;
  gap: 18px;
  margin-top: 18px;
}

.detail-pane__block,
.detail-param,
.detail-alert,
.detail-empty {
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.56);
}

.detail-pane__block h3 {
  margin: 14px 0 0;
  font-size: 24px;
}

.detail-pane__block p,
.detail-empty,
.detail-alert p {
  margin: 12px 0 0;
  color: var(--color-copy);
  line-height: 1.75;
}

.detail-timeline {
  display: grid;
  gap: 16px;
  margin-top: 18px;
}

.detail-timeline__item {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr);
  gap: 12px;
}

.detail-timeline__item > span {
  position: relative;
  width: 12px;
  height: 12px;
  border-radius: 999px;
  margin-top: 7px;
  background: rgba(23, 23, 23, 0.12);
}

.detail-timeline__item > span.is-done {
  background: var(--color-accent);
}

.detail-timeline__item strong {
  display: block;
}

.detail-timeline__item p {
  margin: 6px 0 0;
  color: var(--color-copy);
  line-height: 1.7;
}

.detail-params {
  display: grid;
  gap: 12px;
}

.detail-param span,
.detail-param strong {
  display: block;
}

.detail-param span {
  color: var(--color-muted);
  font-size: 13px;
}

.detail-param strong {
  margin-top: 10px;
  line-height: 1.6;
}

.detail-alert.warn {
  background: rgba(242, 231, 213, 0.72);
}

.detail-alert.danger {
  background: rgba(246, 227, 222, 0.72);
}

.detail-log {
  display: grid;
  gap: 10px;
  margin-top: 18px;
  padding: 16px;
  border-radius: 20px;
  color: #dbe3ee;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  background: #101a26;
}

.detail-checkpoints {
  display: grid;
  gap: 10px;
  margin-top: 18px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-checkpoints__item {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.46);
}

.detail-checkpoints__item strong,
.detail-checkpoints__item span {
  display: block;
}

.detail-checkpoints__item span {
  margin-top: 8px;
  color: var(--color-copy);
}

@media (max-width: 1180px) {
  .detail-hero,
  .detail-grid,
  .detail-metrics {
    grid-template-columns: minmax(0, 1fr);
  }

  .detail-hero__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .detail-hero,
  .detail-stage,
  .detail-side {
    padding: 20px;
  }

  .detail-side__tabs,
  .detail-checkpoints {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
