# Skill System Design for Multi-Agent Platform

> **Status:** Draft for review
> **Date:** 2026-05-06

## 1. 动机

在多 Agent 架构中，每个 Agent 需要执行特定领域的任务——风险审查、法条检索、合同改写等。将这些任务抽象为 **Skill（技能）**，可以实现：

- **可复用**：同一技能可在不同 Agent 团队间共享
- **可插拔**：技能可独立开发、测试、更新
- **可发现**：Gateway 或 Agent 可按需发现和调用技能
- **可度量**：技能执行的 Token 消耗、成功率可追踪

## 2. 核心概念

```
┌──────────────────────────────────────────────┐
│                  Agent                         │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│   │ Skill A  │  │ Skill B  │  │ Skill C  │   │
│   │ 风险审查  │  │ 法条检索  │  │ 合同改写  │   │
│   └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────────────────────────────┘
```

| 概念 | 说明 | 示例 |
|------|------|------|
| **Skill** | 一个可执行的原子能力 | `risk_check`, `legal_search`, `contract_redraft` |
| **Skill Manifest** | 技能的元信息声明 | name, description, input_schema, output_schema, estimated_tokens |
| **Skill Registry** | 全局技能注册中心 | 管理技能的加载、查询、生命周期 |
| **Agent** | Skill 的执行者 | 一个 Agent 可持有多个 Skill |
| **Pipeline** | Skill 的编排 | LangGraph 管线中每个节点调用一个或多个 Skill |

## 3. Skill 定义

每个 Skill 是一个独立的 Python 可调用对象，遵循统一接口：

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class SkillInput(Protocol):
    """Skill 的输入协议。"""
    def model_dump(self) -> dict[str, Any]: ...


class SkillOutput(Protocol):
    """Skill 的输出协议。"""
    def model_dump(self) -> dict[str, Any]: ...


@dataclass
class SkillManifest:
    """Skill 的元信息。"""
    name: str
    description: str
    input_schema: dict[str, Any]         # JSON Schema
    output_schema: dict[str, Any]        # JSON Schema
    estimated_tokens: int = 0
    tags: list[str] = field(default_factory=list)
    timeout_seconds: int = 30
    retry_on_failure: bool = True


class BaseSkill:
    """所有 Skill 的基类。"""

    manifest: SkillManifest

    async def execute(self, input: SkillInput) -> SkillOutput:
        raise NotImplementedError

    def validate_input(self, input: dict[str, Any]) -> bool:
        """校验输入是否符合 manifest.input_schema。"""
        ...
```

### 示例：法条检索 Skill

```python
@dataclass
class LegalSearchInput:
    query: str
    contract_type: str | None = None
    top_k: int = 3

@dataclass  
class LegalSearchOutput:
    results: list[dict]
    total_found: int
    token_used: int

class LegalSearchSkill(BaseSkill):
    manifest = SkillManifest(
        name="legal_search",
        description="从法律知识库检索相关法条",
        input_schema={"query": "string", "contract_type": "string?", "top_k": "integer"},
        output_schema={"results": "array", "total_found": "integer", "token_used": "integer"},
        estimated_tokens=500,
        tags=["legal", "retrieval"],
    )

    async def execute(self, input: LegalSearchInput) -> LegalSearchOutput:
        # 调用现有 RAG 检索能力
        ...
