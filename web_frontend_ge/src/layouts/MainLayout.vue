<template>
  <div class="shell-page">
    <div class="shell-page__orb shell-page__orb--left"></div>
    <div class="shell-page__orb shell-page__orb--right"></div>

    <header class="shell-topbar card-panel">
      <div class="shell-topbar__copy">
        <p class="section-kicker">SMAPO UAV Coordination Console</p>
        <h1>{{ currentRouteTitle }}</h1>
        <p>{{ currentRouteIntro }}</p>
      </div>

      <div class="shell-topbar__meta">
        <div class="shell-signals">
          <article v-for="signal in shellSignals" :key="signal.label" class="shell-signal-card">
            <span>{{ signal.label }}</span>
            <strong>{{ signal.value }}</strong>
            <small>{{ signal.detail }}</small>
          </article>
        </div>

        <button class="shell-account" @click="router.push('/login')">
          <div class="shell-account__avatar">A</div>
          <div>
            <strong>Admin Console</strong>
            <span>返回登录入口</span>
          </div>
        </button>
      </div>
    </header>

    <nav class="shell-nav">
      <button
        v-for="item in menuRoutes"
        :key="item.path"
        class="shell-nav__item"
        :class="{ 'is-active': route.path.startsWith(item.path) }"
        @click="router.push(item.path)"
      >
        <component :is="icons[item.meta.icon]" v-if="icons[item.meta.icon]" class="shell-nav__icon" />
        <span>{{ item.meta.title }}</span>
      </button>
    </nav>

    <main class="shell-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { ChartPieIcon, ViewColumnsIcon, PaperAirplaneIcon } from '@heroicons/vue/24/outline';
import { shellSignals } from '../data/mockMissionData';

const router = useRouter();
const route = useRoute();

const icons = {
  ChartPieIcon,
  ViewColumnsIcon,
  PaperAirplaneIcon,
};

const menuRoutes = computed(() => {
  const mainRoute = router.options.routes.find((item) => item.path === '/');
  return (
    mainRoute?.children
      ?.filter((item) => item.meta && !item.meta.hidden)
      .map((item) => ({
        ...item,
        path: item.path.startsWith('/') ? item.path : `/${item.path}`,
      })) || []
  );
});

const currentRouteTitle = computed(() => route.meta?.title || 'SMAPO 控制台');
const currentRouteIntro = computed(() => route.meta?.intro || '让任务流、机组状态与展示页面保持统一节奏。');
</script>

<style scoped>
.shell-page {
  position: relative;
  width: min(1520px, calc(100% - 40px));
  margin: 0 auto;
  padding: 28px 0 48px;
}

.shell-page__orb {
  position: absolute;
  z-index: 0;
  width: 360px;
  height: 360px;
  border-radius: 999px;
  filter: blur(22px);
  pointer-events: none;
}

.shell-page__orb--left {
  top: 24px;
  left: -120px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.78) 0%, transparent 70%);
}

.shell-page__orb--right {
  top: 220px;
  right: -120px;
  background: radial-gradient(circle, rgba(214, 203, 177, 0.72) 0%, transparent 72%);
}

.shell-topbar,
.shell-nav,
.shell-main {
  position: relative;
  z-index: 1;
}

.shell-topbar {
  padding: 28px 30px;
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(380px, 0.9fr);
  gap: 24px;
  align-items: end;
}

.shell-topbar__copy h1 {
  margin: 16px 0 0;
  font-family: var(--font-display);
  font-size: clamp(42px, 4vw, 66px);
  line-height: 0.96;
  letter-spacing: -0.05em;
}

.shell-topbar__copy p:last-child {
  margin: 16px 0 0;
  max-width: 760px;
  font-size: 17px;
  line-height: 1.75;
  color: var(--color-copy);
}

.shell-topbar__meta {
  display: grid;
  gap: 16px;
}

.shell-signals {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.shell-signal-card {
  padding: 18px 16px;
  border: 1px solid var(--color-line);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.46);
}

.shell-signal-card span,
.shell-signal-card small {
  display: block;
}

.shell-signal-card span {
  font-size: 12px;
  color: var(--color-muted);
}

.shell-signal-card strong {
  display: block;
  margin-top: 12px;
  font-size: 26px;
  line-height: 1;
}

.shell-signal-card small {
  margin-top: 10px;
  color: var(--color-copy);
}

.shell-account {
  display: flex;
  align-items: center;
  gap: 14px;
  width: fit-content;
  padding: 12px 18px 12px 12px;
  border: 1px solid var(--color-line);
  border-radius: 999px;
  color: var(--color-ink);
  background: rgba(255, 255, 255, 0.62);
}

.shell-account__avatar {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--color-ink);
  color: #f8f5ee;
  font-weight: 700;
}

.shell-account strong,
.shell-account span {
  display: block;
  text-align: left;
}

.shell-account span {
  margin-top: 4px;
  color: var(--color-muted);
  font-size: 13px;
}

.shell-nav {
  display: inline-grid;
  grid-auto-flow: column;
  gap: 10px;
  margin: 18px 0 0;
  padding: 10px;
  border: 1px solid var(--color-line);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.5);
}

.shell-nav__item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  color: var(--color-muted);
  background: transparent;
  transition:
    background-color 0.22s ease,
    color 0.22s ease,
    transform 0.22s ease;
}

.shell-nav__item:hover {
  color: var(--color-ink);
}

.shell-nav__item.is-active {
  color: #f8f5ee;
  background: var(--color-ink);
  transform: translateY(-1px);
}

.shell-nav__icon {
  width: 18px;
  height: 18px;
}

.shell-main {
  margin-top: 26px;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition:
    opacity 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(14px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (max-width: 1100px) {
  .shell-page {
    width: min(100%, calc(100% - 28px));
    padding-top: 18px;
  }

  .shell-topbar {
    grid-template-columns: minmax(0, 1fr);
  }

  .shell-signals {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .shell-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
    border-radius: 28px;
  }
}

@media (max-width: 720px) {
  .shell-topbar {
    padding: 22px 20px;
  }

  .shell-topbar__copy h1 {
    font-size: 38px;
  }

  .shell-signals {
    grid-template-columns: minmax(0, 1fr);
  }

  .shell-nav {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
