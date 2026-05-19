import { reactive, readonly } from 'vue';
import { fetchAuthOptions, fetchAuthState, fetchIdentity, loginWithPassword, logoutCurrentUser, registerAccount } from '../services/api';

const state = reactive({
  authBooting: true,
  loggedIn: false,
  authBusy: false,
  authError: '',
  currentUser: null,
  authAccounts: [],
});

function normalizeUser(raw) {
  if (!raw || typeof raw !== "object") return null;
  return {
    user_id: String(raw.user_id || ""),
    username: String(raw.username || ""),
    display_name: String(raw.display_name || "未命名用户"),
    role: raw.role === "admin" || raw.role === "requester" ? raw.role : "executor",
    department: String(raw.department || "未分配部门"),
    title: String(raw.title || ""),
    last_login_at: raw.last_login_at ?? null,
  };
}

async function loadAuthOptions() {
  const payload = await fetchAuthOptions();
  state.authAccounts = Array.isArray(payload?.accounts) ? payload.accounts.map(normalizeUser).filter(Boolean) : [];
}

async function loadIdentity() {
  const payload = await fetchIdentity();
  state.currentUser = normalizeUser(payload?.current_user);
}

async function bootstrapAuth() {
  state.authBooting = true;
  state.authError = "";
  try {
    await loadAuthOptions();
    const statePayload = await fetchAuthState();
    state.loggedIn = !!statePayload?.logged_in;
    state.currentUser = normalizeUser(statePayload?.current_user);
    if (state.loggedIn) {
      await loadIdentity();
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    state.authError = `认证服务不可用：${message}`;
    state.loggedIn = false;
  } finally {
    state.authBooting = false;
  }
}

async function login(role, username, password) {
  state.authBusy = true;
  state.authError = "";
  try {
    const payload = await loginWithPassword({ role, username, password });
    state.loggedIn = !!payload?.logged_in;
    state.currentUser = normalizeUser(payload?.current_user);
    await loadIdentity();
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    state.authError = `登录失败：${message}`;
    return false;
  } finally {
    state.authBusy = false;
  }
}

async function register(payload) {
  state.authBusy = true;
  state.authError = "";
  try {
    const result = await registerAccount(payload);
    state.loggedIn = !!result?.logged_in;
    state.currentUser = normalizeUser(result?.current_user);
    await loadAuthOptions();
    await loadIdentity();
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    state.authError = `注册失败：${message}`;
    return false;
  } finally {
    state.authBusy = false;
  }
}

async function logout() {
  state.authBusy = true;
  state.authError = "";
  try {
    await logoutCurrentUser();
    state.loggedIn = false;
    state.currentUser = null;
    return true;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    state.authError = `退出失败：${message}`;
    return false;
  } finally {
    state.authBusy = false;
  }
}

export const useAuthStore = () => {
  return {
    state: readonly(state),
    bootstrapAuth,
    login,
    register,
    logout,
    loadAuthOptions
  };
};
