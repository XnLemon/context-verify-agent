package com.example.contract.dto;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

public final class DTOConverter {
    private DTOConverter() {}

    private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

    public static ContractResponse toContract(Map<String, Object> c) {
        OffsetDateTime updated = (OffsetDateTime) c.get("updated_at");
        return new ContractResponse(
                asStr(c.get("id")),
                asStr(c.get("title")),
                asStr(c.get("type")),
                asStr(c.get("status")),
                updated == null ? "" : updated.atZoneSameInstant(ZoneOffset.UTC).format(DTF),
                asStr(c.get("author")),
                asStr(c.get("content"))
        );
    }

    @SuppressWarnings("unchecked")
    public static ReviewResultResponse toReview(Map<String, Object> r) {
        List<Map<String, Object>> rawIssues = (List<Map<String, Object>>) r.getOrDefault("issues", List.of());
        return new ReviewResultResponse(
                (Map<String, Object>) r.get("summary"),
                asStr(r.get("report_overview")),
                (List<String>) r.getOrDefault("key_findings", List.of()),
                (List<String>) r.getOrDefault("next_actions", List.of()),
                rawIssues.stream().map(DTOConverter::toIssue).toList(),
                r.get("generated_at") == null ? "" : r.get("generated_at").toString()
        );
    }

    public static IssueResponse toIssue(Map<String, Object> issue) {
        return new IssueResponse(
                asStr(issue.get("id")),
                asStr(issue.get("type")),
                asStr(issue.get("severity")),
                asStr(issue.get("message")),
                asStr(issue.get("suggestion")),
                asStr(issue.get("location")),
                asStr(issue.get("status")),
                (Integer) issue.get("startIndex"),
                (Integer) issue.get("endIndex")
        );
    }

    public static ChatMessageResponse toChatMessage(Map<String, Object> m) {
        return new ChatMessageResponse(
                asStr(m.get("id")),
                asStr(m.get("role")),
                asStr(m.get("content")),
                asStr(m.get("timestamp")),
                m.get("created_at") == null ? "" : m.get("created_at").toString()
        );
    }

    @SuppressWarnings("unchecked")
    public static HistoryResponse toHistory(Map<String, Object> h) {
        return new HistoryResponse(
                asStr(h.get("id")),
                asStr(h.get("type")),
                asStr(h.get("title")),
                asStr(h.get("description")),
                h.get("createdAt") == null ? "" : h.get("createdAt").toString(),
                (Map<String, String>) h.getOrDefault("metadata", Map.of())
        );
    }

    public static MemberResponse toMember(Map<String, Object> m) {
        return new MemberResponse(
                toInt(m.get("id")),
                asStr(m.get("username")),
                asStr(m.get("display_name")),
                asStr(m.get("role")),
                asStr(m.get("member_type")),
                Boolean.parseBoolean(String.valueOf(m.get("is_active"))),
                asStr(m.get("avatar_url")),
                asStr(m.get("theme_preference")),
                asStr(m.get("font_scale")),
                Boolean.parseBoolean(String.valueOf(m.get("notify_enabled"))),
                m.get("last_login_at") == null ? null : m.get("last_login_at").toString(),
                m.get("created_at") == null ? "" : m.get("created_at").toString()
        );
    }

    public static List<ContractResponse> toContractList(List<Map<String, Object>> contracts) {
        return contracts.stream().map(DTOConverter::toContract).toList();
    }

    public static List<ChatMessageResponse> toChatMessageList(List<Map<String, Object>> messages) {
        return messages.stream().map(DTOConverter::toChatMessage).toList();
    }

    public static List<HistoryResponse> toHistoryList(List<Map<String, Object>> history) {
        return history.stream().map(DTOConverter::toHistory).toList();
    }

    private static String asStr(Object v) {
        return v == null ? "" : v.toString();
    }

    private static int toInt(Object v) {
        if (v instanceof Number n) return n.intValue();
        return 0;
    }
}
