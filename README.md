# 合同校审平台（SpringBoot SaaS + Python Agent）

当前架构：

- `backend-java/`: SpringBoot SaaS 业务后端（鉴权、工作台、审批、历史）
- `app/`: Python Agent 代码（仅保留 parse/review/chat/redraft 与 RAG/LLM）
- `app/agent_rpc/server.py`: Python Agent RPC 服务入口
- `archive/python-saas-legacy/`: 原 FastAPI SaaS 代码归档（不参与运行）
- `frontend/`: React 前端

目标是保持业务功能与接口契约不变，将业务后端从 FastAPI 迁到 SpringBoot，并通过可替换 RPC 访问 Agent。

## 1. 核心能力

- 合同导入与解析：支持上传合同并结构化处理（含 DOCX 富文本格式）。
- **Multi-Agent 智能校审**：5 个专业 Agent 流水线协作（解析 → 风险审查 → 法条引用 → 改写建议 → 汇总），支持单 Agent/多 Agent 自动/多 Agent 手动三种模式。
- **公司模板管理**：可创建/编辑/删除公司模板与条款，支持向量嵌入同步，模板内容可插入合同审核面板。
- 对话追问：围绕当前合同进行问答，支持流式输出，辅助法务判断。
- 工作台流转：支持问题采纳/忽略、重写、最终审批、历史追踪。
- 权限体系：支持管理员、法务、员工角色，包含登录挑战与会话管理。
- **前端 UI 重设计**：设计令牌系统 + 暗色模式 + 10 个可复用组件（Modal/Toast/Sidebar/Card 等）。

## 2. 技术栈

- 业务后端：`Java 21`、`SpringBoot`、`Maven`、`Flyway`、`PostgreSQL`
- Agent 后端：`Python 3.13+`、`gRPC`、`LangChain`、`Qwen`
- 模型：`Qwen`（对话/Embedding/Rerank）
- 向量检索：`Milvus`（默认）或 `FAISS`
- 数据库：`PostgreSQL`
- 前端：`React + Vite + TypeScript`

## 3. 目录结构

```text
app/
  agent_rpc/           # gRPC 服务入口与 proto
  core/                # 全局配置
  db/                  # Agent 相关数据库模型与连接
  llm/                 # 大模型客户端与提示词
  multi_agent/         # Multi-Agent 编排（Gateway/Pipeline/Agents/Memory/Events）
  rag/                 # 检索与知识库构建
  services/            # Agent 服务（校审、对话）
  schemas/             # Pydantic 请求/响应模型
archive/python-saas-legacy/
  app/                 # 旧 FastAPI SaaS 后端归档
backend-java/          # SpringBoot 业务后端
  src/main/java/com/example/contract/
    controller/        # REST 控制器（含 TemplateController）
    service/
      agent/           # gRPC Agent 网关
      auth/            # 鉴权服务
      template/        # 模板管理服务
      workbench/       # 工作台服务
    model/             # 数据模型（含 CompanyTemplate/TemplateClause/TemplateTag）
    repository/        # 数据访问层
frontend/              # React 前端
  src/components/ui/   # 可复用 UI 组件库（10+ 组件）
  src/pages/           # 页面（含 TemplateManager）
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

### 4.3 安装 Python Agent 依赖

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

### 4.7 启动 Python Agent RPC 服务

```powershell
python3 -m app.agent_rpc.server
```

### 4.8 启动 SpringBoot 业务后端

```bash
cd backend-java
mvn spring-boot:run
```

后端地址：

- `http://127.0.0.1:8080`

### 4.9 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端地址：`http://127.0.0.1:3000`

可选环境变量：

- `VITE_API_BASE_URL`（默认 `http://127.0.0.1:8080`）

## 5. 默认账户

系统默认可使用管理员账号联调：

- 用户名：`admin`
- 密码：`admin123`
- 账号初始化由 SpringBoot/Flyway 侧负责

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

### 6.4 Multi-Agent 审核

- `POST /api/workbench/contracts/{contract_id}/scan-multi` — 多 Agent 流水线审核（返回 pipeline_id/mode/status/agent_summaries）

### 6.5 模板管理

- `GET /api/tags` — 标签列表
- `POST /api/tags` — 创建标签
- `PUT /api/tags/{id}` — 更新标签
- `DELETE /api/tags/{id}` — 删除标签
- `GET /api/templates?search=&tagIds=&page=1&size=20` — 模板列表
- `GET /api/templates/{id}` — 模板详情
- `POST /api/templates` — 创建模板
- `PUT /api/templates/{id}` — 更新模板
- `DELETE /api/templates/{id}` — 删除模板
- `GET /api/clauses?search=&tagIds=&page=1&size=20` — 条款列表
- `GET /api/clauses/{id}` — 条款详情
- `POST /api/clauses` — 创建条款
- `PUT /api/clauses/{id}` — 更新条款
- `DELETE /api/clauses/{id}` — 删除条款

### 6.6 兼容接口

- `POST /parse`
- `POST /review`
- `POST /review/file`
- `POST /chat`

## 7. 开发与验证

Python Agent 测试：

```powershell
python -m unittest tests.multi_agent.test_gateway tests.multi_agent.test_agents tests.multi_agent.test_pipeline -v
python -m unittest discover -s tests -v
```

Java 后端测试：

```bash
cd backend-java && mvn test
```

前端类型检查与构建：

```powershell
cd frontend
npm run lint
npm run build
```

## 8. gRPC Agent RPC

Python Agent 通过 gRPC 暴露以下 RPC：

| RPC | 说明 |
|-----|------|
| `Health` | 健康检查（含 LLM 配置/知识库状态/版本/能力列表） |
| `ParseFile` | 文件解析（txt/pdf/docx） |
| `Review` | 单 Agent 合同审核 |
| `ReviewMultiAgent` | **多 Agent 流水线审核**（5 Agent 协作） |
| `Chat` | 同步对话 |
| `ChatStream` | 流式对话（支持 ReAct 推理链） |
| `Redraft` | 合同条款改写 |
| `EmbedDocument` | 模板/条款向量嵌入同步 |

## 9. Multi-Agent 架构

```
Gateway Router（模式检测 + 团队路由）
     /                    \
审核团队（5 Agent 流水线）  对话团队（动态路由，规划中）
     \                    /
    三层记忆（Redis/PG/Milvus）
```

- `app/multi_agent/` — 编排模块（protocol/gateway/pipeline/agents/memory/events）
- 模式支持：**单 Agent**（快速）/ **多 Agent 自动** / **多 Agent 手动**（深度）
- 设计文档：`docs/superpowers/specs/2026-05-06-multi-agent-design.md`

## 10. 常见说明

- `health` 为浅健康检查，不代表外部依赖（模型、向量库）在每次请求都可用。
- 运行时工作台仓储已固定为 PostgreSQL，`WORKBENCH_BACKEND` 仅保留兼容语义。
- 迁移与持久化说明见：`docs/persistence.md`。
