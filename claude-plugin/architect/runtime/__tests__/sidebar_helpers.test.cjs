/**
 * Unit tests for pure-ish sidebar helpers in diagram-app.html.
 *
 * We extract the function source directly from the template via regex and run
 * the extracted code in an isolated VM context. This means tests cover the
 * actual JS that ships in the diagram, with no duplication.
 *
 * Tests live in __tests__/ but the source under test lives in
 * skills/architect-diagram/templates/diagram-app.html.
 */

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const TEMPLATE = fs.readFileSync(
  path.resolve(__dirname, "../../../../skills/architect-diagram/templates/diagram-app.html"),
  "utf8"
);

/**
 * Extract a top-level `function name(...) {...}` body from the template by
 * counting braces. The template is one large IIFE, so we cheat with brace
 * balancing rather than a real parser.
 */
function extractFunction(name) {
  const re = new RegExp(`function\\s+${name}\\s*\\([^)]*\\)\\s*\\{`);
  const match = TEMPLATE.match(re);
  if (!match) throw new Error(`function ${name}() not found in template`);
  const start = match.index;
  const openBrace = TEMPLATE.indexOf("{", start);
  let depth = 0;
  for (let i = openBrace; i < TEMPLATE.length; i++) {
    const c = TEMPLATE[i];
    if (c === "{") depth++;
    else if (c === "}") {
      depth--;
      if (depth === 0) return TEMPLATE.slice(start, i + 1);
    }
  }
  throw new Error(`unterminated function ${name}()`);
}

function extractConst(name) {
  const re = new RegExp(`const\\s+${name}\\s*=\\s*\\[[^\\]]*\\];`);
  const match = TEMPLATE.match(re);
  if (!match) throw new Error(`const ${name} not found in template`);
  return match[0];
}

// Build a sandbox preloaded with the helpers we want to exercise.
function buildSandbox() {
  const helpers = [
    "function formatMessageTimestamp(value){return value?new Date(value).toString():''}", // stub to satisfy callers
    extractFunction("formatRelativeTime"),
    extractConst("AVATAR_TONES"),
    extractFunction("colorToneForAuthorId"),
    extractFunction("avatarLetter"),
    extractFunction("latestMessageAuthor"),
    extractFunction("threadGroupKey"),
    extractFunction("threadActivityTime"),
  ].join("\n");

  const ctx = { module: { exports: {} } };
  vm.createContext(ctx);
  vm.runInContext(
    helpers +
      `\n;module.exports = { formatRelativeTime, colorToneForAuthorId, avatarLetter, latestMessageAuthor, threadGroupKey, threadActivityTime, AVATAR_TONES };`,
    ctx
  );
  return ctx.module.exports;
}

const H = buildSandbox();

// ---------------------------------------------------------------------------
// formatRelativeTime
// ---------------------------------------------------------------------------

function nowMinus(ms) { return new Date(Date.now() - ms).toISOString(); }

test("formatRelativeTime: under 60s → 'just now'", () => {
  assert.equal(H.formatRelativeTime(nowMinus(5 * 1000)), "just now");
  assert.equal(H.formatRelativeTime(nowMinus(45 * 1000)), "just now");
});

test("formatRelativeTime: under 60min → '{n}m'", () => {
  assert.equal(H.formatRelativeTime(nowMinus(2 * 60 * 1000)), "2m");
  assert.equal(H.formatRelativeTime(nowMinus(59 * 60 * 1000)), "59m");
});

test("formatRelativeTime: under 24h → '{n}h'", () => {
  assert.equal(H.formatRelativeTime(nowMinus(3 * 3600 * 1000)), "3h");
  assert.equal(H.formatRelativeTime(nowMinus(23 * 3600 * 1000)), "23h");
});

test("formatRelativeTime: under 7d → '{n}d'", () => {
  assert.equal(H.formatRelativeTime(nowMinus(2 * 86400 * 1000)), "2d");
  assert.equal(H.formatRelativeTime(nowMinus(6 * 86400 * 1000)), "6d");
});

test("formatRelativeTime: older than 7d falls back to short month-day", () => {
  const formatted = H.formatRelativeTime(nowMinus(30 * 86400 * 1000));
  assert.match(formatted, /^[A-Z][a-z]{2,4} \d{1,2}$/, `got: ${formatted}`);
});

test("formatRelativeTime: empty / invalid input returns empty string", () => {
  assert.equal(H.formatRelativeTime(""), "");
  assert.equal(H.formatRelativeTime(null), "");
  assert.equal(H.formatRelativeTime(undefined), "");
  assert.equal(H.formatRelativeTime("not-a-date"), "");
});

