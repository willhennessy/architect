/**
 * Integration tests for the /claude-threads* HTTP routes.
 *
 * Spins up the bridge in-process on an ephemeral port (we use NEW ARCHITECT_BRIDGE_PORT
 * per worker) and exercises each route via fetch(). The MCP transport is never
 * connected — we only care about the HTTP surface here.
 */

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const os = require("node:os");

const { requestHandler } = require("../architect_runtime.cjs");

// ---------------------------------------------------------------------------
// Server helpers
// ---------------------------------------------------------------------------

async function startServer() {
  return await new Promise((resolve, reject) => {
    const server = http.createServer(requestHandler(null));
    server.removeAllListeners("request");
    server.on("request", requestHandler(server));
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { address, port } = server.address();
      resolve({ server, baseUrl: `http://${address}:${port}` });
    });
  });
}

async function stopServer(server) {
  if (!server) return;
  await new Promise((resolve) => server.close(resolve));
}

async function createFixture() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "http-routes-test-"));
  await fs.mkdir(path.join(dir, "architecture"), { recursive: true });
  return dir;
}

async function cleanupFixture(dir) {
  if (!dir) return;
  await fs.rm(dir, { recursive: true, force: true });
}

async function postJson(baseUrl, urlPath, body) {
  const res = await fetch(baseUrl + urlPath, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch (_err) { /* leave null */ }
  return { status: res.status, json, text };
}

async function getJson(baseUrl, urlPath) {
  const res = await fetch(baseUrl + urlPath);
  const text = await res.text();
  let json = null;
  try { json = JSON.parse(text); } catch (_err) { /* leave null */ }
  return { status: res.status, json, text };
}

// ---------------------------------------------------------------------------
// GET /health (sanity)
// ---------------------------------------------------------------------------

test("GET /health returns ok and the architect-comments name", async (t) => {
  const { server, baseUrl } = await startServer();
  t.after(() => stopServer(server));
  const { status, json } = await getJson(baseUrl, "/health");
  assert.equal(status, 200);
  assert.equal(json.ok, true);
  assert.equal(json.name, "architect-comments");
});

// ---------------------------------------------------------------------------
// GET /claude-threads
// ---------------------------------------------------------------------------

test("GET /claude-threads requires output_root", async (t) => {
  const { server, baseUrl } = await startServer();
  t.after(() => stopServer(server));
  const { status, json } = await getJson(baseUrl, "/claude-threads");
  assert.equal(status, 400);
  assert.match(json.error, /output_root is required/);
});

test("GET /claude-threads returns empty snapshot for a fresh output_root", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const { status, json } = await getJson(baseUrl, `/claude-threads?output_root=${encodeURIComponent(dir)}`);
  assert.equal(status, 200);
  assert.deepEqual(json.threads, []);
});

// ---------------------------------------------------------------------------
// POST /claude-threads
// ---------------------------------------------------------------------------

test("POST /claude-threads creates a thread and returns 201", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const { status, json } = await postJson(baseUrl, "/claude-threads", {
    output_root: dir,
    view_id: "system-context",
    element_id: "rundler",
    target_label: "Rundler",
    body: "Single binary or split?",
    diagram_revision_id: "rev1",
  });
  assert.equal(status, 201);
  assert.match(json.thread.thread_id, /^thr_/);
  assert.equal(json.thread.status, "open");
  assert.equal(json.thread.messages[0].body, "Single binary or split?");
  assert.equal(json.thread.messages[0].author, "claude");
  assert.equal(json.message.id, json.thread.messages[0].id);

  // File on disk reflects the create.
  const filePath = path.join(dir, "architecture", ".out", "claude-comments.json");
  assert.ok(fsSync.existsSync(filePath));
  const raw = JSON.parse(await fs.readFile(filePath, "utf8"));
  assert.equal(raw.threads.length, 1);
});

test("POST /claude-threads rejects missing output_root", async (t) => {
  const { server, baseUrl } = await startServer();
  t.after(() => stopServer(server));
  const { status, json } = await postJson(baseUrl, "/claude-threads", {
    view_id: "x", element_id: "y", body: "z",
  });
  assert.equal(status, 400);
  assert.match(json.error, /output_root is required/);
});

test("POST /claude-threads rejects when output_root has no architecture/", async (t) => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "no-arch-route-"));
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });
  const { status, json } = await postJson(baseUrl, "/claude-threads", {
    output_root: dir,
    view_id: "x",
    element_id: "y",
    body: "z",
  });
  assert.equal(status, 400);
  assert.match(json.error, /must contain architecture/);
});

// ---------------------------------------------------------------------------
// POST /claude-threads/:id/messages
// ---------------------------------------------------------------------------

async function seedThread(baseUrl, dir, overrides = {}) {
  const { json } = await postJson(baseUrl, "/claude-threads", {
    output_root: dir,
    view_id: "system-context",
    element_id: "rundler",
    target_label: "Rundler",
    body: "root question",
    diagram_revision_id: "rev1",
    ...overrides,
  });
  return json.thread;
}

test("POST /claude-threads/:id/messages appends a message", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const thread = await seedThread(baseUrl, dir);
  const { status, json } = await postJson(baseUrl, `/claude-threads/${thread.thread_id}/messages`, {
    output_root: dir,
    author: "user",
    body: "got it",
  });
  assert.equal(status, 200);
  assert.equal(json.thread.messages.length, 2);
  assert.equal(json.thread.messages[1].author, "user");
  assert.equal(json.thread.messages[1].body, "got it");
});

