---
name: page-agent-codex
description: Integrate Alibaba Page Agent into existing web applications with safe key handling, minimal runtime setup, and deterministic validation. Use when users ask to add page-agent, migrate between CDN and npm integration, debug runtime issues, or build a quick in-page GUI-agent demo.
---

# Page Agent Codex

## Overview

Integrate `page-agent` into a web app without rewriting backend services.
Choose the appropriate integration mode, implement minimal runnable code, and verify behavior with repeatable checks.

## Workflow

1. Identify the app stack and runtime boundary.
2. Choose integration mode (`npm` or `CDN`).
3. Add initialization code with explicit model endpoint config.
4. Validate startup and first command execution.
5. Diagnose failures using the troubleshooting checklist.

## Determine Integration Mode

Use `npm` when the project already has a build pipeline (Vite/Webpack/Next/Nuxt/Vue CLI).
Use `CDN` when the goal is a fast prototype on a plain HTML page.
Prefer `npm` in production code to keep dependency versions controlled.

## Implement NPM Mode

1. Install the package:
```bash
npm install page-agent
```
2. Create a dedicated initializer module (for example `src/lib/pageAgent.ts`).
3. Inject runtime config through environment variables, not hardcoded keys.
4. Export a factory function and call it from a user-triggered action.
5. Run a first command such as `Click the login button` and verify action trace.

## Implement CDN Mode

1. Add the IIFE script URL from Page Agent release docs.
2. Initialize the global constructor with model/baseURL/apiKey/language.
3. Gate the initializer behind a visible button for manual testing.
4. Validate one read action and one click action.
5. Replace prototype key material before sharing code.

## Validate Integration

1. Confirm package or script version is pinned.
2. Confirm key source is runtime config (`.env` or secure secret source).
3. Confirm agent can read DOM and execute a single deterministic action.
4. Confirm error paths are visible in console and surfaced to users.
5. Confirm fallback behavior when LLM endpoint is unavailable.

## Troubleshoot Quickly

If constructor import fails, verify bundler module format and import path.
If all actions fail silently, verify browser console for CORS or invalid API key errors.
If the agent clicks wrong elements, reduce prompt ambiguity and test on stable DOM nodes.
If response latency is high, lower task scope to one action per command and retry.

## References

Read `references/page-agent-integration.md` for framework-specific starter snippets and validation commands.
