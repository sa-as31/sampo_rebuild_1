<template>
  <section class="login-stage">
    <article class="login-stage__hero">
      <p class="section-kicker">UAV Coordination Research Interface</p>
      <h1>让任务申请、调度与舰队观测在一套更克制的前端里形成闭环。</h1>
      <p>
        这里延续仓库里的暖白编辑式设计语言，把毕业设计展示最重要的几件事压缩得更清楚:
        谁在申请、谁在调度、谁在执行，以及任务运行时到底发生了什么。
      </p>

      <div class="login-stage__notes">
        <article v-for="note in notes" :key="note.title" class="login-note">
          <span>{{ note.kicker }}</span>
          <strong>{{ note.title }}</strong>
          <p>{{ note.copy }}</p>
        </article>
      </div>
    </article>

    <article class="login-card card-panel">
      <div class="login-card__inner">
        <div>
          <p class="section-kicker">System Access</p>
          <h2>进入演示环境</h2>
          <p class="login-sub">
            选择一个示例身份后即可进入新版前端工作台。当前界面以“管理员视角”作为默认落点。
          </p>
        </div>

        <form class="login-form" @submit.prevent="handleLogin">
          <div class="segmented login-role-switcher">
            <button
              v-for="role in roles"
              :key="role.value"
              type="button"
              :class="{ 'is-active': form.role === role.value }"
              @click="selectRole(role)"
            >
              {{ role.label }}
            </button>
          </div>

          <label class="login-field">
            <span>账号</span>
            <input v-model="form.username" type="text" autocomplete="username" required placeholder="请输入账号" />
          </label>

          <label class="login-field">
            <span>密码</span>
            <input v-model="form.password" type="password" autocomplete="current-password" required placeholder="演示环境密码统一为 1" />
          </label>

          <div class="login-presets">
            <button
              v-for="account in roleAccounts"
              :key="account.username"
              type="button"
              class="login-preset"
              @click="applyAccount(account)"
            >
              <strong>{{ account.username }}</strong>
              <span>{{ account.hint }}</span>
            </button>
          </div>

          <div class="login-submit-row">
            <p>{{ currentRoleHint }}</p>
            <button type="submit" class="app-btn app-btn--primary" :disabled="loading">
              <span v-if="loading" class="login-spinner"></span>
              {{ loading ? '载入工作台...' : '进入系统' }}
            </button>
          </div>
        </form>
      </div>
    </article>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const roles = [
  { label: '管理员', value: 'admin' },
  { label: '申请人', value: 'requester' },
  { label: '飞手', value: 'executor' },
];

const accounts = {
  admin: [
    { username: 'admin', password: '1', hint: '审核、调度与归档复盘' },
    { username: 'ops_lead', password: '1', hint: '偏运营展示的管理员账号' },
  ],
  requester: [
    { username: 'requester01', password: '1', hint: '提交任务并查看审核进度' },
    { username: 'lab_requester', password: '1', hint: '偏实验室场景的申请账号' },
  ],
  executor: [
    { username: 'executor01', password: '1', hint: '执行联调、反馈与回放' },
    { username: 'pilot_chen', password: '1', hint: '测绘任务常用飞手账号' },
  ],
};

const notes = [
  {
    kicker: 'Task Flow',
    title: '申请、审核、执行分开讲',
    copy: '每个页面只承担一个主要目的，避免一屏同时塞满审批、地图、回放与反馈。',
  },
  {
    kicker: 'Mission Stage',
    title: '深色舞台只留给关键任务',
    copy: '把 2D / 3D 运行区域保留在详情页，用更高对比度承托真正重要的实时状态。',
  },
  {
    kicker: 'Presentation Rhythm',
    title: '适合毕业设计展示的节奏',
    copy: '首页负责概览，看板负责筛选，详情负责操作，舰队页负责说明系统整体能力。',
  },
];

const form = reactive({
  role: 'admin',
  username: 'admin',
  password: '1',
});

const loading = ref(false);

