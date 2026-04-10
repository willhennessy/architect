# Architecture Summary

## System Purpose
Capture and process patient intake data with strict PHI boundaries, role-based authorization, and immutable audit evidence.

## Repo Archetype
service_oriented_backend with security and compliance boundaries as first-class architecture concerns.

## Primary Containers or Modules
- Intake API: orchestrates intake workflows and external export
- Authorization Service: policy decision and role checks
- PHI Store: authoritative patient intake SoR
- Compliance Audit Log: immutable compliance evidence

## Critical Flows
- Intake submission -> authz decision -> PHI write -> audit append -> optional EHR export

## Data Ownership Notes
- patient-intake-record: PHI Store SoR
- audit-event: Compliance Audit Log SoR

## Major Risks or Unknowns
- KMS ownership and key rotation operating model

## Recommended Next Reads
- `architecture/model.yaml`: canonical evidence-backed model

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/container.yaml`: container view
