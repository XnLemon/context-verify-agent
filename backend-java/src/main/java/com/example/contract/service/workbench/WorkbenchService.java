package com.example.contract.service.workbench;

import com.example.contract.config.AppProperties;
import com.example.contract.dto.*;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.WorkbenchRepository;
import com.example.contract.service.agent.AgentGateway;
import com.example.contract.util.Jsons;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.function.Consumer;

@Service
public class WorkbenchService {
    private final WorkbenchRepository repository;
    private final AgentGateway agentGateway;
    private final AppProperties props;
    private final TransactionTemplate transactionTemplate;

    public WorkbenchService(WorkbenchRepository repository, AgentGateway agentGateway, AppProperties props, TransactionTemplate transactionTemplate) {
        this.repository = repository;
        this.agentGateway = agentGateway;
        this.props = props;
        this.transactionTemplate = transactionTemplate;
    }

    public SummaryResponse summary(Member currentMember) {
        List<Map<String, Object>> contracts = visibleContracts(currentMember);
        int pendingCount = (int) contracts.stream().filter(c -> "pending".equals(c.get("status"))).count();
        int total = contracts.size();
        int highRisk = 0;
        int reviewed = 0;
        for (Map<String, Object> c : contracts) {
            Optional<Map<String, Object>> review = repository.getReview((String) c.get("id"));
            if (review.isPresent()) {
                reviewed += 1;
                List<Map<String, Object>> issues = (List<Map<String, Object>>) review.get().get("issues");
                highRisk += issues.stream().filter(i -> "high".equals(i.get("severity")) && "pending".equals(i.get("status"))).count();
            }
        }
        double compliance = reviewed == 0 ? 100.0 : Math.round((double) (reviewed - highRisk) / reviewed * 1000.0) / 10.0;
        return new SummaryResponse(
                pendingCount,
                compliance,
                highRisk,
                0.0,
                total
        );
    }

    public ContractListResponse listContracts(String status, String search, Member currentMember) {
        String keyword = search == null ? "" : search.trim().toLowerCase(Locale.ROOT);
        List<Map<String, Object>> items = new ArrayList<>();
        for (Map<String, Object> contract : visibleContracts(currentMember)) {
            if (status != null && !status.isBlank() && !status.equals(contract.get("status"))) {
                continue;
            }
            if (!keyword.isBlank()) {
                String hay = (contract.get("title") + " " + contract.get("type") + " " + contract.get("author") + " " + contract.get("content")).toLowerCase(Locale.ROOT);
                if (!hay.contains(keyword)) {
                    continue;
                }
            }
            items.add(toContractListItem(contract));
        }
        items.sort((a, b) -> String.valueOf(b.get("updatedAt")).compareTo(String.valueOf(a.get("updatedAt"))));
        return new ContractListResponse(DTOConverter.toContractList(items), items.size());
    }

    public ContractDetailResponse contractDetail(String contractId, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        int memberId = memberScopeId(currentMember);
        ReviewResultResponse review = repository.getReview(contractId)
                .map(DTOConverter::toReview)
                .orElse(null);
        return new ContractDetailResponse(
                DTOConverter.toContract(contract),
                review,
                DTOConverter.toChatMessageList(repository.getChatMessages(contractId, memberId))
        );
    }

    public ImportContractResponse importContract(String fileName, byte[] content, String contractType, String author, String ownerUsername, Member currentMember) {
        Map<String, Object> parsed = agentGateway.parseFile(fileName, content);
        Map<String, Object> document = (Map<String, Object>) parsed.get("document");
        Map<String, Object> metadata = (Map<String, Object>) document.get("metadata");
        String rawText = String.valueOf(document.getOrDefault("raw_text", ""));
        String title = asString(metadata.get("title"));
        if (title.isBlank()) {
            title = stripSuffix(fileName);
        }
        String type = contractType != null && !contractType.isBlank() ? contractType : asString(metadata.get("contract_type_hint"));
        if (type.isBlank()) {
            type = props.getDefaultContractType();
        }
        String id = "contract-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        repository.createContract(title, type, "pending", author, ownerUsername, rawText, fileName, id);
        appendHistory(id, currentMember, "import", "导入合同", "已从文件 " + fileName + " 导入合同。", Map.of("file_name", fileName));
        return new ImportContractResponse(DTOConverter.toContract(requireContract(id, currentMember)));
    }

