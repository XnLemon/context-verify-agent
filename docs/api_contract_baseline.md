# API Contract Baseline (Frozen)

This baseline is used for SpringBoot migration parity.

## Required Endpoints

- `GET /health`
- `POST /api/auth/login/challenge`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/auth/profile`
- `PATCH /api/auth/profile`
- `POST /api/auth/profile/avatar`
- `GET /api/auth/settings`
- `PATCH /api/auth/settings`
- `GET /api/admin/employees`
- `POST /api/admin/employees`
- `GET /api/workbench/summary`
- `GET /api/workbench/contracts`
- `GET /api/workbench/contracts/{contract_id}`
- `PATCH /api/workbench/contracts/{contract_id}`
- `POST /api/workbench/contracts/{contract_id}/scan`
- `POST /api/workbench/contracts/{contract_id}/chat`
- `POST /api/workbench/contracts/{contract_id}/issues/{issue_id}/decision`
- `POST /api/workbench/contracts/{contract_id}/final-decision`
- `POST /api/workbench/contracts/{contract_id}/redraft`
- `GET /api/workbench/contracts/{contract_id}/history`
- `POST /api/workbench/contracts/import`
- `POST /parse`
- `POST /review`
- `POST /review/file`
- `POST /chat`

## Status Code Contract

- Validation errors: `400`
- Auth errors: `401`
- Permission errors: `403`
- Resource not found: `404`
- Body validation failure: `422`
- Runtime dependency failure (LLM/KB/RPC): `503`

## Compatibility Notes

- Keep mixed naming behavior as-is (`snake_case` and `camelCase` both exist in current APIs).
- Keep `detail` error payload shape: `{ "detail": "..." }`.
- Keep `/review/file` unsupported suffix error containing `Unsupported file type`.
