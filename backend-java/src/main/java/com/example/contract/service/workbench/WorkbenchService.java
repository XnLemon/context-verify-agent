package com.example.contract.service.workbench;

import com.example.contract.config.AppProperties;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.WorkbenchRepository;
import com.example.contract.service.agent.AgentGateway;
import com.example.contract.util.Jsons;
import org.springframework.stereotype.Service;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.function.Consumer;

@Service
public class WorkbenchService {
    private static final Set<String> VALID_ISSUE_STATUSES = Set.of("pending", "accepted", "rejected");
    private final WorkbenchRepository repository;
    private final AgentGateway agentGateway;
    private final AppProperties props;

    public WorkbenchService(WorkbenchRepository repository, AgentGateway agentGateway, AppProperties props) {
        this.repository = repository;
        this.agentGateway = agentGateway;
        this.props = props;
    }

    public Map<String, Object> summary(Member currentMember) {
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
        return Map.of(
                "pendingCount", pendingCount,
                "complianceRate", compliance,
                "highRiskCount", highRisk,
                "averageReviewDurationHours", 0.0,
                "totalContracts", total
        );
    }

    public Map<String, Object> listContracts(String status, String search, Member currentMember) {
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
        return Map.of("items", items, "total", items.size());
    }

    public Map<String, Object> contractDetail(String contractId, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("contract", toContractListItem(contract));
        repository.getReview(contractId).ifPresent(review -> out.put("latestReview", toReviewResult(review)));
        int memberId = memberScopeId(currentMember);
        out.put("chatMessages", repository.getChatMessages(contractId, memberId));
        if (!out.containsKey("latestReview")) {
            out.put("latestReview", null);
        }
        return out;
    }

    public Map<String, Object> importContract(String fileName, byte[] content, String contractType, String author, String ownerUsername, Member currentMember) {
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
        Map<String, Object> contract = requireContract(id, currentMember);
        return Map.of("contract", toContractListItem(contract));
    }

    public Map<String, Object> updateContractContent(String contractId, String content, Member currentMember) {
        if (content == null || content.isBlank()) {
            throw new ApiException(400, "合同正文不能为空。");
        }
        Map<String, Object> contract = requireContract(contractId, currentMember);
        contract.put("content", content);
        contract.put("status", "pending");
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        appendHistory(contractId, currentMember, "manual_edit", "手动编辑合同", "已手动更新合同正文，建议重新执行扫描。", Map.of("content_length", String.valueOf(content.length())));
        return Map.of("contract", toContractListItem(contract));
    }

    public Map<String, Object> scanContract(String contractId, String contractType, String ourSide, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> review = agentGateway.reviewText((String) contract.get("content"), contractType != null ? contractType : (String) contract.get("type"), ourSide);
        Map<String, Object> stored = buildStoredReview(contractId, review, null);
        saveStoredReview(stored);
        contract.put("type", ((Map<String, Object>) review.get("summary")).get("contract_type"));
        contract.put("status", deriveStatus((List<Map<String, Object>>) stored.get("issues")));
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        int historyCount = appendHistory(contractId, currentMember, "scan", "完成合同扫描", "已完成扫描。", Map.of("overall_risk", String.valueOf(((Map<String, Object>) review.get("summary")).get("overall_risk"))));
        return Map.of(
                "contract", toContractListItem(contract),
                "latestReview", toReviewResult(stored),
                "historyCount", historyCount
        );
    }

    public Map<String, Object> chatContract(String contractId, Map<String, Object> payload, Member currentMember) {
        ChatContext chatContext = prepareChatContext(contractId, payload, currentMember);
        Map<String, Object> chat = agentGateway.chat(chatContext.chatPayload());
        return finalizeChat(contractId, chatContext, chat, currentMember, null);
    }

