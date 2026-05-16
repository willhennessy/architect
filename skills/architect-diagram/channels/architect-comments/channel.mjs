#!/usr/bin/env node

import fs from "node:fs"
import http from "node:http"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { randomUUID } from "node:crypto"
import { fileURLToPath } from "node:url"
import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js"

const name = process.env.ARCHITECT_CHANNEL_NAME || "architect-comments"
const port = parseInt(process.env.ARCHITECT_CHANNEL_PORT || "8788", 10)
const secret = process.env.ARCHITECT_CHANNEL_SECRET || ""
const bind = process.env.ARCHITECT_CHANNEL_BIND || "127.0.0.1"
const moduleDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(moduleDir, "../../../..")
const feedbackValidatorScript = path.join(repoRoot, "skills/architect-diagram/scripts/validate-feedback-update.py")
const svgFragmentScript = path.join(repoRoot, "skills/architect-diagram/scripts/generate-svg-fragments.py")
const renderDiagramScript = path.join(repoRoot, "skills/architect-diagram/scripts/render-diagram-html.py")
const htmlValidatorScript = path.join(repoRoot, "skills/architect-diagram/scripts/validate-diagram-html.sh")

function log(message, data = null) {
  const prefix = `[architect-channel] ${message}`
  if (data === null) {
    process.stderr.write(`${prefix}\n`)
    return
  }
  process.stderr.write(`${prefix} ${JSON.stringify(data)}\n`)
}

function stringifyValue(value) {
  if (value === null || value === undefined) return ""
  if (typeof value === "string") return value
  return JSON.stringify(value)
}

function sanitizeMeta(meta) {
  const out = {}
  for (const [key, value] of Object.entries(meta || {})) {
    if (!/^[A-Za-z0-9_]+$/.test(key)) continue
    out[key] = stringifyValue(value)
  }
  return out
}

function formatComment(comment, index) {
  const target =
    comment.element_id ||
    comment.relationship_id ||
    comment.view_id ||
    comment.anchor ||
    "canvas"
  const body = String(comment.body || comment.comment || "").trim()
  return `${index + 1}. [${target}] ${body}`
}

function buildCommentLines(comments) {
  return comments.length
    ? comments.map((comment, index) => formatComment(comment, index))
    : ["1. No comments were included."]
}

function buildFeedbackContent(body) {
  const comments = Array.isArray(body.comments) ? body.comments : []
  if (comments.length === 1) {
    return "Got it, let me noodle on this comment."
  }
  if (comments.length > 1) {
    return `Got it, let me noodle on these ${comments.length} comments.`
  }
  return "Got it, let me noodle on these comments."
}

function buildChannelEvent(body) {
  const eventType = String(body.event_type || "architect_feedback_batch")
  const comments = Array.isArray(body.comments) ? body.comments : []
  const commentLines = buildCommentLines(comments)
  const openThreadIds = Array.isArray(body.open_thread_ids) ? body.open_thread_ids : []
  const openThreadSummary = Array.isArray(body.open_thread_summary)
    ? body.open_thread_summary
    : typeof body.open_thread_summary === "string"
      ? [body.open_thread_summary]
      : []
  const baseMeta = {
    event_type: eventType,
    state: body.state || "",
    job_id: body.job_id || randomUUID(),
    bridge_url: body.bridge_url || "",
    output_root: body.output_root || "",
    diagram_revision_id: body.diagram_revision_id || "",
    comment_count: String(comments.length),
    comments_json: comments,
    comments_summary: commentLines,
    open_thread_ids: openThreadIds,
    open_thread_summary: openThreadSummary,
  }
  if (eventType === "architect_thread_user_reply") {
    baseMeta.thread_id = body.thread_id || ""
    baseMeta.parent_message_id = body.parent_message_id || ""
    baseMeta.view_id = body.view_id || ""
    baseMeta.element_id = body.element_id || ""
    baseMeta.relationship_id = body.relationship_id || ""
    baseMeta.target_label = body.target_label || ""
    baseMeta.reply_body = body.reply_body || body.body || ""
  }
  const meta = sanitizeMeta(baseMeta)
  let content
  if (eventType === "architect_feedback_batch") {
    content = buildFeedbackContent(body)
  } else if (eventType === "architect_thread_user_reply") {
    content = "The user replied to one of your comment threads. Read reply_body and decide whether to answer, answer-and-resolve, or silently resolve."
  } else {
    content = stringifyValue(body.content || body.message || body)
  }
  return { meta, content }
}

