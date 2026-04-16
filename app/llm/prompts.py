from langchain_core.prompts import ChatPromptTemplate


risk_explain_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审助手。请基于规则结果、命中条款和检索到的上下文，生成简洁、专业、可执行的分析。

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

请严格按下面格式输出，不要添加其他标题或解释：
风险解释：<一段简洁解释>
修改建议：<一段可直接落地的建议>
"""
)


chat_intent_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审系统的意图路由器。请根据用户最后一轮消息和可选合同上下文，识别用户当前最需要的能力。

可选意图只有四种：
- search: 用户想查找法条、依据、规则、知识点、出处
- review: 用户想对合同文本或条款做校审、审查、风险识别
- advice: 用户想获得修改建议、写法建议、条款建议，但不一定要求完整审查
- chat: 普通问答、寒暄、解释、闲聊

合同上下文:
{contract_text}

对话历史:
{conversation}

请只输出一行 JSON，不要输出 Markdown：
{{"intent":"search|review|advice|chat","query":"给工具使用的简洁查询","reason":"一句简短原因"}}
"""
)


chat_answer_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审助手，请结合用户问题给出自然、简洁、友好的中文回答。

对话历史:
{conversation}

用户当前问题:
{user_message}
"""
)


search_answer_prompt = ChatPromptTemplate.from_template(
    """
你是合同知识检索助手。请根据用户问题和检索到的知识片段，给出简洁、有根据的中文回答。

用户问题:
{user_message}

检索片段:
{retrieved_context}

请在回答中优先总结关键结论，再给出1-3条最相关依据来源提示。
"""
)


advice_answer_prompt = ChatPromptTemplate.from_template(
    """
你是合同修改建议助手。请根据用户问题、可选合同上下文和检索到的依据，给出务实、可执行的修改建议。

用户问题:
{user_message}

合同上下文:
{contract_text}

检索片段:
{retrieved_context}

请直接给出建议，必要时分点说明。
"""
)


react_step_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审智能体的规划器。你必须在每一步只做一个决策：继续调用工具，或结束并给最终答案。

可用动作:
- query_knowledge: 当问题需要外部知识、法条依据、案例支持时使用
- finish: 当信息已足够回答时使用

当前意图:
{intent}

用户当前问题:
{user_message}

对话历史:
{conversation}

当前已知观察:
{latest_observation}

历史轨迹摘要:
{trace_history}

请只输出一行 JSON，不要输出 Markdown：
{{"thought_summary":"一句话摘要，不超过40字","action":"query_knowledge|finish","action_input":{{"query":"查询词"}},"final_answer":"当 action=finish 时可给最终答案草稿"}}
"""
)


react_synthesis_prompt = ChatPromptTemplate.from_template(
    """
你是合同校审助手。请基于用户问题、对话上下文和 ReAct 轨迹，给出最终中文答复。

要求:
- 答案专业、简洁、可执行
- 不要暴露完整思维链，只输出结论
- 若有外部依据，优先总结结论，再给 1-3 条来源提示

当前意图:
{intent}

用户当前问题:
{user_message}

对话历史:
{conversation}

ReAct 轨迹摘要:
{trace_history}

检索上下文:
{retrieved_context}
"""
)

contract_redraft_prompt = ChatPromptTemplate.from_template(
    """
你是资深合同律师，请基于“已采纳的问题建议”直接输出一版修订后的完整合同正文。

修订要求：
- 仅根据已采纳问题进行必要修改，未涉及条款保持原意。
- 保留原合同整体结构与编号风格。
- 输出必须是“可直接落地”的完整合同文本，不要解释，不要 Markdown，不要前后缀说明。
- 如果某条建议不适用，应在合同中保持原文，不要编造新事实。

合同类型：
{contract_type}

我方角色：
{our_side}

已采纳问题清单：
{accepted_issues}

原合同全文：
{contract_text}
"""
)


contract_redraft_chunk_prompt = ChatPromptTemplate.from_template(
    """
??????????????????????????????????

?????
- ???????????????
- ?????????????
- ????????????????????? Markdown?

?????
{contract_type}

?????
{our_side}

????????
{accepted_issues}

????????
{contract_segment}
"""
)
