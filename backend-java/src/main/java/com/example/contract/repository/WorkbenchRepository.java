package com.example.contract.repository;

import com.example.contract.util.Jsons;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Repository
public class WorkbenchRepository {
    private final JdbcTemplate jdbc;

    public WorkbenchRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public List<Map<String, Object>> listContracts() {
        return jdbc.query("select * from contracts", this::toContract);
    }

    public Optional<Map<String, Object>> getContract(String contractId) {
        List<Map<String, Object>> rows = jdbc.query("select * from contracts where id=?", this::toContract, contractId);
        return rows.stream().findFirst();
    }

    public void saveContract(Map<String, Object> contract) {
        jdbc.update("""
                insert into contracts(id,title,type,status,author,owner_username,content,source_file_name,created_at,updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict (id) do update set title=excluded.title,type=excluded.type,status=excluded.status,author=excluded.author,
                owner_username=excluded.owner_username,content=excluded.content,source_file_name=excluded.source_file_name,
                updated_at=excluded.updated_at
                """,
                contract.get("id"), contract.get("title"), contract.get("type"), contract.get("status"), contract.get("author"),
                contract.get("owner_username"), contract.get("content"), contract.get("source_file_name"),
                contract.get("created_at"), contract.get("updated_at")
        );
    }

    public Optional<Map<String, Object>> getReview(String contractId) {
        List<Map<String, Object>> rows = jdbc.query("select * from review_records where contract_id=?", (rs, i) -> {
            Map<String, Object> summary = Jsons.toMap(rs.getString("summary"));
            List<Map<String, Object>> issues = jdbc.query("select * from review_issues where review_id=? order by id", this::toIssue, rs.getInt("id"));
            return Map.of(
                    "contract_id", rs.getString("contract_id"),
                    "summary", summary,
                    "report_overview", rs.getString("report_overview"),
                    "key_findings", toStringList(rs.getObject("key_findings")),
                    "next_actions", toStringList(rs.getObject("next_actions")),
                    "issues", issues,
                    "generated_at", rs.getObject("generated_at", OffsetDateTime.class)
            );
        }, contractId);
        return rows.stream().findFirst();
    }