const mcp = new Server(
  { name, version: "0.0.1" },
  {
    capabilities: {
      experimental: { "claude/channel": {} },
      tools: {},
    },
    instructions:
      "Messages arrive as <channel source=\"architect-comments\" ...>. " +
      "When a feedback batch arrives, treat the channel line itself as the user-visible acknowledgment and do not add a second acknowledgment message before you start work. " +
      "Read the referenced job details from the channel attributes, including bridge_url, output_root, diagram_revision_id, comments_summary, and comments_json, then implement the requested updates directly. " +
      "Do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. " +
      "If the comment is a connectivity check, a simple acknowledgment, or otherwise does not request an architecture change, resolve it immediately by calling update_feedback_status with state=completed and a concise message such as \"Resolved 1 comment. No architecture changes were requested.\" Do not ask a follow-up question for those no-op comments. " +
      "Use update_feedback_status to report progress back to the browser bridge in a compact user-facing voice. " +
      "After you edit the artifacts, call finalize_feedback_update instead of guessing shell commands so validation and rendering stay deterministic. " +
      "Keep model edits contract-safe, for example use `database` instead of `datastore`. " +
      "When you summarize the result, describe the actual written graph changes and keep the browser-ready completion message short. " +
      "If the batch event includes open_thread_ids or open_thread_summary, the user did NOT reply to those Claude-authored threads on this turn. Do not resolve them, do not add a follow-up reply, and do not mention them in your completion message — treat them as pending for a future turn. " +
      "When you need to ask the user a design question during plan mode, call post_claude_comment anchored to the specific view_id and element_id or relationship_id that the question is about. One focused question per comment, always state the default you assumed. Do not post comments for stylistic or minor concerns. " +
      "When a <channel source=\"architect-comments\" ...> event arrives with event_type=architect_thread_user_reply, use post_claude_reply (NOT finalize_feedback_update) to respond. Read thread_id and reply_body from the channel attributes. Set resolves=true when the user's reply fully answers your question and no further conversation is needed; otherwise reply without resolving. Use resolve_thread for silent resolution when the question became moot without needing a textual reply.",
  },
)

function runCommand(command, args) {
  const result = spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  })

  if (result.error) {
    throw result.error
  }

  const stdout = String(result.stdout || "")
  const stderr = String(result.stderr || "")
  if (result.status !== 0) {
    const detail = [
      `${command} ${args.join(" ")} failed with exit code ${result.status}`,
      stdout.trim(),
      stderr.trim(),
    ]
      .filter(Boolean)
      .join("\n")
    throw new Error(detail)
  }

  return { stdout, stderr }
}

function extractEmbeddedDiagramData(html) {
  const startMarker = "const DATA = "
  const endMarker = ";\nconst MODE = "
  const start = html.indexOf(startMarker)
  if (start === -1) return null
  const end = html.indexOf(endMarker, start)
  if (end === -1) return null
  const jsonText = html.slice(start + startMarker.length, end).trim()
  try {
    return JSON.parse(jsonText)
  } catch (_error) {
    return null
  }
}

function diagramPathFor(outputRoot) {
  return path.join(outputRoot, "architecture", "diagram.html")
}

