import { reactive, ref, computed } from 'vue';
import { fetchOpsTasks } from '../services/api';

const state = reactive({
  tasks: [],
  status: '任务中心初始化中...',
});

let pollTimer = null;

async function loadTasks() {
  try {
    const payload = await fetchOpsTasks();
    if (payload?.tasks && Array.isArray(payload.tasks)) {
      state.tasks = payload.tasks;
      state.status = "";
    }
  } catch (error) {
    state.status = `加载任务失败: ${error instanceof Error ? error.message : "未知错误"}`;
  }
}

function startPolling(interval = 3000) {
  if (!pollTimer) {
    pollTimer = setInterval(loadTasks, interval);
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

export const useTaskStore = () => {
  return {
    state,
    loadTasks,
    startPolling,
    stopPolling,
  };
};