test("POST /claude-threads/:id/messages returns 404 for unknown thread", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const { status, json } = await postJson(baseUrl, "/claude-threads/thr_nope/messages", {
    output_root: dir, author: "user", body: "x",
  });
  assert.equal(status, 404);
  assert.match(json.error, /thread not found/);
});

test("POST /claude-threads/:id/messages 400s on a resolved thread", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const thread = await seedThread(baseUrl, dir);
  await postJson(baseUrl, `/claude-threads/${thread.thread_id}/resolve`, {
    output_root: dir, resolved_by: "claude",
  });
  const { status, json } = await postJson(baseUrl, `/claude-threads/${thread.thread_id}/messages`, {
    output_root: dir, author: "user", body: "late",
  });
  assert.equal(status, 400);
  assert.match(json.error, /not open/);
});

// ---------------------------------------------------------------------------
// POST /claude-threads/:id/resolve
// ---------------------------------------------------------------------------

test("POST /claude-threads/:id/resolve flips status and stamps resolved fields", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  const thread = await seedThread(baseUrl, dir);
  const { status, json } = await postJson(baseUrl, `/claude-threads/${thread.thread_id}/resolve`, {
    output_root: dir, resolved_by: "user",
  });
  assert.equal(status, 200);
  assert.equal(json.thread.status, "resolved");
  assert.equal(json.thread.resolved_by, "user");
  assert.ok(json.thread.resolved_at);
});

test("POST /claude-threads/:id/resolve returns 404 for unknown thread", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });
  const { status } = await postJson(baseUrl, "/claude-threads/thr_nope/resolve", {
    output_root: dir, resolved_by: "claude",
  });
  assert.equal(status, 404);
});

// ---------------------------------------------------------------------------
// GET /claude-threads/events (SSE)
// ---------------------------------------------------------------------------

function consumeSseUntil(baseUrl, urlPath, frameCount, timeoutMs = 2500) {
  return new Promise((resolve, reject) => {
    const url = new URL(baseUrl + urlPath);
    const req = http.request({
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: "GET",
      headers: { Accept: "text/event-stream" },
    }, (res) => {
      let buf = "";
      const timer = setTimeout(() => {
        req.destroy();
        reject(new Error(`timed out waiting for ${frameCount} SSE frames; got: ${buf.slice(0, 200)}`));
      }, timeoutMs);
      res.setEncoding("utf8");
      res.on("data", (chunk) => {
        buf += chunk;
        const frames = parseFrames(buf);
        if (frames.length >= frameCount) {
          clearTimeout(timer);
          req.destroy();
          resolve(frames.slice(0, frameCount));
        }
      });
      res.on("error", (err) => {
        clearTimeout(timer);
        reject(err);
      });
    });
    req.on("error", (err) => {
      // EventSource-style disconnect after we got what we wanted is fine.
      if (err && err.code !== "ECONNRESET") reject(err);
    });
    req.end();
  });
}

function parseFrames(buffer) {
  // SSE frames are terminated by a blank line. We must NOT count a frame
  // until we've seen its terminator, otherwise a chunk split between the
  // event: line and the data: line produces a half-parsed frame.
  if (!buffer.endsWith("\n\n")) {
    // Drop any trailing incomplete frame.
    const lastTerminator = buffer.lastIndexOf("\n\n");
    if (lastTerminator === -1) return [];
    buffer = buffer.slice(0, lastTerminator + 2);
  }
  return buffer
    .split(/\n\n/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .filter((chunk) => chunk.startsWith("event:") && chunk.includes("\ndata: "))
    .map((chunk) => {
      const lines = chunk.split("\n");
      const event = (lines.find((l) => l.startsWith("event: ")) || "").slice(7);
      const dataLine = lines.find((l) => l.startsWith("data: "));
      let data = null;
      try { data = JSON.parse(dataLine.slice(6)); } catch (_err) { /* ignore */ }
      return { event, data };
    });
}

test("GET /claude-threads/events streams initial snapshot then live events", async (t) => {
  const dir = await createFixture();
  const { server, baseUrl } = await startServer();
  t.after(async () => {
    await stopServer(server);
    await cleanupFixture(dir);
  });

  // Seed one thread before subscribing so the initial snapshot has content.
  const thread = await seedThread(baseUrl, dir);

  // Subscribe, then post a new message and resolve — collect 3 frames
  // (snapshot + message_appended + thread_resolved).
  const framesPromise = consumeSseUntil(
    baseUrl,
    `/claude-threads/events?output_root=${encodeURIComponent(dir)}`,
    3
  );

  // Wait briefly so the subscriber is registered before we mutate.
  await new Promise((r) => setTimeout(r, 75));
  await postJson(baseUrl, `/claude-threads/${thread.thread_id}/messages`, {
    output_root: dir, author: "user", body: "reply",
  });
  await postJson(baseUrl, `/claude-threads/${thread.thread_id}/resolve`, {
    output_root: dir, resolved_by: "claude",
  });

  const frames = await framesPromise;
  assert.equal(frames[0].event, "snapshot");
  assert.equal(frames[0].data.threads.length, 1);
  assert.equal(frames[1].event, "message_appended");
  assert.equal(frames[1].data.message.body, "reply");
  assert.equal(frames[2].event, "thread_resolved");
  assert.equal(frames[2].data.resolved_by, "claude");
});

// ---------------------------------------------------------------------------
// 404 fallback
// ---------------------------------------------------------------------------

test("unknown path returns 404 JSON", async (t) => {
  const { server, baseUrl } = await startServer();
  t.after(() => stopServer(server));
  const { status, json } = await getJson(baseUrl, "/not-a-real-route");
  assert.equal(status, 404);
  assert.equal(json.error, "not found");
});
