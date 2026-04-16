# PostgreSQL + Milvus Persistence Guide

## Environment Variables

- `POSTGRES_DSN`: `postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent`
- `WORKBENCH_BACKEND` (deprecated): runtime is now fixed to PostgreSQL. If set to `json` or `dual_write`, service will log a warning and still use PostgreSQL.
- `VECTOR_BACKEND`: `milvus` | `faiss`
- `MILVUS_URI`: `http://127.0.0.1:19530`
- `MILVUS_COLLECTION_NAME`: `legal_knowledge_chunks`

## Local Infra

```powershell
docker compose up -d postgres etcd minio milvus
```

## Migrations

```powershell
python -m alembic upgrade head
```

## JSON -> PostgreSQL Migration (historical tool)

JSON persistence is no longer used at runtime. The scripts below are retained only for historical backfill and verification.

```powershell
python -m app.scripts.migrate_json_to_postgres --json-base-dir .run/workbench
python -m app.scripts.verify_json_postgres_migration --json-base-dir .run/workbench
```

## Knowledge Ingestion

```powershell
python -m app.rag.ingest --source-dir knowledge/laws --output-dir knowledge/ingested/laws_faiss --manifest-path knowledge/ingested/laws_chunks.jsonl
```

When `VECTOR_BACKEND=milvus`, vector data is written to Milvus and `output-dir` is ignored.
