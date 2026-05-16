# Plugin runtime tests

Three suites covering the bidirectional comment thread feature in
`architect_runtime.cjs` plus the sidebar helpers in `diagram-app.html`.

## Run

From `claude-plugin/architect/`:

```bash
npm install   # one-time: pulls @modelcontextprotocol/sdk
npm test
```

`npm test` shells out to `node --test runtime/__tests__/*.test.cjs` (Node's
built-in test runner — no Jest, no Mocha, no extra deps).

## What's covered

| File | Suite | Covers |
|---|---|---|
| `claude_thread_store.test.cjs` | unit | ClaudeThreadStore: create / append / resolve, persistence layout, ID format, SSE broadcast + subscriber lifecycle, concurrency safety under the per-output-root write-lock chain. |
| `http_routes.test.cjs` | integration | The `/claude-threads*` HTTP routes end-to-end. Spins the bridge up in-process on an ephemeral port, fires real HTTP requests, asserts JSON + SSE delivery. |
| `sidebar_helpers.test.cjs` | unit | Pure helpers in `diagram-app.html`: `formatRelativeTime`, `colorToneForAuthorId`, `avatarLetter`, `latestMessageAuthor`, `threadGroupKey`, `threadActivityTime`. Function source is extracted from the template at test time and run in a VM context, so the tests cover the actual shipped code. |

## What's NOT covered

- The MCP tool wiring (`setRequestHandler(CallToolRequestSchema, ...)`). The
  tool handlers just shape the request and POST to the bridge — covered
  indirectly by the HTTP integration tests and by the live MCP `tools/list`
  smoke test in the manual run instructions.
- DOM rendering inside `diagram-app.html`. Use the `/browse` skill for visual
  smoke; jsdom adds friction for low signal here.
- The Python `comment_feedback_bridge.py` parallel implementation. It's the
  dev harness, not the production path; the Node runtime is what ships.

## Adding tests

- Pure functions in the template → add to `sidebar_helpers.test.cjs` and bump
  the `helpers` list in `buildSandbox()` if you need a new function in scope.
- New runtime methods → add to `claude_thread_store.test.cjs`.
- New HTTP routes → add to `http_routes.test.cjs`.
