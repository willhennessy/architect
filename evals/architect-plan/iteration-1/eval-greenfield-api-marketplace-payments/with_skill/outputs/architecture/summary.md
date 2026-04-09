# Architecture Summary

## System Purpose
A greenfield B2B marketplace backend that supports buyer/seller activity, checkout, Stripe payments, and fulfillment handoff while preserving clear ownership boundaries for order and payment state.

## Repo Archetype
service_oriented_backend — the plan models discrete deployable services with explicit async boundaries and a shared transactional datastore.

## Primary Containers or Modules
- Marketplace API: public API for buyer/seller/admin actions
- Order Service: order lifecycle and checkout orchestration
- Payment Service: Stripe integration, webhook deduplication, and reconciliation
- Fulfillment Worker: async fulfillment processing
- Fulfillment Queue: decouples checkout completion from fulfillment execution
- Marketplace Database: authoritative transactional data store

## Critical Flows
- Checkout to payment authorization: enables order creation and charge handling
- Payment webhook reconciliation: ensures idempotent state transitions
- Async fulfillment enqueue/consume: isolates latency/failure in fulfillment systems

## Data Ownership Notes
- order/order-line/checkout-state: owned by Order Service
- payment-attempt: owned by Payment Service
- account/catalog-item/order/payment-attempt persistence: Marketplace Database as stored system of record for v1

## Major Risks or Unknowns
- Refund/partial capture policy and ownership split
- Dashboard freshness requirements for admin analytics
- Operational DLQ/retry policy specifics

## Recommended Next Reads
- `architecture/model.yaml`: canonical graph, evidence, and confidence
- `architecture/views/container.yaml`: runtime boundaries and relationships
- `architecture/views/sequence-checkout-to-fulfillment.yaml`: critical workflow

## Artifact Index
- `architecture/model.yaml`: canonical architecture model
- `architecture/views/system-context.yaml`: system context view
