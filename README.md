# Contract Review Agent MVP

这是一个面向合同文本校审的最小可演示系统，当前已经打通以下闭环：

- 粘贴合同全文进行文本校审
- 上传 `txt / docx / pdf` 文件进行解析和校审
- 自动进行条款切分与关键信息抽取
- 识别常见合同风险点
- 检索本地法律知识库并给出依据来源
- 调用 Qwen 生成风险解释和修改建议
- 返回结构化校审报告
- 提供一个最小前端页面用于现场演示

## 主要能力

当前版本重点覆盖以下能力：

- 功能要求
  - 合同文本输入
  - 文件上传解析
  - 条款识别
  - 风险检测
  - 法律知识检索
  - 校审报告生成
- 效果要求
  - 识别付款约定不明确
  - 识别违约责任缺失
  - 识别争议解决条款不完整或对我方不利
  - 输出风险说明、依据来源、修改建议
- 交付形态
  - FastAPI API
  - 内置最小演示页 `/`
  - 可通过 `/docs` 直接演示接口

## 当前目录结构

```text
app/
  api/
  core/
  data/
  llm/
  rag/
  schemas/
  services/
  static/
knowledge/
  laws/
  ingested/
requirements.txt
README.md
```

## 环境要求

建议使用可用的 Python 3.13 环境运行。当前仓库里的 `.venv313` 可能依赖本机特定路径，若无法直接使用，请直接使用系统 Python 3.13。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 必需配置

当前交付要求中，LLM 是必需依赖，不再支持静默降级到纯规则模式。

请至少配置以下环境变量：

```powershell
[Environment]::SetEnvironmentVariable('QWEN_API_KEY','your_key','User')
[Environment]::SetEnvironmentVariable('QWEN_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1','User')
[Environment]::SetEnvironmentVariable('QWEN_CHAT_MODEL','qwen-max','User')
[Environment]::SetEnvironmentVariable('QWEN_EMBEDDING_MODEL','text-embedding-v4','User')
```

说明：

- `QWEN_API_KEY` 必须有效，否则 `/review` 和 `/review/file` 会返回错误
- 当前知识库目录固定为 `knowledge/ingested/laws_faiss`
- 外部用户不能通过环境变量随意指定知识库目录

## 知识库构建

将法律文本放入：

- `knowledge/laws/`

执行入库命令：

```powershell
python -m app.rag.ingest --source-dir knowledge/laws --output-dir knowledge/ingested/laws_faiss --manifest-path knowledge/ingested/laws_chunks.jsonl
```

入库后会得到：

- `knowledge/ingested/laws_chunks.jsonl`
- `knowledge/ingested/laws_faiss/`

当前在线检索只会读取固定目录：

- `knowledge/ingested/laws_faiss`

## 启动方式

```powershell
python -m uvicorn app.main:app --reload
```

启动后可访问：

- 演示页：`http://127.0.0.1:8000/`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

## 演示流程

推荐现场演示顺序：

1. 先访问 `/health`，确认服务在线
2. 打开 `/`，使用文本或文件方式提交合同
3. 查看摘要、抽取字段、风险清单、依据来源和修改建议
4. 如需展示接口层，再打开 `/docs`

## API 说明

### 1. `GET /health`

返回基础运行状态。

示例响应：

```json
{
  "status": "ok",
  "llm_configured": true,
  "knowledge_base_ready": true
}
```

说明：

- 这是浅层 readiness
- 它只表示“配置存在/目录存在”
- 不代表 LLM 一定可实际调用成功，也不代表 FAISS 索引一定可成功加载

### 2. `POST /parse`

上传文件并解析，返回结构化文档。

请求方式：`multipart/form-data`

字段：

- `file`: 合同文件，支持 `txt/docx/pdf`

### 3. `POST /review`

提交合同文本并返回结构化校审报告。

示例请求：

```json
{
  "contract_text": "采购合同\n甲方：甲公司\n乙方：乙公司\n第二条 付款方式\n甲方应于合同签订后5日内支付100%合同价款。\n第三条 争议解决\n争议由乙方所在地人民法院管辖。",
  "contract_type": "采购合同",
  "our_side": "甲方"
}
```

### 4. `POST /review/file`

上传合同文件并返回结构化校审报告。

请求方式：`multipart/form-data`

字段：

- `file`: 合同文件，支持 `txt/docx/pdf`
- `contract_type`: 可选
- `our_side`: 可选，默认 `甲方`

## 返回结果说明

`ReviewResponse` 主要包含：

- `summary`
  - `contract_type`
  - `overall_risk`
  - `risk_count`
- `extracted_fields`
  - `contract_name`
  - `party_a`
  - `party_b`
  - `amount`
  - `dispute_clause`
- `risks`
  - `title`
  - `severity`
  - `description`
  - `evidence`
  - `suggestion`
  - `ai_explanation`
  - `basis_sources`
  - 定位字段：`clause_no`、`section_title`、`page_no` 等
- `report`
  - `generated_at`
  - `overview`
  - `key_findings`
  - `next_actions`

## 测试方式

运行测试：

```powershell
& 'C:\Users\16040\AppData\Local\Programs\Python\Python313\python.exe' -m unittest discover -s tests -v
```

当前验证通过：

- API 路由
- Demo 页面入口
- 上传解析
- 上传校审
- 规则链路
- 分类与抽取
- 报告结构
- reviewer 修复项的失败路径

## 已知限制

- 当前规则覆盖范围有限，重点覆盖常见合同风险点，不代表完整法审
- `/health` 只是浅层检查，不代表真实调用一定成功
- FAISS 加载使用了危险反序列化能力，因此只适合本地受信任索引目录，不适合不受控来源
- 当前知识库目录固定为 `knowledge/ingested/laws_faiss`
- 当前前端页面仅用于演示，不是完整产品化界面
- 暂不包含用户权限、数据库、多租户、异步任务、PDF/HTML 报告导出等能力
