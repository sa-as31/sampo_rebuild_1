async function parseJsonOrThrow(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

export async function fetchDefaults() {
  const response = await fetch("/api/defaults");
  return parseJsonOrThrow(response);
}

export async function fetchAuthState() {
  const response = await fetch("/api/auth/state");
  return parseJsonOrThrow(response);
}

export async function fetchAuthOptions() {
  const response = await fetch("/api/auth/options");
  return parseJsonOrThrow(response);
}

export async function loginWithPassword(payload) {
  const response = await fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

export async function registerAccount(payload) {
  const response = await fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

export async function logoutCurrentUser() {
  const response = await fetch("/api/auth/logout", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  return parseJsonOrThrow(response);
}

export async function runInference(payload) {
  const response = await fetch("/api/run-demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

export async function createOpsTask(payload) {
  const response = await fetch("/api/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

export async function controlOpsTask(taskId, action, extra = {}) {
  const response = await fetch(`/api/tasks/${taskId}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...extra }),
  });
  return parseJsonOrThrow(response);
}

export async function getOpsTask(taskId) {
  const response = await fetch(`/api/tasks/${taskId}`);
  return parseJsonOrThrow(response);
}

export async function fetchOpsAlerts(taskId, limit = 20) {
  const response = await fetch(`/api/tasks/${taskId}/alerts?limit=${limit}`);
  return parseJsonOrThrow(response);
}

export function connectOpsTaskEvents(taskId, afterSeq = 0) {
  return new EventSource(`/api/tasks/${taskId}/events?after=${afterSeq}`);
}

export async function fetchOpsTasks(limit = 60) {
  const response = await fetch(`/api/tasks?limit=${limit}`);
  return parseJsonOrThrow(response);
}

export async function fetchDashboardSummary() {
  const response = await fetch("/api/dashboard/summary");
  return parseJsonOrThrow(response);
}

export async function fetchTaskReplay(taskId) {
  const response = await fetch(`/api/tasks/${taskId}/replay`);
  return parseJsonOrThrow(response);
}

export async function fetchTaskFeedback(taskId, limit = 20) {
  const response = await fetch(`/api/tasks/${taskId}/feedback?limit=${limit}`);
  return parseJsonOrThrow(response);
}

export async function submitTaskFeedback(taskId, payload) {
  const response = await fetch(`/api/tasks/${taskId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

export async function fetchIdentity() {
  const response = await fetch("/api/identity");
  return parseJsonOrThrow(response);
}

export async function switchIdentity(userId) {
  const response = await fetch("/api/identity/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId }),
  });
  return parseJsonOrThrow(response);
}
