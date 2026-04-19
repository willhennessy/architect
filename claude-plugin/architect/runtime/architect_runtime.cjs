#!/usr/bin/env node

const fs = require("node:fs");
const fsp = require("node:fs/promises");
const http = require("node:http");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const { randomUUID, createHash } = require("node:crypto");
const { URL } = require("node:url");

const { Server } = require("@modelcontextprotocol/sdk/server/index.js");
const { StdioServerTransport } = require("@modelcontextprotocol/sdk/server/stdio.js");
const { CallToolRequestSchema, ListToolsRequestSchema } = require("@modelcontextprotocol/sdk/types.js");

const pluginRoot = process.env.CLAUDE_PLUGIN_ROOT || path.resolve(__dirname, "..");
const pluginData = process.env.CLAUDE_PLUGIN_DATA || path.join(pluginRoot, ".data");
const bind = process.env.ARCHITECT_BRIDGE_BIND || "127.0.0.1";
const port = Number.parseInt(process.env.ARCHITECT_BRIDGE_PORT || "8765", 10);
const name = "architect-comments";
const pythonFromVenv = path.join(pluginData, "venv", "bin", "python");
const pythonBin = fs.existsSync(pythonFromVenv) ? pythonFromVenv : (process.env.PYTHON || "python3");
const feedbackValidatorScript = path.join(pluginRoot, "scripts", "validate-feedback-update.py");
const svgFragmentScript = path.join(pluginRoot, "scripts", "generate-svg-fragments.py");
const renderDiagramScript = path.join(pluginRoot, "scripts", "render-diagram-html.py");
const htmlValidatorScript = path.join(pluginRoot, "scripts", "validate-diagram-html.sh");
const jobIndexPath = path.join(pluginData, "job-index.json");
const channelAckTimeoutMs = Number.parseInt(process.env.ARCHITECT_CHANNEL_ACK_TIMEOUT_MS || "20000", 10);
const channelAckTimeoutMessage = "The agent did not acknowledge this update. Confirm Claude is running with the installed Architect plugin channel enabled, then submit again.";
const runtimeDirName = ".out";

const STATE_ORDER = [
  "received",
  "acknowledged",
  "analyzing",
  "fast_patch_running",
  "fast_patch_ready",
  "slow_patch_running",
  "completed",
  "failed",
  "blocked",
];

const TERMINAL_STATES = new Set(["completed", "failed", "blocked"]);

const STATUS_DEFAULTS = {
  acknowledged: {
    needs_refresh: false,
    has_fast_result: false,
    has_final_result: false,
    refresh_hint: "",
  },
  analyzing: {
    needs_refresh: false,
    has_fast_result: false,
    has_final_result: false,
    refresh_hint: "",
  },
  fast_patch_running: {
    needs_refresh: false,
    has_fast_result: false,
    has_final_result: false,
    refresh_hint: "",
  },
  fast_patch_ready: {
    needs_refresh: true,
    has_fast_result: true,
    has_final_result: false,
    refresh_hint: "Refresh the page to see updates.",
  },
  slow_patch_running: {
    needs_refresh: true,
    has_fast_result: true,
    has_final_result: false,
    refresh_hint: "Refresh the page to see updates.",
  },
  completed: {
    needs_refresh: true,
    has_fast_result: true,
    has_final_result: true,
    refresh_hint: "Refresh the page to see updates.",
  },
  failed: {
    needs_refresh: false,
    has_fast_result: false,
    has_final_result: false,
    refresh_hint: "",
  },
  blocked: {
    needs_refresh: false,
    has_fast_result: false,
    has_final_result: false,
    refresh_hint: "",
  },
};

function log(message, data) {
  const prefix = `[architect-plugin] ${message}`;
  if (data === undefined) {
    process.stderr.write(`${prefix}\n`);
    return;
  }
  process.stderr.write(`${prefix} ${JSON.stringify(data)}\n`);
}

function utcNowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function ensureDir(dirPath) {
  await fsp.mkdir(dirPath, { recursive: true });
}

async function writeJson(filePath, data) {
  await ensureDir(path.dirname(filePath));
  await fsp.writeFile(filePath, JSON.stringify(data, null, 2) + "\n", "utf8");
}

