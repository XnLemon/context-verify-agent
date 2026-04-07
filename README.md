# Contract Review Agent

合同校审工作台（前后端一体）：

- 后端：FastAPI + LangChain + Qwen + FAISS
- 前端：React + Vite
- 目标：支持合同列表、合同扫描、风险处理、对话追问、历史记录等工作台能力

## 当前能力

- 工作台接口（`/api/workbench/*`）
  - 合同列表与搜索
  - 合同详情
  - 合同扫描（触发审查）
  - 风险项处理（采纳/忽略）
  - 对话问答
  - 操作历史
  - 文件导入
- 低层能力接口（兼容保留）
  - `GET /health`
  - `POST /parse`
  - `POST /review`
  - `POST /review/file`
  - `POST /chat`
- 前端页面
  - Dashboard（统计卡片 + 合同列表）
  - Review（正文 + 风险 + 对话 + 历史）

## 目录结构

```text
app/
  api/
  core/
  data/
  llm/
  rag/
  schemas/
  services/
frontend/
  src/
knowledge/
  laws/
  ingested/
tests/
requirements.txt
README.md
```

## 环境要求

- Python 3.13（推荐）
- Node.js 20+

## 后端启动

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

必要环境变量（至少 `QWEN_API_KEY`）：

```powershell
[Environment]::SetEnvironmentVariable('QWEN_API_KEY','your_key','User')
[Environment]::SetEnvironmentVariable('QWEN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1','User')
[Environment]::SetEnvironmentVariable('QWEN_CHAT_MODEL','qwen-max','User')
[Environment]::SetEnvironmentVariable('QWEN_EMBEDDING_MODEL','text-embedding-v4','User')
```

启动服务：

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

默认地址：

- `http://localhost:3000/`

可选配置（前端 API 基地址）：

- `VITE_API_BASE_URL`（默认 `http://127.0.0.1:8000`）

## 知识库构建

将法律文本放入 `knowledge/laws/`，然后执行：

```powershell
python -m app.rag.ingest --source-dir knowledge/laws --output-dir knowledge/ingested/laws_faiss --manifest-path knowledge/ingested/laws_chunks.jsonl
```

在线检索默认读取：

- `knowledge/ingested/laws_faiss`

## Workbench API 简要

- `GET /api/workbench/summary`
- `GET /api/workbench/contracts`
- `GET /api/workbench/contracts/{contract_id}`
- `POST /api/workbench/contracts/{contract_id}/scan`
- `POST /api/workbench/contracts/{contract_id}/chat`
- `POST /api/workbench/contracts/{contract_id}/issues/{issue_id}/decision`
- `GET /api/workbench/contracts/{contract_id}/history`
- `POST /api/workbench/contracts/import`

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 已知说明

- `health` 是浅检查，不代表所有依赖一定可实时调用成功
- 工作台状态目前是轻量文件存储（`.run/workbench/`）
- 当前规则覆盖的是常见风险场景，不等价于完整法审