    public ContractResponse updateContractContent(String contractId, String content, Member currentMember) {
        if (content == null || content.isBlank()) {
            throw new ApiException(400, "合同正文不能为空。");
        }
        Map<String, Object> contract = requireContract(contractId, currentMember);
        contract.put("content", content);
        contract.put("status", "pending");
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        appendHistory(contractId, currentMember, "manual_edit", "手动编辑合同", "已手动更新合同正文，建议重新执行扫描。", Map.of("content_length", String.valueOf(content.length())));
        return DTOConverter.toContract(contract);
    }

    public ScanResponse scanContract(String contractId, String contractType, String ourSide, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> review = agentGateway.reviewText((String) contract.get("content"), contractType != null ? contractType : (String) contract.get("type"), ourSide);
        Map<String, Object> stored = buildStoredReview(contractId, review, null);
        saveStoredReview(stored);
        contract.put("type", ((Map<String, Object>) review.get("summary")).get("contract_type"));
        contract.put("status", deriveStatus((List<Map<String, Object>>) stored.get("issues")));
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        int historyCount = appendHistory(contractId, currentMember, "scan", "完成合同扫描", "完成扫描。", Map.of("overall_risk", String.valueOf(((Map<String, Object>) review.get("summary")).get("overall_risk"))));
        return new ScanResponse(
                DTOConverter.toContract(contract),
                DTOConverter.toReview(stored),
                historyCount
        );
    }

    public ChatResponse chatContract(String contractId, Map<String, Object> payload, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        int memberId = memberScopeId(currentMember);
        List<Map<String, Object>> messages = new ArrayList<>();
        Object payloadMsgs = payload.get("messages");
        if (payloadMsgs instanceof List<?> m && !m.isEmpty()) {
            for (Object item : m) messages.add((Map<String, Object>) item);
        } else {
            messages.addAll(repository.getChatMessages(contractId, memberId));
        }
        String message = asString(payload.get("message"));
        if (!message.isBlank()) {
            messages.add(chatMessage("user", message));
        }
        if (messages.isEmpty()) {
            throw new ApiException(400, "至少需要一条用户消息。");
        }

        Map<String, Object> chatPayload = new LinkedHashMap<>();
        chatPayload.put("messages", messages.stream().map(m -> Map.of("role", m.get("role"), "content", m.get("content"))).toList());
        chatPayload.put("contract_text", contract.get("content"));
        chatPayload.put("contract_type", payload.getOrDefault("contract_type", contract.get("type")));
        chatPayload.put("our_side", payload.getOrDefault("our_side", "甲方"));
        Map<String, Object> chat = agentGateway.chat(chatPayload);

        Map<String, Object> assistant = chatMessage("assistant", asString(chat.get("answer")));
        Object traceData = chat.get("trace_summary");
        if (traceData != null) {
            assistant.put("trace_json", traceData);
        }
        messages.add(assistant);
        repository.saveChatMessages(contractId, memberId, messages);

        Object reviewObj = chat.get("review_result");
        Object latestReview = null;
        if (reviewObj instanceof Map<?, ?> reviewResult) {
            Map<String, Object> stored = buildStoredReview(contractId, (Map<String, Object>) reviewResult, null);
            saveStoredReview(stored);
            contract.put("status", deriveStatus((List<Map<String, Object>>) stored.get("issues")));
            contract.put("updated_at", OffsetDateTime.now());
            repository.saveContract(contract);
            latestReview = toReviewResult(stored);
        }

        appendHistory(contractId, currentMember, "chat", "新增 AI 对话", asString(messages.get(messages.size() - 2).get("content")), Map.of("tool_used", asString(chat.get("tool_used"))));
        return new ChatResponse(
                asString(chat.getOrDefault("intent", "chat")),
                asString(chat.getOrDefault("tool_used", "chat")),
                DTOConverter.toChatMessage(assistant),
                DTOConverter.toChatMessageList(messages),
                latestReview instanceof Map<?, ?> r ? DTOConverter.toReview((Map<String, Object>) r) : null
        );
    }

    public void chatContractStream(String contractId, Map<String, Object> payload, Member currentMember,
                                    Consumer<AgentGateway.ChatStreamEvent> emitter) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        int memberId = memberScopeId(currentMember);
        List<Map<String, Object>> messages = new ArrayList<>();
        Object payloadMsgs = payload.get("messages");
        if (payloadMsgs instanceof List<?> m && !m.isEmpty()) {
            for (Object item : m) messages.add((Map<String, Object>) item);
        } else {
            messages.addAll(repository.getChatMessages(contractId, memberId));
        }
        String message = asString(payload.get("message"));
        if (!message.isBlank()) {
            messages.add(chatMessage("user", message));
        }
        if (messages.isEmpty()) {
            throw new ApiException(400, "至少需要一条用户消息。");
        }