const roleAccounts = computed(() => accounts[form.role] || []);
const currentRoleHint = computed(() => {
  if (form.role === 'admin') return '管理员入口适合查看任务全流程与设计后的整体 UI 节奏。';
  if (form.role === 'requester') return '申请人入口更强调任务申请与审核结果的表达。';
  return '飞手入口用于展示执行控制、现场反馈与任务回放。';
});

function applyAccount(account) {
  form.username = account.username;
  form.password = account.password;
}

function selectRole(role) {
  form.role = role.value;
  applyAccount(accounts[role.value][0]);
}

function handleLogin() {
  loading.value = true;
  window.setTimeout(() => {
    loading.value = false;
    router.push('/dashboard');
  }, 520);
}
</script>

<style scoped>
.login-stage {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(420px, 0.82fr);
  gap: 42px;
  align-items: center;
}

.login-stage__hero h1 {
  margin: 18px 0 0;
  max-width: 10.5em;
  font-family: var(--font-display);
  font-size: clamp(58px, 6vw, 90px);
  line-height: 0.94;
  letter-spacing: -0.05em;
}

.login-stage__hero > p:last-of-type {
  margin: 24px 0 0;
  max-width: 720px;
  font-size: 19px;
  line-height: 1.82;
  color: var(--color-copy);
}

.login-stage__notes {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-top: 32px;
}

.login-note {
  padding: 22px;
  border: 1px solid var(--color-line);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.42);
  box-shadow: var(--shadow-soft);
}

.login-note span,
.login-note strong,
.login-note p {
  display: block;
}

.login-note span {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--color-muted);
}

.login-note strong {
  margin-top: 14px;
  font-size: 22px;
  line-height: 1.2;
}

.login-note p {
  margin-top: 12px;
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-copy);
}

.login-card {
  padding: 30px;
}

.login-card__inner {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 28px;
}

.login-card h2 {
  margin: 16px 0 0;
  font-family: var(--font-display);
  font-size: 42px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.login-sub {
  margin: 14px 0 0;
  color: var(--color-copy);
  line-height: 1.7;
}

.login-form {
  display: grid;
  gap: 18px;
}

.login-role-switcher {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.login-field {
  display: grid;
  gap: 10px;
}

.login-field span {
  font-size: 14px;
  color: var(--color-muted);
}

.login-field input {
  min-height: 54px;
  padding: 0 16px;
  border: 1px solid var(--color-line);
  border-radius: 18px;
  color: var(--color-ink);
  background: rgba(255, 255, 255, 0.72);
  transition:
    border-color 0.22s ease,
    box-shadow 0.22s ease,
    background-color 0.22s ease;
}

.login-field input:focus {
  outline: none;
  border-color: var(--color-line-strong);
  box-shadow: 0 0 0 4px rgba(23, 23, 23, 0.05);
  background: rgba(255, 255, 255, 0.96);
}

.login-presets {
  display: grid;
  gap: 10px;
}

.login-preset {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-line);
  border-radius: 18px;
  text-align: left;
  background: rgba(255, 255, 255, 0.48);
}

.login-preset:hover {
  border-color: var(--color-line-strong);
  background: rgba(255, 255, 255, 0.82);
}

.login-preset strong,
.login-preset span {
  display: block;
}

.login-preset span {
  color: var(--color-copy);
  font-size: 13px;
}

.login-submit-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-top: 4px;
}

.login-submit-row p {
  margin: 0;
  max-width: 240px;
  color: var(--color-muted);
  font-size: 14px;
  line-height: 1.7;
}

.login-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.32);
  border-top-color: white;
  border-radius: 999px;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1120px) {
  .login-stage {
    grid-template-columns: minmax(0, 1fr);
  }

  .login-stage__notes {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 720px) {
  .login-card {
    padding: 20px;
  }

  .login-card h2 {
    font-size: 34px;
  }

  .login-submit-row {
    flex-direction: column;
    align-items: stretch;
  }

  .login-submit-row p {
    max-width: none;
  }
}
</style>
