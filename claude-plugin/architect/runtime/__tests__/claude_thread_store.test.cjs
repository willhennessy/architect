/**
 * Unit tests for ClaudeThreadStore.
 *
 * Run with:
 *   cd claude-plugin/architect && npm test
 * Or:
 *   NODE_PATH=claude-plugin/architect/.data/node_modules \
 *     node --test claude-plugin/architect/runtime/__tests__/
 */

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const fsSync = require("node:fs");
const path = require("node:path");
const os = require("node:os");

const {
  ClaudeThreadStore,
  THREAD_SCHEMA_VERSION,
  claudeThreadsPath,
} = require("../architect_runtime.cjs");

// ---------------------------------------------------------------------------
// Test fixture: a temp output_root that mimics a project with architecture/
// ---------------------------------------------------------------------------

async function createFixture() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "claude-threads-test-"));
  await fs.mkdir(path.join(dir, "architecture"), { recursive: true });
  return dir;
}

async function cleanupFixture(dir) {
  if (!dir) return;
  await fs.rm(dir, { recursive: true, force: true });
}

// A minimal stub for the HTTP response object that the store writes SSE to.
// sendThreadEvent does two res.write() calls per event (event: line + data: line).
// We concatenate everything written and parse the buffer into discrete frames.
function fakeResponse() {
  return {
    buffer: "",
    write(chunk) { this.buffer += String(chunk); },
    get frames() { return parseSseFrames(this.buffer); },
  };
}

function parseSseFrames(buffer) {
  return buffer
    .split(/\n\n/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const lines = chunk.split("\n");
      const event = (lines.find((l) => l.startsWith("event: ")) || "").slice(7);
      const dataLine = lines.find((l) => l.startsWith("data: "));
      return {
        event,
        data: dataLine ? JSON.parse(dataLine.slice(6)) : null,
      };
    });
}

// ---------------------------------------------------------------------------
// snapshot
// ---------------------------------------------------------------------------

test("snapshot returns empty default for an output_root with no file", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const snap = await store.snapshot(dir);
    assert.equal(snap.schema_version, THREAD_SCHEMA_VERSION);
    assert.deepEqual(snap.threads, []);
  } finally {
    await cleanupFixture(dir);
  }
});

test("snapshot reads back what createThread wrote", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await store.createThread(dir, {
      view_id: "system-context",
      element_id: "rundler",
      target_label: "Rundler",
      body: "Single binary or split?",
    });
    const snap = await store.snapshot(dir);
    assert.equal(snap.threads.length, 1);
    assert.equal(snap.threads[0].view_id, "system-context");
    assert.equal(snap.threads[0].messages.length, 1);
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// createThread
// ---------------------------------------------------------------------------

test("createThread writes the JSON file at the expected path", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await store.createThread(dir, {
      view_id: "system-context",
      element_id: "rundler",
      target_label: "Rundler",
      body: "Hello?",
    });
    const filePath = claudeThreadsPath(dir);
    assert.ok(fsSync.existsSync(filePath), "claude-comments.json must exist");
    const raw = JSON.parse(await fs.readFile(filePath, "utf8"));
    assert.equal(raw.schema_version, THREAD_SCHEMA_VERSION);
    assert.equal(raw.threads.length, 1);
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread generates thr_ + msg_ prefixed ids", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread, message } = await store.createThread(dir, {
      view_id: "system-context",
      element_id: "rundler",
      target_label: "Rundler",
      body: "ping",
    });
    assert.match(thread.thread_id, /^thr_[0-9a-f]{10}$/);
    assert.match(message.id, /^msg_[0-9a-f]{10}$/);
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread defaults author to claude and status to open", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "system-context",
      element_id: "rundler",
      target_label: "Rundler",
      body: "test",
    });
    assert.equal(thread.status, "open");
    assert.equal(thread.messages[0].author, "claude");
    assert.equal(thread.resolved_at, null);
    assert.equal(thread.resolved_by, null);
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread rejects when view_id is missing", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.createThread(dir, { body: "no view" }),
      /view_id is required/
    );
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread rejects when body is missing", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.createThread(dir, { view_id: "x", element_id: "a" }),
      /body is required/
    );
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread rejects when both element_id and relationship_id are set", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.createThread(dir, {
        view_id: "x",
        element_id: "a",
        relationship_id: "b",
        body: "y",
      }),
      /mutually exclusive/
    );
  } finally {
    await cleanupFixture(dir);
  }
});

test("createThread rejects when output_root has no architecture/", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "no-arch-"));
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.createThread(dir, { view_id: "x", element_id: "a", body: "y" }),
      /must contain architecture/
    );
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// appendMessage
// ---------------------------------------------------------------------------