        Map<String, Object> chatPayload = new LinkedHashMap<>();
        chatPayload.put("messages", messages.stream().map(m -> Map.of("role", m.get("role"), "content", m.get("content"))).toList());
        chatPayload.put("contract_text", contract.get("content"));
        chatPayload.put("contract_type", payload.getOrDefault("contract_type", contract.get("type")));
        chatPayload.put("our_side", payload.getOrDefault("our_side", "甲方"));

        emitter.accept(new AgentGateway.ChatStreamEvent("start", Jsons.toJson(Map.of("id", contractId, "timestamp", OffsetDateTime.now().toString()))));

        Map<String, Object> donePayload = new LinkedHashMap<>();
        StringBuilder deltaBuffer = new StringBuilder();
        Iterator<AgentGateway.ChatStreamEvent> stream = agentGateway.chatStream(chatPayload);
        while (stream.hasNext()) {
            AgentGateway.ChatStreamEvent evt = stream.next();
            if ("delta".equals(evt.event())) {
                Map<String, Object> parsed = Jsons.toMapSafe(evt.dataJson(), null);
                if (parsed != null) {
                    deltaBuffer.append(parsed.getOrDefault("delta", ""));
                }
            } else if ("done".equals(evt.event())) {
                donePayload = Jsons.toMapSafe(evt.dataJson(), null);
                if (donePayload == null) {
                    emitter.accept(new AgentGateway.ChatStreamEvent("error", Jsons.toJson(Map.of("error", "chat stream ended with malformed done event"))));
                    return;
                }
                break;
            }
            emitter.accept(evt);
        }

        if (donePayload.isEmpty()) {
            emitter.accept(new AgentGateway.ChatStreamEvent("error", Jsons.toJson(Map.of("error", "chat stream ended without done event"))));
            return;
        }

        String answer = asString(donePayload.get("answer"));
        if (!deltaBuffer.isEmpty() && answer.isEmpty()) {
            answer = deltaBuffer.toString();
        }
        Object traceData = donePayload.get("trace_summary");
        Map<String, Object> assistant = chatMessage("assistant", answer);
        // Attach trace data to the assistant message for DB persistence
        if (traceData != null) {
            assistant.put("trace_json", traceData);
        }
        messages.add(assistant);

        Map<String, Object> latestReview = new HashMap<>(1);
        Map<String, Object> finalContract = contract;
        List<Map<String, Object>> finalMessages = messages;
        Map<String, Object> finalDonePayload = donePayload;
        transactionTemplate.executeWithoutResult(status -> {
            repository.saveChatMessages(contractId, memberId, finalMessages);

            Object reviewObj = finalDonePayload.get("review_result");
            if (reviewObj instanceof Map<?, ?> reviewResult) {
                Map<String, Object> stored = buildStoredReview(contractId, (Map<String, Object>) reviewResult, null);
                saveStoredReview(stored);
                finalContract.put("status", deriveStatus((List<Map<String, Object>>) stored.get("issues")));
                finalContract.put("updated_at", OffsetDateTime.now());
                repository.saveContract(finalContract);
                latestReview.put("_val", toReviewResult(stored));
            }

            appendHistory(contractId, currentMember, "chat", "新增 AI 对话",
                    asString(finalMessages.get(finalMessages.size() - 2).get("content")),
                    Map.of("tool_used", asString(finalDonePayload.get("tool_used"))));
        });
        Map<String, Object> latestReviewResult = (Map<String, Object>) latestReview.get("_val");