    public void saveReview(String contractId, Map<String, Object> summary, String reportOverview, List<String> keyFindings, List<String> nextActions,
                           List<Map<String, Object>> issues, OffsetDateTime generatedAt) {
        Integer reviewId = jdbc.queryForObject("""
                insert into review_records(contract_id,summary,report_overview,key_findings,next_actions,generated_at)
                values (?, cast(? as jsonb), ?, cast(? as jsonb), cast(? as jsonb), ?)
                on conflict(contract_id) do update set summary=excluded.summary,report_overview=excluded.report_overview,
                key_findings=excluded.key_findings,next_actions=excluded.next_actions,generated_at=excluded.generated_at
                returning id
                """, Integer.class,
                contractId, Jsons.toJson(summary), reportOverview, Jsons.toJson(keyFindings), Jsons.toJson(nextActions), generatedAt);

        jdbc.update("delete from review_issues where review_id=?", reviewId);
        for (Map<String, Object> issue : issues) {
            jdbc.update("""
                    insert into review_issues(review_id,contract_id,issue_id,type,severity,message,suggestion,location,status,start_index,end_index)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    reviewId, contractId,
                    issue.get("id"), issue.get("type"), issue.get("severity"), issue.get("message"), issue.get("suggestion"),
                    issue.get("location"), issue.get("status"), issue.get("startIndex"), issue.get("endIndex")
            );
        }
    }

    public List<Map<String, Object>> getChatMessages(String contractId, int memberId) {
        return jdbc.query("""
                select m.* from chat_messages m
                join chat_threads t on t.id=m.thread_id
                where t.contract_id=? and t.member_id=?
                order by m.id
                """, this::toChatMessage, contractId, memberId);
    }

    public void saveChatMessages(String contractId, int memberId, List<Map<String, Object>> messages) {
        Integer threadId = jdbc.query("select id from chat_threads where contract_id=? and member_id=?", (rs, i) -> rs.getInt("id"), contractId, memberId)
                .stream().findFirst().orElse(null);
        if (threadId == null) {
            threadId = jdbc.queryForObject("insert into chat_threads(contract_id,member_id,created_at,updated_at) values (?, ?, now(), now()) returning id", Integer.class, contractId, memberId);
        } else {
            jdbc.update("update chat_threads set updated_at=now() where id=?", threadId);
        }
        jdbc.update("delete from chat_messages where thread_id=?", threadId);
        for (Map<String, Object> m : messages) {
            jdbc.update("insert into chat_messages(thread_id,contract_id,msg_id,role,content,timestamp,created_at) values (?, ?, ?, ?, ?, ?, ?)",
                    threadId, contractId, m.get("id"), m.get("role"), m.get("content"), m.get("timestamp"), m.get("created_at"));
        }
    }

    public List<Map<String, Object>> getHistory(String contractId, int memberId) {
        return jdbc.query("select * from history_logs where contract_id=? and member_id=? order by created_at desc", this::toHistory, contractId, memberId);
    }

    public int appendHistory(String contractId, int memberId, Map<String, Object> history) {
        jdbc.update("insert into history_logs(contract_id,member_id,event_id,type,title,description,created_at,metadata_json) values (?, ?, ?, ?, ?, ?, ?, cast(? as jsonb))",
                contractId, memberId, history.get("id"), history.get("type"), history.get("title"), history.get("description"), history.get("createdAt"), Jsons.toJson(history.get("metadata")));
        Integer count = jdbc.queryForObject("select count(*) from history_logs where contract_id=? and member_id=?", Integer.class, contractId, memberId);
        return count == null ? 0 : count;
    }

    public String createContract(String title, String type, String status, String author, String ownerUsername, String content, String sourceFileName, String id) {
        jdbc.update("insert into contracts(id,title,type,status,author,owner_username,content,source_file_name,created_at,updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, now(), now())",
                id, title, type, status, author, ownerUsername, content, sourceFileName);
        return id;
    }

    private Map<String, Object> toContract(ResultSet rs, int i) throws SQLException {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", rs.getString("id"));
        out.put("title", rs.getString("title"));
        out.put("type", rs.getString("type"));
        out.put("status", rs.getString("status"));
        out.put("author", rs.getString("author"));
        out.put("owner_username", rs.getString("owner_username"));
        out.put("content", rs.getString("content"));
        out.put("source_file_name", rs.getString("source_file_name"));
        out.put("created_at", rs.getObject("created_at", OffsetDateTime.class));
        out.put("updated_at", rs.getObject("updated_at", OffsetDateTime.class));
        return out;
    }

    private Map<String, Object> toIssue(ResultSet rs, int i) throws SQLException {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", rs.getString("issue_id"));
        out.put("type", rs.getString("type"));
        out.put("severity", rs.getString("severity"));
        out.put("message", rs.getString("message"));
        out.put("suggestion", rs.getString("suggestion"));
        out.put("location", rs.getString("location"));
        out.put("status", rs.getString("status"));
        out.put("startIndex", rs.getObject("start_index"));
        out.put("endIndex", rs.getObject("end_index"));
        return out;
    }

    private Map<String, Object> toChatMessage(ResultSet rs, int i) throws SQLException {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", rs.getString("msg_id"));
        out.put("role", rs.getString("role"));
        out.put("content", rs.getString("content"));
        out.put("timestamp", rs.getString("timestamp"));
        out.put("created_at", rs.getObject("created_at", OffsetDateTime.class));
        return out;
    }

    private Map<String, Object> toHistory(ResultSet rs, int i) throws SQLException {
        Map<String, Object> out = new java.util.LinkedHashMap<>();
        out.put("id", rs.getString("event_id"));
        out.put("type", rs.getString("type"));
        out.put("title", rs.getString("title"));
        out.put("description", rs.getString("description"));
        out.put("createdAt", rs.getObject("created_at", OffsetDateTime.class));
        out.put("metadata", Jsons.toMap(rs.getString("metadata_json")));
        return out;
    }

    private List<String> toStringList(Object jsonValue) {
        if (jsonValue == null) {
            return List.of();
        }
        if (jsonValue instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        String raw = String.valueOf(jsonValue);
        try {
            if (!raw.isBlank() && raw.trim().startsWith("[")) {
                return Jsons.MAPPER.readValue(raw, Jsons.MAPPER.getTypeFactory().constructCollectionType(List.class, String.class));
            }
            if (!raw.isBlank() && raw.trim().startsWith("{")) {
                // Backward-compatible fallback for malformed historical values.
                return List.of(raw);
            }
        } catch (Exception ignored) {
            return List.of(raw);
        }
        return List.of(raw);
    }
}
