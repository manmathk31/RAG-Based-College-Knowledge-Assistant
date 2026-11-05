# Changelog

All notable changes to the `RAG-Based-College-Knowledge-Assistant` project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Foundational Architecture & Engineering Governance**:
  - Root `AGENTS.md` governing persistent coding guidelines, invariants, testing policy, and AI agent rules.
  - Architecture documentation: `SYSTEM_ARCHITECTURE.md`, `DATA_FLOW.md`, `INGESTION_PIPELINE.md`.
  - Architecture Decision Records: `ADR-001-INITIAL-ARCHITECTURE.md` capturing 10 key technical choices.
  - Development and testing documentation: `DEVELOPMENT_GUIDE.md`, `CODING_CONVENTIONS.md`, `TESTING_STRATEGY.md`.
  - Project tracking: `PROJECT_STATUS.md`, `IMPLEMENTATION_PLAN.md`, `CHANGELOG.md`.
  - Environment templates: root `.env.example`, `backend/.env.example`.
  - Monorepo directory structure for backend and dual frontends (`frontend/user-app`, `frontend/admin-app`).
  - Minimal local Docker Compose configuration (`docker-compose.yml`).
  - Backend scaffold: FastAPI application, Pydantic settings, health check endpoint (`/api/v1/health`), and structured logging.
  - Frontend scaffolds: Independent React + TypeScript + Vite + Tailwind CSS setups for User and Admin apps.
  - Verification & validation pass: Successfully verified backend imports, executed Pytest suite for health endpoints, verified live Uvicorn HTTP health check, and built both frontend bundles (`tsc && vite build`).
