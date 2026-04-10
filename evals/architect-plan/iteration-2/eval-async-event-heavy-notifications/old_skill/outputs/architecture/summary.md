# Architecture Summary

## System Purpose
Ingest and deliver high-volume notifications across multiple channels with failure isolation and provider swappability.

## Repo Archetype
service_oriented_backend with explicit event-driven boundaries.

## Primary Containers or Modules
- Notification API: validates and publishes delivery events
- Notification Bus: queues delivery workload and retries
- Delivery Worker: channel dispatch and retry policy enforcement

## Critical Flows
- Request ingestion -> event publish -> worker consume -> provider dispatch

## Data Ownership Notes
- delivery-attempt is owned by Delivery Worker
- provider delivery state remains external SoR

## Major Risks or Unknowns
- retention/replay policy and multi-tenant partitioning details

## Recommended Next Reads
- `architecture/model.yaml`: full canonical model

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/container.yaml`: container view