async function readJson(filePath, fallback = null) {
  try {
    const raw = await fsp.readFile(filePath, "utf8");
    return JSON.parse(raw);
  } catch (error) {
    if (error && error.code === "ENOENT") return fallback;
    throw error;
  }
}

async function appendLine(filePath, line) {
  await ensureDir(path.dirname(filePath));
  await fsp.appendFile(filePath, line, "utf8");
}

function shortHash(text, length = 4) {
  return createHash("sha1").update(text).digest("hex").slice(0, length);
}

function defaultStatusFields(state) {
  return JSON.parse(JSON.stringify(STATUS_DEFAULTS[state] || {}));
}

function summarizeCommentCount(n) {
  return `Received ${n} diagram comment${n === 1 ? "" : "s"}. Thinking through the update now.`;
}

function architectureDir(outputRoot) {
  return path.join(outputRoot, "architecture");
}

function runtimeDir(outputRoot) {
  return path.join(architectureDir(outputRoot), runtimeDirName);
}

function feedbackJobsDir(outputRoot) {
  return path.join(runtimeDir(outputRoot), "feedback-jobs");
}

function diagramPathFor(outputRoot) {
  return path.join(architectureDir(outputRoot), "diagram.html");
}

function timestampMs(value) {
  if (!value) return null;
  const parsed = Date.parse(String(value));
  return Number.isFinite(parsed) ? parsed : null;
}

function stateIndex(state) {
  return STATE_ORDER.indexOf(String(state || ""));
}

function stringifyValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function sanitizeMeta(meta) {
  const out = {};
  for (const [key, value] of Object.entries(meta || {})) {
    if (!/^[A-Za-z0-9_]+$/.test(key)) continue;
    out[key] = stringifyValue(value);
  }
  return out;
}

function formatComment(comment, index) {
  const target =
    comment.element_id ||
    comment.relationship_id ||
    comment.view_id ||
    comment.anchor ||
    "canvas";
  const body = String(comment.body || comment.comment || "").trim();
  return `${index + 1}. [${target}] ${body}`;
}

function buildCommentLines(comments) {
  return comments.length
    ? comments.map((comment, index) => formatComment(comment, index))
    : ["1. No comments were included."];
}

function buildFeedbackContent(body) {
  const comments = Array.isArray(body.comments) ? body.comments : [];
  if (comments.length === 1) {
    return "Got it, let me noodle on this comment.";
  }
  if (comments.length > 1) {
    return `Got it, let me noodle on these ${comments.length} comments.`;
  }
  return "Got it, let me noodle on these comments.";
}

function buildChannelEvent(body) {
  const comments = Array.isArray(body.comments) ? body.comments : [];
  const commentLines = buildCommentLines(comments);
  return {
    meta: sanitizeMeta({
      event_type: String(body.event_type || "architect_feedback_batch"),
      state: body.state || "",
      job_id: body.job_id || randomUUID(),
      bridge_url: body.bridge_url || "",
      output_root: body.output_root || "",
      diagram_revision_id: body.diagram_revision_id || "",
      comment_count: String(comments.length),
      comments_json: comments,
      comments_summary: commentLines,
    }),
    content: buildFeedbackContent(body),
  };
}

class JobStore {
  constructor() {
    this.records = new Map();
    this.subscribers = new Map();
    this.outputRootActiveJobs = new Map();
    this.receivedTimeouts = new Map();
  }

  async ensureLoaded() {
    await ensureDir(pluginData);
    const index = await readJson(jobIndexPath, {});
    if (!index || typeof index !== "object") return;
    for (const [jobId, item] of Object.entries(index)) {
      if (!item || typeof item !== "object") continue;
      this.records.set(jobId, item);
    }
  }

  async persistIndex() {
    const index = {};
    for (const [jobId, record] of this.records.entries()) {
      index[jobId] = record;
    }
    await writeJson(jobIndexPath, index);
  }

  async get(jobId) {
    if (this.records.has(jobId)) return this.records.get(jobId);
    await this.ensureLoaded();
    return this.records.get(jobId) || null;
  }

