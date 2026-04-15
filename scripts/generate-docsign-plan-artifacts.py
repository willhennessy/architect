#!/usr/bin/env python3
"""Generate architecture artifacts for the fixed DocSign test prompt.

This script is used by manual test harness runs when architect-plan changes.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import yaml


def dump_yaml(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", required=True)
    args = ap.parse_args()

    out = Path(args.output_root).expanduser().resolve()
    arch = out / "architecture"
    views = arch / "views"
    arch.mkdir(parents=True, exist_ok=True)
    views.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 2,
        "system_name": "DocSign Platform",
        "generated_by_skill": "architect-plan",
        "mode": "initial",
        "evidence_basis": "plan",
        "architecture_state": "proposed",
        "repo_archetype": "service_oriented_backend",
        "modeling_style": {"primary": "C4", "supplemental": ["Sequence"]},
        "scope": {
            "in_scope": ["multi-tenant B2B document signing MVP"],
            "out_of_scope": ["advanced enterprise integrations beyond webhook", "native mobile app"],
        },
        "audiences": ["pms", "senior_architects", "new_hires"],
        "artifacts": [
            {"id": "model", "path": "architecture/model.yaml", "type": "canonical_model", "status": "complete"},
            {"id": "view-system-context", "path": "architecture/views/system-context.yaml", "type": "view", "status": "complete"},
            {"id": "view-container", "path": "architecture/views/container.yaml", "type": "view", "status": "complete"},
            {"id": "view-sequence-signing", "path": "architecture/views/sequence-signing-flow.yaml", "type": "view", "status": "complete"},
        ],
        "assumptions": [
            {"text": "Single region MVP with managed cloud services", "confidence": "strong_inference"},
            {"text": "Event volume is moderate in first 10 weeks", "confidence": "strong_inference"},
        ],
        "unknowns": [
            "Exact webhook delivery SLA per customer tier",
            "Whether customers require webhook replay APIs at MVP",
            "Target analytics freshness requirements for admin dashboard",
            "Regional data residency commitments for early design partners",
        ],
        "overall_summary": "The architecture separates core signing, notification, webhook, and audit concerns to keep ownership clear across a small team. A Platform API orchestrates document flows while async services ensure reliable outbound messaging and immutable audit capture. This decomposition supports a 10-week MVP while preserving extensibility for stricter compliance and larger tenant scale.",
    }

    evidence = [
        {"id": "req-signing", "path": "plan://requirements/signing", "kind": "plan_requirement", "strength": "high", "reason": "Core signer flow + document lifecycle requirement"},
        {"id": "req-webhooks", "path": "plan://requirements/webhooks", "kind": "plan_requirement", "strength": "high", "reason": "Customer callback requirement"},
        {"id": "req-audit", "path": "plan://requirements/audit", "kind": "plan_requirement", "strength": "high", "reason": "Tamper-evident audit requirement"},
        {"id": "req-analytics", "path": "plan://requirements/analytics", "kind": "plan_requirement", "strength": "medium", "reason": "Admin dashboard needs usage/ops metrics"},
        {"id": "con-team", "path": "plan://constraints/team-size", "kind": "plan_constraint", "strength": "high", "reason": "Five engineers requires clear service boundaries"},
        {"id": "con-timeline", "path": "plan://constraints/timeline", "kind": "plan_constraint", "strength": "high", "reason": "10-week MVP favors managed services and simple ownership"},
        {"id": "trd-decomposition", "path": "plan://tradeoffs/service-decomposition", "kind": "plan_tradeoff", "strength": "medium", "reason": "Separate async responsibilities for reliability and observability"},
    ]

    elements = [
        {
            "id": "person-doc-sender",
            "name": "Document Sender",
            "aliases": ["B2B Customer System User"],
            "kind": "person",
            "c4_level": "context",
            "description": "Business user who uploads and sends documents for signature.",
            "responsibility": "Initiates signing workflows.",
            "technology": "",
            "owned_data": ["document templates"],
            "system_of_record": ["customer internal source systems"],
            "runtime_boundary": "external",
            "deployable": False,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://actors/document-sender"],
            "tags": ["actor"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing"],
        },
        {
            "id": "person-document-signer",
            "name": "Document Signer",
            "aliases": ["Recipient"],
            "kind": "person",
            "c4_level": "context",
            "description": "End user who signs documents via magic-link flow.",
            "responsibility": "Signs requested documents.",
            "technology": "",
            "owned_data": ["signature intent"],
            "system_of_record": ["DocSign Platform"],
            "runtime_boundary": "external",
            "deployable": False,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://actors/document-signer"],
            "tags": ["actor"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing"],
        },
        {
            "id": "person-platform-admin",
            "name": "Platform Admin",
            "aliases": ["Tenant Admin"],
            "kind": "person",
            "c4_level": "context",
            "description": "Admin user configuring webhook settings and dashboard views.",
            "responsibility": "Operates tenant settings and analytics.",
            "technology": "",
            "owned_data": ["tenant configuration"],
            "system_of_record": ["DocSign Platform"],
            "runtime_boundary": "external",
            "deployable": False,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://actors/platform-admin"],
            "tags": ["actor"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-analytics"],
        },
        {
            "id": "sys-docsign-platform",
            "name": "DocSign Platform",
            "aliases": ["Multi-tenant Document Signing System"],
            "kind": "software_system",
            "c4_level": "context",
            "description": "Multi-tenant B2B document signing platform.",
            "responsibility": "Provides signing workflows, callbacks, audit, and analytics.",
            "technology": "Managed cloud + Node.js services",
            "owned_data": ["documents", "signature events", "tenant config"],
            "system_of_record": ["documents", "signature status", "audit events"],
            "runtime_boundary": "process",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://system/docsign"],
            "tags": ["core-system"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "req-webhooks", "req-audit", "req-analytics"],
        },
        {
            "id": "ext-customer-webhook-endpoint",
            "name": "Customer Webhook Endpoint",
            "aliases": ["Customer Callback Receiver"],
            "kind": "external_system",
            "c4_level": "context",
            "description": "Customer-owned endpoint receiving signing lifecycle callbacks.",
            "responsibility": "Consumes callback events.",
            "technology": "HTTPS endpoint",
            "owned_data": ["customer integration events"],
            "system_of_record": ["customer systems"],
            "runtime_boundary": "external",
            "deployable": True,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://external/customer-webhooks"],
            "tags": ["external-callback"],
            "confidence": "confirmed",
            "evidence_ids": ["req-webhooks"],
        },
        {
            "id": "ext-email-provider",
            "name": "Email Provider",
            "aliases": ["SES/SendGrid"],
            "kind": "external_system",
            "c4_level": "context",
            "description": "Third-party outbound email delivery provider.",
            "responsibility": "Delivers magic-link emails.",
            "technology": "SES or SendGrid API",
            "owned_data": ["email delivery logs"],
            "system_of_record": ["provider telemetry"],
            "runtime_boundary": "external",
            "deployable": True,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://external/email-provider"],
            "tags": ["external-communication"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing"],
        },
        {
            "id": "ext-object-storage",
            "name": "Object Storage (S3)",
            "aliases": ["Blob Store"],
            "kind": "external_system",
            "c4_level": "context",
            "description": "Durable binary document storage.",
            "responsibility": "Stores document binaries and signed artifacts.",
            "technology": "Amazon S3",
            "owned_data": ["document binaries", "signed PDFs"],
            "system_of_record": ["document binaries"],
            "runtime_boundary": "external",
            "deployable": True,
            "external": True,
            "parent_id": "",
            "source_paths": ["plan://external/object-storage"],
            "tags": ["storage"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing"],
        },
        {
            "id": "container-web-application",
            "name": "Web Application",
            "aliases": ["Web SPA"],
            "kind": "container",
            "c4_level": "container",
            "description": "Tenant-facing UI for document send, signing progress, and admin dashboard.",
            "responsibility": "Renders sender/admin workflows and signer screens.",
            "technology": "Next.js / React",
            "owned_data": ["session state"],
            "system_of_record": ["none"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/web-application"],
            "tags": ["frontend"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "req-analytics", "con-team"],
        },
        {
            "id": "container-platform-api",
            "name": "Platform API",
            "aliases": ["API Server"],
            "kind": "container",
            "c4_level": "container",
            "description": "Core API for documents, signing orchestration, tenant config, and analytics reads.",
            "responsibility": "Orchestrates sync requests and emits async work items.",
            "technology": "Node.js",
            "owned_data": ["document metadata", "tenant configuration", "signature status"],
            "system_of_record": ["document metadata", "signature status", "tenant configuration"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/platform-api"],
            "tags": ["backend"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "req-webhooks", "req-analytics"],
        },
        {
            "id": "container-signing-service",
            "name": "Signing Service",
            "aliases": ["Magic Link Signing"],
            "kind": "container",
            "c4_level": "container",
            "description": "Handles signer identity challenge and signature capture lifecycle.",
            "responsibility": "Processes signing actions and emits signature events.",
            "technology": "Node.js",
            "owned_data": ["magic-link tokens", "signature events"],
            "system_of_record": ["signature events"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/signing-service"],
            "tags": ["domain-signing"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "trd-decomposition"],
        },
        {
            "id": "container-notification-service",
            "name": "Notification Service",
            "aliases": ["Email Notification Worker"],
            "kind": "container",
            "c4_level": "container",
            "description": "Consumes async events and sends notification emails.",
            "responsibility": "Delivers magic-link and status emails.",
            "technology": "Node.js worker",
            "owned_data": ["notification jobs"],
            "system_of_record": ["notification delivery status"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/notification-service"],
            "tags": ["async", "notification"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "trd-decomposition"],
        },
        {
            "id": "container-webhook-service",
            "name": "Webhook Service",
            "aliases": ["Callback Dispatcher"],
            "kind": "container",
            "c4_level": "container",
            "description": "Delivers signed-event webhooks to customer endpoints with retries.",
            "responsibility": "Publishes customer callbacks.",
            "technology": "Node.js worker",
            "owned_data": ["webhook delivery attempts"],
            "system_of_record": ["webhook delivery status"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/webhook-service"],
            "tags": ["async", "webhook"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-webhooks", "trd-decomposition"],
        },
        {
            "id": "container-audit-service",
            "name": "Audit Service",
            "aliases": ["Audit Writer"],
            "kind": "container",
            "c4_level": "container",
            "description": "Persists immutable audit events for compliance and forensic tracing.",
            "responsibility": "Writes append-only audit trail.",
            "technology": "Node.js worker",
            "owned_data": ["audit event stream"],
            "system_of_record": ["audit trail"],
            "runtime_boundary": "deployable",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://containers/audit-service"],
            "tags": ["async", "audit"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-audit", "trd-decomposition"],
        },
        {
            "id": "database-postgres-primary",
            "name": "PostgreSQL (Primary)",
            "aliases": ["Primary DB"],
            "kind": "database",
            "c4_level": "container",
            "description": "Primary relational store for tenants, documents, signer state, and config.",
            "responsibility": "Serves transactional system-of-record data.",
            "technology": "PostgreSQL",
            "owned_data": ["tenants", "documents", "signatures", "settings"],
            "system_of_record": ["tenants", "documents", "signature status", "tenant configuration"],
            "runtime_boundary": "data_store",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://datastores/postgres-primary"],
            "tags": ["database"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-signing", "req-analytics"],
        },
        {
            "id": "queue-message-queue",
            "name": "Message Queue",
            "aliases": ["SQS/BullMQ"],
            "kind": "queue",
            "c4_level": "container",
            "description": "Decouples async work for notifications, webhooks, and audit processing.",
            "responsibility": "Buffers and fans out async jobs.",
            "technology": "SQS or BullMQ",
            "owned_data": ["notification jobs", "webhook jobs", "audit jobs"],
            "system_of_record": ["none"],
            "runtime_boundary": "data_store",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://datastores/message-queue"],
            "tags": ["queue"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-webhooks", "req-audit", "trd-decomposition"],
        },
        {
            "id": "database-audit-log",
            "name": "Audit Log",
            "aliases": ["Append-only Audit Table"],
            "kind": "database",
            "c4_level": "container",
            "description": "Immutable append-only audit ledger for compliance.",
            "responsibility": "Stores signed-event audit records.",
            "technology": "PostgreSQL append-only table",
            "owned_data": ["audit trail"],
            "system_of_record": ["audit trail"],
            "runtime_boundary": "data_store",
            "deployable": True,
            "external": False,
            "parent_id": "",
            "source_paths": ["plan://datastores/audit-log"],
            "tags": ["database", "audit"],
            "confidence": "strong_inference",
            "evidence_ids": ["req-audit", "trd-decomposition"],
        },
    ]

    relationships = [
        {"id": "rel-sender-webapp", "source_id": "person-doc-sender", "target_id": "container-web-application", "label": "Uses sender workflow", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "human", "protocol": "https", "data_objects": ["document drafts"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-signer-webapp", "source_id": "person-document-signer", "target_id": "container-web-application", "label": "Opens magic-link signing page", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "human", "protocol": "https", "data_objects": ["magic-link token"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-admin-webapp", "source_id": "person-platform-admin", "target_id": "container-web-application", "label": "Views admin analytics dashboard", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "human", "protocol": "https", "data_objects": ["analytics queries"], "confidence": "strong_inference", "evidence_ids": ["req-analytics"]},
        {"id": "rel-webapp-api", "source_id": "container-web-application", "target_id": "container-platform-api", "label": "Calls authenticated platform APIs", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "sync", "protocol": "https", "data_objects": ["documents", "tenant settings", "dashboard stats"], "confidence": "strong_inference", "evidence_ids": ["req-signing", "req-analytics"]},
        {"id": "rel-api-signing", "source_id": "container-platform-api", "target_id": "container-signing-service", "label": "Starts signing sessions", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "sync", "protocol": "https", "data_objects": ["signing session"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-signing-queue", "source_id": "container-signing-service", "target_id": "queue-message-queue", "label": "Publishes signature events", "interaction_type": "publishes", "directionality": "unidirectional", "sync_async": "async", "protocol": "n_a", "data_objects": ["signature events"], "confidence": "strong_inference", "evidence_ids": ["req-signing", "trd-decomposition"]},
        {"id": "rel-api-queue", "source_id": "container-platform-api", "target_id": "queue-message-queue", "label": "Publishes notification/webhook/audit jobs", "interaction_type": "publishes", "directionality": "unidirectional", "sync_async": "async", "protocol": "n_a", "data_objects": ["job envelopes"], "confidence": "strong_inference", "evidence_ids": ["req-webhooks", "req-audit"]},
        {"id": "rel-notification-queue", "source_id": "queue-message-queue", "target_id": "container-notification-service", "label": "Notification jobs", "interaction_type": "subscribes", "directionality": "unidirectional", "sync_async": "async", "protocol": "n_a", "data_objects": ["notification jobs"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-webhook-queue", "source_id": "queue-message-queue", "target_id": "container-webhook-service", "label": "Webhook jobs", "interaction_type": "subscribes", "directionality": "unidirectional", "sync_async": "async", "protocol": "n_a", "data_objects": ["webhook jobs"], "confidence": "strong_inference", "evidence_ids": ["req-webhooks"]},
        {"id": "rel-audit-queue", "source_id": "queue-message-queue", "target_id": "container-audit-service", "label": "Audit jobs", "interaction_type": "subscribes", "directionality": "unidirectional", "sync_async": "async", "protocol": "n_a", "data_objects": ["audit jobs"], "confidence": "strong_inference", "evidence_ids": ["req-audit"]},
        {"id": "rel-notification-email", "source_id": "container-notification-service", "target_id": "ext-email-provider", "label": "Sends magic-link/status emails", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "async", "protocol": "https", "data_objects": ["email payloads"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-webhook-customer", "source_id": "container-webhook-service", "target_id": "ext-customer-webhook-endpoint", "label": "POST signature callbacks with retry", "interaction_type": "calls", "directionality": "unidirectional", "sync_async": "async", "protocol": "https", "data_objects": ["callback events"], "confidence": "confirmed", "evidence_ids": ["req-webhooks"]},
        {"id": "rel-audit-log", "source_id": "container-audit-service", "target_id": "database-audit-log", "label": "Appends immutable audit events", "interaction_type": "writes", "directionality": "unidirectional", "sync_async": "storage", "protocol": "sql", "data_objects": ["audit events"], "confidence": "strong_inference", "evidence_ids": ["req-audit"]},
        {"id": "rel-api-postgres", "source_id": "container-platform-api", "target_id": "database-postgres-primary", "label": "Reads/writes core metadata", "interaction_type": "writes", "directionality": "unidirectional", "sync_async": "storage", "protocol": "sql", "data_objects": ["documents", "tenants", "signing status"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-signing-postgres", "source_id": "container-signing-service", "target_id": "database-postgres-primary", "label": "Stores signer state", "interaction_type": "writes", "directionality": "unidirectional", "sync_async": "storage", "protocol": "sql", "data_objects": ["magic-link tokens", "signature records"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-api-storage", "source_id": "container-platform-api", "target_id": "ext-object-storage", "label": "Reads/writes PDF binaries", "interaction_type": "stores", "directionality": "unidirectional", "sync_async": "storage", "protocol": "s3", "data_objects": ["PDF binaries"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
        {"id": "rel-webapp-storage", "source_id": "container-web-application", "target_id": "ext-object-storage", "label": "Downloads signed files via pre-signed URLs", "interaction_type": "reads", "directionality": "unidirectional", "sync_async": "sync", "protocol": "https", "data_objects": ["signed PDFs"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
    ]

    model = {
        "version": 2,
        "system_name": "DocSign Platform",
        "repo_archetype": "service_oriented_backend",
        "elements": elements,
        "relationships": relationships,
        "evidence": evidence,
        "unknowns": manifest["unknowns"],
        "assumptions": [
            {"text": "Background workers can be deployed independently.", "confidence": "strong_inference"},
            {"text": "Audit table append-only enforcement is available in DB layer.", "confidence": "weak_inference"},
        ],
    }

    system_context = {
        "version": 2,
        "id": "system-context",
        "type": "system_context",
        "title": "DocSign Platform — System Context",
        "audience": ["pms", "senior_architects"],
        "purpose": "Show the system boundary and external actors/integrations.",
        "scope": "External actors and systems around DocSign Platform.",
        "source_model": "architecture/model.yaml",
        "element_ids": [
            "person-doc-sender",
            "person-document-signer",
            "person-platform-admin",
            "sys-docsign-platform",
            "ext-customer-webhook-endpoint",
            "ext-email-provider",
            "ext-object-storage",
        ],
        "relationship_ids": [
            "rel-sender-webapp",
            "rel-signer-webapp",
            "rel-admin-webapp",
            "rel-webhook-customer",
            "rel-notification-email",
            "rel-api-storage",
            "rel-webapp-storage",
        ],
        "assumptions": [{"text": "DocSign is the system of interest.", "confidence": "confirmed"}],
        "unknowns": ["Exact customer webhook auth scheme."],
        "notes": ["Container internals hidden at this level."],
    }

    container_view = {
        "version": 2,
        "id": "container",
        "type": "container",
        "title": "DocSign Platform — Container View",
        "audience": ["senior_architects", "new_hires"],
        "purpose": "Show deployable units and their interactions for MVP scope.",
        "scope": "Core containers, external integrations, and primary data stores.",
        "source_model": "architecture/model.yaml",
        "element_ids": [
            "person-doc-sender",
            "person-document-signer",
            "person-platform-admin",
            "container-web-application",
            "container-platform-api",
            "container-signing-service",
            "container-notification-service",
            "container-webhook-service",
            "container-audit-service",
            "database-postgres-primary",
            "queue-message-queue",
            "database-audit-log",
            "ext-customer-webhook-endpoint",
            "ext-email-provider",
            "ext-object-storage",
        ],
        "relationship_ids": [r["id"] for r in relationships if r["id"] != "rel-webapp-storage"],
        "assumptions": [{"text": "Single region managed queue and database for MVP.", "confidence": "strong_inference"}],
        "unknowns": ["Need final retry/backoff policy per tenant SLA tiers."],
        "notes": ["Async responsibilities intentionally split into webhook, notification, and audit services."],
    }

    sequence = {
        "version": 2,
        "id": "sequence-signing-flow",
        "type": "sequence",
        "title": "Signer Magic-Link Authentication and Signing Flow",
        "audience": ["pms", "senior_architects"],
        "purpose": "Explain end-to-end signing lifecycle with async fanout.",
        "scope": "From send action to callbacks and audit persistence.",
        "source_model": "architecture/model.yaml",
        "participant_ids": [
            "person-doc-sender",
            "container-web-application",
            "container-platform-api",
            "container-signing-service",
            "queue-message-queue",
            "container-notification-service",
            "container-webhook-service",
            "container-audit-service",
            "ext-email-provider",
            "ext-customer-webhook-endpoint",
            "database-audit-log",
        ],
        "steps": [
            {"order": 1, "source_id": "person-doc-sender", "target_id": "container-web-application", "relationship_id": "rel-sender-webapp", "label": "Create and send document", "sync_async": "human", "data_objects": ["document request"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 2, "source_id": "container-web-application", "target_id": "container-platform-api", "relationship_id": "rel-webapp-api", "label": "Submit document + recipients", "sync_async": "sync", "data_objects": ["document metadata"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 3, "source_id": "container-platform-api", "target_id": "container-signing-service", "relationship_id": "rel-api-signing", "label": "Initiate signer session", "sync_async": "sync", "data_objects": ["signer session"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 4, "source_id": "container-signing-service", "target_id": "queue-message-queue", "relationship_id": "rel-signing-queue", "label": "Publish signer event", "sync_async": "async", "data_objects": ["signer event"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 5, "source_id": "queue-message-queue", "target_id": "container-notification-service", "relationship_id": "rel-notification-queue", "label": "Dispatch email job", "sync_async": "async", "data_objects": ["notification job"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 6, "source_id": "container-notification-service", "target_id": "ext-email-provider", "relationship_id": "rel-notification-email", "label": "Send magic-link email", "sync_async": "async", "data_objects": ["email payload"], "confidence": "strong_inference", "evidence_ids": ["req-signing"]},
            {"order": 7, "source_id": "container-signing-service", "target_id": "queue-message-queue", "relationship_id": "rel-signing-queue", "label": "Publish signed event", "sync_async": "async", "data_objects": ["signed event"], "confidence": "strong_inference", "evidence_ids": ["req-webhooks", "req-audit"]},
            {"order": 8, "source_id": "queue-message-queue", "target_id": "container-webhook-service", "relationship_id": "rel-webhook-queue", "label": "Dispatch callback job", "sync_async": "async", "data_objects": ["webhook job"], "confidence": "strong_inference", "evidence_ids": ["req-webhooks"]},
            {"order": 9, "source_id": "container-webhook-service", "target_id": "ext-customer-webhook-endpoint", "relationship_id": "rel-webhook-customer", "label": "POST signed callback", "sync_async": "async", "data_objects": ["callback event"], "confidence": "confirmed", "evidence_ids": ["req-webhooks"]},
            {"order": 10, "source_id": "queue-message-queue", "target_id": "container-audit-service", "relationship_id": "rel-audit-queue", "label": "Dispatch audit job", "sync_async": "async", "data_objects": ["audit job"], "confidence": "strong_inference", "evidence_ids": ["req-audit"]},
            {"order": 11, "source_id": "container-audit-service", "target_id": "database-audit-log", "relationship_id": "rel-audit-log", "label": "Append immutable audit row", "sync_async": "storage", "data_objects": ["audit record"], "confidence": "strong_inference", "evidence_ids": ["req-audit"]},
        ],
        "assumptions": [{"text": "Callback retries are idempotent per event key.", "confidence": "strong_inference"}],
        "unknowns": ["Replay API scope for webhook failures."],
        "notes": ["Sequence emphasizes async decomposition for reliability and compliance."],
    }

    summary = """# Architecture Summary