function inspectExistingDiagram(outputRoot) {
  const diagramPath = diagramPathFor(outputRoot)
  if (!fs.existsSync(diagramPath)) return null

  const html = fs.readFileSync(diagramPath, "utf8")
  const data = extractEmbeddedDiagramData(html)
  const handoffContext =
    data &&
    data.comment_handoff &&
    data.comment_handoff.render_context &&
    typeof data.comment_handoff.render_context === "object"
      ? data.comment_handoff.render_context
      : null
  const modeMatch =
    html.match(/<meta name="diagram-render-mode" content="([^"]+)"/) ||
    html.match(/const MODE = "([^"]+)"/)
  const viewTypes = Array.isArray(handoffContext?.view_types)
    ? handoffContext.view_types.map((value) => String(value || "")).filter(Boolean)
    : Array.isArray(data?.views)
      ? data.views.map((view) => String(view?.type || "")).filter(Boolean)
      : []
  const svgFragmentViewIds = Array.isArray(handoffContext?.svg_fragment_view_ids)
    ? handoffContext.svg_fragment_view_ids.map((value) => String(value || "")).filter(Boolean)
    : Array.isArray(data?.views)
      ? data.views.filter((view) => Boolean(view?.svg_fragment)).map((view) => String(view?.id || "")).filter(Boolean)
      : []

  return {
    mode: String(handoffContext?.mode || (modeMatch ? modeMatch[1] : "fast")).trim() === "rich" ? "rich" : "fast",
    includeSequence: Boolean(handoffContext?.include_sequence) || viewTypes.includes("sequence"),
    viewTypes,
    svgFragmentViewIds,
    hasSvgFragments: svgFragmentViewIds.length > 0,
  }
}

function resolveRenderProfile(outputRoot, requestedMode) {
  const existing = inspectExistingDiagram(outputRoot)
  const currentNeedsRich =
    !!existing &&
    (existing.mode === "rich" || existing.viewTypes.includes("component") || existing.hasSvgFragments)
  return {
    requestedMode,
    renderMode: requestedMode === "rich" || currentNeedsRich ? "rich" : "fast",
    includeSequence: Boolean(existing?.includeSequence),
    regenerateSvgFragments: Boolean(existing?.hasSvgFragments) || requestedMode === "rich" || currentNeedsRich,
    preservedExistingProfile: requestedMode === "fast" && currentNeedsRich,
    existing,
  }
}

