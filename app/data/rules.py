RULES = {
    "采购合同": [
        {
            "rule_id": "PAY_001",
            "title": "付款条款可能早于验收",
            "severity": "high",
            "description": "付款条款出现高比例预付款或全额付款，但同一条款内或相关验收条款中未体现验收、履约保障或尾款挂钩安排。",
            "risk_domain": "付款",
            "check_scope": "clause",
            "applies_to": ["付款", "支付", "价款", "验收", "交付"],
            "exclusions": ["履约保证", "保函"],
            "requires_cross_clause": True,
            "trigger_keywords": ["支付100%", "100%合同价款", "预付款", "首付款", "付款"],
            "must_have_any": ["验收", "验收合格", "质保金", "履约保证"],
            "suggestion": "建议改为分阶段付款，并明确尾款以验收合格为前提，必要时设置质保金或履约担保。"
        },
        {
            "rule_id": "ACC_001",
            "title": "缺少验收条款",
            "severity": "high",
            "description": "采购合同通常需要明确验收标准、验收时间和异议处理机制。",
            "risk_domain": "验收",
            "check_scope": "document",
            "applies_to": ["验收"],
            "exclusions": [],
            "requires_cross_clause": False,
            "missing_keywords": ["验收", "验收标准", "验收合格"],
            "suggestion": "建议补充验收标准、验收流程、验收期限和异议处理方式。"
        },
        {
            "rule_id": "JUR_001",
            "title": "争议管辖可能对我方不利",
            "severity": "medium",
            "description": "争议解决条款若约定由对方所在地法院管辖，通常会增加我方诉讼成本。",
            "risk_domain": "争议解决",
            "check_scope": "clause",
            "applies_to": ["争议", "管辖"],
            "exclusions": [],
            "requires_cross_clause": False,
            "trigger_keywords": ["乙方所在地人民法院", "卖方所在地人民法院"],
            "suggestion": "建议优先约定我方所在地法院、仲裁机构，或采用更中立的争议解决方式。"
        }
    ],
    "通用合同": [
        {
            "rule_id": "GEN_001",
            "title": "缺少合同主体信息",
            "severity": "high",
            "description": "合同通常应明确双方主体名称及身份信息。",
            "risk_domain": "主体",
            "check_scope": "document",
            "applies_to": ["主体", "签约方"],
            "exclusions": [],
            "requires_cross_clause": False,
            "missing_keywords": ["甲方", "乙方"],
            "suggestion": "建议补充完整的合同主体名称、统一社会信用代码或其他身份信息。"
        },
        {
            "rule_id": "GEN_002",
            "title": "缺少合同金额信息",
            "severity": "medium",
            "description": "若合同未明确金额、币种或计价口径，后续履约容易产生争议。",
            "risk_domain": "价款",
            "check_scope": "document",
            "applies_to": ["价款", "金额"],
            "exclusions": [],
            "requires_cross_clause": False,
            "missing_keywords": ["元", "人民币", "合同总价"],
            "suggestion": "建议补充合同金额、币种、税费承担和计价方式。"
        },
        {
            "rule_id": "GEN_003",
            "title": "付款约定不明确",
            "severity": "medium",
            "description": "合同包含付款表述，但未明确支付时间、条件或付款节点，后续履约容易产生争议。",
            "risk_domain": "付款",
            "check_scope": "clause",
            "applies_to": ["付款", "支付"],
            "exclusions": ["支付时间", "付款时间", "验收合格后", "付款节点", "分期"],
            "requires_cross_clause": False,
            "trigger_keywords": ["付款", "支付"],
            "must_have_any": ["支付时间", "付款时间", "验收合格后", "付款节点", "分期", "日期"],
            "suggestion": "建议明确付款时间、触发条件、付款比例和逾期处理方式。"
        },
        {
            "rule_id": "GEN_004",
            "title": "缺少违约责任条款",
            "severity": "high",
            "description": "合同通常应明确违约责任、违约金或损失赔偿安排。",
            "risk_domain": "违约责任",
            "check_scope": "document",
            "applies_to": ["违约责任"],
            "exclusions": [],
            "requires_cross_clause": False,
            "missing_keywords": ["违约责任", "违约金", "赔偿损失"],
            "suggestion": "建议补充违约责任、违约金计算方式及损失赔偿范围。"
        },
        {
            "rule_id": "GEN_005",
            "title": "争议解决条款不完整",
            "severity": "medium",
            "description": "争议解决条款未明确法院或仲裁机构时，可能导致后续处理路径不清晰。",
            "risk_domain": "争议解决",
            "check_scope": "clause",
            "applies_to": ["争议解决"],
            "exclusions": ["人民法院", "仲裁委员会", "仲裁院"],
            "requires_cross_clause": False,
            "trigger_keywords": ["争议", "争议解决"],
            "must_have_any": ["人民法院", "仲裁委员会", "仲裁院"],
            "suggestion": "建议明确约定有管辖权的法院或具体仲裁机构。"
        }
    ]
}
