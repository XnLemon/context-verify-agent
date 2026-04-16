# Python SaaS Legacy Archive

This folder is an archive snapshot of the original Python SaaS backend implementation
(auth/workbench/api/db/service layers) before full Java backend cutover.

## Purpose

- Keep historical Python SaaS implementation for reference and rollback analysis.
- Do not treat this folder as active runtime entrypoint.

## Current Runtime Architecture

- Active business backend: `backend-java/` (SpringBoot)
- Active agent backend: `app/agent_rpc/` + Python agent capabilities

## Archive Scope

Included:
- `app/main.py`, `app/api/routes.py`
- SaaS related `services/*` (auth/workbench/review/chat and dependencies)
- related `schemas/*`, `db/*`, `core/config.py`
- historical docs and source snapshots

Not intended for active deployment without additional dependency and path adjustments.