  recordFromStatus(statusPath, status, outputRoot) {
    const jobDir = path.dirname(statusPath);
    const jobId = String((status && status.job_id) || path.basename(jobDir));
    const existing = this.records.get(jobId);
    if (existing) return existing;
    const record = {
      job_id: jobId,
      output_root: outputRoot,
      job_dir: jobDir,
      payload: {},
    };
    this.records.set(jobId, record);
    return record;
  }

  async latestStatusForOutputRoot(outputRoot) {
    const latestPath = path.join(feedbackJobsDir(outputRoot), "latest.json");
    const latest = await readJson(latestPath, null);
    if (!latest || typeof latest !== "object") return null;
    if (!latest.status_path) return null;
    let status = await readJson(latest.status_path, null);
    if (!status || typeof status !== "object") return null;
    if (this.isReceivedTimedOut(status)) {
      const record = this.recordFromStatus(latest.status_path, status, outputRoot);
      status = await this.expireReceivedJob(record, status);
    }
    return status;
  }

  async assertNoActiveJob(outputRoot) {
    const current = await this.latestStatusForOutputRoot(outputRoot);
    if (!current || !current.state) return;
    if (!TERMINAL_STATES.has(String(current.state))) {
      const error = new Error("Another comment update is already in progress for this diagram.");
      error.code = "JOB_IN_PROGRESS";
      throw error;
    }
  }

  async createJob(payload, bridgeUrl) {
    const outputRoot = path.resolve(String(payload.output_root || ""));
    const archDir = architectureDir(outputRoot);
    if (!outputRoot || !fs.existsSync(outputRoot) || !fs.existsSync(archDir)) {
      throw new Error(`output_root must contain architecture/: ${outputRoot}`);
    }

    await this.assertNoActiveJob(outputRoot);

    const jobId = new Date().toISOString().replace(/[:.]/g, "-").replace(/Z$/, "Z");
    const recordId = `job_${jobId}_${shortHash(`${Date.now()}-${Math.random()}`)}`;
    const jobDir = path.join(feedbackJobsDir(outputRoot), recordId);
    await ensureDir(jobDir);

    const jobPayload = {
      ...payload,
      output_root: outputRoot,
      job_id: recordId,
      bridge_url: bridgeUrl,
      submitted_at: utcNowIso(),
    };

    await writeJson(path.join(jobDir, "input.json"), jobPayload);

    const baselineModel = path.join(archDir, "model.yaml");
    if (fs.existsSync(baselineModel)) {
      await fsp.copyFile(baselineModel, path.join(jobDir, "baseline-model.yaml"));
    }

    const record = {
      job_id: recordId,
      output_root: outputRoot,
      job_dir: jobDir,
      payload: jobPayload,
    };
    this.records.set(recordId, record);
    await this.persistIndex();

    const status = await this.updateStatus(record, "received", "Comments sent. The agent is reviewing them now.", {
      submitted_comment_count: Array.isArray(jobPayload.comments) ? jobPayload.comments.length : 0,
      needs_refresh: false,
      has_fast_result: false,
      has_final_result: false,
      diagram_path: diagramPathFor(outputRoot),
      output_root: outputRoot,
      bridge_url: bridgeUrl,
    });
    return { record, status };
  }

  clearReceivedTimeout(jobId) {
    const timeout = this.receivedTimeouts.get(jobId);
    if (!timeout) return;
    clearTimeout(timeout);
    this.receivedTimeouts.delete(jobId);
  }

  isReceivedTimedOut(status) {
    if (!status || status.state !== "received") return false;
    const receivedAt = timestampMs(status.timestamps && status.timestamps.received_at);
    if (receivedAt === null) return false;
    return Date.now() - receivedAt >= channelAckTimeoutMs;
  }