    public void chatContractStream(
            String contractId,
            Map<String, Object> payload,
            Member currentMember,
            Consumer<AgentGateway.ChatStreamEvent> eventConsumer
    ) {
        ChatContext chatContext = prepareChatContext(contractId, payload, currentMember);
        Map<String, Object> streamAssistant = chatMessage("assistant", "");
        eventConsumer.accept(new AgentGateway.ChatStreamEvent(
                "start",
                Jsons.toJson(Map.of(
                        "id", asString(streamAssistant.get("id")),
                        "timestamp", asString(streamAssistant.get("timestamp"))
                ))
        ));

        StringBuilder streamedAnswer = new StringBuilder();
        Map<String, Object> donePayload = null;
        Iterator<AgentGateway.ChatStreamEvent> events = agentGateway.chatStream(chatContext.chatPayload());

        while (events.hasNext()) {
            AgentGateway.ChatStreamEvent event = events.next();
            String eventName = event.event() == null ? "" : event.event();
            if ("delta".equals(eventName)) {
                Map<String, Object> data = parseEventData(event.dataJson());
                streamedAnswer.append(asString(data.get("delta")));
                eventConsumer.accept(event);
                continue;
            }
            if ("done".equals(eventName)) {
                donePayload = Jsons.toMap(event.dataJson());
                continue;
            }
            if ("error".equals(eventName)) {
                eventConsumer.accept(event);
                return;
            }
        }

        if (donePayload == null) {
            donePayload = new LinkedHashMap<>();
            donePayload.put("intent", "chat");
            donePayload.put("tool_used", "chat_stream_fallback");
            donePayload.put("answer", streamedAnswer.toString());
            donePayload.put("review_result", null);
        }

        Map<String, Object> finalPayload = finalizeChat(contractId, chatContext, donePayload, currentMember, streamAssistant);
        eventConsumer.accept(new AgentGateway.ChatStreamEvent("done", Jsons.toJson(finalPayload)));
    }

    private ChatContext prepareChatContext(String contractId, Map<String, Object> payload, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        int memberId = memberScopeId(currentMember);
        List<Map<String, Object>> messages = new ArrayList<>();
        Object payloadMsgs = payload.get("messages");
        if (payloadMsgs instanceof List<?> m && !m.isEmpty()) {
            for (Object item : m) {
                messages.add((Map<String, Object>) item);
            }
        } else {
            messages.addAll(repository.getChatMessages(contractId, memberId));
        }

        String message = asString(payload.get("message"));
        if (!message.isBlank()) {
            messages.add(chatMessage("user", message));
        }
        if (messages.isEmpty()) {
            throw new ApiException(400, "At least one user message is required.");
        }

        Map<String, Object> chatPayload = new LinkedHashMap<>();
        chatPayload.put("messages", messages.stream().map(m -> Map.of("role", m.get("role"), "content", m.get("content"))).toList());
        chatPayload.put("contract_text", contract.get("content"));
        chatPayload.put("contract_type", payload.getOrDefault("contract_type", contract.get("type")));
        chatPayload.put("our_side", payload.getOrDefault("our_side", "甲方"));

        return new ChatContext(contract, memberId, messages, chatPayload);
    }