```

## 4. Skill Registry

全局注册中心，管理所有可用 Skill：

```python
class SkillRegistry:
    """全局技能注册中心。"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.manifest.name] = skill

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def find_by_tag(self, tag: str) -> list[BaseSkill]:
        return [s for s in self._skills.values() if tag in s.manifest.tags]

    def manifest_all(self) -> list[SkillManifest]:
        return [s.manifest for s in self._skills.values()]

    def execute(self, name: str, input: dict) -> dict:
        skill = self.get(name)
        if not skill:
            raise KeyError(f"Skill '{name}' not found")
        if not skill.validate_input(input):
            raise ValueError(f"Invalid input for skill '{name}'")
        return skill.execute(input)
```

## 5. 与 Multi-Agent 架构的集成

### 5.1 Agent → Skill 调用链

```
Agent (eg. 风险审查 Agent)
  │
  ├── Skill: clause_parser       → 解析条款
  ├── Skill: rule_check          → 规则引擎匹配
  ├── Skill: legal_search        → 法条检索
  └── Skill: llm_enrich          → LLM 丰富分析
```

### 5.2 Pipeline 中的 Skill 调用

```python
# 在 pipeline.py 中
class PipelineOrchestrator:
    def __init__(self):
        self.skill_registry = SkillRegistry()
        # 注册全局 Skill
        self.skill_registry.register(LegalSearchSkill())
        self.skill_registry.register(RuleCheckSkill())
        ...

    def run_agent(self, agent_id: str, ctx: dict) -> AgentOutput:
        agent = self._agents[agent_id]
        # Agent 在其上下文中可访问 Skill Registry
        skills = self.skill_registry.find_by_tag(agent.tags)
        return agent.execute(ctx, skills)
```

### 5.3 数据流

```
                          Skill Registry
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Agent A │ │ Agent B │ │ Agent C │
              │ Skill 1 │ │ Skill 2 │ │ Skill 3 │
              │ Skill 2 │ │ Skill 3 │ │ Skill 1 │
              └─────────┘ └─────────┘ └─────────┘
                    │          │          │
                    └──────────┼──────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Pipeline Context │
                    │  (shared state)   │
                    └──────────────────┘
```

## 6. 技能发现与动态加载

### 6.1 声明式注册

Skill 可通过文件系统或配置声明自动发现：

```
skills/
  legal/
    __init__.py    # 注册 skills
    legal_search.py
    case_lookup.py
  review/
    risk_check.py
    clause_parse.py
  ...
```

### 6.2 自动扫描

```python
# skills_loader.py
import importlib
import pkgutil
from pathlib import Path


def auto_discover_skills(skills_package: str = "app.skills") -> dict[str, BaseSkill]:
    """自动扫描 skills 目录，发现并实例化所有 BaseSkill 子类。"""
    registry = {}
    for importer, modname, ispkg in pkgutil.iter_modules([skills_package.replace(".", "/")]):
        module = importlib.import_module(f"{skills_package}.{modname}")
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseSkill) and attr is not BaseSkill:
                skill = attr()
                registry[skill.manifest.name] = skill
    return registry
```

## 7. 与现有架构的映射

当前系统中的能力可以映射为 Skill：

| 现有能力 | Skill 名称 | 所属 Agent | 说明 |
|----------|-----------|-----------|------|
| ContractParser.parse_text | `clause_parse` | 解析 Agent | 合同条款解析 |
| ContractClassifier.classify | `contract_classify` | 解析 Agent | 合同类型分类 |
| RuleEngine.check | `rule_check` | 风险审查 Agent | 规则引擎匹配 |
| LLMReviewer.enrich_risk | `llm_enrich` | 风险审查 Agent | LLM 风险分析 |
| KnowledgeRetriever.retrieve | `legal_search` | 法条引用 Agent | 法条检索 |
| ContractEditor.redraft | `contract_redraft` | 改写建议 Agent | 条款改写 |
| Summarizer | `report_generate` | 汇总 Agent | 报告生成 |

## 8. 实施建议

### 第一阶段：Skill 基础设施（1-2 天）
- 定义 `BaseSkill`、`SkillManifest`、`SkillInput`/`SkillOutput` 协议
- 实现 `SkillRegistry`
- 实现自动扫描与加载

### 第二阶段：现有能力迁移（2-3 天）
- 将现有 5 个 Agent 的能力拆分为 Skill
- 每个 Agent 持有对应 Skill 列表
- 保持行为不变，验证测试通过

### 第三阶段：Skill 市场与发现（后续）
- 技能版本管理
- 技能热加载
- 跨项目技能共享

## 9. 关键设计决策

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| Skill 粒度 | 粗/细 | 按能力拆分 | 与现有 Agent 职责对齐，避免过度拆分 |
| 注册方式 | 声明式/自动扫描 | 自动扫描 | 减少配置，新 Skill 即丢即用 |
| 输入输出 | Pydantic/dataclass | Pydantic | 与现有协议类型一致，自带验证 |
| 同步/异步 | sync/async | async | 与未来 WebSocket 和流式兼容 |
| 共享状态 | 全局/隔离 | 隔离 | 每个调用独立 context，避免副作用 |
