# 公司模板知识库管理系统设计文档

## 概述

在公司合同校审平台中，知识库需要纳入公司的自主合同模板和条款片段，支持可视化的 CRUD 管理、实时持久化存储，并在合同审查时通过自动召回和手动选择两种方式进行检索使用。

## 架构

```
前端 (React/TipTap)
  │  REST API
  ▼
SpringBoot 后端 (Controller → Service → Repository)
  │  @Transactional → PostgreSQL
  │  异步事件 → embedding 同步
  ▼
同步队列 → Python Agent (embedding) → Milvus/FAISS
         ↘ 重试 3 次 → 失败日志兜底
```

- 前端管理页面与现有布局风格一致
- 模板 TipTap 编辑器复用现有 TipTap 组件
- Python Agent 新增 template embedding 端点（增量）
- 向量库统一管理，`source_type` 区分内容来源

## 数据库设计

### company_templates — 全文合同模板

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 主键 |
| name | varchar(255) | 模板名称 |
| description | text | 模板描述 |
| content | text | HTML 内容（TipTap 输出） |
| tags | jsonb | 标签 ID 数组 |
| created_by | UUID, FK → users | 创建人 |
| updated_by | UUID, FK → users | 最后修改人 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |
| is_deleted | boolean, default false | 软删除标记 |

### template_clauses — 条款片段

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 主键 |
| title | varchar(255) | 条款标题 |
| content | text | HTML 内容 |
| tags | jsonb | 标签 ID 数组 |
| created_by | UUID, FK → users | 创建人 |
| updated_by | UUID, FK → users | 最后修改人 |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |
| is_deleted | boolean, default false | 软删除标记 |

### template_tags — 标签表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID, PK | 主键 |
| name | varchar(100), unique | 标签名称 |
| color | varchar(7) | 显示颜色 (#2563eb) |
| created_at | timestamptz | 创建时间 |
| updated_at | timestamptz | 更新时间 |

- 条款片段与全文模板无外键关联，独立维护
- 通过 Flyway 迁移创建新表

## API 设计

### 全文模板
- `GET /api/templates` — 分页列表，支持标签过滤和搜索
- `GET /api/templates/:id` — 详情
- `POST /api/templates` — 创建
- `PUT /api/templates/:id` — 更新（触发重新 embedding）
- `DELETE /api/templates/:id` — 软删除（移除向量）

### 条款片段
- `GET /api/clauses` — 分页列表，支持标签过滤和搜索
- `GET /api/clauses/:id` — 详情
- `POST /api/clauses` — 创建
- `PUT /api/clauses/:id` — 更新（触发重新 embedding）
- `DELETE /api/clauses/:id` — 软删除（移除向量）

### 标签
- `GET /api/tags` — 标签列表
- `POST /api/tags` — 创建标签
- `PUT /api/tags/:id` — 修改标签
- `DELETE /api/tags/:id` — 删除标签

## 增量 Embedding 同步机制

1. SpringBoot 事务提交后发布 `TemplateSyncEvent`
2. 异步消费者处理事件，调用 Python Agent `/api/embed` 端点
3. 写入向量库，携带 `source_type` 和 `db_id` 元数据
4. 失败自动重试 3 次，仍失败写入失败日志

增量策略：每次只处理发生变更的单条模板/条款，不做全量重做。

## 向量库文档格式

```json
{
  "id": "向量ID",
  "text": "模板/条款纯文本内容",
  "metadata": {
    "source_type": "template | clause",
    "db_id": "PostgreSQL 记录 UUID",
    "name": "模板名称/条款标题",
    "tags": ["标签1", "标签2"]
  }
}
```

## 前端页面

1. **模板管理列表页** — 全文模板/条款片段 tab 切换，搜索框，标签过滤，新建按钮，列表展示
2. **模板编辑器** — 复用 TipTap，新增 `{{ 变量 }}` 自定义节点，右侧变量列表面板
3. **标签管理** — 可视化标签 CRUD，彩色标签 + 删除按钮
4. **审查/编辑嵌入面板** — 右侧边栏模板库，搜索选用/插入

## 权限控制

- admin / legal / 主管角色：模板和标签的完整 CRUD
- 其他角色：仅查看和使用（检索、浏览、选用）

## 召回方式

- **自动召回**：RAG 检索时增加 `source_type: template | clause` 过滤，将匹配的公司模板混入审查上下文
- **手动选择**：审查页面和编辑器右侧提供模板选择面板，用户主动搜索浏览并应用