  async writeStatusSnapshot(record, status) {
    const statusPath = path.join(record.job_dir, "status.json");
    await writeJson(statusPath, status);
    await appendLine(path.join(record.job_dir, "events.ndjson"), JSON.stringify({ event: "state", data: status }) + "\n");
    await writeJson(path.join(feedbackJobsDir(record.output_root), "latest.json"), {
      job_id: record.job_id,
      state: status.state,
      status_path: statusPath,
      result_path: path.join(record.job_dir, "result.json"),
      diagram_path: diagramPathFor(record.output_root),
      output_root: record.output_root,
    });

    const subscribers = this.subscribers.get(record.job_id) || new Set();
    for (const response of subscribers) {
      sendStatusEvent(response, status);
    }
    return status;
  }

  async expireReceivedJob(record, current = null) {
    const existing = current || (await readJson(path.join(record.job_dir, "status.json"), {})) || {};
    if (!existing || existing.state !== "received" || !this.isReceivedTimedOut(existing)) {
      return existing;
    }
    this.clearReceivedTimeout(record.job_id);
    const timestamps = existing.timestamps && typeof existing.timestamps === "object" ? existing.timestamps : {};
    if (!timestamps.received_at) timestamps.received_at = utcNowIso();
    timestamps.failed_at = utcNowIso();
    const status = {
      ...existing,
      ...defaultStatusFields("failed"),
      error: "agent_ack_timeout",
      job_id: record.job_id,
      state: "failed",
      message: channelAckTimeoutMessage,
      timestamps,
      diagram_path: diagramPathFor(record.output_root),
      output_root: record.output_root,
    };
    return await this.writeStatusSnapshot(record, status);
  }

  armReceivedTimeout(record) {
    this.clearReceivedTimeout(record.job_id);
    const timeout = setTimeout(async () => {
      try {
        await this.expireReceivedJob(record);
      } catch (error) {
        log("failed to expire unacknowledged job", { job_id: record.job_id, error: String(error) });
      }
    }, channelAckTimeoutMs);
    this.receivedTimeouts.set(record.job_id, timeout);
  }

  async updateStatus(record, state, message, extraFields = {}) {
    if (!STATE_ORDER.includes(state)) {
      throw new Error(`Unsupported state: ${state}`);
    }
    const statusPath = path.join(record.job_dir, "status.json");
    const current = (await readJson(statusPath, {})) || {};
    if (current.state) {
      if (TERMINAL_STATES.has(String(current.state)) && state !== current.state) {
        const error = new Error(`Cannot change terminal job ${record.job_id} from ${current.state} to ${state}.`);
        error.code = "TERMINAL_STATUS";
        throw error;
      }
      if (stateIndex(state) < stateIndex(current.state)) {
        const error = new Error(`Cannot move job ${record.job_id} backwards from ${current.state} to ${state}.`);
        error.code = "STALE_STATUS_TRANSITION";
        throw error;
      }
    }
    const timestamps = current.timestamps && typeof current.timestamps === "object" ? current.timestamps : {};
    if (!timestamps.received_at) timestamps.received_at = utcNowIso();
    timestamps[`${state}_at`] = utcNowIso();

    const status = {
      ...current,
      ...defaultStatusFields(state),
      ...extraFields,
      job_id: record.job_id,
      state,
      message,
      timestamps,
      diagram_path: diagramPathFor(record.output_root),
      output_root: record.output_root,
    };

    if (state !== "received") {
      this.clearReceivedTimeout(record.job_id);
    }
    return await this.writeStatusSnapshot(record, status);
  }

  subscribe(jobId, response) {
    if (!this.subscribers.has(jobId)) this.subscribers.set(jobId, new Set());
    this.subscribers.get(jobId).add(response);
  }

  unsubscribe(jobId, response) {
    const set = this.subscribers.get(jobId);
    if (!set) return;
    set.delete(response);
    if (set.size === 0) this.subscribers.delete(jobId);
  }
}

function parseRequestBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}"));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

function sendJson(res, code, payload) {
  const body = Buffer.from(JSON.stringify(payload), "utf8");
  res.writeHead(code, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": String(body.length),
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "content-type",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  });
  res.end(body);
}

function sendStatusEvent(res, status) {
  const payload = JSON.stringify({ state: status.state, message: status.message, status });
  res.write(`event: state\n`);
  res.write(`data: ${payload}\n\n`);
}

