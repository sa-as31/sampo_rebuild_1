const STORAGE_KEY = "OPS_PARAM_TEMPLATES_V1";
const DEFAULT_TASK_TICK_MS = 600;

function parseTemplates(raw) {
  if (!raw) return [];
  try {
    const data = JSON.parse(raw);
    if (!Array.isArray(data)) return [];
    return data
      .map((item) => ({
        id: String(item.id || cryptoRandomId()),
        name: String(item.name || "未命名模板"),
        template: normalizeTemplate(item.template),
        source: normalizeSource(item.source),
        mission_name: String(item.mission_name || "enterprise_batch_demo"),
        num_agents: toInt(item.num_agents, 16, 1, 128),
        max_frames: toInt(item.max_frames, 64, 4, 2048),
        tick_ms: toInt(item.tick_ms, DEFAULT_TASK_TICK_MS, 120, 2000),
        created_at: Number(item.created_at || Date.now()),
      }))
      .sort((a, b) => b.created_at - a.created_at);
  } catch {
    return [];
  }
}

function toInt(value, fallback, min, max) {
  const parsed = Number.parseInt(value, 10);
  if (Number.isNaN(parsed)) return fallback;
  return Math.min(max, Math.max(min, parsed));
}

function normalizeTemplate(value) {
  return ["warehouse", "campus", "emergency"].includes(String(value)) ? String(value) : "warehouse";
}

function normalizeSource(value) {
  return String(value) === "model" ? "model" : "sample";
}

function cryptoRandomId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) return crypto.randomUUID().slice(0, 10);
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

function persist(templates) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
  window.dispatchEvent(new CustomEvent("ops-template-updated"));
}

export function loadOpsTemplates() {
  return parseTemplates(window.localStorage.getItem(STORAGE_KEY));
}

export function upsertOpsTemplate(template) {
  const current = loadOpsTemplates();
  const id = String(template.id || cryptoRandomId());
  const nextItem = {
    id,
    name: String(template.name || "未命名模板"),
    template: normalizeTemplate(template.template),
    source: normalizeSource(template.source),
    mission_name: String(template.mission_name || "enterprise_batch_demo"),
    num_agents: toInt(template.num_agents, 16, 1, 128),
    max_frames: toInt(template.max_frames, 64, 4, 2048),
    tick_ms: toInt(template.tick_ms, DEFAULT_TASK_TICK_MS, 120, 2000),
    created_at: Number(template.created_at || Date.now()),
  };

  const index = current.findIndex((item) => item.id === id);
  if (index >= 0) current[index] = nextItem;
  else current.unshift(nextItem);
  persist(current);
  return nextItem;
}

export function deleteOpsTemplate(templateId) {
  const current = loadOpsTemplates();
  const next = current.filter((item) => item.id !== templateId);
  persist(next);
}

export { STORAGE_KEY as OPS_TEMPLATE_STORAGE_KEY };
