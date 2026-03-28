<template>
  <div class="app-shell">
    <section v-if="authStore.state.authBooting" class="login-shell">
      <div class="login-stage login-stage-loading">
        <div class="login-card editorial-card">
          <span class="eyebrow">System Access</span>
          <h2>正在加载账户信息...</h2>
        </div>
      </div>
    </section>

    <router-view v-else v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { onMounted, watch } from "vue";
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from "./stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

onMounted(async () => {
  await authStore.bootstrapAuth();
  
  // 简单的全局导航守卫逻辑（由于没在 router 层面配置 beforeEach，可以放这里处理初始加载跳转）
  if (!authStore.state.loggedIn && route.path !== '/login') {
    router.push('/login');
  } else if (authStore.state.loggedIn && route.path === '/login') {
    const role = authStore.state.currentUser?.role;
    if (role === 'admin') router.push('/admin');
    else if (role === 'requester') router.push('/requester');
    else router.push('/executor');
  }
});

// 监听登录状态变化，防止手动输入 URL
watch(() => authStore.state.loggedIn, (loggedIn) => {
  if (!loggedIn && route.path !== '/login') {
    router.push('/login');
  }
});
</script>

<style>
/* 增加丝滑的路由过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.35s cubic-bezier(0.25, 1, 0.5, 1), transform 0.35s cubic-bezier(0.25, 1, 0.5, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(15px);
}
.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}
</style>