// ---------------------------------------------------------------------------
// colorToneForAuthorId
// ---------------------------------------------------------------------------

test("colorToneForAuthorId returns one of the 5 palette tones", () => {
  const tones = new Set(H.AVATAR_TONES);
  for (const id of ["user", "claude", "alice", "bob", "carol", "dan", "eve"]) {
    const tone = H.colorToneForAuthorId(id);
    assert.ok(tones.has(tone), `${id} → ${tone} should be in palette`);
  }
});

test("colorToneForAuthorId is deterministic per id", () => {
  for (const id of ["user", "claude", "alice", "12345"]) {
    assert.equal(H.colorToneForAuthorId(id), H.colorToneForAuthorId(id));
  }
});

test("colorToneForAuthorId user vs claude are different tones", () => {
  // (Distinct colors matter for the avatar — would catch a regression in
  // the hash function that accidentally collapsed them.)
  assert.notEqual(H.colorToneForAuthorId("user"), H.colorToneForAuthorId("claude"));
});

// ---------------------------------------------------------------------------
// avatarLetter
// ---------------------------------------------------------------------------

test("avatarLetter returns first uppercase code-point", () => {
  assert.equal(H.avatarLetter("Maya Reyes"), "M");
  assert.equal(H.avatarLetter("you"), "Y");
  assert.equal(H.avatarLetter("Claude"), "C");
  assert.equal(H.avatarLetter("alice"), "A");
});

test("avatarLetter returns '?' for empty / whitespace input", () => {
  assert.equal(H.avatarLetter(""), "?");
  assert.equal(H.avatarLetter("   "), "?");
  assert.equal(H.avatarLetter(null), "?");
  assert.equal(H.avatarLetter(undefined), "?");
});

// ---------------------------------------------------------------------------
// latestMessageAuthor
// ---------------------------------------------------------------------------

test("latestMessageAuthor returns 'claude' for a thread with no messages", () => {
  assert.equal(H.latestMessageAuthor({ messages: [] }), "claude");
  assert.equal(H.latestMessageAuthor(null), "claude");
  assert.equal(H.latestMessageAuthor(undefined), "claude");
});

test("latestMessageAuthor returns the author of the last message", () => {
  const thread = {
    messages: [
      { author: "claude", body: "q1" },
      { author: "user", body: "r1" },
      { author: "claude", body: "q2" },
    ],
  };
  assert.equal(H.latestMessageAuthor(thread), "claude");
  thread.messages.push({ author: "user", body: "r2" });
  assert.equal(H.latestMessageAuthor(thread), "user");
});

test("latestMessageAuthor normalizes anything-but-user to 'claude'", () => {
  assert.equal(H.latestMessageAuthor({ messages: [{ author: "robot" }] }), "claude");
  assert.equal(H.latestMessageAuthor({ messages: [{ author: "" }] }), "claude");
});

// ---------------------------------------------------------------------------
// threadGroupKey
// ---------------------------------------------------------------------------

test("threadGroupKey prefers element_id, then relationship_id, then view_id", () => {
  assert.equal(H.threadGroupKey({ element_id: "rundler" }), "el:rundler");
  assert.equal(H.threadGroupKey({ relationship_id: "rel1" }), "rel:rel1");
  assert.equal(H.threadGroupKey({ view_id: "system-context" }), "view:system-context");
  assert.equal(H.threadGroupKey({}), "view:__");
  assert.equal(H.threadGroupKey(null), "view:__");
});

test("threadGroupKey: element_id wins over relationship_id when both set", () => {
  assert.equal(H.threadGroupKey({ element_id: "a", relationship_id: "b" }), "el:a");
});

// ---------------------------------------------------------------------------
// threadActivityTime
// ---------------------------------------------------------------------------

test("threadActivityTime returns 0 for empty / null thread", () => {
  assert.equal(H.threadActivityTime({ messages: [] }), 0);
  assert.equal(H.threadActivityTime(null), 0);
  assert.equal(H.threadActivityTime(undefined), 0);
});

test("threadActivityTime returns the last message's createdAt as ms", () => {
  const t = new Date("2026-05-13T12:00:00Z").getTime();
  const thread = {
    messages: [
      { author: "claude", created_at: "2026-05-13T10:00:00Z" },
      { author: "user", created_at: "2026-05-13T12:00:00Z" },
    ],
  };
  assert.equal(H.threadActivityTime(thread), t);
});