        Map<String, Object> doneResult = new LinkedHashMap<>();
        doneResult.put("intent", asString(donePayload.getOrDefault("intent", "chat")));
        doneResult.put("toolUsed", asString(donePayload.getOrDefault("tool_used", "chat")));
        doneResult.put("assistantMessage", DTOConverter.toChatMessage(assistant));
        doneResult.put("messages", DTOConverter.toChatMessageList(messages));
        if (latestReviewResult != null) {
            doneResult.put("latestReview", DTOConverter.toReview(latestReviewResult));
        }
        // Forward trace to frontend (snake_case from Python → camelCase for JS)
        if (traceData != null) {
            doneResult.put("traceSummary", traceData);
        }
        emitter.accept(new AgentGateway.ChatStreamEvent("done", Jsons.toJson(doneResult)));
    }

    public ReviewResultResponse decideIssue(String contractId, String issueId, Map<String, Object> payload, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> review = repository.getReview(contractId).orElseThrow(() -> new ApiException(404, "Contract review not found: " + contractId));
        String status = asString(payload.get("status"));
        if (!Set.of("accepted", "rejected", "pending", "overridden").contains(status)) {
            throw new ApiException(400, "无效的问题状态: " + status);
        }
        boolean found = false;
        List<Map<String, Object>> issues = (List<Map<String, Object>>) review.get("issues");
        for (Map<String, Object> issue : issues) {
            if (issueId.equals(issue.get("id"))) {
                issue.put("status", status);
                found = true;
                break;
            }
        }
        if (!found) throw new ApiException(404, "Issue not found: " + issueId);
        repository.saveReview(contractId, (Map<String, Object>) review.get("summary"), asString(review.get("report_overview")),
                (List<String>) review.get("key_findings"), (List<String>) review.get("next_actions"), issues, (OffsetDateTime) review.get("generated_at"));
        contract.put("status", deriveStatus(issues));
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        appendHistory(contractId, currentMember, "issue_decision", "更新风险处理状态", "问题 " + issueId + " 已标记为 " + status + "。", Map.of("issue_id", issueId, "status", status));
        return DTOConverter.toReview(repository.getReview(contractId).orElseThrow());
    }

    public RedraftResponse redraftContract(String contractId, String ourSide, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> review = repository.getReview(contractId).orElseThrow(() -> new ApiException(404, "Contract review not found: " + contractId));
        List<Map<String, Object>> accepted = ((List<Map<String, Object>>) review.get("issues")).stream()
                .filter(i -> "accepted".equals(i.get("status")))
                .toList();
        if (accepted.isEmpty()) {
            throw new ApiException(400, "当前没有已采纳的问题，无法生成修订稿。");
        }
        List<Map<String, String>> acceptedIssues = accepted.stream().map(i -> Map.of(
                "message", asString(i.get("message")),
                "suggestion", asString(i.get("suggestion")),
                "location", asString(i.get("location"))
        )).toList();
        String revised = agentGateway.redraft(asString(contract.get("content")), asString(contract.get("type")), ourSide, acceptedIssues);
        contract.put("content", revised);
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        appendHistory(contractId, currentMember, "redraft", "生成合同修订稿", "已基于 " + accepted.size() + " 条采纳建议生成合同修订稿。", Map.of("accepted_issue_count", String.valueOf(accepted.size())));
        return new RedraftResponse(DTOConverter.toContract(contract), DTOConverter.toReview(review), accepted.size());
    }

    public List<HistoryResponse> history(String contractId, Member currentMember) {
        requireContract(contractId, currentMember);
        return DTOConverter.toHistoryList(repository.getHistory(contractId, memberScopeId(currentMember)));
    }

    public FinalizeResponse finalizeContract(String contractId, String status, String operatorName, String comment, Member currentMember) {
        if (!"approved".equals(status) && !"rejected".equals(status)) {
            throw new ApiException(400, "最终审批状态必须为 approved 或 rejected。");
        }
        Map<String, Object> contract = requireContract(contractId, currentMember);
        contract.put("status", status);
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        int historyCount = appendHistory(contractId, currentMember, "final_decision", "完成最终审批",
                operatorName + " 将合同标记为 " + ("approved".equals(status) ? "通过" : "驳回") + (comment != null && !comment.isBlank() ? "。 备注：" + comment : "。"),
                Map.of("status", status, "operator", operatorName));
        return new FinalizeResponse(DTOConverter.toContract(contract), historyCount);
    }

    private Map<String, Object> requireContract(String contractId, Member currentMember) {
        Map<String, Object> contract = repository.getContract(contractId).orElseThrow(() -> new ApiException(404, "Contract not found: " + contractId));
        if (isOwnerRestricted(currentMember) && !Objects.equals(contract.get("owner_username"), currentMember.username())) {
            throw new ApiException(404, "Contract not found: " + contractId);
        }
        return new LinkedHashMap<>(contract);
    }

    private List<Map<String, Object>> visibleContracts(Member currentMember) {
        List<Map<String, Object>> contracts = repository.listContracts();
        if (!isOwnerRestricted(currentMember)) return contracts;
        return contracts.stream().filter(c -> Objects.equals(c.get("owner_username"), currentMember.username())).toList();
    }

    private boolean isOwnerRestricted(Member member) {
        return member != null && "employee".equals(member.role()) && !"legal".equals(member.memberType());
    }

    private int memberScopeId(Member member) {
        return member == null ? 0 : member.id();
    }

    private int appendHistory(String contractId, Member currentMember, String type, String title, String description, Map<String, String> metadata) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("id", "history-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        row.put("type", type);
        row.put("title", title);
        row.put("description", description);
        row.put("createdAt", OffsetDateTime.now());
        row.put("metadata", metadata);
        return repository.appendHistory(contractId, memberScopeId(currentMember), row);
    }

    private Map<String, Object> toContractListItem(Map<String, Object> contract) {
        OffsetDateTime updated = (OffsetDateTime) contract.get("updated_at");
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", contract.get("id"));
        item.put("title", contract.get("title"));
        item.put("type", contract.get("type"));
        item.put("status", contract.get("status"));
        item.put("updatedAt", updated == null ? "" : updated.atZoneSameInstant(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
        item.put("author", contract.get("author"));
        item.put("content", contract.get("content"));
        return item;
    }

    private Map<String, Object> buildStoredReview(String contractId, Map<String, Object> reviewResponse, Map<String, String> previousStatuses) {
        Map<String, Object> summary = (Map<String, Object>) reviewResponse.get("summary");
        List<Map<String, Object>> risks = (List<Map<String, Object>>) reviewResponse.getOrDefault("risks", List.of());
        List<Map<String, Object>> issues = new ArrayList<>();
        int index = 0;
        for (Map<String, Object> risk : risks) {
            index += 1;
            Map<String, Object> issue = new LinkedHashMap<>();
            String rid = asString(risk.get("rule_id"));
            Object startOffset = risk.get("start_offset");
            String id = rid + "-" + (startOffset == null ? index : String.valueOf(startOffset)) + "-" + index;
            issue.put("id", id);
            issue.put("type", mapIssueType(asString(risk.get("risk_domain")), asString(risk.get("severity"))));
            issue.put("severity", risk.get("severity"));
            issue.put("message", risk.get("title"));
            issue.put("suggestion", risk.get("suggestion"));
            String location = (asString(risk.get("clause_no")) + " | " + asString(risk.get("section_title"))).trim();
            issue.put("location", location.isBlank() ? null : location);
            issue.put("status", previousStatuses != null && previousStatuses.containsKey(id) ? previousStatuses.get(id) : "pending");
            issue.put("startIndex", startOffset);
            issue.put("endIndex", risk.get("end_offset"));
            issues.add(issue);
        }
        Map<String, Object> report = (Map<String, Object>) reviewResponse.get("report");
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("contract_id", contractId);
        out.put("summary", summary);
        out.put("report_overview", report.get("overview"));
        out.put("key_findings", report.getOrDefault("key_findings", List.of()));
        out.put("next_actions", report.getOrDefault("next_actions", List.of()));
        out.put("issues", issues);
        out.put("generated_at", OffsetDateTime.parse(asString(report.get("generated_at"))));
        return out;
    }

    private void saveStoredReview(Map<String, Object> stored) {
        repository.saveReview((String) stored.get("contract_id"),
                (Map<String, Object>) stored.get("summary"),
                asString(stored.get("report_overview")),
                (List<String>) stored.get("key_findings"),
                (List<String>) stored.get("next_actions"),
                (List<Map<String, Object>>) stored.get("issues"),
                (OffsetDateTime) stored.get("generated_at"));
    }

    private Map<String, Object> toReviewResult(Map<String, Object> review) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("summary", review.get("summary"));
        out.put("reportOverview", review.get("report_overview"));
        out.put("keyFindings", review.get("key_findings"));
        out.put("nextActions", review.get("next_actions"));
        out.put("issues", review.get("issues"));
        out.put("generatedAt", review.get("generated_at"));
        return out;
    }

    private String mapIssueType(String domain, String severity) {
        if (domain.contains("主体") || domain.contains("合规") || domain.contains("资质")) {
            return "compliance";
        }
        if ("low".equals(severity)) {
            return "suggestion";
        }
        return "risk";
    }

    private String deriveStatus(List<Map<String, Object>> issues) {
        return issues.stream().anyMatch(i -> "pending".equals(i.get("status"))) ? "reviewing" : "approved";
    }

    private Map<String, Object> chatMessage(String role, String content) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", "msg-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        out.put("role", role);
        out.put("content", content);
        out.put("timestamp", OffsetDateTime.now(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern("HH:mm")));
        out.put("created_at", OffsetDateTime.now());
        return out;
    }

    private String stripSuffix(String fileName) {
        if (fileName == null) return "";
        int i = fileName.lastIndexOf('.');
        return i > 0 ? fileName.substring(0, i) : fileName;
    }

    private String asString(Object value) {
        return value == null ? "" : value.toString();
    }
}
