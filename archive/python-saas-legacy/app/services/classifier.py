class ContractClassifier:
    def classify(self, text: str) -> str:
        if any(keyword in text for keyword in ("采购", "买卖", "供货")):
            return "采购合同"
        if any(keyword in text for keyword in ("保密", "NDA")):
            return "保密协议"
        if any(keyword in text for keyword in ("服务", "运维", "咨询")):
            return "服务合同"
        return "通用合同"