async function postBridgeStatus(args) {
  const bridgeUrl = String(args.bridge_url || "").replace(/\/$/, "")
  const jobId = String(args.job_id || "").trim()
  const state = String(args.state || "").trim()
  const message = String(args.message || "").trim()

  if (!bridgeUrl) throw new Error("bridge_url is required")
  if (!jobId) throw new Error("job_id is required")
  if (!state) throw new Error("state is required")
  if (!message) throw new Error("message is required")

  const payload = { state, message }
  for (const key of [
    "needs_refresh",
    "has_fast_result",
    "has_final_result",
    "refresh_hint",
    "warnings",
    "error",
  ]) {
    if (key in args) payload[key] = args[key]
  }

  const response = await fetch(`${bridgeUrl}/jobs/${encodeURIComponent(jobId)}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`bridge status update failed (${response.status}): ${text}`)
  }

  return await response.json()
}

async function postBridgeJson(bridgeUrl, urlPath, body) {
  const base = String(bridgeUrl || "").replace(/\/$/, "")
  if (!base) throw new Error("bridge_url is required")
  const response = await fetch(`${base}${urlPath}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const text = await response.text()
  if (!response.ok) {
    throw new Error(`bridge POST ${urlPath} failed (${response.status}): ${text}`)
  }
  try {
    return text ? JSON.parse(text) : {}
  } catch (_error) {
    return { raw: text }
  }
}

async function postClaudeComment(args) {
  const rawOutputRoot = String(args.output_root || "").trim()
  if (!rawOutputRoot) throw new Error("output_root is required")
  const outputRoot = path.isAbsolute(rawOutputRoot) ? rawOutputRoot : path.resolve(repoRoot, rawOutputRoot)
  const viewId = String(args.view_id || "").trim()
  if (!viewId) throw new Error("view_id is required")
  const body = String(args.body || "").trim()
  if (!body) throw new Error("body is required")
  const elementId = args.element_id ? String(args.element_id).trim() : null
  const relationshipId = args.relationship_id ? String(args.relationship_id).trim() : null
  if (elementId && relationshipId) {
    throw new Error("provide element_id OR relationship_id, not both")
  }
  return await postBridgeJson(args.bridge_url, "/claude-threads", {
    output_root: outputRoot,
    view_id: viewId,
    element_id: elementId,
    relationship_id: relationshipId,
    target_label: String(args.target_label || "").trim() || null,
    body,
    diagram_revision_id: args.diagram_revision_id ? String(args.diagram_revision_id) : null,
  })
}

async function postClaudeReply(args) {
  const threadId = String(args.thread_id || "").trim()
  if (!threadId) throw new Error("thread_id is required")
  const rawOutputRoot = String(args.output_root || "").trim()
  if (!rawOutputRoot) throw new Error("output_root is required")
  const outputRoot = path.isAbsolute(rawOutputRoot) ? rawOutputRoot : path.resolve(repoRoot, rawOutputRoot)
  const resolves = Boolean(args.resolves)
  const silentResolve = Boolean(args.silent_resolve)

  if (silentResolve) {
    return await postBridgeJson(args.bridge_url, `/claude-threads/${encodeURIComponent(threadId)}/resolve`, {
      output_root: outputRoot,
      resolved_by: "claude",
      silent: true,
    })
  }

  const body = String(args.body || "").trim()
  if (!body) throw new Error("body is required unless silent_resolve=true")
  const messageResult = await postBridgeJson(
    args.bridge_url,
    `/claude-threads/${encodeURIComponent(threadId)}/messages`,
    { output_root: outputRoot, author: "claude", body },
  )

  if (resolves) {
    const resolveResult = await postBridgeJson(
      args.bridge_url,
      `/claude-threads/${encodeURIComponent(threadId)}/resolve`,
      { output_root: outputRoot, resolved_by: "claude", silent: false },
    )
    return { message: messageResult, resolve: resolveResult }
  }
  return { message: messageResult }
}

async function resolveThread(args) {
  const threadId = String(args.thread_id || "").trim()
  if (!threadId) throw new Error("thread_id is required")
  const rawOutputRoot = String(args.output_root || "").trim()
  if (!rawOutputRoot) throw new Error("output_root is required")
  const outputRoot = path.isAbsolute(rawOutputRoot) ? rawOutputRoot : path.resolve(repoRoot, rawOutputRoot)
  return await postBridgeJson(args.bridge_url, `/claude-threads/${encodeURIComponent(threadId)}/resolve`, {
    output_root: outputRoot,
    resolved_by: "claude",
    silent: true,
  })
}

function finalizeFeedbackUpdate(args) {
  const rawOutputRoot = String(args.output_root || "").trim()
  const outputRoot = path.isAbsolute(rawOutputRoot) ? rawOutputRoot : path.resolve(repoRoot, rawOutputRoot)
  const bridgeUrl = String(args.bridge_url || "").trim()
  const requestedRenderMode = String(args.render_mode || "fast").trim()

  if (!rawOutputRoot) throw new Error("output_root is required")
  if (!["fast", "rich"].includes(requestedRenderMode)) {
    throw new Error("render_mode must be one of: fast, rich")
  }
  const renderProfile = resolveRenderProfile(outputRoot, requestedRenderMode)

  const validationResult = runCommand("python3", [
    feedbackValidatorScript,
    "--output-root",
    outputRoot,
    "--json",
  ])
  const validation = JSON.parse(validationResult.stdout || "{}")

  let svgGenerationResult = null
  if (renderProfile.regenerateSvgFragments) {
    svgGenerationResult = runCommand("python3", [svgFragmentScript, "--output-root", outputRoot])
  }

  const renderArgs = [renderDiagramScript, "--output-root", outputRoot, "--mode", renderProfile.renderMode]
  if (renderProfile.includeSequence) {
    renderArgs.push("--include-sequence")
  }
  if (bridgeUrl) {
    renderArgs.push("--feedback-bridge-url", bridgeUrl)
  }
  const renderResult = runCommand("python3", renderArgs)

  const diagramPath = diagramPathFor(outputRoot)
  const htmlValidationResult = runCommand("bash", [htmlValidatorScript, diagramPath])

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
    html_validation_stdout: htmlValidationResult.stdout.trim(),
    next_step:
      "Now call update_feedback_status with state=completed and a concise refresh message, unless you still need to report a blocked or failed outcome.",
  }
}