    private Map<String, Object> finalizeChat(
            String contractId,
            ChatContext chatContext,
            Map<String, Object> chat,
            Member currentMember,
            Map<String, Object> prebuiltAssistant
    ) {
        String answer = asString(chat.get("answer"));
        Map<String, Object> assistant = prebuiltAssistant == null ? chatMessage("assistant", answer) : new LinkedHashMap<>(prebuiltAssistant);
        assistant.put("role", "assistant");
        assistant.put("content", answer);
        if (asString(assistant.get("id")).isBlank()) {
            assistant.put("id", "msg-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12));
        }
        if (asString(assistant.get("timestamp")).isBlank()) {
            assistant.put("timestamp", OffsetDateTime.now(ZoneOffset.UTC).format(DateTimeFormatter.ofPattern("HH:mm")));
        }
        assistant.put("created_at", OffsetDateTime.now());

        chatContext.messages().add(assistant);
        repository.saveChatMessages(contractId, chatContext.memberId(), chatContext.messages());

        Object reviewObj = chat.get("review_result");
        Object latestReview = null;
        if (reviewObj instanceof Map<?, ?> reviewResult) {
            Map<String, String> previousStatuses = repository.getReview(contractId)
                    .map(r -> (List<Map<String, Object>>) r.get("issues"))
                    .orElse(List.of())
                    .stream()
                    .filter(i -> i.get("id") != null)
                    .collect(java.util.stream.Collectors.toMap(
                            i -> String.valueOf(i.get("id")),
                            i -> asString(i.get("status")),
                            (a, b) -> a,
                            LinkedHashMap::new
                    ));
            Map<String, Object> stored = buildStoredReview(contractId, (Map<String, Object>) reviewResult, previousStatuses);
            saveStoredReview(stored);
            chatContext.contract().put("status", deriveStatus((List<Map<String, Object>>) stored.get("issues")));
            chatContext.contract().put("updated_at", OffsetDateTime.now());
            repository.saveContract(chatContext.contract());
            latestReview = toReviewResult(stored);
        }

        appendHistory(
                contractId,
                currentMember,
                "chat",
                "新增 AI 对话",
                asString(chatContext.messages().get(chatContext.messages().size() - 2).get("content")),
                Map.of("tool_used", asString(chat.get("tool_used")))
        );

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("intent", chat.getOrDefault("intent", "chat"));
        out.put("toolUsed", chat.getOrDefault("tool_used", "chat"));
        out.put("assistantMessage", assistant);
        out.put("messages", chatContext.messages());
        out.put("latestReview", latestReview);
        return out;
    }

    private Map<String, Object> parseEventData(String dataJson) {
        if (dataJson == null || dataJson.isBlank()) {
            return Map.of();
        }
        return Jsons.toMap(dataJson);
    }

    private record ChatContext(
            Map<String, Object> contract,
            int memberId,
            List<Map<String, Object>> messages,
            Map<String, Object> chatPayload
    ) {}

    public Map<String, Object> decideIssue(String contractId, String issueId, Map<String, Object> payload, Member currentMember) {
        Map<String, Object> contract = requireContract(contractId, currentMember);
        Map<String, Object> review = repository.getReview(contractId).orElseThrow(() -> new ApiException(404, "Contract review not found: " + contractId));
        String status = asString(payload.get("status"));
        if (!VALID_ISSUE_STATUSES.contains(status)) {
            throw new ApiException(400, "Issue status must be one of pending, accepted, rejected.");
        }
        boolean autoRedraft = parseBoolean(payload.get("auto_redraft"));
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
        boolean autoRedraftAttempted = false;
        boolean autoRedraftSucceeded = false;
        String autoRedraftError = null;
        if ("accepted".equals(status) && autoRedraft) {
            autoRedraftAttempted = true;
            String ourSide = asString(payload.get("our_side"));
            if (ourSide.isBlank()) {
                ourSide = "鐢叉柟";
            }
            try {
                redraftContract(contractId, ourSide, currentMember);
                autoRedraftSucceeded = true;
            } catch (Exception e) {
                autoRedraftError = e.getClass().getSimpleName();
                appendHistory(contractId, currentMember, "redraft_failed", "Auto redraft failed",
                        "Auto redraft failed but issue decision was saved.",
                        Map.of("issue_id", issueId, "error", autoRedraftError));
            }
        }
        Map<String, Object> response = new LinkedHashMap<>(toReviewResult(repository.getReview(contractId).orElseThrow()));
        if (autoRedraftAttempted) {
            Map<String, Object> autoRedraftResult = new LinkedHashMap<>();
            autoRedraftResult.put("attempted", true);
            autoRedraftResult.put("succeeded", autoRedraftSucceeded);
            if (!autoRedraftSucceeded) {
                autoRedraftResult.put("error", autoRedraftError == null ? "UnknownError" : autoRedraftError);
            }
            response.put("autoRedraft", autoRedraftResult);
        }
        return response;
    }

    public Map<String, Object> redraftContract(String contractId, String ourSide, Member currentMember) {
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
        return Map.of("contract", toContractListItem(contract), "latestReview", toReviewResult(review), "acceptedIssueCount", accepted.size());
    }

    public List<Map<String, Object>> history(String contractId, Member currentMember) {
        requireContract(contractId, currentMember);
        return repository.getHistory(contractId, memberScopeId(currentMember));
    }

    public Map<String, Object> finalizeContract(String contractId, String status, String operatorName, String comment, Member currentMember) {
        if (!"approved".equals(status) && !"rejected".equals(status)) {
            throw new ApiException(400, "最终审批状态必须为 approved 或 rejected。");
        }
        Map<String, Object> contract = requireContract(contractId, currentMember);
        contract.put("status", status);
        contract.put("updated_at", OffsetDateTime.now());
        repository.saveContract(contract);
        int historyCount = appendHistory(contractId, currentMember, "final_decision", "完成最终审批",
                operatorName + " 将合同标记为 " + ("approved".equals(status) ? "通过" : "驳回") + (comment != null && !comment.isBlank() ? "。备注：" + comment : "。"),
                Map.of("status", status, "operator", operatorName));
        return Map.of("contract", toContractListItem(contract), "historyCount", historyCount);
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
        if (domain.contains("涓讳綋") || domain.contains("鍚堣") || domain.contains("璧勮川")) {
            return "compliance";
        }
        if ("low".equals(severity)) {
            return "suggestion";
        }
        return "risk";
    }

    private String deriveStatus(List<Map<String, Object>> issues) {
        if (issues == null || issues.isEmpty()) {
            return "approved";
        }
        for (Map<String, Object> issue : issues) {
            String issueStatus = asString(issue.get("status"));
            if (!VALID_ISSUE_STATUSES.contains(issueStatus) || "pending".equals(issueStatus)) {
                return "reviewing";
            }
        }
        return "approved";
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

    private boolean parseBoolean(Object value) {
        if (value instanceof Boolean b) {
            return b;
        }
        return value != null && Boolean.parseBoolean(value.toString());
    }
}