test("appendMessage appends in order and updates updated_at", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread: created } = await store.createThread(dir, {
      view_id: "v",
      element_id: "e",
      target_label: "E",
      body: "first",
    });
    const firstUpdatedAt = created.updated_at;
    // Force a measurable time difference: utcNowIso() trims milliseconds.
    await new Promise((r) => setTimeout(r, 1100));
    await store.appendMessage(dir, created.thread_id, { author: "user", body: "second" });
    await new Promise((r) => setTimeout(r, 1100));
    await store.appendMessage(dir, created.thread_id, { author: "claude", body: "third" });

    const snap = await store.snapshot(dir);
    const thread = snap.threads[0];
    assert.equal(thread.messages.length, 3);
    assert.deepEqual(
      thread.messages.map((m) => [m.author, m.body]),
      [["claude", "first"], ["user", "second"], ["claude", "third"]]
    );
    assert.notEqual(thread.updated_at, firstUpdatedAt, "updated_at must move forward");
  } finally {
    await cleanupFixture(dir);
  }
});

test("appendMessage rejects with THREAD_NOT_FOUND when thread does not exist", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.appendMessage(dir, "thr_does_not_exist", { author: "user", body: "x" }),
      (err) => err.code === "THREAD_NOT_FOUND"
    );
  } finally {
    await cleanupFixture(dir);
  }
});

test("appendMessage rejects with THREAD_NOT_OPEN once a thread is resolved", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "q",
    });
    await store.resolveThread(dir, thread.thread_id, { resolved_by: "claude" });
    await assert.rejects(
      store.appendMessage(dir, thread.thread_id, { author: "user", body: "late" }),
      (err) => err.code === "THREAD_NOT_OPEN"
    );
  } finally {
    await cleanupFixture(dir);
  }
});

test("appendMessage normalizes author to claude when input is anything but 'user'", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "q",
    });
    await store.appendMessage(dir, thread.thread_id, { author: "robot", body: "huh" });
    const snap = await store.snapshot(dir);
    assert.equal(snap.threads[0].messages.at(-1).author, "claude");
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// resolveThread
// ---------------------------------------------------------------------------

test("resolveThread flips status and stamps resolved_at/by", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "q",
    });
    await store.resolveThread(dir, thread.thread_id, { resolved_by: "user" });
    const snap = await store.snapshot(dir);
    const resolved = snap.threads[0];
    assert.equal(resolved.status, "resolved");
    assert.equal(resolved.resolved_by, "user");
    assert.ok(resolved.resolved_at, "resolved_at should be set");
  } finally {
    await cleanupFixture(dir);
  }
});

test("resolveThread rejects when thread does not exist", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    await assert.rejects(
      store.resolveThread(dir, "thr_nope", { resolved_by: "claude" }),
      (err) => err.code === "THREAD_NOT_FOUND"
    );
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// openThreads + threadSummary
// ---------------------------------------------------------------------------

test("openThreads excludes resolved threads", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const a = await store.createThread(dir, { view_id: "v", element_id: "a", target_label: "A", body: "q1" });
    const b = await store.createThread(dir, { view_id: "v", element_id: "b", target_label: "B", body: "q2" });
    await store.resolveThread(dir, a.thread.thread_id, { resolved_by: "claude" });
    const open = await store.openThreads(dir);
    assert.equal(open.length, 1);
    assert.equal(open[0].thread_id, b.thread.thread_id);
  } finally {
    await cleanupFixture(dir);
  }
});

test("threadSummary builds 'awaiting reply' lines for the requested thread ids", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "rundler", target_label: "Rundler", body: "q",
    });
    const lines = await store.threadSummary(dir, [thread.thread_id, "thr_missing"]);
    assert.equal(lines.length, 1, "missing thread ids are dropped");
    assert.match(lines[0], /Rundler/);
    assert.match(lines[0], /awaiting reply/);
  } finally {
    await cleanupFixture(dir);
  }
});

test("threadSummary returns empty array for empty input", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    assert.deepEqual(await store.threadSummary(dir, []), []);
    assert.deepEqual(await store.threadSummary(dir, null), []);
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// SSE subscribers
// ---------------------------------------------------------------------------

test("subscribe + createThread broadcasts a thread_created SSE frame", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const res = fakeResponse();
    store.subscribe(dir, res);
    await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "hello",
    });
    assert.equal(res.frames.length, 1);
    assert.equal(res.frames[0].event, "thread_created");
    assert.equal(res.frames[0].data.thread.messages[0].body, "hello");
  } finally {
    await cleanupFixture(dir);
  }
});

