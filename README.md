# 合同校审 Agent

基于 `FastAPI + LangChain + Qwen + Milvus + React` 的合同校审工作台，用于合同导入、智能扫描、风险处置、对话追问与审批流转。

## 1. 核心能力

- 合同导入与解析：支持上传合同并结构化处理。
- 智能校审：基于规则与模型识别风险点并给出修订建议。
- 对话追问：围绕当前合同进行问答，辅助法务判断。
- 工作台流转：支持问题采纳/忽略、重写、最终审批、历史追踪。
- 权限体系：支持管理员与员工角色，包含登录挑战与会话管理。

## 2. 技术栈

- 后端：`Python 3.13`、`FastAPI`、`LangChain`、`SQLAlchemy`、`Alembic`
- 模型：`Qwen`（对话/Embedding/Rerank）
- 向量检索：`Milvus`（默认）或 `FAISS`
- 数据库：`PostgreSQL`
- 前端：`React + Vite + TypeScript`

## 3. 目录结构

```text
app/
  api/                 # 路由层
  core/                # 全局配置
  db/                  # 数据库模型与连接
  llm/                 # 大模型客户端与提示词
  rag/                 # 检索与知识库构建
  services/            # 业务服务（校审、工作台、鉴权等）
  schemas/             # Pydantic 请求/响应模型
frontend/              # React 前端
knowledge/             # 法规与知识数据
docs/                  # 设计与持久化文档
tests/                 # 后端测试
docker-compose.yml     # Postgres + Milvus 本地依赖
```

## 4. 本地快速启动

### 4.1 前置条件

- Python `3.13`
- Node.js `20+`
- Docker（用于 Postgres/Milvus 依赖）

### 4.2 启动基础设施

```powershell
docker compose up -d postgres etcd minio milvus
```

### 4.3 安装后端依赖

```powershell
python -m pip install -r requirements.txt
```

### 4.4 配置环境变量

至少需要配置 `QWEN_API_KEY`，其余可按默认值运行：

```powershell
[Environment]::SetEnvironmentVariable('QWEN_API_KEY','your_key','User')
[Environment]::SetEnvironmentVariable('QWEN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1','User')
[Environment]::SetEnvironmentVariable('QWEN_CHAT_MODEL','qwen-max','User')
[Environment]::SetEnvironmentVariable('QWEN_EMBEDDING_MODEL','text-embedding-v4','User')
[Environment]::SetEnvironmentVariable('VECTOR_BACKEND','milvus','User')
[Environment]::SetEnvironmentVariable('MILVUS_URI','http://127.0.0.1:19530','User')
[Environment]::SetEnvironmentVariable('POSTGRES_DSN','postgresql+psycopg://postgres:postgres@127.0.0.1:5432/contract_agent','User')
```

### 4.5 初始化数据库

```powershell
python -m alembic upgrade head
```

### 4.6 构建知识库（首次建议执行）

```powershell
python -m app.rag.ingest --source-dir knowledge/laws --output-dir knowledge/ingested/laws_faiss --manifest-path knowledge/ingested/laws_chunks.jsonl
```

说明：当 `VECTOR_BACKEND=milvus` 时，向量写入 Milvus，`--output-dir` 仅保留参数兼容。

### 4.7 启动后端

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

后端地址：

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/docs`（OpenAPI）

### 4.8 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:3000`

可选环境变量：

- `VITE_API_BASE_URL`（默认 `http://127.0.0.1:8000`）

## 5. 默认账户

系统默认会引导初始化管理员（可通过环境变量覆盖）：

- 用户名：`admin`
- 密码：`admin123`
- 对应变量：`BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`

## 6. 主要 API

### 6.1 健康检查

- `GET /health`

### 6.2 鉴权与用户

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

### 6.3 工作台

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

### 6.4 兼容接口

- `POST /parse`
- `POST /review`
- `POST /review/file`
- `POST /chat`

## 7. 开发与验证

后端测试：

```powershell
python -m unittest discover -s tests -v
```

前端类型检查与构建：

```powershell
cd frontend
npm run lint
npm run build
```

## 8. 常见说明

- `health` 为浅健康检查，不代表外部依赖（模型、向量库）在每次请求都可用。
- 运行时工作台仓储已固定为 PostgreSQL，`WORKBENCH_BACKEND` 仅保留兼容语义。
- 迁移与持久化说明见：`docs/persistence.md`。

