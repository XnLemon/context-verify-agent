from langchain_core.prompts import ChatPromptTemplate


risk_explain_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审助手。请基于规则结果、命中条款和检索到的上下文，生成简洁、专业、可执行的风险解释。

合同类型:
{contract_type}

风险标题:
{title}

风险域:
{risk_domain}

规则描述:
{description}

命中证据:
{evidence}

当前条款:
{clause_text}

相关上下文:
{retrieved_context}

请输出两部分：
1. 风险解释：说明为什么这是风险。
2. 修改建议：给出更可执行的修改方向。
"""
)
