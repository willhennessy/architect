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

function buildFeedbackContent(body) {
  const comments = Array.isArray(body.comments) ? body.comments : []
  const header = [
    "Architect feedback batch received.",
    "",
    `Job: ${body.job_id || "unknown"}`,
    `Bridge URL: ${body.bridge_url || ""}`,
    `Output root: ${body.output_root || ""}`,
    `Diagram revision: ${body.diagram_revision_id || ""}`,
    "",
    "Comments:",
  ]
  const lines = comments.length
    ? comments.map((comment, index) => formatComment(comment, index))
    : ["1. No comments were included."]
  const footer = [
    "",
    "Please:",
    `1. Acknowledge receipt to the user immediately and call update_feedback_status with state=acknowledged.`,
    "2. Inspect the referenced job and output root to gather the needed context, then call update_feedback_status with state=analyzing.",
    "3. Implement the requested updates directly instead of stopping at a plan, unless you are blocked or the feedback is genuinely ambiguous or high-risk.",
    "4. Keep edits contract-safe. Use canonical model kinds like `database`, not `datastore`.",
    "5. After editing, call finalize_feedback_update with the output_root and bridge_url instead of guessing render commands.",
    '6. If finalize succeeds, call update_feedback_status with state=completed and the exact message: "Refresh the page to see updates."',
    "7. If you are blocked or validation fails, report it with update_feedback_status using state=blocked or state=failed and a concise reason.",
    "8. When you tell the user what changed, summarize the actual edits you wrote. Do not imply bidirectionality unless the relationship is truly bidirectional in the model.",
  ]
  return [...header, ...lines, ...footer].join("\n")
}

function buildChannelEvent(body) {
  const eventType = String(body.event_type || "architect_feedback_batch")
  const comments = Array.isArray(body.comments) ? body.comments : []
  const meta = sanitizeMeta({
    event_type: eventType,
    state: body.state || "",
    job_id: body.job_id || randomUUID(),
    bridge_url: body.bridge_url || "",
    output_root: body.output_root || "",
    diagram_revision_id: body.diagram_revision_id || "",
    comment_count: String(comments.length),
  })
  const content =
    eventType === "architect_feedback_batch"
      ? buildFeedbackContent(body)
      : stringifyValue(body.content || body.message || body)
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
      "When a feedback batch arrives, acknowledge it in the active Claude session, " +
      "inspect the referenced output root and job details, and implement the requested updates directly. " +
      "Do not stop after proposing a plan unless you are blocked or the feedback is genuinely ambiguous or high-risk. " +
      "Use update_feedback_status to report progress back to the browser bridge in a compact user-facing voice. " +
      "After you edit the artifacts, call finalize_feedback_update instead of guessing shell commands so validation and rendering stay deterministic. " +
      "Keep model edits contract-safe, for example use `database` instead of `datastore`. " +
      "When you summarize the result, describe the actual written graph changes and keep the browser-ready completion message short.",
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
