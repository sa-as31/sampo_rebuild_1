# Page Agent Integration Reference

## 1. NPM Mode (Recommended)

Install:

```bash
npm install page-agent
```

Create initializer:

```ts
import { PageAgent } from "page-agent";

export function createPageAgent() {
  return new PageAgent({
    model: import.meta.env.VITE_PAGE_AGENT_MODEL || "qwen3.5-plus",
    baseURL: import.meta.env.VITE_PAGE_AGENT_BASE_URL || "",
    apiKey: import.meta.env.VITE_PAGE_AGENT_API_KEY || "",
    language: "zh-CN",
  });
}
```

Trigger action:

```ts
const agent = createPageAgent();
await agent.execute("Click the login button");
```

## 2. CDN Mode (Prototype)

Use CDN script in HTML:

```html
<script src="https://cdn.jsdelivr.net/npm/page-agent@1.5.11/dist/iife/page-agent.demo.js" crossorigin="true"></script>
```

Runtime setup:

```js
const agent = new window.PageAgent({
  model: "qwen3.5-plus",
  baseURL: "https://dashscope.aliyuncs.com/compatible-mode/v1",
  apiKey: "YOUR_API_KEY",
  language: "zh-CN",
});

await agent.execute("Click the login button");
```

## 3. Validation Checklist

1. Ensure `page-agent` version is pinned.
2. Ensure API key is loaded from runtime config for production.
3. Ensure one read-only command works before click/input commands.
4. Ensure browser console logs are captured for failure analysis.
5. Ensure fallback behavior exists when API call fails.

## 4. Common Failures

- `Module not found`: run install in correct workspace and check lockfile update.
- `401/403`: API key invalid or endpoint mismatch.
- `CORS blocked`: endpoint does not allow browser-origin requests.
- No visible action: command too broad; rewrite as one deterministic step.