function runCommand(command, args) {
  const result = spawnSync(command, args, {
    cwd: pluginRoot,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });

  if (result.error) throw result.error;
  if (result.status !== 0) {
    const detail = [
      `${command} ${args.join(" ")} failed with exit code ${result.status}`,
      String(result.stdout || "").trim(),
      String(result.stderr || "").trim(),
    ].filter(Boolean).join("\n");
    throw new Error(detail);
  }
  return {
    stdout: String(result.stdout || ""),
    stderr: String(result.stderr || ""),
  };
}

function extractEmbeddedDiagramData(html) {
  const startMarker = "const DATA = ";
  const endMarker = ";\nconst MODE = ";
  const start = html.indexOf(startMarker);
  if (start === -1) return null;
  const end = html.indexOf(endMarker, start);
  if (end === -1) return null;
  const jsonText = html.slice(start + startMarker.length, end).trim();
  try {
    return JSON.parse(jsonText);
  } catch (_error) {
    return null;
  }
}

function inspectExistingDiagram(outputRoot) {
  const diagramPath = diagramPathFor(outputRoot);
  if (!fs.existsSync(diagramPath)) return null;

  const html = fs.readFileSync(diagramPath, "utf8");
  const data = extractEmbeddedDiagramData(html);
  const handoffContext = data && data.comment_handoff && data.comment_handoff.render_context && typeof data.comment_handoff.render_context === "object"
    ? data.comment_handoff.render_context
    : null;
  const modeMatch = html.match(/<meta name="diagram-render-mode" content="([^"]+)"/) || html.match(/const MODE = "([^"]+)"/);
  const viewTypes = Array.isArray(handoffContext?.view_types)
    ? handoffContext.view_types.map((value) => String(value || "")).filter(Boolean)
    : Array.isArray(data?.views)
      ? data.views.map((view) => String(view?.type || "")).filter(Boolean)
      : [];
  const svgFragmentViewIds = Array.isArray(handoffContext?.svg_fragment_view_ids)
    ? handoffContext.svg_fragment_view_ids.map((value) => String(value || "")).filter(Boolean)
    : Array.isArray(data?.views)
      ? data.views.filter((view) => Boolean(view?.svg_fragment)).map((view) => String(view?.id || "")).filter(Boolean)
      : [];

  return {
    mode: String(handoffContext?.mode || (modeMatch ? modeMatch[1] : "fast")).trim() === "rich" ? "rich" : "fast",
    includeSequence: Boolean(handoffContext?.include_sequence) || viewTypes.includes("sequence"),
    viewTypes,
    svgFragmentViewIds,
    hasSvgFragments: svgFragmentViewIds.length > 0,
  };
}

function resolveRenderProfile(outputRoot, requestedMode) {
  const existing = inspectExistingDiagram(outputRoot);
  const currentNeedsRich = Boolean(
    existing && (
      existing.mode === "rich" ||
      existing.viewTypes.includes("component") ||
      existing.hasSvgFragments
    )
  );
  return {
    requestedMode,
    renderMode: requestedMode === "rich" || currentNeedsRich ? "rich" : "fast",
    includeSequence: Boolean(existing?.includeSequence),
    regenerateSvgFragments: Boolean(existing?.hasSvgFragments) || requestedMode === "rich" || currentNeedsRich,
    preservedExistingProfile: requestedMode === "fast" && currentNeedsRich,
    existing,
  };
}

