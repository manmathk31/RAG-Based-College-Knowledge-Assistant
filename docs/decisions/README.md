# Architecture Decision Records (ADRs)

## What is an Architecture Decision Record?

An Architecture Decision Record (ADR) is a lightweight document that captures a significant architectural decision made in the project, along with its context, rationale, trade-offs, and consequences.

Recording architectural decisions prevents knowledge loss, eliminates recurring debates on previously settled choices, and provides clear guardrails for both human contributors and AI coding agents.

## Structure of an ADR

Every ADR in this directory must follow this standard format:

1. **Title**: Sequentially numbered with a clear slug (e.g., `ADR-001-INITIAL-ARCHITECTURE.md`).
2. **Status**: `PROPOSED`, `ACCEPTED`, `REJECTED`, `SUPERSEDED`, or `DEPRECATED`.
3. **Date**: The date the decision was accepted.
4. **Context**: What problem or requirement triggered the need for this decision? What constraints exist?
5. **Decision**: What was chosen or established?
6. **Reasoning**: Why was this solution chosen over alternatives?
7. **Trade-offs**: What are the trade-offs, compromises, or downsides accepted by making this decision?
8. **Consequences**: What impacts does this decision have on development, operations, maintenance, or downstream architecture?

## Decision Log Index

| ADR ID | Title | Status | Date |
|---|---|---|---|
| [ADR-001](ADR-001-INITIAL-ARCHITECTURE.md) | Initial Architecture & Technology Stack | ACCEPTED | 2026-11-05 |
| [ADR-002](ADR-002-HOSTED-EMBEDDINGS-HF.md) | Hosted Embeddings via Hugging Face Inference Providers | ACCEPTED | 2026-11-05 |

## Guidelines for Proposing New ADRs

- If a new requirement necessitates introducing a new database, changing the embedding provider, altering the monorepo structure, or modifying core retrieval logic, an ADR must be drafted.
- Number new records incrementally (`ADR-002-...`, `ADR-003-...`).
- If an ADR supersedes a previous one, mark the previous ADR as `SUPERSEDED` and link to the new record.