test("appendMessage broadcasts a message_appended frame with thread_id + message", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "hi",
    });
    const res = fakeResponse();
    store.subscribe(dir, res);
    await store.appendMessage(dir, thread.thread_id, { author: "user", body: "reply" });
    assert.equal(res.frames.length, 1);
    assert.equal(res.frames[0].event, "message_appended");
    assert.equal(res.frames[0].data.thread_id, thread.thread_id);
    assert.equal(res.frames[0].data.message.author, "user");
    assert.equal(res.frames[0].data.message.body, "reply");
  } finally {
    await cleanupFixture(dir);
  }
});

test("resolveThread broadcasts thread_resolved with resolved_by + resolved_at", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "hi",
    });
    const res = fakeResponse();
    store.subscribe(dir, res);
    await store.resolveThread(dir, thread.thread_id, { resolved_by: "claude" });
    assert.equal(res.frames.length, 1);
    assert.equal(res.frames[0].event, "thread_resolved");
    assert.equal(res.frames[0].data.thread_id, thread.thread_id);
    assert.equal(res.frames[0].data.resolved_by, "claude");
    assert.ok(res.frames[0].data.resolved_at);
  } finally {
    await cleanupFixture(dir);
  }
});

test("unsubscribe removes a response so it stops receiving events", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const res = fakeResponse();
    store.subscribe(dir, res);
    store.unsubscribe(dir, res);
    await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "hi",
    });
    assert.equal(res.frames.length, 0);
  } finally {
    await cleanupFixture(dir);
  }
});

test("subscribers from different output_roots do not cross-talk", async () => {
  const dirA = await createFixture();
  const dirB = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const resA = fakeResponse();
    const resB = fakeResponse();
    store.subscribe(dirA, resA);
    store.subscribe(dirB, resB);
    await store.createThread(dirA, {
      view_id: "v", element_id: "e", target_label: "E", body: "for A",
    });
    assert.equal(resA.frames.length, 1, "A subscriber should receive");
    assert.equal(resB.frames.length, 0, "B subscriber should NOT receive A's event");
  } finally {
    await cleanupFixture(dirA);
    await cleanupFixture(dirB);
  }
});

test("a throwing subscriber does not interrupt broadcast to other subscribers", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const throwingRes = {
      write() { throw new Error("subscriber boom"); },
    };
    const goodRes = fakeResponse();
    store.subscribe(dir, throwingRes);
    store.subscribe(dir, goodRes);
    await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "x",
    });
    assert.equal(goodRes.frames.length, 1, "good subscriber must still receive the event");
  } finally {
    await cleanupFixture(dir);
  }
});

// ---------------------------------------------------------------------------
// Concurrency: per-output-root write-lock chain
// ---------------------------------------------------------------------------

test("concurrent appendMessage calls do not lose any messages", async () => {
  const dir = await createFixture();
  try {
    const store = new ClaudeThreadStore();
    const { thread } = await store.createThread(dir, {
      view_id: "v", element_id: "e", target_label: "E", body: "root",
    });
    const N = 20;
    const ops = [];
    for (let i = 0; i < N; i++) {
      ops.push(store.appendMessage(dir, thread.thread_id, {
        author: i % 2 === 0 ? "user" : "claude",
        body: `msg-${i}`,
      }));
    }
    await Promise.all(ops);
    const snap = await store.snapshot(dir);
    assert.equal(snap.threads[0].messages.length, N + 1, "all concurrent messages should land");
    // Every message_id must be unique — no collisions.
    const ids = snap.threads[0].messages.map((m) => m.id);
    assert.equal(new Set(ids).size, ids.length, "message ids must be unique");
  } finally {
    await cleanupFixture(dir);
  }
});

test("concurrent createThread + appendMessage interleave safely on disk", async () => {
  const dirs = await Promise.all([createFixture(), createFixture()]);
  try {
    const store = new ClaudeThreadStore();
    // Create one thread on each output_root, then concurrently append.
    const created = await Promise.all(dirs.map((d) =>
      store.createThread(d, { view_id: "v", element_id: "e", target_label: "E", body: "root" })
    ));
    const ops = [];
    for (let i = 0; i < 10; i++) {
      ops.push(store.appendMessage(dirs[0], created[0].thread.thread_id, { author: "user", body: `a-${i}` }));
      ops.push(store.appendMessage(dirs[1], created[1].thread.thread_id, { author: "claude", body: `b-${i}` }));
    }
    await Promise.all(ops);
    const [snapA, snapB] = await Promise.all(dirs.map((d) => store.snapshot(d)));
    assert.equal(snapA.threads[0].messages.length, 11);
    assert.equal(snapB.threads[0].messages.length, 11);
  } finally {
    await Promise.all(dirs.map(cleanupFixture));
  }
});
