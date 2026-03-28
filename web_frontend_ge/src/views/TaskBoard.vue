<template>
  <section class="board-page">
    <article class="board-hero card-panel">
      <div>
        <p class="section-kicker">Mission Board</p>
        <h2 class="section-title">把任务流拆成可读的四段，而不是一整面信息墙。</h2>
        <p class="section-copy">
          看板页负责筛任务、分清阶段和快速进入详情。这里保留“少卡片、大容器”的节奏，
          既适合老师演示，也方便你后面继续把真实接口接进来。
        </p>
      </div>

      <div class="board-hero__controls">
        <div class="segmented board-hero__segmented">
          <button v-for="view in views" :key="view.id" :class="{ 'is-active': currentView === view.id }" @click="currentView = view.id">
            {{ view.label }}
          </button>
        </div>
        <button class="app-btn app-btn--primary">新建任务申请</button>
      </div>
    </article>

    <div class="board-toolbar">
      <div class="segmented board-filter">
        <button v-for="filter in stageFilters" :key="filter.id" :class="{ 'is-active': currentFilter === filter.id }" @click="currentFilter = filter.id">
          {{ filter.label }}
        </button>
      </div>
      <p>当前共 {{ filteredTasks.length }} 条任务，点击任一任务卡可进入新版详情工作台。</p>
    </div>

    <transition name="fade-slide" mode="out-in">
      <section v-if="currentView === 'board'" key="board" class="board-columns">
        <article v-for="column in visibleColumns" :key="column.id" class="board-column card-panel">
          <div class="board-column__head">
            <span class="tone-badge" :class="`tone-${column.tone}`">{{ column.label }}</span>
            <strong>{{ column.tasks.length }}</strong>
          </div>

          <div class="board-column__list">
            <button v-for="task in column.tasks" :key="task.id" class="task-card" @click="$router.push(`/tasks/${task.id}`)">
              <div class="task-card__meta">
                <span class="tone-badge" :class="`tone-${categoryTone(task.category)}`">{{ task.category }}</span>
                <small>{{ task.schedule }}</small>
              </div>
              <h3>{{ task.name }}</h3>
              <p>{{ task.summary }}</p>
              <div class="task-card__footer">
                <span>{{ task.location }}</span>
                <strong>{{ task.drones }} 架</strong>
              </div>
            </button>
          </div>
        </article>
      </section>

      <section v-else key="list" class="board-list">
        <article v-for="task in filteredTasks" :key="task.id" class="board-list__row card-panel" @click="$router.push(`/tasks/${task.id}`)">
          <div class="board-list__main">
            <div class="board-list__head">
              <span class="tone-badge" :class="`tone-${task.tone}`">{{ task.stage }}</span>
              <span class="tone-badge" :class="`tone-${categoryTone(task.category)}`">{{ task.category }}</span>
            </div>
            <h3>{{ task.name }}</h3>
            <p>{{ task.summary }}</p>
          </div>

          <div class="board-list__meta">
            <div>
              <span>地点</span>
              <strong>{{ task.location }}</strong>
            </div>
            <div>
              <span>飞手</span>
              <strong>{{ task.operator }}</strong>
            </div>
            <div>
              <span>吞吐量</span>
              <strong>{{ task.throughput }}</strong>
            </div>
          </div>

          <div class="board-list__progress">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: `${task.progress}%` }"></div>
            </div>
            <small>{{ task.progress }}%</small>
          </div>
        </article>
      </section>
    </transition>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue';
import { getBoardColumns, tasks } from '../data/mockMissionData';

const currentView = ref('board');
const currentFilter = ref('all');

const views = [
  { id: 'board', label: '看板视图' },
  { id: 'list', label: '列表视图' },
];

const stageFilters = [
  { id: 'all', label: '全部' },
  { id: 'pending', label: '待审核' },
  { id: 'ready', label: '待执行' },
  { id: 'running', label: '执行中' },
  { id: 'archived', label: '已归档' },
];

const boardColumns = computed(() => getBoardColumns());
const filteredTasks = computed(() => {
  if (currentFilter.value === 'all') return tasks;
  return tasks.filter((task) => task.stageKey === currentFilter.value);
});

const visibleColumns = computed(() => {
  if (currentFilter.value === 'all') return boardColumns.value;
  return boardColumns.value.filter((column) => column.id === currentFilter.value);
});

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
.board-page {
  display: grid;
  gap: 24px;
}

.board-hero {
  padding: 28px 30px;
  display: grid;
  gap: 22px;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.75fr);
}

.board-hero__controls {
  display: grid;
  gap: 16px;
  justify-items: end;
  align-content: start;
}

.board-hero__segmented {
  width: 100%;
}

.board-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.board-toolbar p {
  margin: 0;
  color: var(--color-copy);
}

.board-columns {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.board-column {
  padding: 18px;
}

.board-column__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.board-column__head strong {
  font-size: 28px;
  line-height: 1;
}

.board-column__list {
  display: grid;
  gap: 14px;
}

.task-card {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  text-align: left;
  background: rgba(255, 255, 255, 0.58);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    border-color 0.22s ease;
}

.task-card:hover,
.board-list__row:hover {
  transform: translateY(-2px);
  border-color: var(--color-line-strong);
  box-shadow: 0 14px 34px rgba(17, 17, 17, 0.08);
}

.task-card__meta,
.task-card__footer,
.board-list__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-card__meta small,
.task-card__footer span {
  color: var(--color-muted);
}

.task-card h3,
.board-list__main h3 {
  margin: 0;
  font-size: 22px;
  line-height: 1.2;
}

.task-card p,
.board-list__main p {
  margin: 0;
  color: var(--color-copy);
  line-height: 1.7;
}

.board-list {
  display: grid;
  gap: 16px;
}

.board-list__row {
  padding: 22px 24px;
  display: grid;
  gap: 20px;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.75fr) 140px;
  align-items: center;
  cursor: pointer;
}

.board-list__meta {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.board-list__meta span,
.board-list__progress small {
  color: var(--color-muted);
}

.board-list__meta strong {
  display: block;
  margin-top: 8px;
}

.board-list__progress {
  display: grid;
  gap: 10px;
}

@media (max-width: 1180px) {
  .board-hero,
  .board-list__row {
    grid-template-columns: minmax(0, 1fr);
  }

  .board-hero__controls {
    justify-items: stretch;
  }

  .board-columns {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .board-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 720px) {
  .board-hero {
    padding: 20px;
  }

  .board-columns {
    grid-template-columns: minmax(0, 1fr);
  }

  .board-filter {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }

  .board-list__meta {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