mcp.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "update_feedback_status",
      description:
        "Update the Architect feedback job status in the local bridge so the browser can show progress, refresh instructions, and failures.",
      inputSchema: {
        type: "object",
        properties: {
          bridge_url: {
            type: "string",
            description: "Bridge base URL from the architect-comments channel event, for example http://127.0.0.1:8766",
          },
          job_id: {
            type: "string",
            description: "Feedback job id from the architect-comments channel event",
          },
          state: {
            type: "string",
            enum: [
              "acknowledged",
              "analyzing",
              "fast_patch_running",
              "fast_patch_ready",
              "slow_patch_running",
              "completed",
              "failed",
              "blocked",
            ],
            description: "Current job state to write back to the bridge",
          },
          message: {
            type: "string",
            description:
              "User-facing status message to show in the browser and bridge job status. Keep ready-state messages concise.",
          },
          needs_refresh: {
            type: "boolean",
            description: "Optional override for whether the browser should tell the user to refresh now",
          },
          has_fast_result: {
            type: "boolean",
            description: "Optional override for whether a quick partial result is ready",
          },
          has_final_result: {
            type: "boolean",
            description: "Optional override for whether the final update is ready",
          },
          refresh_hint: {
            type: "string",
            description: "Optional browser refresh instruction override",
          },
          warnings: {
            type: "array",
            items: { type: "string" },
            description: "Optional warnings to attach to the job status",
          },
          error: {
            type: "string",
            description: "Optional error detail for failed jobs",
          },
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
          output_root: {
            type: "string",
            description: "Absolute or repo-relative output root that contains architecture/",
          },
          bridge_url: {
            type: "string",
            description:
              "Optional bridge base URL from the architect-comments channel event. Pass this to preserve the current submit URL in the rewritten diagram.html.",
          },
          render_mode: {
            type: "string",
            enum: ["fast", "rich"],
            description: "Requested render mode override. The current diagram's richer profile is preserved automatically when present.",
          },
        },
        required: ["output_root"],
      },
    },
    {
      name: "post_claude_comment",
      description:
        "Post a new Claude-authored comment thread anchored to a specific view/element/relationship in the architect diagram. Use this during plan mode to ask the user a focused design question at the place on the diagram where it matters.",
      inputSchema: {
        type: "object",
        properties: {
          bridge_url: {
            type: "string",
            description: "Bridge base URL (for example http://127.0.0.1:8765)",
          },
          output_root: {
            type: "string",
            description: "Absolute or repo-relative output root that contains architecture/",
          },
          view_id: {
            type: "string",
            description: "The id of the view (context, container, component, sequence) this comment is anchored to",
          },
          element_id: {
            type: "string",
            description: "Optional. The node/container id the comment is anchored to. Provide either element_id OR relationship_id, not both. Leave both null for a canvas-level comment.",
          },
          relationship_id: {
            type: "string",
            description: "Optional. The relationship id the comment is anchored to. Provide either element_id OR relationship_id, not both.",
          },
          target_label: {
            type: "string",
            description: "Human-readable label for the target (element or relationship display name). Stored verbatim so the thread still renders if the anchor is later removed.",
          },
          body: {
            type: "string",
            description: "The comment text. One focused question. State the default you assumed.",
          },
          diagram_revision_id: {
            type: "string",
            description: "Optional diagram_revision_id to stamp the thread with",
          },
        },
        required: ["bridge_url", "output_root", "view_id", "body"],
      },
    },
    {
      name: "post_claude_reply",
      description:
        "Post a Claude reply into an existing thread. Use this when responding to an architect_thread_user_reply event. Set resolves=true to mark the thread resolved after the reply lands. Set silent_resolve=true to resolve without writing a reply.",
      inputSchema: {
        type: "object",
        properties: {
          bridge_url: {
            type: "string",
            description: "Bridge base URL",
          },
          output_root: {
            type: "string",
            description: "Absolute or repo-relative output root that contains architecture/",
          },
          thread_id: {
            type: "string",
            description: "Thread id from the architect_thread_user_reply channel event",
          },
          body: {
            type: "string",
            description: "Reply text. Required unless silent_resolve=true.",
          },
          resolves: {
            type: "boolean",
            description: "If true, mark the thread resolved after appending this reply. Default false.",
          },
          silent_resolve: {
            type: "boolean",
            description: "If true, resolve the thread without appending a reply. body is ignored in this mode.",
          },
        },
        required: ["bridge_url", "output_root", "thread_id"],
      },
    },
    {
      name: "resolve_thread",
      description:
        "Silently resolve a Claude comment thread without posting a reply. Use this when a question has become moot and no textual response is needed.",
      inputSchema: {
        type: "object",
        properties: {
          bridge_url: {
            type: "string",
            description: "Bridge base URL",
          },
          output_root: {
            type: "string",
            description: "Absolute or repo-relative output root that contains architecture/",
          },
          thread_id: {
            type: "string",
            description: "Thread id to resolve",
          },
        },
        required: ["bridge_url", "output_root", "thread_id"],
      },
    },
  ],
}))

mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
  if (req.params.name === "update_feedback_status") {
    const result = await postBridgeStatus(req.params.arguments || {})
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              ok: true,
              job_id: result.job_id,
              state: result.state,
              message: result.message,
            },
            null,
            2,
          ),
        },
      ],
    }
  }

  if (req.params.name === "finalize_feedback_update") {
    const result = finalizeFeedbackUpdate(req.params.arguments || {})
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    }
  }

  if (req.params.name === "post_claude_comment") {
    const result = await postClaudeComment(req.params.arguments || {})
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    }
  }

  if (req.params.name === "post_claude_reply") {
    const result = await postClaudeReply(req.params.arguments || {})
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    }
  }

  if (req.params.name === "resolve_thread") {
    const result = await resolveThread(req.params.arguments || {})
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    }
  }

  throw new Error(`unknown tool: ${req.params.name}`)
})

async function sendChannelNotification(body) {
  const { meta, content } = buildChannelEvent(body)
  await mcp.notification({
    method: "notifications/claude/channel",
    params: { meta, content },
  })
  log("delivered channel event", { meta })
}

const httpServer = http.createServer(async (req, res) => {
  if (!req.url) {
    res.writeHead(400).end("missing url")
    return
  }

  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "content-type": "application/json" })
    res.end(JSON.stringify({ ok: true, name, port }))
    return
  }

  if (req.method !== "POST" || req.url !== "/notify") {
    res.writeHead(404).end("not found")
    return
  }

  if (secret) {
    const provided = req.headers["x-architect-secret"]
    if (provided !== secret) {
      res.writeHead(403).end("forbidden")
      return
    }
  }

  const chunks = []
  for await (const chunk of req) chunks.push(chunk)

  let body
  try {
    body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}")
  } catch {
    res.writeHead(400).end("invalid json")
    return
  }

  try {
    await sendChannelNotification(body)
    res.writeHead(202, { "content-type": "application/json" })
    res.end(JSON.stringify({ ok: true }))
  } catch (error) {
    log("failed to deliver channel event", { error: String(error) })
    res.writeHead(500).end("delivery failed")
  }
})

async function main() {
  const transport = new StdioServerTransport()
  await mcp.connect(transport)
  httpServer.listen(port, bind, () => {
    log("listening", { bind, port, name })
  })
}

main().catch((error) => {
  log("fatal", { error: String(error), stack: error?.stack || "" })
  process.exit(1)
})
