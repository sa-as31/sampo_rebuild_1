<template>
  <div class="auth-shell">
    <div class="auth-shell__orb auth-shell__orb--left"></div>
    <div class="auth-shell__orb auth-shell__orb--right"></div>
    <div class="auth-shell__inner">
      <router-view v-slot="{ Component }">
        <transition name="scale" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.auth-shell {
  position: relative;
  min-height: 100vh;
  padding: 32px;
}

.auth-shell__inner {
  position: relative;
  z-index: 1;
  width: min(1480px, 100%);
  min-height: calc(100vh - 64px);
  margin: 0 auto;
  display: flex;
  align-items: center;
}

.auth-shell__orb {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 999px;
  filter: blur(18px);
  opacity: 0.42;
  pointer-events: none;
}

.auth-shell__orb--left {
  top: 6%;
  left: -120px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.78) 0%, rgba(255, 255, 255, 0) 70%);
}

.auth-shell__orb--right {
  right: -120px;
  bottom: 4%;
  background: radial-gradient(circle, rgba(214, 203, 177, 0.72) 0%, rgba(214, 203, 177, 0) 70%);
}

.scale-enter-active,
.scale-leave-active {
  transition: all 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}

.scale-enter-from {
  opacity: 0;
  transform: scale(0.96) translateY(14px);
}

.scale-leave-to {
  opacity: 0;
  transform: scale(1.02) translateY(-10px);
}

@media (max-width: 720px) {
  .auth-shell {
    padding: 18px;
  }

  .auth-shell__inner {
    min-height: calc(100vh - 36px);
  }
}
</style>
