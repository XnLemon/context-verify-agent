package com.example.contract.service.workbench;

import com.example.contract.config.AppProperties;
import com.example.contract.dto.ReviewResultResponse;
import com.example.contract.exception.ApiException;
import com.example.contract.model.Member;
import com.example.contract.repository.WorkbenchRepository;
import com.example.contract.service.agent.AgentGateway;
import com.example.contract.util.Jsons;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionStatus;
import org.springframework.transaction.support.TransactionTemplate;

import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class WorkbenchServiceTest {
    private WorkbenchRepository repository;
    private AgentGateway agentGateway;
    private WorkbenchService service;
    private Member member;

    @BeforeEach
    void setUp() {
        repository = mock(WorkbenchRepository.class);
        agentGateway = mock(AgentGateway.class);
        PlatformTransactionManager ptm = mock(PlatformTransactionManager.class);
        when(ptm.getTransaction(any())).thenReturn(mock(TransactionStatus.class));
        service = new WorkbenchService(repository, agentGateway, new AppProperties(), new TransactionTemplate(ptm));
        member = new Member(1, "u1", "User One", "employee", "legal", true,
                null, "system", "medium", true, OffsetDateTime.now(), null);
        when(repository.appendHistory(anyString(), anyInt(), anyMap())).thenReturn(1);
    }

    @Test
    void decideIssueRejectsInvalidStatus() {
        String contractId = "c-1";
        String issueId = "iss-1";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(reviewWithIssues(List.of(issue(issueId, "pending")))));

        ApiException ex = assertThrows(ApiException.class,
                () -> service.decideIssue(contractId, issueId, Map.of("status", "approved"), member));
        assertEquals(400, ex.getStatus());
        verify(repository, never()).saveReview(anyString(), anyMap(), anyString(), anyList(), anyList(), anyList(), any());
    }

    @Test
    void decideIssueKeepsReviewingWhenUnknownStatusExists() {
        String contractId = "c-2";
        String issueId = "iss-1";
        Map<String, Object> review = reviewWithIssues(new ArrayList<>(List.of(
                issue(issueId, "pending"),
                issue("iss-2", "mystery")
        )));
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(review), Optional.of(review));

        service.decideIssue(contractId, issueId, Map.of("status", "accepted"), member);

        ArgumentCaptor<Map<String, Object>> contractCaptor = ArgumentCaptor.forClass(Map.class);
        verify(repository).saveContract(contractCaptor.capture());
        assertEquals("reviewing", contractCaptor.getValue().get("status"));
    }

    @Test
    void decideIssueApprovesContractWhenAllIssuesResolved() {
        String contractId = "c-4";
        String issueId = "iss-1";
        Map<String, Object> review = reviewWithIssues(new ArrayList<>(List.of(issue(issueId, "pending"))));
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(review), Optional.of(review));

        ReviewResultResponse result = service.decideIssue(contractId, issueId,
                Map.of("status", "accepted"), member);

        assertNotNull(result);
        ArgumentCaptor<Map<String, Object>> contractCaptor = ArgumentCaptor.forClass(Map.class);
        verify(repository).saveContract(contractCaptor.capture());
        assertEquals("approved", contractCaptor.getValue().get("status"));
    }

    @Test
    void chatContractPreservesExistingIssueStatusesAndDefaultsNewToPending() {
        String contractId = "c-3";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        when(repository.getReview(contractId)).thenReturn(Optional.of(reviewWithIssues(List.of(issue("ruleA-10-1", "accepted")))));
        when(agentGateway.chat(anyMap())).thenReturn(Map.of(
                "answer", "ok",
                "review_result", reviewResult()
        ));

        service.chatContract(contractId, Map.of("message", "recheck"), member);

        ArgumentCaptor<List<Map<String, Object>>> issuesCaptor = ArgumentCaptor.forClass(List.class);
        verify(repository).saveReview(eq(contractId), anyMap(), anyString(), anyList(), anyList(), issuesCaptor.capture(), any());

        Map<String, Object> first = issuesCaptor.getValue().stream().filter(i -> "ruleA-10-1".equals(i.get("id"))).findFirst().orElseThrow();
        Map<String, Object> second = issuesCaptor.getValue().stream().filter(i -> "ruleB-20-2".equals(i.get("id"))).findFirst().orElseThrow();
        assertEquals("accepted", first.get("status"));
        assertEquals("pending", second.get("status"));
    }

    @Test
    void chatContractStreamForwardsReasoningActionObservationAndDoneTraceSummary() {
        String contractId = "c-stream-1";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        Map<String, Object> done = new LinkedHashMap<>();
        done.put("intent", "chat");
        done.put("tool_used", "react");
        done.put("answer", "hello world");
        done.put("review_result", null);
        done.put("traceSummary", List.of(Map.of("step", 1, "thought", "x", "action", "query_knowledge", "observation", "y")));
        when(agentGateway.chatStream(anyMap())).thenReturn(List.of(
                new AgentGateway.ChatStreamEvent("reasoning", Jsons.toJson(Map.of("step", 1, "summary", "need external knowledge"))),
                new AgentGateway.ChatStreamEvent("action", Jsons.toJson(Map.of("step", 1, "name", "query_knowledge", "input_preview", "termination clause"))),
                new AgentGateway.ChatStreamEvent("observation", Jsons.toJson(Map.of("step", 1, "action", "query_knowledge", "success", true, "summary", "found 2 refs"))),
                new AgentGateway.ChatStreamEvent("delta", Jsons.toJson(Map.of("delta", "hello "))),
                new AgentGateway.ChatStreamEvent("done", Jsons.toJson(done))
        ).iterator());

        List<AgentGateway.ChatStreamEvent> emitted = new ArrayList<>();
        service.chatContractStream(contractId, Map.of("message", "what is market practice"), member, emitted::add);

        assertEquals("start", emitted.get(0).event());
        assertEquals("reasoning", emitted.get(1).event());
        assertEquals("action", emitted.get(2).event());
        assertEquals("observation", emitted.get(3).event());
        assertEquals("delta", emitted.get(4).event());
        assertEquals("done", emitted.get(5).event());

        Map<String, Object> donePayload = Jsons.toMap(emitted.get(5).dataJson());
        assertEquals("react", donePayload.get("toolUsed"));
        assertEquals("hello world", ((Map<String, Object>) donePayload.get("assistantMessage")).get("content"));
        assertTrue(donePayload.containsKey("traceSummary"));
        assertEquals(1, ((List<?>) donePayload.get("traceSummary")).size());
    }

    @Test
    void chatContractStreamKeepsLegacyDeltaDoneBehaviorWhenOnlyLegacyEvents() {
        String contractId = "c-stream-2";
        when(repository.getContract(contractId)).thenReturn(Optional.of(contract(contractId)));
        Map<String, Object> done = new LinkedHashMap<>();
        done.put("intent", "chat");
        done.put("tool_used", "legacy_stream");
        done.put("review_result", null);
        when(agentGateway.chatStream(anyMap())).thenReturn(List.of(
                new AgentGateway.ChatStreamEvent("delta", Jsons.toJson(Map.of("delta", "A"))),
                new AgentGateway.ChatStreamEvent("delta", Jsons.toJson(Map.of("delta", "B"))),
                new AgentGateway.ChatStreamEvent("done", Jsons.toJson(done))
        ).iterator());

        List<AgentGateway.ChatStreamEvent> emitted = new ArrayList<>();
        service.chatContractStream(contractId, Map.of("message", "ping"), member, emitted::add);

        assertEquals("start", emitted.get(0).event());
        assertEquals("delta", emitted.get(1).event());
        assertEquals("delta", emitted.get(2).event());
        assertEquals("done", emitted.get(3).event());

        Map<String, Object> donePayload = Jsons.toMap(emitted.get(3).dataJson());
        Map<String, Object> assistant = (Map<String, Object>) donePayload.get("assistantMessage");
        assertEquals("AB", assistant.get("content"));
        assertFalse(donePayload.containsKey("traceSummary"));
    }

    private Map<String, Object> contract(String id) {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("id", id);
        out.put("title", "t");
        out.put("type", "采购合同");
        out.put("status", "pending");
        out.put("author", "a");
        out.put("owner_username", "u1");
        out.put("content", "contract text");
        out.put("source_file_name", "a.docx");
        out.put("created_at", OffsetDateTime.now().minusDays(1));
        out.put("updated_at", OffsetDateTime.now().minusHours(1));
        return out;
    }

    private Map<String, Object> reviewWithIssues(List<Map<String, Object>> issues) {
        return new LinkedHashMap<>(Map.of(
                "contract_id", "c",
                "summary", Map.of("contract_type", "采购合同", "overall_risk", "medium"),
                "report_overview", "overview",
                "key_findings", List.of(),
                "next_actions", List.of(),
                "issues", issues,
                "generated_at", OffsetDateTime.now()
        ));
    }

    private Map<String, Object> issue(String id, String status) {
        return new LinkedHashMap<>(Map.of(
                "id", id,
                "type", "risk",
                "severity", "high",
                "message", "m",
                "suggestion", "s",
                "location", "loc",
                "status", status,
                "startIndex", 1,
                "endIndex", 2
        ));
    }

    private Map<String, Object> reviewResult() {
        return new LinkedHashMap<>(Map.of(
                "summary", Map.of("contract_type", "采购合同", "overall_risk", "high"),
                "risks", List.of(
                        Map.of("rule_id", "ruleA", "start_offset", 10, "end_offset", 20, "risk_domain", "合规", "severity", "high",
                                "title", "A", "suggestion", "fix A", "clause_no", "1", "section_title", "S1"),
                        Map.of("rule_id", "ruleB", "start_offset", 20, "end_offset", 30, "risk_domain", "履约", "severity", "medium",
                                "title", "B", "suggestion", "fix B", "clause_no", "2", "section_title", "S2")
                ),
                "report", Map.of("overview", "ov", "key_findings", List.of(), "next_actions", List.of(), "generated_at", OffsetDateTime.now().toString())
        ));
    }
}