function finalizeFeedbackUpdate(args) {
  const rawOutputRoot = String(args.output_root || "").trim();
  if (!rawOutputRoot) throw new Error("output_root is required");

  const outputRoot = path.isAbsolute(rawOutputRoot) ? rawOutputRoot : path.resolve(process.cwd(), rawOutputRoot);
  const bridgeUrl = String(args.bridge_url || "").trim();
  const requestedRenderMode = String(args.render_mode || "fast").trim();
  if (!["fast", "rich"].includes(requestedRenderMode)) {
    throw new Error("render_mode must be one of: fast, rich");
  }
  const renderProfile = resolveRenderProfile(outputRoot, requestedRenderMode);

  const validationResult = runCommand(pythonBin, [feedbackValidatorScript, "--output-root", outputRoot, "--json"]);
  const validation = JSON.parse(validationResult.stdout || "{}");
  let svgGenerationResult = null;
  if (renderProfile.regenerateSvgFragments) {
    svgGenerationResult = runCommand(pythonBin, [svgFragmentScript, "--output-root", outputRoot]);
  }

  const renderArgs = [renderDiagramScript, "--output-root", outputRoot, "--mode", renderProfile.renderMode];
  if (renderProfile.includeSequence) {
    renderArgs.push("--include-sequence");
  }
  if (bridgeUrl) {
    renderArgs.push("--feedback-bridge-url", bridgeUrl);
  }
  const renderResult = runCommand(pythonBin, renderArgs);
  const diagramPath = diagramPathFor(outputRoot);
  const htmlValidation = runCommand("bash", [htmlValidatorScript, diagramPath]);

  return {
    ok: true,
    output_root: outputRoot,
    diagram_path: diagramPath,
    render_mode_requested: requestedRenderMode,
    render_mode: renderProfile.renderMode,
    include_sequence: renderProfile.includeSequence,
    regenerated_svg_fragments: renderProfile.regenerateSvgFragments,
    preserved_existing_render_profile: renderProfile.preservedExistingProfile,
    existing_render_profile: renderProfile.existing,
    validation: {
      ok: Boolean(validation.ok),
      error_count: Number(validation.error_count || 0),
      warning_count: Number(validation.warning_count || 0),
      warnings: Array.isArray(validation.warnings) ? validation.warnings : [],
    },
    svg_generation_stdout: svgGenerationResult ? svgGenerationResult.stdout.trim() : "",
    render_stdout: renderResult.stdout.trim(),
    html_validation_stdout: htmlValidation.stdout.trim(),
    next_step: "Now call update_feedback_status with state=completed and the exact message: \"Refresh the page to see updates.\"",
  };
}

const mcp = new Server(
  { name, version: "0.1.0" },
  {
    capabilities: {
      experimental: { "claude/channel": {} },
      tools: {},
    },
    instructions:
      "Messages arrive as <channel source=\"architect-comments\" ...>. " +
      "When a feedback batch arrives, treat the channel line itself as the user-visible acknowledgment and do not add a second acknowledgment message before you start work. " +
      "Read the referenced job details from the channel attributes, including bridge_url, output_root, diagram_revision_id, and comments_json, then implement the requested updates directly. " +
      "Do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. " +
      "Use update_feedback_status to report progress back to the browser bridge in a compact, implementation-aware voice. " +
      "After you edit the artifacts, call finalize_feedback_update instead of guessing shell commands so validation and rendering stay deterministic. " +
      "Keep model edits contract-safe, for example use `database` instead of `datastore`. " +
      "When you summarize the result, describe the actual written graph changes and keep the browser-ready completion message short.",
  },
);

