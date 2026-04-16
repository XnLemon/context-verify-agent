package com.example.contract.service.agent;

import com.example.contract.exception.ApiException;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class CustomStubAgentGateway implements AgentGateway {
    @Override
    public Map<String, Object> health() {
        return Map.of(
                "status", "ok",
                "llm_configured", true,
                "knowledge_base_ready", true,
                "version", "custom-stub",
                "capabilities", List.of("health", "parse", "review", "chat", "redraft")
        );
    }

    @Override
    public Map<String, Object> parseFile(String fileName, byte[] content) {
        String raw = new String(content);
        return Map.of(
                "document", Map.of(
                        "metadata", Map.of("file_name", fileName, "title", fileName),
                        "raw_text", raw,
                        "spans", List.of(),
                        "clause_chunks", List.of()
                )
        );
    }

    @Override
    public Map<String, Object> reviewText(String contractText, String contractType, String ourSide) {
        return reviewLike(contractText, contractType);
    }

    @Override
    public Map<String, Object> reviewFile(String fileName, byte[] content, String contractType, String ourSide) {
        return reviewLike(new String(content), contractType);
    }

    @Override
    public Map<String, Object> chat(Map<String, Object> payload) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("intent", "chat");
        out.put("tool_used", "custom_stub");
        out.put("answer", "custom adapter stub response");
        out.put("generated_at", OffsetDateTime.now().toString());
        out.put("search_results", List.of());
        out.put("review_result", null);
        return out;
    }

    @Override
    public String redraft(String contractText, String contractType, String ourSide, List<Map<String, String>> acceptedIssues) {
        return contractText + "\n\n[custom adapter stub redraft]";
    }

    private Map<String, Object> reviewLike(String text, String contractType) {
        if (text == null || text.isBlank()) {
            throw new ApiException(400, "合同正文不能为空");
        }
        Map<String, Object> risk = new LinkedHashMap<>();
        risk.put("rule_id", "PAY_001");
        risk.put("title", "付款节点偏前");
        risk.put("severity", "high");
        risk.put("description", "付款约定早于验收");
        risk.put("evidence", "乙方收到款项后履行交付");
        risk.put("suggestion", "增加验收后付款节点");
        risk.put("risk_domain", "付款");
        risk.put("clause_no", "第一条");
        risk.put("section_title", "付款");
        risk.put("start_offset", 1);
        risk.put("end_offset", 20);
        return Map.of(
                "summary", Map.of("contract_type", contractType == null || contractType.isBlank() ? "采购合同" : contractType, "overall_risk", "high", "risk_count", 1),
                "extracted_fields", Map.of(),
                "risks", List.of(risk),
                "report", Map.of("generated_at", OffsetDateTime.now().toString(), "overview", "stub", "key_findings", List.of("付款节点偏前"), "next_actions", List.of("增加验收后付款节点"))
        );
    }
}
