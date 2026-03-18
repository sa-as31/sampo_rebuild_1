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

export async function runInference(payload) {
  const response = await fetch("/api/run-demo", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseJsonOrThrow(response);
}