## System Purpose
DocSign Platform enables multi-tenant B2B document signing with sender/admin workflows, signer magic-link flows, reliable customer callbacks, immutable audit history, and an operational analytics dashboard for tenant admins.

## Repo Archetype
service_oriented_backend — the MVP is dominated by API + worker services with asynchronous processing and strong data/audit boundaries.

## Primary Containers or Modules
- Web Application: sender/admin UX, signer entry screens, and dashboard rendering.
- Platform API: orchestrates document lifecycle, tenant config, and sync API surface.
- Signing Service: signer-session and signature-state processing.
- Notification Service: outbound email notifications (magic-link + status).
- Webhook Service: customer callback delivery with retry logic.
- Audit Service: append-only audit persistence.
- PostgreSQL (Primary): source of truth for documents/tenants/signature state.
- Message Queue: decoupled async fanout for notification/webhook/audit jobs.
- Audit Log: immutable compliance event history.

## Critical Flows
- Sender to signer initiation: sender submits document, API creates signer session, notification service sends magic-link email.
- Signed-event fanout: signing completion emits async events consumed separately by webhook and audit services.
- Admin analytics: dashboard reads aggregate operational metrics from primary stores.

## Key Decisions
- [DEC-001] Separate async responsibilities into Notification, Webhook, and Audit services to avoid tight coupling and improve operability with a 5-engineer team | covers: container-notification-service,container-webhook-service,container-audit-service,queue-message-queue,container
- [DEC-002] Keep append-only audit log in PostgreSQL-based store for MVP compliance traceability over introducing new datastores | covers: database-audit-log,rel-audit-log,container-audit-service
- [DEC-003] Use queue-mediated fanout so webhook retries do not block signing UX | covers: rel-signing-queue,rel-webhook-queue,container-webhook-service
- [DEC-004] Keep API orchestration centralized in Platform API while signer state handling remains in dedicated Signing Service | covers: container-platform-api,container-signing-service,rel-api-signing
- [DEC-005] Include admin analytics in MVP scope through existing service/data boundaries (no separate analytics platform in MVP) | covers: person-platform-admin,container-web-application,container-platform-api,database-postgres-primary

## Data Ownership Notes
- documents/signature status: Platform API + PostgreSQL (Primary) system of record.
- webhook delivery status: Webhook Service owns delivery attempts and retry outcomes.
- audit trail: Audit Service writes immutable records to Audit Log.
- notification delivery state: Notification Service tracks provider outcomes.

## Major Risks or Unknowns
- Webhook retry policy and backoff tuning by tenant SLA tier.
- Need for webhook replay and signature-event export endpoints in MVP.
- Analytics freshness/aggregation strategy for dashboard under load.
- Potential regional data residency requirements for early enterprise tenants.

## Recommended Next Reads
- `architecture/model.yaml`: canonical element and relationship graph.
- `architecture/views/container.yaml`: deployable boundaries and async split.
- `architecture/views/sequence-signing-flow.yaml`: end-to-end signing + callback + audit flow.

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/system-context.yaml`: system context view
"""

    dump_yaml(arch / "manifest.yaml", manifest)
    dump_yaml(arch / "model.yaml", model)
    dump_yaml(views / "system-context.yaml", system_context)
    dump_yaml(views / "container.yaml", container_view)
    dump_yaml(views / "sequence-signing-flow.yaml", sequence)
    (arch / "summary.md").write_text(summary, encoding="utf-8")

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
