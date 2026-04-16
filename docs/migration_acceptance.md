# Migration Acceptance Checklist

## 1. Start Dependencies

```bash
docker compose up -d postgres etcd minio milvus
```

## 2. Start Agent RPC

```bash
python3 -m pip install -r requirements.txt
./app/agent_rpc/gen_proto.sh
python3 -m app.agent_rpc.server
```

## 3. Start SpringBoot Backend

```bash
cd backend-java
mvn spring-boot:run
```

## 4. End-to-End Chains

### Chain A: challenge -> login -> me -> logout

- `POST /api/auth/login/challenge`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`

### Chain B: import -> scan -> issues

- `POST /api/workbench/contracts/import`
- `POST /api/workbench/contracts/{id}/scan`

### Chain C: issue decision -> status update -> history

- `POST /api/workbench/contracts/{id}/issues/{issue}/decision`
- `GET /api/workbench/contracts/{id}`
- `GET /api/workbench/contracts/{id}/history`

### Chain D: chat (with optional review trigger)

- `POST /api/workbench/contracts/{id}/chat`

### Chain E: redraft

- `POST /api/workbench/contracts/{id}/redraft`

### Chain F: final decision

- `POST /api/workbench/contracts/{id}/final-decision`

## 5. RPC Decoupling Check

Switch SpringBoot config:

```yaml
app:
  agent:
    rpc:
      provider: custom
```

Then restart SpringBoot and verify `/health`, `/review`, `/chat` still return valid responses (from custom stub adapter).
