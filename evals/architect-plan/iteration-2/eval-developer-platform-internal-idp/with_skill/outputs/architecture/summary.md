# Architecture Summary

## System Purpose
Internal Developer Platform planning architecture with explicit service, async, and data ownership boundaries.

## Repo Archetype
service_oriented_backend

## Primary Containers or Modules
- API Service: synchronous orchestration boundary
- Workflow Worker: async execution boundary
- Workflow Queue: decoupling and retry boundary
- Primary Database: canonical SoR boundary

## Critical Flows
- User request -> API -> async queue -> worker -> persisted outcomes

## Data Ownership Notes
- domain-entity SoR: Primary Database
- workflow-attempt ownership: Workflow Worker

## Major Risks or Unknowns
- Final throughput/SLO targets and operational policy specifics

## Recommended Next Reads
- `architecture/model.yaml`: canonical graph and evidence

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/container.yaml`: container view
