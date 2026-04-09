# Architecture Summary

## System Purpose
Provide posting, comments, and feed experiences for a new social app while preserving explicit uncertainty where requirements are missing.

## Repo Archetype
full_stack_product with backend boundaries modeled for content write/read and moderation pipelines.

## Primary Containers or Modules
- Social API: write/read API orchestration
- Feed Service: feed computation boundary
- Moderation Queue: async moderation intake
- Social Database: canonical content persistence

## Critical Flows
- user request -> Social API -> write/read path
- post/comment write -> moderation task publish

## Data Ownership Notes
- post/comment SoR: Social Database
- feed-read-model: derived data owned by Feed Service (non-authoritative)

## Major Risks or Unknowns
- target DAU/throughput and moderation operating model
- regulatory and data residency constraints

## Recommended Next Reads
- `architecture/model.yaml`: confidence-labeled claims and unknowns

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/container.yaml`: container view