const store = new JobStore();

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "update_feedback_status",
      description:
        "Update the Architect feedback job status in the local browser bridge so the diagram app can show progress and refresh instructions.",
      inputSchema: {
        type: "object",
        properties: {
          bridge_url: { type: "string" },
          job_id: { type: "string" },
          state: { type: "string", enum: STATE_ORDER },
          message: { type: "string" },
          needs_refresh: { type: "boolean" },
          has_fast_result: { type: "boolean" },
          has_final_result: { type: "boolean" },
          refresh_hint: { type: "string" },
          warnings: { type: "array", items: { type: "string" } },
          error: { type: "string" },
        },
        required: ["bridge_url", "job_id", "state", "message"],
      },
    },
    {
      name: "finalize_feedback_update",
      description:
        "Validate architecture artifacts, preserve the current diagram's quality and view set when rerendering diagram.html, and validate the generated HTML before you mark a feedback job complete.",
      inputSchema: {
        type: "object",
        properties: {
          output_root: { type: "string" },
          bridge_url: { type: "string" },
          render_mode: { type: "string", enum: ["fast", "rich"] },
        },
        required: ["output_root"],
      },
    },
  ],
}));

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "update_feedback_status") {
    const args = req.params.arguments || {};
    const bridgeUrl = String(args.bridge_url || "").replace(/\/$/, "");
    const jobId = String(args.job_id || "").trim();
    const state = String(args.state || "").trim();
    const message = String(args.message || "").trim();
    if (!bridgeUrl) throw new Error("bridge_url is required");
    if (!jobId) throw new Error("job_id is required");
    if (!state) throw new Error("state is required");
    if (!message) throw new Error("message is required");

    const response = await fetch(`${bridgeUrl}/jobs/${encodeURIComponent(jobId)}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args),
    });
    if (!response.ok) {
      throw new Error(`bridge status update failed (${response.status}): ${await response.text()}`);
    }
    const result = await response.json();
    return {
      content: [{ type: "text", text: JSON.stringify({ ok: true, job_id: result.job_id, state: result.state, message: result.message }, null, 2) }],
    };
  }

  if (req.params.name === "finalize_feedback_update") {
    const result = finalizeFeedbackUpdate(req.params.arguments || {});
    return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
  }

  throw new Error(`unknown tool: ${req.params.name}`);
});

async function sendChannelNotification(body) {
  const { meta, content } = buildChannelEvent(body);
  await mcp.notification({
    method: "notifications/claude/channel",
    params: { meta, content },
  });
  log("delivered channel event", meta);
}

function bridgeBaseUrl(server) {
  const address = server.address();
  return `http://${address.address}:${address.port}`;
}

function requestHandler(server) {
  return async (req, res) => {
    if (!req.url) {
      sendJson(res, 400, { error: "missing url" });
      return;
    }

    const parsed = new URL(req.url, `http://${bind}:${port}`);

    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "content-type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      });
      res.end();
      return;
    }

    if (req.method === "GET" && parsed.pathname === "/health") {
      sendJson(res, 200, { ok: true, name, time: utcNowIso(), port });
      return;
    }

    if (req.method === "GET" && parsed.pathname === "/latest-status") {
      const outputRoot = parsed.searchParams.get("output_root");
      if (!outputRoot) {
        sendJson(res, 400, { error: "output_root is required" });
        return;
      }
      const status = await store.latestStatusForOutputRoot(path.resolve(outputRoot));
      sendJson(res, 200, { status });
      return;
    }

    const jobMatch = parsed.pathname.match(/^\/jobs\/([^/]+)$/);
    if (req.method === "GET" && jobMatch) {
      const record = await store.get(jobMatch[1]);
      if (!record) {
        sendJson(res, 404, { error: "job not found" });
        return;
      }
      let status = await readJson(path.join(record.job_dir, "status.json"), {});
      if (store.isReceivedTimedOut(status)) {
        status = await store.expireReceivedJob(record, status);
      }
      sendJson(res, 200, status || {});
      return;
    }

    const eventsMatch = parsed.pathname.match(/^\/jobs\/([^/]+)\/events$/);
    if (req.method === "GET" && eventsMatch) {
      const record = await store.get(eventsMatch[1]);
      if (!record) {
        sendJson(res, 404, { error: "job not found" });
        return;
      }
      res.writeHead(200, {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "Access-Control-Allow-Origin": "*",
      });
      store.subscribe(record.job_id, res);
      const current = (await readJson(path.join(record.job_dir, "status.json"), {})) || {};
      sendStatusEvent(res, current);
      const heartbeat = setInterval(() => {
        try {
          res.write(": heartbeat\n\n");
        } catch (error) {
          clearInterval(heartbeat);
        }
      }, 15000);
      req.on("close", () => {
        clearInterval(heartbeat);
        store.unsubscribe(record.job_id, res);
      });
      return;
    }

    const statusMatch = parsed.pathname.match(/^\/jobs\/([^/]+)\/status$/);
    if (req.method === "POST" && statusMatch) {
      const record = await store.get(statusMatch[1]);
      if (!record) {
        sendJson(res, 404, { error: "job not found" });
        return;
      }

      let body;
      try {
        body = await parseRequestBody(req);
      } catch {
        sendJson(res, 400, { error: "invalid json" });
        return;
      }

      const state = body.state;
      const message = body.message;
      if (!STATE_ORDER.includes(state)) {
        sendJson(res, 400, { error: "state must be one of the supported job states" });
        return;
      }
      if (!message || typeof message !== "string") {
        sendJson(res, 400, { error: "message is required" });
        return;
      }

      const extraFields = {};
      for (const key of ["needs_refresh", "has_fast_result", "has_final_result", "refresh_hint", "warnings", "error"]) {
        if (Object.prototype.hasOwnProperty.call(body, key)) extraFields[key] = body[key];
      }
      let status;
      try {
        status = await store.updateStatus(record, state, message.trim(), extraFields);
      } catch (error) {
        const code = error && (error.code === "TERMINAL_STATUS" || error.code === "STALE_STATUS_TRANSITION") ? 409 : 400;
        sendJson(res, code, { error: String(error.message || error) });
        return;
      }
      sendJson(res, 200, status);
      return;
    }

    if (req.method === "POST" && parsed.pathname === "/notify") {
      let body;
      try {
        body = await parseRequestBody(req);
      } catch {
        sendJson(res, 400, { error: "invalid json" });
        return;
      }
      try {
        await sendChannelNotification(body);
        sendJson(res, 202, { ok: true });
      } catch (error) {
        log("failed to deliver channel event", { error: String(error) });
        sendJson(res, 500, { error: "delivery failed" });
      }
      return;
    }

    if (req.method === "POST" && parsed.pathname === "/feedback-batches") {
      let body;
      try {
        body = await parseRequestBody(req);
      } catch {
        sendJson(res, 400, { error: "invalid json" });
        return;
      }
      if (!Array.isArray(body.comments) || body.comments.length === 0) {
        sendJson(res, 400, { error: "comments must be a non-empty list" });
        return;
      }
      if (!body.output_root) {
        sendJson(res, 400, { error: "output_root is required" });
        return;
      }

      let created;
      try {
        created = await store.createJob(body, bridgeBaseUrl(server));
      } catch (error) {
        const code = error && error.code === "JOB_IN_PROGRESS" ? 409 : 400;
        sendJson(res, code, { error: String(error.message || error) });
        return;
      }

      const { record, status } = created;
      const ack = summarizeCommentCount((record.payload.comments || []).length);
      log(`[${record.job_id}] ${ack}`);

      try {
        await sendChannelNotification({
          event_type: "architect_feedback_batch",
          state: "received",
          message: status.message,
          job_id: record.job_id,
          output_root: record.output_root,
          diagram_revision_id: String(record.payload.diagram_revision_id || ""),
          bridge_url: bridgeBaseUrl(server),
          comments: record.payload.comments || [],
        });
        store.armReceivedTimeout(record);
      } catch (error) {
        await store.updateStatus(
          record,
          "failed",
          "Claude channel delivery failed. Confirm the Architect plugin channel is enabled and retry.",
          { error: String(error) },
        );
      }

      const currentStatus = (await readJson(path.join(record.job_dir, "status.json"), {})) || status;

      sendJson(res, 202, {
        job_id: record.job_id,
        state: currentStatus.state,
        message: currentStatus.message,
        status_url: `${bridgeBaseUrl(server)}/jobs/${record.job_id}`,
        events_url: `${bridgeBaseUrl(server)}/jobs/${record.job_id}/events`,
        diagram_path: diagramPathFor(record.output_root),
      });
      return;
    }

    sendJson(res, 404, { error: "not found" });
  };
}

async function main() {
  await store.ensureLoaded();
  const transport = new StdioServerTransport();
  await mcp.connect(transport);

  const server = http.createServer(requestHandler(null));
  server.removeAllListeners("request");
  server.on("request", requestHandler(server));
  server.on("error", (error) => {
    const detail = error && error.code === "EADDRINUSE"
      ? `bridge port ${port} on ${bind} is already in use. Stop the other Architect runtime and restart Claude. Example: pkill -f architect_runtime.cjs`
      : String(error);
    log("fatal", { error: detail });
    process.exit(1);
  });
  server.listen(port, bind, () => {
    log("listening", { bind, port, name });
  });
}

main().catch((error) => {
  log("fatal", { error: String(error), stack: error && error.stack ? error.stack : "" });
  process.exit(1);
});
