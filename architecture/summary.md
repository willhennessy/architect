# Architecture Summary

## System Purpose
DocSign is a multi-tenant B2B SaaS platform for document e-signature workflows. Tenants (customer organizations) create and send documents; signers authenticate via a 6-digit OTP sent to their email, without needing a platform account. The platform delivers real-time webhook callbacks to customer backend systems on signature events, maintains an immutable audit trail, and provides tenant admins with an analytics dashboard.

## Repo Archetype
`full_stack_product` — the system ships multiple deployable boundaries (frontend apps, backend API, async worker, datastores) that together form a complete customer-facing product.

## Primary Containers or Modules
- **Admin Web App**: Svelte SPA for tenant admins — document creation, signer assignment, status tracking, analytics dashboard
- **Signer Portal**: Public-facing React app — OTP entry, document review, signature capture
- **API Server**: Node.js REST API — multi-tenant enforcement, document lifecycle, OTP validation, synchronous audit writes, job dispatch
- **Async Worker**: Background job processor — OTP email dispatch, webhook delivery with retries, PDF finalization
- **Primary Database**: MongoDB — system of record for all transactional + audit data (tenant_id-scoped documents)
- **Document Storage**: S3 object storage — raw uploaded documents + finalized signed PDFs
- **Job Queue**: Redis/SQS — async job buffering decoupling the API from email and webhook delivery

## Critical Flows
- **Document Send**: Admin uploads document → API stores in S3, creates signing session in DB → enqueues email job → Worker dispatches OTP code email to signer
- **Signing**: Signer opens signing URL → Portal prompts for 6-digit OTP → Portal submits OTP to API → API validates OTP, serves document from S3 → Signer submits signature → API writes signature + audit event to DB → enqueues webhook + PDF finalization jobs → Worker delivers webhook to customer and writes signed PDF to S3
- **Webhook Delivery**: Worker dequeues job → POSTs to customer endpoint → on failure, exponential-backoff retry tracked in DB → final delivery state reflected in audit trail
- **Analytics**: Admin Web App queries API → API runs tenant-scoped aggregation queries on DB → returns metrics (document completion rates, time-to-sign, pending queue)

## Key Decisions
- [DEC-001] Modular monolith (API + Worker) over microservices for MVP | covers: container-api,container-worker,view-container
- [DEC-002] Separate Signer Portal from Admin Web App for independent security posture on the public signer flow | covers: container-web-app,container-signer-portal,rel-admin-webapp,rel-signer-portal,view-container
- [DEC-003] Document-level tenant_id isolation in MongoDB over schema-per-tenant for MVP multi-tenancy simplicity | covers: container-api,db-primary,view-container
- [DEC-004] Audit events written synchronously within the signing operation (not via async queue) to guarantee atomicity and correctness | covers: container-api,db-primary,rel-api-db
- [DEC-005] Async queue for webhook + email delivery to enable reliable retries independent of the API request cycle | covers: queue-jobs,container-worker,rel-api-queue,rel-worker-queue,rel-worker-webhook,rel-worker-email,view-container
- [DEC-006] S3-compatible object storage for documents to separate file durability from transactional DB | covers: store-documents,rel-api-store,rel-worker-store,view-container

## Data Ownership Notes
- **Documents**: system of record is `db-primary` (metadata) and `store-documents` (file bytes)
- **Signatures**: system of record is `db-primary`
- **Audit events**: system of record is `db-primary` (append-only `audit_events` table)
- **Tenant accounts / users**: system of record is `db-primary`
- **Webhook configs**: system of record is `db-primary`
- **Raw + signed PDFs**: system of record is `store-documents`

## Major Risks or Unknowns
- **Compliance scope not confirmed**: HIPAA, SOC 2, or eIDAS requirements could materially change the signing method and data residency architecture
- **Webhook reliability contract undefined**: retry policy, dead-letter handling, and max-attempt SLA need product decisions before implementation
- **Signature capture method unspecified**: typed, drawn, or cryptographic — determines complexity of PDF finalization and legal validity
- **Analytics scale unknown**: if tenant document volumes grow large, MongoDB aggregation pipelines may not be sufficient and a separate OLAP store may be needed
- **Tenant auth method undefined**: email/password, OAuth, or enterprise SSO (SAML) for tenant admins is unconfirmed
- **Row-level isolation risk**: without careful ORM/query discipline, cross-tenant data leaks are a constant risk — a tenant_id enforcement middleware layer is required

## Recommended Next Reads
- `architecture/model.yaml`: full canonical element and relationship graph
- `architecture/views/container.yaml`: container-level deployment boundaries and interactions
- `architecture/views/system-context.yaml`: top-level actor and external system map

## Artifact Index
- `architecture/manifest.yaml`: scope, mode, evidence basis, and artifact index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/system-context.yaml`: system context view
- `architecture/views/container.yaml`: container view
- `architecture/diagram.html`: interactive HTML diagram with drill-down navigation
